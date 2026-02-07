# Setup & Onboarding Guide

## Prerequisites
- Python 3.11+
- Node.js 20+ with pnpm (`corepack enable`)
- PostgreSQL 16
- Redis 7 (optional — for caching + activity stream)

## First-Time Setup

1. Clone and configure environment:
   ```sh
   git clone https://github.com/pauly7610/support101
   cd support101
   cp .env.example .env
   # Edit .env with your API keys (see README for full list)
   ```

2. Install Python dependencies:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   ```

3. Install frontend dependencies:
   ```sh
   corepack enable
   pnpm install
   ```

4. Set up the database:
   ```sh
   createdb support101

   # Run migrations
   PYTHONPATH=$PWD alembic -c apps/backend/alembic.ini upgrade head
   # Windows: $env:PYTHONPATH=$PWD; alembic -c apps/backend/alembic.ini upgrade head
   ```

5. Run tests to verify:
   ```sh
   # Backend (197 tests)
   pytest tests/ apps/backend/tests/ -v

   # Frontend
   pnpm --filter customer-bot test
   pnpm --filter agent-copilot test
   pnpm --filter admin-dashboard test
   ```

6. Start development servers:
   ```sh
   uvicorn apps.backend.main:app --reload          # Backend (port 8000)
   pnpm --filter customer-bot dev                   # Customer bot (port 3000)
   pnpm --filter admin-dashboard dev                # Admin dashboard (port 3002)
   pnpm --filter agent-copilot dev                  # Chrome extension (webpack)
   ```

## Docker Alternative

Skip steps 2-6 and use Docker Compose instead:
```sh
docker compose -f docker-compose.dev.yml up
```

Or for production:
```sh
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting
- **`relation "users" does not exist`** — Run Alembic migrations: `PYTHONPATH=$PWD alembic -c apps/backend/alembic.ini upgrade head`
- **pnpm lockfile errors in CI** — Run `pnpm install` locally after modifying any `package.json`, then commit the updated `pnpm-lock.yaml`
- **`React is not defined` in tests** — Ensure `@vitejs/plugin-react` is in devDependencies and configured in `vitest.config.ts`
- **Redis connection errors** — Redis is optional; caching and activity stream fall back to in-memory when unavailable
- **Python import errors** — Ensure `PYTHONPATH` includes the project root, or use `pip install -e ".[dev]"`

## Verification Checklist
- [ ] `uvicorn apps.backend.main:app` starts without errors
- [ ] `GET /health` returns 200
- [ ] `pytest tests/ apps/backend/tests/ -v` — all tests pass
- [ ] `pnpm --filter customer-bot test` — all tests pass
- [ ] No API keys or credentials in `git status` output
