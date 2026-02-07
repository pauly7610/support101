import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# --- Existing Models (expanded and merged) ---
class UserContext(BaseModel):
    user_id: str
    name: str | None = None
    email: str | None = None
    # ... other user details


class MemoryState(BaseModel):
    memory_id: str | None = None
    user_id: str | None = None
    state: dict | None = None
    conversation_history: list[dict[str, str]] | None = (
        None  # e.g., [{"role": "user", "content": "Hi"}, ...]
    )


class TicketContext(BaseModel):
    ticket_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    content: str | None = None  # alias for user_query
    user_query: str | None = None
    user_context: UserContext | None = None
    metadata: dict | None = None
    # conversation_history: Optional[List[Dict[str, str]]] = None
    # relevant_documents_for_context: Optional[List[str]] = None


# --- New/Adapted Models ---
class DocumentMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    language: str | None = "en"
    crawl_date: datetime | None = Field(default_factory=datetime.now)
    source_url: HttpUrl | None = None
    # Add any other metadata you deem important (breadcrumbs, section, etc.)


class DocumentPayload(BaseModel):
    id: str  # UUID for the document chunk
    content: str
    source_url: HttpUrl | None = None
    title: str | None = None
    metadata: dict[str, Any] = {}


class CrawledPage(BaseModel):
    content: str
    url: HttpUrl
    metadata: DocumentMetadata


class IngestURLRequest(BaseModel):
    url: HttpUrl
    crawl_limit: int | None = 20


class IngestResponse(BaseModel):
    status: str
    message: str
    pages_crawled: int
    documents_added: int


class QueryResult(BaseModel):
    id: str
    score: float
    payload: DocumentPayload


class SourceDocument(BaseModel):
    url: str | None = None
    title: str | None = None
    excerpt: str | None = None
    confidence: float | None = None
    last_updated: str | None = None


class SuggestedResponse(BaseModel):
    reply_text: str | None = None
    sources: list[SourceDocument] = []
    error: dict[str, Any] | None = None


class TTSRequest(BaseModel):
    text_to_speak: str
    voice: str | None = "alloy"
    tts_instructions: str | None = None
