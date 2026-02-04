#!/bin/bash
# Local test runner script for Linux/macOS
# Starts PostgreSQL and Redis via Docker, runs tests, then stops services

set -e

KEEP_RUNNING=false
TEST_PATH="apps/backend/tests"

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-running)
            KEEP_RUNNING=true
            shift
            ;;
        --path)
            TEST_PATH="$2"
            shift 2
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

echo -e "\033[36mStarting test services...\033[0m"
docker-compose -f docker-compose.test.yml up -d

echo -e "\033[36mWaiting for services to be healthy...\033[0m"

# Wait for PostgreSQL
MAX_RETRIES=30
RETRY_COUNT=0
until docker-compose -f docker-compose.test.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "\033[31mPostgreSQL failed to start\033[0m"
        docker-compose -f docker-compose.test.yml down
        exit 1
    fi
    sleep 1
done
echo -e "\033[32mPostgreSQL is ready!\033[0m"

# Wait for Redis
RETRY_COUNT=0
until [ "$(docker-compose -f docker-compose.test.yml exec -T redis redis-cli ping 2>/dev/null)" = "PONG" ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "\033[31mRedis failed to start\033[0m"
        docker-compose -f docker-compose.test.yml down
        exit 1
    fi
    sleep 1
done
echo -e "\033[32mRedis is ready!\033[0m"

echo -e "\n\033[36mRunning tests...\033[0m"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test"

python -m pytest "$TEST_PATH" -v --tb=short
TEST_EXIT_CODE=$?

if [ "$KEEP_RUNNING" = false ]; then
    echo -e "\n\033[36mStopping test services...\033[0m"
    docker-compose -f docker-compose.test.yml down
else
    echo -e "\n\033[33mServices still running. Stop with: docker-compose -f docker-compose.test.yml down\033[0m"
fi

exit $TEST_EXIT_CODE
