from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# --- Existing Models (expanded and merged) ---
class UserContext(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    # ... other user details


class MemoryState(BaseModel):
    memory_id: Optional[str] = None
    user_id: Optional[str] = None
    state: Optional[dict] = None
    conversation_history: Optional[List[Dict[str, str]]] = None  # e.g., [{"role": "user", "content": "Hi"}, ...]


class TicketContext(BaseModel):
    ticket_id: str
    user_id: Optional[str] = None
    content: Optional[str] = None  # alias for user_query
    user_query: Optional[str] = None
    user_context: Optional[UserContext] = None
    metadata: Optional[dict] = None
    # conversation_history: Optional[List[Dict[str, str]]] = None
    # relevant_documents_for_context: Optional[List[str]] = None


# --- New/Adapted Models ---
class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = "en"
    crawl_date: Optional[datetime] = Field(default_factory=datetime.now)
    source_url: Optional[HttpUrl] = None
    # Add any other metadata you deem important (breadcrumbs, section, etc.)


class DocumentPayload(BaseModel):
    id: str  # UUID for the document chunk
    content: str
    source_url: HttpUrl
    title: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CrawledPage(BaseModel):
    content: str
    url: HttpUrl
    metadata: DocumentMetadata


class IngestURLRequest(BaseModel):
    url: HttpUrl
    crawl_limit: Optional[int] = 20


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
    url: HttpUrl
    title: Optional[str] = None
    # snippet: Optional[str] = None


class SuggestedResponse(BaseModel):
    reply_text: str
    sources: List[SourceDocument]
    # debug_info: Optional[Dict[str, Any]] = None


class TTSRequest(BaseModel):
    text_to_speak: str
    voice: Optional[str] = "alloy"
    tts_instructions: Optional[str] = None
