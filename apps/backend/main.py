import io
import mimetypes
import os
import uuid
from typing import List

import jwt
import pdfplumber
from fastapi import Body, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from prometheus_client import Histogram, Counter

from packages.llm_engine.chains.rag_chain import RAGChain
from packages.llm_engine.embeddings import get_fastembed_model
from packages.llm_engine.vector_store import (
    get_pinecone_index,
    upsert_documents_to_pinecone,
)
from packages.shared.models import (
    DocumentPayload,
    IngestResponse,
    SuggestedResponse,
    TicketContext,
)

app = FastAPI(title="Support Intelligence Core API")

security = HTTPBearer()


@app.post(
    "/feedback",
    tags=["Feedback"],
    summary="Submit user feedback",
    response_description="Feedback received",
)
def submit_feedback(feedback: dict = Body(...)):
    """
    Accepts user feedback in JSON: {"feedback": str}.
    Logs or stores feedback for review. No authentication required.
    """


JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret")
JWT_ALGORITHM = "HS256"


def mask_api_keys(detail: str) -> str:
    return detail.replace(os.getenv("PINECONE_API_KEY", "***"), "***MASKED***")


async def jwt_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT token.")


LLM_RESPONSE_TIME = Histogram(
    "llm_response_time_seconds",
    "LLM response time in seconds",
    buckets=(0.1, 0.5, 1, 2, 5, 10),
)
API_ERROR_COUNT = Counter(
    "api_error_count", "Count of API errors", ["endpoint", "exception_type"]
)
VECTOR_STORE_CACHE_HITS = Counter(
    "vector_store_cache_hits", "Count of vector store cache hits"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_error_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        API_ERROR_COUNT.labels(
            endpoint=request.url.path, exception_type=type(exc).__name__
        ).inc()
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
    return {
        "status": "healthy",
        "pinecone_index_name": os.getenv("PINECONE_INDEX_NAME", "support-docs"),
    }


def chunk_page_content(
    page_content: str, chunk_size: int = 1000, chunk_overlap: int = 100
) -> List[str]:
    return [
        page_content[i : i + chunk_size]
        for i in range(0, len(page_content), chunk_size - chunk_overlap)
    ]


@app.post("/ingest_documentation", response_model=IngestResponse)
@RateLimiter(times=5, seconds=60, scope="ingest_documentation")
async def ingest_documentation_endpoint(
    file: UploadFile = File(...), chunk_size: int = Body(1000), auth=Depends(jwt_auth)
):
    allowed_types = {"application/pdf", "text/markdown", "text/plain"}
    file_type, _ = mimetypes.guess_type(file.filename)
    if file_type not in allowed_types:
        return JSONResponse(
            status_code=400,
            content={
                "error_type": "invalid_file_type",
                "message": "Only PDF, Markdown, or TXT files are supported.",
                "retryable": False,
                "documentation": "https://api.support101/errors#E415",
            },
        )

    if not (512 <= chunk_size <= 2048):
        return JSONResponse(
            status_code=400,
            content={
                "error_type": "invalid_chunk_size",
                "message": "Chunk size must be between 512 and 2048 tokens.",
                "retryable": False,
                "documentation": "https://api.support101/errors#E416",
            },
        )

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
            text_pages = [decoded]
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error_type": "invalid_file_type",
                    "message": f"File extension {file_ext} not allowed.",
                    "retryable": False,
                    "documentation": "https://api.support101/errors#E415",
                },
            )
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
                        metadata={"page": page_num + 1, "chunk": i + 1},
                    )
                )
                chunked_count += 1
        if documents_to_upsert:
            embedding_model = get_fastembed_model()
            upserted_count = await upsert_documents_to_pinecone(
                documents_to_upsert, embedding_model
            )
        return IngestResponse(
            status="success",
            message=(
                f"Ingested {len(text_pages)} page(s) from file, created {chunked_count} chunk(s), "
                f"{upserted_count} document(s) added/updated."
            ),
            pages_crawled=len(text_pages),
            documents_added=upserted_count
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error_type": "ingestion_processing_error",
                "message": f"Failed during documentation ingestion: {mask_api_keys(str(e))}",
                "documentation": "https://api.support101/errors#E500",
            },
        )


@app.get("/openapi.json")
def custom_openapi():
    return app.openapi()


ADR_PATH = os.path.join(os.path.dirname(__file__), "../../docs/ADR.md")
SOC2_PATH = os.path.join(os.path.dirname(__file__), "../../docs/SOC2_checklist.md")


# NOTE: Pinecone encrypts vectors at rest by default (see Pinecone docs).
# For Vault/API key rotation, see deployment pipeline and ops docs.


@app.on_event("startup")
async def startup_event():
    # Initialize rate limiter (assumes Redis running at localhost:6379)
    try:
        await FastAPILimiter.init("redis://localhost:6379")
    except Exception as e:
        print(
            "Warning: Rate limiter not initialized: {}".format(e)
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error during ingestion: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Internal server error during ingestion: {str(e)}"
        )


@app.post("/generate_reply", response_model=SuggestedResponse)
async def generate_reply_endpoint(
    ticket_context: TicketContext = Body(...),
    rag_chain: RAGChain = Depends(get_rag_chain),
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
            endpoint="/generate_reply", exception_type=type(e).__name__
        ).inc()
        print(f"Error in /generate_reply: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error_type": "generate_reply_exception",
                "message": mask_api_keys(
                    f"Failed to generate reply due to an unexpected error: "
                    f"{str(e)}"
                ),
                "retryable": False,  # Usually false for unexpected server errors
                "documentation": "https://api.support101/errors#E500",
            },
        )
