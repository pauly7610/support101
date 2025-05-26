import os
import uuid
from typing import List

from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
# Prometheus imports
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Histogram,
                               generate_latest)
from starlette.responses import Response as StarletteResponse

from packages.llm_engine.chains.rag_chain import RAGChain
from packages.llm_engine.embeddings import get_fastembed_model
from packages.llm_engine.vector_store import (get_pinecone_index,
                                              upsert_documents_to_pinecone)
# Import shared models
from packages.shared.models import (CrawledPage, DocumentMetadata,
                                    DocumentPayload, IngestResponse,
                                    IngestURLRequest, SuggestedResponse,
                                    TicketContext)

app = FastAPI(title="Support Intelligence Core API")

@app.post("/feedback", tags=["Feedback"], summary="Submit user feedback", response_description="Feedback received")
def submit_feedback(feedback: dict = Body(...)):
    """
    Accepts user feedback in JSON: {"feedback": str}.
    Logs or stores feedback for review. No authentication required.
    """
    import datetime
    text = feedback.get("feedback", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Feedback text required.")
    # Store feedback in a local file (append mode)
    try:
        with open("/tmp/support101_feedback.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] {text}\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {e}")
    return {"status": "success", "message": "Feedback received."}

@app.get("/openapi.yaml", include_in_schema=False)
def openapi_yaml():
    yaml_path = os.path.join(os.path.dirname(__file__), "../../docs/openapi.yaml")
    return FileResponse(yaml_path, media_type="application/yaml")

# Optional: If you want to override the OpenAPI schema with your static YAML, uncomment below.
# import yaml
# def custom_openapi():
#     yaml_path = os.path.join(os.path.dirname(__file__), "../../docs/openapi.yaml")
#     with open(yaml_path, "r") as f:
#         return yaml.safe_load(f)
# app.openapi = custom_openapi

# Prometheus metrics
LLM_RESPONSE_TIME = Histogram(
    'llm_response_time_seconds',
    'LLM response time in seconds',
    buckets=(0.1, 0.5, 1, 2, 5, 10)
)
API_ERROR_COUNT = Counter(
    'api_error_count',
    'Count of API errors',
    ['endpoint', 'exception_type']
)
VECTOR_STORE_CACHE_HITS = Counter(
    'vector_store_cache_hits',
    'Count of vector store cache hits'
)

# CORS Middleware (adjust origins as needed for your frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Replace with your frontend domains for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return StarletteResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def prometheus_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        API_ERROR_COUNT.labels(endpoint=request.url.path, exception_type=type(exc).__name__).inc()
        raise

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

# Stub: increment VECTOR_STORE_CACHE_HITS if/when cache is implemented
# Example usage: VECTOR_STORE_CACHE_HITS.inc()
def _crawl_documentation_firecrawl(base_url: str, limit_pages: int = 5) -> List[CrawledPage]:
    # TODO: Implement Firecrawl ingestion
    # For now, return empty list
    return []

def chunk_page_content(page_content: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
    return [page_content[i:i + chunk_size] for i in range(0, len(page_content), chunk_size - chunk_overlap)]

import mimetypes
import threading
import time

import jwt
import schedule
from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_limiter import FastAPILimiter, RateLimiter

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()

def mask_api_keys(detail: str) -> str:
    # Mask anything that looks like an API key
    return detail.replace(os.getenv("PINECONE_API_KEY", "***"), "***MASKED***")

async def jwt_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT token.")

@app.post("/gdpr_delete")
async def gdpr_delete(user_id: str = Body(...), auth=Depends(jwt_auth)):
    deleted = 0
    for log in CHAT_LOGS[:]:
        if log["user_id"] == user_id:
            CHAT_LOGS.remove(log)
            deleted += 1
    return {"status": "success", "message": f"Data deleted for user {user_id}", "logs_deleted": deleted}

@app.post("/ccpa_optout")
async def ccpa_optout(user_id: str = Body(...), auth=Depends(jwt_auth)):
    # Mark all logs for user as anonymized
    count = 0
    for log in CHAT_LOGS:
        if log["user_id"] == user_id and not log.get("anonymized"):
            log["text"] = "[ANONYMIZED]"
            log["anonymized"] = True
            count += 1
    return {"status": "success", "message": f"Opt-out processed for user {user_id}", "logs_anonymized": count}

import asyncio
from collections import defaultdict

from fastapi import APIRouter, Depends

# Persistent escalation analytics using PostgreSQL
from .db import Escalation, SessionLocal, init_db


@app.on_event("startup")
def on_startup():
    # Initialize the database
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())

@app.post("/report_escalation")
async def report_escalation(event: dict, auth=Depends(jwt_auth)):
    async with SessionLocal() as session:
        escalation = Escalation(
            user_id=event.get("user_id", "unknown"),
            text=event.get("text", ""),
            timestamp=event.get("timestamp"),
            last_updated=event.get("last_updated"),
            confidence=event.get("confidence"),
            source_url=event.get("source_url"),
        )
        session.add(escalation)
        await session.commit()
    return {"status": "ok"}


@app.get("/analytics/escalations")
async def get_escalation_analytics(user_id: str = None, start_time: float = None, end_time: float = None, auth=Depends(jwt_auth)):
    async with SessionLocal() as session:
        query = Escalation.__table__.select().order_by(Escalation.timestamp.asc())
        if user_id:
            query = query.where(Escalation.user_id == user_id)
        if start_time:
            query = query.where(Escalation.timestamp >= start_time)
        if end_time:
            query = query.where(Escalation.timestamp <= end_time)
        result = await session.execute(query)
        rows = result.fetchall()
        per_day = defaultdict(int)
        total = 0
        last = None
        for row in rows:
            day = time.strftime("%Y-%m-%d", time.gmtime(row.timestamp))
            per_day[day] += 1
            total += 1
            last = {
                'id': row.id,
                'user_id': row.user_id,
                'text': row.text,
                'timestamp': row.timestamp,
                'last_updated': str(row.last_updated),
                'confidence': row.confidence,
                'source_url': row.source_url
            }
        return {
            "total_escalations": total,
            "per_day": dict(per_day),
            "last_escalation": last
        }


import time as _time


def anonymize_chat_logs():
    print("[Schedule] Anonymizing chat logs older than 30 days...")
    now = _time.time()
    cutoff = now - 30 * 24 * 3600
    count = 0
    for log in CHAT_LOGS:
        if not log.get("anonymized") and log["timestamp"] < cutoff:
            log["text"] = "[ANONYMIZED]"
            log["anonymized"] = True
            count += 1
    print(f"Anonymized {count} chat logs.")


def schedule_anonymization():
    schedule.every().day.at("00:00").do(anonymize_chat_logs)
    while True:
        schedule.run_pending()
        time.sleep(60)


threading.Thread(target=schedule_anonymization, daemon=True).start()


@app.get("/openapi.json")
def custom_openapi():
    return app.openapi()


# ADR and SOC2 checklist stubs
ADR_PATH = os.path.join(os.path.dirname(__file__), "../../docs/ADR.md")
SOC2_PATH = os.path.join(os.path.dirname(__file__), "../../docs/SOC2_checklist.md")


# NOTE: Pinecone encrypts vectors at rest by default (see Pinecone docs). For Vault/API key rotation, see deployment pipeline and ops docs.


@app.on_event("startup")
async def startup_event():
    # Initialize rate limiter (assumes Redis running at localhost:6379)
    try:
        await FastAPILimiter.init("redis://localhost:6379")
    except Exception as e:
        print(f"Warning: Rate limiter not initialized: {e}")


@app.post("/ingest_documentation", response_model=IngestResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def ingest_documentation_endpoint(
    file: UploadFile = File(...),
    chunk_size: int = Body(1000),
    auth=Depends(jwt_auth)
):
    # File type restriction
    allowed_types = {"application/pdf", "text/markdown", "text/plain"}
    file_type, _ = mimetypes.guess_type(file.filename)
    if file_type not in allowed_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_type": "invalid_file_type",
                "message": "Only PDF, Markdown, or TXT files are supported.",
                "retryable": False,
                "documentation": "https://api.support101/errors#E415"
            }
        )

    # Chunk size validation
    if not (512 <= chunk_size <= 2048):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error_type": "invalid_chunk_size",
                "message": "Chunk size must be between 512 and 2048 tokens.",
                "message": (
                    "Chunk size must be between 512 and 2048 tokens."
                ),
                "retryable": False,
                "documentation": "https://api.support101/errors#E416"
            }
        )

    # Actual file read, parsing, chunking, and upsert logic
    import io

    import pdfplumber
    documents_to_upsert: List[DocumentPayload] = []
    try:
        contents = await file.read()
        file_ext = os.path.splitext(file.filename)[1].lower()
        text_pages = []
        if file_ext == ".pdf":
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        text_pages.append(text)
        elif file_ext in [".md", ".txt"]:
            decoded = contents.decode("utf-8", errors="ignore")
            # For markdown, optionally strip frontmatter or metadata
            text_pages = [decoded]
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error_type": "invalid_file_type",
                    "message": f"File extension {file_ext} not allowed.",
                    "retryable": False,
                    "documentation": "https://api.support101/errors#E415"
                }
            )
        # Chunk and build DocumentPayloads
        chunked_count = 0
        for page_num, page_text in enumerate(text_pages):
            chunks = chunk_page_content(page_text, chunk_size=chunk_size)
            for i, chunk_content in enumerate(chunks):
                doc_id = str(uuid.uuid4())
                documents_to_upsert.append(
                    DocumentPayload(
                        id=doc_id,
                        content=chunk_content,
                        source_url=None,
                        title=file.filename,
                        metadata={"page": page_num + 1, "chunk": i + 1}
                    )
                )
                chunked_count += 1
        # Upsert to Pinecone
        if documents_to_upsert:
            embedding_model = get_fastembed_model()
            upserted = await upsert_documents_to_pinecone(documents_to_upsert, embedding_model)
        else:
            upserted = 0
        return IngestResponse(
            status="success",
            message=f"Ingested {len(text_pages)} page(s), {chunked_count} chunk(s), {upserted} document(s) added.",
            pages_crawled=len(text_pages),
            documents_added=upserted
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_type": "ingestion_error",
                "message": mask_api_keys(str(e)),
                "retryable": False,
                "documentation": "https://api.support101/errors#E500"
            }
        )

        # The following block was incorrectly indented inside the except block. It should be outside.
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
) -> SuggestedResponse:
    """Generate a reply to a ticket using RAGChain and track LLM response time."""
    try:
        print(f"Received generate_reply request for ticket: {ticket_context.ticket_id}")
        with LLM_RESPONSE_TIME.time():
            response = await rag_chain.invoke(ticket_context)
        if hasattr(response, "error") and response.error:
            # Unified error response for LLM timeouts etc.
            return JSONResponse(status_code=504, content=response.error)
        return response
    except Exception as e:
        API_ERROR_COUNT.labels(
            endpoint="/generate_reply",
            exception_type=type(e).__name__
        ).inc()
        print(f"Error in /generate_reply: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error_type": "internal_error",
                "message": mask_api_keys(
                    f"Failed to generate reply: {str(e)}"
                ),
                "retryable": False,
                "documentation": "https://api.support101/errors#E500"
            }
        )
