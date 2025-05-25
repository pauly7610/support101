import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain_core.messages import AIMessage, HumanMessage

from packages.shared.models import TicketContext, SuggestedResponse, SourceDocument, QueryResult, DocumentPayload
from .embeddings import get_fastembed_model, get_huggingface_embedding_model
from .vector_store import query_pinecone
from fastembed import TextEmbedding as FastEmbedModelType

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o")

def get_llm():
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set for LLM initialization.")
    return ChatOpenAI(model=LLM_MODEL_NAME, temperature=0.3)

RAG_PROMPT_TEMPLATE = """You are a helpful customer support documentation assistant.
Your task is to answer the user's question clearly and concisely based *only* on the provided documentation context.
If the context does not contain the answer, state that you cannot answer based on the provided documents.
Include relevant examples from the context if available.
When referencing specific content, cite the source URLs.
Keep responses natural, conversational, and formatted for easy readability.

Provided Documentation Context:
{context_str}

User Question: {question}

Answer:"""

class RAGChain:
    def __init__(self):
        self.embedding_model: FastEmbedModelType = get_fastembed_model()
        self.llm = get_llm()
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

    async def _retrieve_and_format_context(self, input_data: Dict[str, Any]) -> str:
        question = input_data["question"]
        top_k = input_data.get("top_k", 3)
        search_results_raw = await query_pinecone(
            query_text=question,
            embedding_model=self.embedding_model,
            top_k=top_k
        )
        self.retrieved_sources = []
        context_parts = []
        if not search_results_raw:
            return "No relevant documents found in the knowledge base."
        for result_raw in search_results_raw:
            payload_data = result_raw.get('metadata', {})
            content = payload_data.get('text', '')
            url = payload_data.get('source_url', 'Unknown URL')
            title = payload_data.get('title', '')
            if content:
                context_parts.append(f"Source URL: {url}\nTitle: {title}\nContent:\n{content}\n---")
                self.retrieved_sources.append(SourceDocument(url=url, title=title))
        if not context_parts:
            return "No relevant documents found with content in the knowledge base."
        return "\n\n".join(context_parts)

    async def invoke(self, ticket_context: TicketContext) -> SuggestedResponse:
        self.retrieved_sources = []
        question_to_llm = ticket_context.user_query or ticket_context.content or ""
        response_text = await self.chain.ainvoke({"question": question_to_llm})
        return SuggestedResponse(
            reply_text=response_text,
            sources=self.retrieved_sources
        )
