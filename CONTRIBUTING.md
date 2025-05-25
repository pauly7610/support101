# Contributing to Support Intelligence Core (SIC)

Thank you for your interest in contributing! 🚀

## How to Contribute

1. **Fork the repository** and clone it locally.
2. **Create a new branch** for your feature or fix:
   ```sh
   git checkout -b my-feature
   ```
3. **Make your changes** with clear commit messages.
4. **Run DB migrations** if you add/modify models: `python apps/backend/migrations.py`
5. **Test your changes** locally (backend: pytest, frontend: Cypress, type checks)
6. **Open a pull request** with a clear description of your changes and reference the PRD if relevant.

## Code Style
- Python: PEP8, type hints, async/await, Black formatting
- JS/TS: Strict TypeScript, Prettier, Cypress types for tests
- Document new functions and modules
- Add or update tests as appropriate (see `tests/` and PRD for coverage)
- Ensure compliance and analytics features are not broken

## Reporting Issues
- Use GitHub Issues for bugs, feature requests, or questions.
- Please provide as much detail as possible (logs, screenshots, etc).

## Code of Conduct
This project follows the [Contributor Covenant](https://www.contributor-covenant.org/). Be respectful and inclusive.

---

We welcome all contributions—big or small!
