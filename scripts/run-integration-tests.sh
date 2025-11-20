#!/bin/bash
# Run integration tests locally with Docker Compose

set -e

echo "======================================"
echo "  Running Integration Tests"
echo "======================================"
echo ""

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    echo "ERROR: docker compose not found. Please install it first."
    exit 1
fi

# Cleanup any existing containers/volumes from previous runs
echo "Cleaning up previous test environment..."
docker compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.test.yml rm -fsv 2>/dev/null || true

# Build and run tests with fresh containers
echo ""
echo "Building Docker images..."
docker compose -f docker-compose.test.yml build

echo ""
echo "Running integration tests..."
# Temporarily disable exit-on-error to capture test results even if tests fail
set +e
docker compose -f docker-compose.test.yml up --force-recreate --abort-on-container-exit --exit-code-from test-runner

# Capture exit code
EXIT_CODE=$?
set -e

# Copy test results before cleanup
echo ""
echo "Copying test results..."
docker cp twcaldav-test-runner:/app/test-results.xml . 2>/dev/null && echo "✓ Test results copied to test-results.xml" || echo "Note: No test results file found (this is OK if tests didn't complete)"

# Cleanup after test run (always run, even if tests failed)
echo ""
echo "Cleaning up test environment..."
set +e  # Don't exit if cleanup commands fail
docker compose -f docker-compose.test.yml down -v --remove-orphans 2>&1
docker compose -f docker-compose.test.yml rm -fsv 2>&1

# Remove any dangling test volumes
echo "Removing dangling volumes..."
docker volume ls -q -f "dangling=true" -f "name=twcaldav" | xargs -r docker volume rm 2>/dev/null || true
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ All integration tests passed!"
else
    echo ""
    echo "✗ Integration tests failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
