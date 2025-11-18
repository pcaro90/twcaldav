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

# Build and run tests
echo "Building Docker images..."
docker compose -f docker-compose.test.yml build

echo ""
echo "Running integration tests..."
docker compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test-runner

# Capture exit code
EXIT_CODE=$?

# Copy test results before cleanup
echo ""
echo "Copying test results..."
docker cp twcaldav-test-runner:/app/test-results.xml . 2>/dev/null && echo "✓ Test results copied to test-results.xml" || echo "Note: No test results file found (this is OK if tests didn't complete)"

# Cleanup
echo ""
echo "Cleaning up containers..."
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml rm -fsv

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ All integration tests passed!"
else
    echo ""
    echo "✗ Integration tests failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
