# Shared Package

Pydantic models, types, and shared utilities for the monorepo.

- Used for all API contracts, analytics, and compliance features
- Production-ready and tested via CI

## Core Models
- `UserContext`: User/session context
- `TicketContext`: Ticket and query context for RAG
- `MemoryState`: Conversation/memory state
- `DocumentMetadata`, `DocumentPayload`, `CrawledPage`: For doc ingestion/chunking
- `IngestURLRequest`, `IngestResponse`: For backend ingestion endpoints
- `QueryResult`, `SourceDocument`, `SuggestedResponse`, `TTSRequest`: For RAG and TTS flows

## Integration
- Used by backend and both frontends for data contracts
- Import models for API requests/responses

See root `DESIGN_SYSTEM.md` for frontend design tokens and shared UI patterns.
