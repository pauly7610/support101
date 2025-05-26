"""
Basic RAG chain using LangChain, HuggingFace embeddings, and Pinecone.
Modular: swap in-memory or Pinecone vector store as needed.
"""

import os
from typing import Optional

from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.llms.base import LLM
from langchain.vectorstores import Pinecone as PineconeStore
from langchain.vectorstores.base import VectorStore


# In-memory fallback
class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self.docs = []
        self.embeddings = []

    def add_documents(self, docs, embeddings):
        self.docs.extend(docs)
        self.embeddings.extend(embeddings)

    def similarity_search(self, query, k=3):
        # Dummy: return all docs
        return self.docs[:k]


# Base chain class for reuse
class BaseLangchainChain:
    def __init__(self, llm: LLM, vectorstore: VectorStore):
        self.llm = llm
        self.vectorstore = vectorstore


class RAGChain(BaseLangchainChain):
    def __init__(self, llm: LLM, use_pinecone: bool = True):
        if use_pinecone and os.getenv("PINECONE_API_KEY"):
            embeddings = HuggingFaceEmbeddings()
            # Pinecone vector store setup
            vectorstore = PineconeStore(
                index_name=os.getenv("PINECONE_INDEX", "support-core"),
                embedding_function=embeddings,
            )
        else:
            # Fallback to in-memory
            vectorstore = InMemoryVectorStore()
        super().__init__(llm, vectorstore)
        self.qa = RetrievalQA(llm=llm, retriever=vectorstore.as_retriever())

    def generate(self, question: str, context: Optional[str] = None) -> dict:
        # For now, dummy output
        return {
            "reply": f"[RAGChain] Answer to: {question}",
            "sources": ["docA", "docB"],
        }


# Usage example (to be called from backend):
# from transformers import pipeline
# rag = RAGChain(llm=SomeLLM(...))
# rag.generate(question="How do I reset my password?")
