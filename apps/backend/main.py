import os
import uuid
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# Import shared models
from packages.shared.models import (
    TicketContext, SuggestedResponse, IngestURLRequest, IngestResponse,
    CrawledPage, DocumentPayload, DocumentMetadata
)
from packages.llm_engine.chains import RAGChain
from packages.llm_engine.embeddings import get_fastembed_model
from packages.llm_engine.vector_store import upsert_documents_to_pinecone, get_pinecone_index

app = FastAPI(title="Support Intelligence Core API")

# CORS Middleware (adjust origins as needed for your frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Replace with your frontend domains for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rag_chain_instance: RAGChain = None

def get_rag_chain():
    global _rag_chain_instance
    if _rag_chain_instance is None:
        print("Initializing RAG Chain...")
        _rag_chain_instance = RAGChain()
        try:
            get_pinecone_index()
            print("Pinecone index connection successful.")
        except Exception as e:
            print(f"ERROR: Failed to initialize Pinecone: {e}")
    return _rag_chain_instance

@app.get("/health")
async def health_check():
    return {"status": "healthy", "pinecone_index_name": os.getenv("PINECONE_INDEX_NAME", "support-docs")}

# Placeholder for Firecrawl ingestion logic
def _crawl_documentation_firecrawl(base_url: str, limit_pages: int = 5) -> List[CrawledPage]:
    # TODO: Implement Firecrawl ingestion
    # For now, return empty list
    return []

def chunk_page_content(page_content: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
    return [page_content[i:i + chunk_size] for i in range(0, len(page_content), chunk_size - chunk_overlap)]

@app.post("/ingest_documentation", response_model=IngestResponse)
async def ingest_documentation_endpoint(request: IngestURLRequest = Body(...)):
    try:
        print(f"Received ingestion request for URL: {request.url}")
        crawled_pages = _crawl_documentation_firecrawl(str(request.url), limit_pages=request.crawl_limit or 20)
        if not crawled_pages:
            return IngestResponse(status="warning", message="No pages crawled or no content found.", pages_crawled=0, documents_added=0)
        documents_to_upsert: List[DocumentPayload] = []
        for page in crawled_pages:
            content_chunks = chunk_page_content(page.content)
            for i, chunk_content in enumerate(content_chunks):
                doc_id = str(uuid.uuid4())
                documents_to_upsert.append(
                    DocumentPayload(
                        id=doc_id,
                        content=chunk_content,
                        source_url=page.url,
                        title=page.metadata.title,
                        metadata={
                            "original_page_title": page.metadata.title,
                            "crawl_date": page.metadata.crawl_date.isoformat() if page.metadata.crawl_date else None,
                            "language": page.metadata.language,
                            "chunk_index": i
                        }
                    )
                )
        if not documents_to_upsert:
            return IngestResponse(status="warning", message="No document chunks to process after crawling.", pages_crawled=len(crawled_pages), documents_added=0)
        embedding_model = get_fastembed_model()
        num_added = await upsert_documents_to_pinecone(documents_to_upsert, embedding_model)
        return IngestResponse(
            status="success",
            message=f"Successfully crawled and ingested content from {request.url}.",
            pages_crawled=len(crawled_pages),
            documents_added=num_added
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during ingestion: {str(e)}")

@app.post("/generate_reply", response_model=SuggestedResponse)
async def generate_reply_endpoint(
    ticket_context: TicketContext = Body(...),
    rag_chain: RAGChain = Depends(get_rag_chain)
):
    try:
        print(f"Received generate_reply request for ticket: {ticket_context.ticket_id}")
        response = await rag_chain.invoke(ticket_context)
        return response
    except Exception as e:
        print(f"Error in /generate_reply: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate reply: {str(e)}")
