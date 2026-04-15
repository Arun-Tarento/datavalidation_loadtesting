#!/bin/bash
# Detailed timing analysis for NMT API using curl
# Usage: ENV=sandbox ./testing/AI4I/loadtesting/analyze_request_timing.sh

set -e

# Load environment
ENV=${ENV:-staging}
source "testing/.${ENV}.env"

echo "================================"
echo "NMT API Timing Analysis - $ENV"
echo "================================"

# Login first
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${TEST_ACCOUNT_EMAIL_PATTERN/\{\}/1}\", \"password\": \"$TEST_ACCOUNT_PASSWORD\", \"remember_me\": false}")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✅ Login successful"
echo ""

# Run NMT request with detailed timing
echo "Making NMT request with timing breakdown..."
echo ""

curl -w "\n\n📊 TIMING BREAKDOWN:\n\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\
  DNS Lookup:           %{time_namelookup}s\n\
  TCP Connection:       %{time_connect}s\n\
  TLS Handshake:        %{time_appconnect}s\n\
  Request Sent:         %{time_pretransfer}s\n\
  ⏱️  TTFB (Server):       %{time_starttransfer}s  ← Server processing time\n\
  Response Download:    %{time_total}s\n\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\
  Total Time:           %{time_total}s\n\
\n\
📈 BREAKDOWN:\n\
  Network setup:        $(echo "%{time_appconnect}" | bc)s  (DNS + TCP + TLS)\n\
  Server processing:    $(echo "%{time_starttransfer} - %{time_pretransfer}" | bc)s  (TTFB - request sent)\n\
  Response transfer:    $(echo "%{time_total} - %{time_starttransfer}" | bc)s\n\
\n\
HTTP Status:          %{http_code}\n\
Content Type:         %{content_type}\n\
Size Downloaded:      %{size_download} bytes\n\
Speed:                %{speed_download} bytes/sec\n\n" \
  -X POST "$BASE_URL/api/v1/nmt/inference" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"input\": [{\"source\": \"नमस्ते, आप कैसे हैं?\"}],
    \"config\": {
      \"serviceId\": \"$NMT_SERVICE_ID\",
      \"language\": {
        \"sourceLanguage\": \"hi\",
        \"targetLanguage\": \"en\"
      }
    },
    \"controlConfig\": {\"additionalProp1\": {\"dataTracking\": false}}
  }" \
  -s -o /tmp/nmt_response.json \
  -D /tmp/nmt_headers.txt

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RESPONSE HEADERS (check for timing info):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat /tmp/nmt_headers.txt | grep -iE "time|timing|duration|process|inference" || echo "  (no timing headers found)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 INTERPRETATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  • TTFB (time_starttransfer) = Total server processing"
echo "  • If server provides 'X-Inference-Time' header, you can calculate:"
echo "    Non-inference time = TTFB - X-Inference-Time"
echo "  • This gives you: auth + validation + pre/post-processing time"
echo ""
echo "Response saved to: /tmp/nmt_response.json"
echo "Headers saved to: /tmp/nmt_headers.txt"
