#!/bin/bash
set -e

# Setup Radicale test data for CI/CD integration testing
# This script creates a test calendar and returns its ID

RADICALE_URL="${CALDAV_URL:-http://localhost:5232/test-user/}"
USERNAME="${CALDAV_USERNAME:-test-user}"
PASSWORD="${CALDAV_PASSWORD:-test-pass}"
CALENDAR_NAME="test-calendar"

echo "Setting up Radicale test data..."
echo "URL: $RADICALE_URL"
echo "User: $USERNAME"

# Wait for Radicale to be ready
echo "Waiting for Radicale to be ready..."
BASE_URL=$(echo "$RADICALE_URL" | sed 's|/test-user/||')
echo "Base URL: $BASE_URL"

MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
  RETRY=$((RETRY + 1))
  echo "  Attempt $RETRY/$MAX_RETRIES..."
  
  # Try to connect to base URL with auth
  if curl -sf -u "$USERNAME:$PASSWORD" "$BASE_URL" > /dev/null 2>&1; then
    echo "✓ Radicale is ready!"
    break
  fi
  
  # Show more details on last attempt
  if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "ERROR: Radicale not ready after $MAX_RETRIES attempts"
    echo "Trying one more time with verbose output:"
    curl -v -u "$USERNAME:$PASSWORD" "$BASE_URL" 2>&1 || true
    echo ""
    echo "Also trying without auth:"
    curl -v "$BASE_URL" 2>&1 || true
    exit 1
  fi
  
  sleep 2
done

# Create a test calendar collection using CalDAV MKCALENDAR
CALENDAR_URL="${RADICALE_URL}${CALENDAR_NAME}/"

echo "Creating test calendar at: $CALENDAR_URL"

# Create calendar with MKCALENDAR request
curl -X MKCALENDAR "$CALENDAR_URL" \
  -u "$USERNAME:$PASSWORD" \
  -H "Content-Type: application/xml; charset=utf-8" \
  --data '<?xml version="1.0" encoding="utf-8" ?>
<C:mkcalendar xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:set>
    <D:prop>
      <D:displayname>Test Calendar</D:displayname>
      <C:calendar-description>Test calendar for CI/CD integration testing</C:calendar-description>
      <C:supported-calendar-component-set>
        <C:comp name="VTODO"/>
        <C:comp name="VEVENT"/>
      </C:supported-calendar-component-set>
    </D:prop>
  </D:set>
</C:mkcalendar>' \
  -w "\nHTTP Status: %{http_code}\n" \
  2>&1 || echo "Calendar may already exist (this is OK)"

echo "✓ Test calendar created/verified: $CALENDAR_NAME"
echo "✓ Setup complete!"

# Export for use in tests
export CALDAV_CALENDAR_ID="$CALENDAR_NAME"
echo "Calendar ID: $CALDAV_CALENDAR_ID"
