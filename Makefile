.PHONY: test-local test-start test-stop test-backend test-agent-framework

# Start test services (PostgreSQL + Redis)
test-start:
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services..."
	@sleep 5
	@echo "Services ready!"

# Stop test services
test-stop:
	docker-compose -f docker-compose.test.yml down

# Run backend tests with local services
test-backend: test-start
	DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test \
	python -m pytest apps/backend/tests -v --tb=short
	$(MAKE) test-stop

# Run agent framework tests (no external services needed)
test-agent-framework:
	python -m pytest tests/agent_framework -v --tb=short

# Run all tests locally
test-local: test-start
	DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test \
	python -m pytest apps/backend/tests tests/agent_framework -v --tb=short
	$(MAKE) test-stop

# Quick lint check before push
lint:
	ruff check packages/ apps/backend/
	ruff format packages/ apps/backend/ --check

# Format code
format:
	ruff format packages/ apps/backend/
	ruff check packages/ apps/backend/ --fix
