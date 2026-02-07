# Contributing to Support Intelligence Core (SIC)

Thank you for your interest in contributing!

## How to Contribute

1. **Fork the repository** and clone it locally.
2. **Create a new branch** for your feature or fix:
   ```sh
   git checkout -b my-feature
   ```
3. **Make your changes** with clear, conventional commit messages (e.g. `fix:`, `feat:`, `docs:`).
4. **Run DB migrations** if you add/modify models:
   ```sh
   PYTHONPATH=$PWD alembic -c apps/backend/alembic.ini upgrade head
   ```
5. **Run linters and tests** before pushing:
   ```sh
   # Python
   ruff check packages/ apps/backend/ tests/
   ruff format packages/ apps/backend/ tests/ --check
   pytest tests/ apps/backend/tests/ -v

   # Frontend (all 3 apps)
   pnpm --filter customer-bot lint
   pnpm --filter agent-copilot lint
   pnpm --filter admin-dashboard lint
   pnpm --filter customer-bot test
   pnpm --filter agent-copilot test
   pnpm --filter admin-dashboard test
   ```
6. **Update pnpm lockfile** if you modify any `package.json`:
   ```sh
   pnpm install
   ```
7. **Open a pull request** with a clear description of your changes.

## Code Style

### Python
- PEP 8 enforced via **Ruff** (replaces black + flake8 + isort)
- Type hints required for all functions
- Use `async/await` for LLM and database calls
- Format: `ruff format .`

### JavaScript / TypeScript
- **Biome** for linting, formatting, and import sorting (replaces ESLint + Prettier)
- Strict TypeScript mode — avoid `any` types
- React hooks rules enforced
- Format: `pnpm --filter <app> lint:fix`

### General
- Document new functions and modules
- Add or update tests for all changes
- Never commit API keys or credentials

## Package Management

This project uses **pnpm workspaces**. Always use pnpm (not npm or yarn):
```sh
corepack enable          # enables pnpm via Node.js corepack
pnpm install             # install all workspace dependencies
pnpm --filter <app> dev  # run a specific app
```

## Reporting Issues
- Use GitHub Issues for bugs, feature requests, or questions.
- Provide as much detail as possible (logs, screenshots, reproduction steps).

## Code of Conduct
This project follows the [Contributor Covenant](https://www.contributor-covenant.org/). Be respectful and inclusive.

---

We welcome all contributions — big or small!
