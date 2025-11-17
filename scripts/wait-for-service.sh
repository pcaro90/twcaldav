#!/bin/bash
# Wait for a service to be ready
# Usage: ./wait-for-service.sh <url> <max_retries>

URL="${1:-http://localhost:5232}"
MAX_RETRIES="${2:-30}"

echo "Waiting for service at $URL to be ready..."

RETRY=0
until curl -sf "$URL" > /dev/null 2>&1 || [ $RETRY -eq $MAX_RETRIES ]; do
  echo "  Attempt $((RETRY + 1))/$MAX_RETRIES..."
  sleep 2
  RETRY=$((RETRY + 1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
  echo "ERROR: Service not ready after $MAX_RETRIES attempts"
  exit 1
fi

echo "✓ Service is ready!"
exit 0
