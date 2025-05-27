"""
Async RAG chain using LangChain, FastEmbed, and Pinecone.
- Pinecone vector store integration (768 dims, cosine)
- Exponential backoff for API errors
- Source citation with cosine similarity threshold 0.75
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

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

RAG_PROMPT_TEMPLATE = """You are a helpful customer support documentation assistant.\nYour task is to answer the user's question clearly and concisely based *only* on the provided documentation context.\nIf the context does not contain the answer, state that you cannot answer based on the provided documents.\nInclude relevant examples from the context if available.\nWhen referencing specific content, cite the source URLs.\nKeep responses natural, conversational, and formatted for easy readability.\n\nProvided Documentation Context:\n{context_str}\n\nUser Question: {question}\n\nAnswer:"""


class RAGChain:
    def __init__(self):
        self.embedding_model = get_fastembed_model()
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL_NAME", "gpt-4o"), temperature=0.3
        )
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
        return await query_pinecone(
            query_text=question, embedding_model=self.embedding_model, top_k=top_k
        )

    async def _retrieve_and_format_context(self, input_data: Dict[str, Any]) -> str:
        question = input_data["question"]
        top_k = input_data.get("top_k", 3)
        search_results_raw = await self._safe_query_pinecone(question, top_k)
        self.retrieved_sources = []
        context_parts = []
        if not search_results_raw:
            return "No relevant documents found in the knowledge base."
        for result_raw in search_results_raw:
            payload_data = result_raw.get("metadata", {})
            content = payload_data.get("text", "")
            url = payload_data.get("source_url", "Unknown URL")
            title = payload_data.get("title", "")
            score = result_raw.get("score", 0.0)
            if content and score >= SIMILARITY_THRESHOLD:
                context_parts.append(
                    f"Source URL: {url}\nTitle: {title}\nContent:\n{content}\n---"
                )
                self.retrieved_sources.append(
                    SourceDocument(url=url, title=title, score=score)
                )
        if not context_parts:
            return "No relevant documents found with content in the knowledge base above similarity threshold."
        return "\n\n".join(context_parts)

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
        return SuggestedResponse(
            reply_text=response_text, sources=self.retrieved_sources
        )
