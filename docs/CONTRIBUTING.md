# Contributing to Support101

See the root [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full contributing guide, including:

- Code style (Ruff for Python, Biome for JS/TS)
- Package management (pnpm workspaces)
- Testing commands (pytest, Vitest, Cypress)
- Database migrations (Alembic)

## Quick Reference

```sh
# Database migrations
PYTHONPATH=$PWD alembic -c apps/backend/alembic.ini upgrade head

# Run all tests
pytest tests/ apps/backend/tests/ -v
pnpm --filter customer-bot test
pnpm --filter agent-copilot test
pnpm --filter admin-dashboard test

# Lint
ruff check packages/ apps/backend/ tests/
pnpm --filter customer-bot lint
pnpm --filter agent-copilot lint
pnpm --filter admin-dashboard lint
```

## Security
- All API keys must be in `.env` (never in code or test configs)
- Never commit real credentials
- API keys are automatically scrubbed from error responses
