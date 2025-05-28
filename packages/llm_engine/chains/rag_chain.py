"""
Async RAG chain using LangChain, FastEmbed, and Pinecone.
- Pinecone vector store integration (768 dims, cosine)
- Exponential backoff for API errors
- Source citation with cosine similarity threshold 0.75
"""

import asyncio
import os
from typing import Any, Dict, List

from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from packages.shared.models import SourceDocument, SuggestedResponse, TicketContext

from ..embeddings import get_fastembed_model
from ..vector_store import query_pinecone

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "support101")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
SIMILARITY_THRESHOLD = 0.75

RAG_PROMPT_TEMPLATE = (
    "You are a helpful customer support documentation assistant.\n"
    "Your task is to answer the user's question clearly and concisely based *only* on the provided "
    "documentation context.\n"
    "If the context does not contain the answer, state that you cannot answer based on the "
    "provided documents.\n"
    # Line break for flake8 E501 compliance
    "Include relevant examples from the context if available.\n"
    "When referencing specific content, cite the source URLs.\n"
    "Keep responses natural, conversational, and formatted for easy readability.\n\n"
    "Provided Documentation Context:\n{context_str}\n\nUser Question: {question}\n\nAnswer:"
)


class RAGChain:
    """
    Retrieval-Augmented Generation (RAG) chain for customer support using LangChain,
    FastEmbed, and Pinecone.
    Handles context retrieval, LLM calls, source citation,
    and robust error handling.
    """

    def __init__(self) -> None:
        self.embedding_model = get_fastembed_model()
        self.llm = ChatOpenAI(model=os.getenv("LLM_MODEL_NAME", "gpt-4o"), temperature=0.3)
        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        self.chain = (
            RunnablePassthrough.assign(
                context_str=RunnableLambda(self._retrieve_and_format_context)
            )
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        self.retrieved_sources: List[SourceDocument] = []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(Exception),
    )
    async def _safe_query_pinecone(self, question: str, top_k: int = 3) -> List[dict]:
        """
        Query Pinecone vector store with exponential backoff and error masking.
        """
        try:
            return await query_pinecone(
                query_text=question,
                embedding_model=self.embedding_model,
                top_k=top_k,
            )
        except Exception as e:
            # Mask API key if present in error
            msg = str(e).replace(os.getenv("PINECONE_API_KEY", "***"), "***")
            return self._unified_error(
                error_type="vector_store_error",
                message=f"Vector store error: {msg}",
                retryable=True,
                doc_url="https://api.support101/errors#E500",
            )

    async def _retrieve_and_format_context(self, input_data: Dict[str, Any]) -> str:
        """
        Retrieve relevant context from Pinecone and format for prompt.
        Applies cosine similarity threshold and records citations.
        """
        question: str = input_data["question"]
        try:
            matches = await self._safe_query_pinecone(question, top_k=5)
        except Exception as e:
            return self._unified_error(
                error_type="vector_store_error",
                message=f"Failed to retrieve context: {e}",
                retryable=True,
                doc_url="https://api.support101/errors#E500",
            )
        context_chunks = []
        self.retrieved_sources.clear()
        for match in matches:
            score = match.get("score", 0.0)
            if score >= SIMILARITY_THRESHOLD:
                meta = match.get("metadata", {})
                source = SourceDocument(
                    url=meta.get("source_url", ""),
                    excerpt=meta.get("text", "")[:256],
                    confidence=score,
                    last_updated=meta.get("last_updated", ""),
                )
                self.retrieved_sources.append(source)
                context_chunks.append(f"[{source.url}] {source.excerpt}")
        if not context_chunks:
            return "No relevant documentation found."
        return "\n---\n".join(context_chunks)

    async def generate(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a support response using RAG.
        Returns answer and citations, or unified error on failure.
        """
        try:
            result = await asyncio.wait_for(
                self.chain.ainvoke({"question": question, **kwargs}), timeout=30
            )
            citations = [
                {
                    "url": s.url,
                    "excerpt": s.excerpt,
                    "confidence": s.confidence,
                    "last_updated": s.last_updated,
                }
                for s in self.retrieved_sources
            ]
            return {
                "reply": result,
                "sources": citations,
            }
        except asyncio.TimeoutError:
            return self._unified_error(
                error_type="llm_timeout",
                message="LLM response exceeded 30s threshold",
                retryable=True,
                doc_url="https://api.support101/errors#E429",
            )
        except Exception as e:
            msg = str(e).replace(os.getenv("OPENAI_API_KEY", "***"), "***")
            return self._unified_error(
                error_type="llm_engine_error",
                message=f"LLM engine error: {msg}",
                retryable=True,
                doc_url="https://api.support101/errors#E500",
            )

    def _unified_error(
        self, error_type: str, message: str, retryable: bool, doc_url: str
    ) -> Dict[str, Any]:
        """
        Return a unified error response per API spec, masking any sensitive data.
        """
        return {
            "error_type": error_type,
            "message": message,
            "retryable": retryable,
            "documentation": doc_url,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(Exception),
    )
    async def invoke(self, ticket_context: TicketContext) -> SuggestedResponse:
        self.retrieved_sources = []
        question_to_llm = ticket_context.user_query or ticket_context.content or ""
        try:
            response_text = await asyncio.wait_for(
                self.chain.ainvoke({"question": question_to_llm}), timeout=30
            )
        except asyncio.TimeoutError:
            return SuggestedResponse(
                reply_text=None,
                sources=[],
                error={
                    "error_type": "llm_timeout",
                    "message": "LLM response exceeded 30s threshold",
                    "retryable": True,
                    "documentation": "https://api.support101/errors#E429",
                },
            )
        return SuggestedResponse(reply_text=response_text, sources=self.retrieved_sources)
