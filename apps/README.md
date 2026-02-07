# Apps

This folder contains all runnable applications:

| App | Stack | Port | Description |
|-----|-------|------|-------------|
| `backend` | FastAPI + SQLAlchemy | 8000 | API server — RAG, agents, HITL, compliance, analytics, voice, WebSocket, A2A |
| `customer-bot` | Next.js 15 + React 19 + Tailwind | 3000 | Customer-facing chat widget with streaming, voice input, citations |
| `agent-copilot` | React + Webpack (Chrome Extension) | — | Chrome extension sidebar for Zendesk/Intercom with real-time WebSocket suggestions |
| `admin-dashboard` | Next.js 15 + React 19 + Tailwind | 3002 | Admin panel — KB management, agent config, cost tracking, voice config, settings |
| `demo-video` | Remotion | — | Product demo video (7 animated scenes, ~53s) |

## Running

```sh
# All apps (via pnpm workspaces)
pnpm --filter customer-bot dev       # port 3000
pnpm --filter admin-dashboard dev    # port 3002
pnpm --filter agent-copilot dev      # webpack watch
uvicorn apps.backend.main:app --reload  # port 8000

# Demo video
cd apps/demo-video && npx remotion studio
```

## Testing

```sh
pnpm --filter customer-bot test      # 6 Vitest suites
pnpm --filter agent-copilot test     # 1 Vitest suite (5 tests)
pnpm --filter admin-dashboard test   # 1 Vitest suite (15 tests)
```

All frontend apps use **Biome** for linting/formatting and share a unified design system (see root `DESIGN_SYSTEM.md`).
