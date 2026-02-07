#!/bin/bash
# Bash script to start all core services for Support Intelligence Core

echo "[Bash] Starting backend and customer-bot in background..."

# Set PYTHONPATH to the project root so 'packages' is discoverable
# Use absolute path for project root
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
(cd apps/backend && export PYTHONPATH="$PROJECT_ROOT" && uvicorn main:app --reload &)
(cd apps/customer-bot && pnpm dev &)

# (Optional) Start agent-copilot
# (cd apps/agent-copilot && npm run dev &)

echo "All core services are starting in background. Use 'jobs' to see running processes."
