# Setup & Onboarding Guide

## First-Time Setup

1. Copy `.env.template` to `.env`
2. Run `pip install -r requirements.txt`
3. Export the backend to your Python path (Linux/macOS):
   ```sh
   export PYTHONPATH=$PYTHONPATH:$(pwd)/apps/backend
   alembic upgrade head
   ```
   On Windows (PowerShell):
   ```powershell
   $env:PYTHONPATH="$env:PYTHONPATH;$(Get-Location)\apps\backend"
   alembic upgrade head
   ```
4. (Optional) Seed test data:
   ```sh
   python -m scripts.seed_test_data
   ```
5. Run tests:
   ```sh
   pytest -v
   ```

## Troubleshooting
- If you see `relation "users" does not exist`, run `alembic upgrade head` again.
- If Alembic fails, ensure your PYTHONPATH includes `apps/backend`.
- Ensure you have a running Postgres instance matching your `.env` config.

## Verification Checklist
- [ ] `/instance/db.sqlite3` exists (if using SQLite)
- [ ] All endpoints return 200 in a basic smoke test
- [ ] No API keys or credentials in `git status` output
