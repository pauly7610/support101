# Local test runner script for Windows
# Starts PostgreSQL and Redis via Docker, runs tests, then stops services

param(
    [switch]$KeepRunning,
    [string]$TestPath = "apps/backend/tests"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting test services..." -ForegroundColor Cyan
docker-compose -f docker-compose.test.yml up -d

Write-Host "Waiting for services to be healthy..." -ForegroundColor Cyan
$maxRetries = 30
$retryCount = 0

# Wait for PostgreSQL
while ($retryCount -lt $maxRetries) {
    $pgReady = docker-compose -f docker-compose.test.yml exec -T postgres pg_isready -U postgres 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PostgreSQL is ready!" -ForegroundColor Green
        break
    }
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
    $redisReady = docker-compose -f docker-compose.test.yml exec -T redis redis-cli ping 2>$null
    if ($redisReady -eq "PONG") {
        Write-Host "Redis is ready!" -ForegroundColor Green
        break
    }
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
    docker-compose -f docker-compose.test.yml down
}
else {
    Write-Host "`nServices still running. Stop with: docker-compose -f docker-compose.test.yml down" -ForegroundColor Yellow
}

exit $testExitCode
