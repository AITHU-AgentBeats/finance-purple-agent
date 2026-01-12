#!/bin/bash

# Script to send queries to the Finance Purple Agent via message/send endpoint
# Usage: ./send_query.sh "Your question here"
#        ./send_query.sh                    # Will prompt for input

set -e

# Default values
SERVER_URL="${SERVER_URL:-http://127.0.0.1:9019}"
MESSAGE_ID="query-$(date +%s)"

# Get query from command line argument or prompt
if [ $# -eq 0 ]; then
    echo "Enter your query:"
    read -r QUERY
else
    QUERY="$*"
fi

if [ -z "$QUERY" ]; then
    echo "Error: Query cannot be empty"
    exit 1
fi

echo "Sending query to $SERVER_URL..."
echo "Query: $QUERY"
echo ""

# Send the request
RESPONSE=$(curl -s -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"message/send\",
    \"params\": {
      \"message\": {
        \"messageId\": \"$MESSAGE_ID\",
        \"role\": \"user\",
        \"parts\": [
          {
            \"kind\": \"text\",
            \"text\": \"$QUERY\"
          }
        ]
      }
    },
    \"id\": 1
  }")

# Check if response contains an error
if echo "$RESPONSE" | grep -q '"error"'; then
    echo "Error occurred:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

# Extract and display the response
echo "=== Agent Response ==="
echo "$RESPONSE" | python3 -c "
import sys
import json

try:
    data = json.load(sys.stdin)
    if 'result' in data and 'artifacts' in data['result']:
        for artifact in data['result']['artifacts']:
            for part in artifact.get('parts', []):
                if part.get('kind') == 'data' and 'response' in part.get('data', {}):
                    print(part['data']['response'])
                    print()
                elif part.get('kind') == 'text' and part.get('text') != 'complete':
                    print(part['text'])
    else:
        print(json.dumps(data, indent=2))
except Exception as e:
    print('Error parsing response:', e)
    sys.stdin.seek(0)
    print(sys.stdin.read())
" 2>/dev/null || echo "$RESPONSE" | python3 -m json.tool

# Display task status if available
echo ""
echo "=== Task Status ==="
echo "$RESPONSE" | python3 -c "
import sys
import json

try:
    data = json.load(sys.stdin)
    if 'result' in data:
        result = data['result']
        print(f\"Task ID: {result.get('id', 'N/A')}\")
        print(f\"Context ID: {result.get('contextId', 'N/A')}\")
        if 'status' in result:
            status = result['status']
            print(f\"Status: {status.get('state', 'N/A')}\")
            print(f\"Timestamp: {status.get('timestamp', 'N/A')}\")
except:
    pass
" 2>/dev/null
