# Local test runner script for Windows
# Starts PostgreSQL and Redis via Docker, runs tests, then stops services

param(
    [switch]$KeepRunning,
    [string]$TestPath = "apps/backend/tests"
)

Write-Host "Starting test services..." -ForegroundColor Cyan
docker-compose -f docker-compose.test.yml up -d 2>&1 | Out-Null

Write-Host "Waiting for services to be healthy..." -ForegroundColor Cyan
$maxRetries = 30
$retryCount = 0

# Wait for PostgreSQL
while ($retryCount -lt $maxRetries) {
    try {
        $result = docker exec support101-postgres-1 pg_isready -U postgres 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {}
    $retryCount++
    Start-Sleep -Seconds 1
}

if ($retryCount -eq $maxRetries) {
    Write-Host "PostgreSQL failed to start" -ForegroundColor Red
    docker-compose -f docker-compose.test.yml down
    exit 1
}

# Wait for Redis
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    try {
        $result = docker exec support101-redis-1 redis-cli ping 2>&1
        if ($result -match "PONG") {
            Write-Host "Redis is ready!" -ForegroundColor Green
            break
        }
    } catch {}
    $retryCount++
    Start-Sleep -Seconds 1
}

if ($retryCount -eq $maxRetries) {
    Write-Host "Redis failed to start" -ForegroundColor Red
    docker-compose -f docker-compose.test.yml down
    exit 1
}

Write-Host "`nRunning tests..." -ForegroundColor Cyan
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/support101_test"

python -m pytest $TestPath -v --tb=short
$testExitCode = $LASTEXITCODE

if (-not $KeepRunning) {
    Write-Host "`nStopping test services..." -ForegroundColor Cyan
    docker-compose -f docker-compose.test.yml down 2>&1 | Out-Null
}
else {
    Write-Host "`nServices still running. Stop with: docker-compose -f docker-compose.test.yml down" -ForegroundColor Yellow
}

exit $testExitCode
