# Contributing to Support101

## Database Initialization

1. Set your PYTHONPATH:
   - Linux/macOS: `export PYTHONPATH=$PYTHONPATH:$(pwd)/apps/backend`
   - Windows (PowerShell): `$env:PYTHONPATH="$env:PYTHONPATH;$(Get-Location)\apps\backend"`
2. Run Alembic migrations:
   ```sh
   alembic upgrade head
   ```
3. (Optional) Seed test data:
   ```sh
   python -m scripts.seed_test_data
   ```

## Test Environment Safety
- All API keys must be in `.env` or `config/creds.tpl` (never in code or test configs)
- Never commit real credentials

## Troubleshooting
- If you see `relation "users" does not exist`, check Alembic and PYTHONPATH setup.
