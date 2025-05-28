# Backend (FastAPI)

This is the FastAPI backend for the Support Intelligence Core.

## Compliance & Privacy
- `/gdpr_delete` — GDPR-compliant data deletion (JWT required)
- `/ccpa_optout` — CCPA opt-out support (JWT required)
- Admin dashboard and customer compliance UI

## Analytics
- Escalation metrics, reporting by agent/category, 30-day stats

## Testing
- Async DB mocking, pytest-asyncio, SQLAlchemy utils

## Features
- Healthcheck endpoint (`/health`)
- `/generate_reply` endpoint for RAG-powered agent/customer replies (async, with sources)
- `/ingest_documentation` endpoint for crawling and chunking docs (Firecrawl integration ready)
- LangChain, HuggingFace/FastEmbed, Pinecone vector store
- Uses shared Pydantic models from `packages/shared`
- CORS enabled for frontend integration

## Integration
- Serves as API for both customer bot and agent copilot frontends
- Returns structured ticket, user, and reply data for design system-driven UIs

## Setup & Usage
1. Copy `.env.template` to `.env` and fill in API keys (including `POSTGRES_URL`)
2. `pip install -r requirements.txt`
3. Run DB migrations: `python migrations.py`
4. `uvicorn main:app --reload`

## Prometheus & Grafana Monitoring
- Metrics are exposed at `/metrics` (Prometheus scrape endpoint)
- Tracks LLM response times, API error rates, and vector store cache hits (stub)

### Sample Prometheus Scrape Config
```yaml
scrape_configs:
  - job_name: 'support101-backend'
    static_configs:
      - targets: ['localhost:8000']  # Adjust host/port as needed
```

### Example Grafana Alerts
- **LLM p99 latency > 2s for 5m**
  ```
  histogram_quantile(0.99, sum(rate(llm_response_time_seconds_bucket[5m])) by (le)) > 2
  ```
- **API error rate > 5/min per endpoint**
  ```
  sum(increase(api_error_count[1m])) by (endpoint) > 5
  ```

### Dashboard
- Visualize `llm_response_time_seconds`, `api_error_count`, and `vector_store_cache_hits`.
- Import a dashboard using the above metrics for real-time monitoring.

## Code Formatting
- Enforce PEP-8 using Black: `black .`
- All Python code must use type hints and async/await for LLM calls

## Dev
- See root README for Docker/dev instructions and environment setup
- Update Pinecone/OpenAI keys as needed
- Extend endpoints for new RAG, ingestion, or TTS features
