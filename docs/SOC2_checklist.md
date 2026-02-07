# SOC2 Compliance Checklist

## Access Controls & Authentication
- [x] JWT authentication enforced on all mutation endpoints
- [x] Per-endpoint rate limiting (configurable per route)
- [x] Admin-only controls for sensitive actions (compliance, analytics)
- [x] Access controls for all backend endpoints

## Data Protection
- [x] GDPR deletion endpoint implemented (`POST /v1/compliance/gdpr_delete`)
- [x] CCPA opt-out mechanism implemented (`POST /v1/compliance/ccpa_optout`)
- [x] GDPR/CCPA endpoints require JWT authentication
- [x] API key scrubbing in error responses (`mask_api_keys` + Sentry `before_send`)
- [x] Centralized error logging and masking (unified error format)
- [ ] Pinecone vectors encrypted at rest
- [ ] API keys rotated quarterly (Vault integration)
- [ ] Chat logs anonymized after 30 days

## Audit & Monitoring
- [x] Audit logging for all agent actions (AuditLogger with query/export)
- [x] Prometheus metrics endpoint (LLM response times, cache hits, error rates)
- [x] OpenTelemetry tracing (Traceloop SDK + raw OTEL fallback)
- [x] Sentry error monitoring with performance tracing
- [x] EvalAI governance checks and decision auditing
- [x] LLM cost tracking with budget alerts

## Multi-Tenancy
- [x] Tenant isolation with namespace separation
- [x] Tier-based resource limits (FREE → ENTERPRISE)
- [x] Per-tenant usage tracking and quota enforcement

## Infrastructure
- [x] Production Docker with non-root users, resource limits, healthchecks
- [x] Separate dev/test/prod Docker Compose configurations
- [ ] Regular vulnerability scans
- [ ] Incident response plan documented
- [ ] Annual SOC2 audit scheduled

---
Update this checklist as controls are implemented or audited.
