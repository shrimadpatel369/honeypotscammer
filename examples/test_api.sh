#!/bin/bash

# Test script for the Honeypot API
# Make sure to set your API key in .env file

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

API_URL="http://localhost:8000"
API_KEY="${API_KEY}"

echo "========================================"
echo "Honeypot API Test Script"
echo "========================================"

# Test 1: Health Check
echo -e "\n${GREEN}Test 1: Health Check${NC}"
curl -s -X GET "${API_URL}/health" | jq .

# Test 2: First Message (Scam Detection)
echo -e "\n${GREEN}Test 2: First Message (Scam Detection)${NC}"
RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/honeypot" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d @examples/request_first_message.json)

echo "$RESPONSE" | jq .

# Extract session ID and response for next test
SESSION_ID=$(echo "$RESPONSE" | jq -r '.sessionId')
echo -e "\nSession ID: ${SESSION_ID}"

# Test 3: Follow-up Message
echo -e "\n${GREEN}Test 3: Follow-up Message${NC}"
curl -s -X POST "${API_URL}/api/v1/honeypot" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d @examples/request_followup_message.json | jq .

# Test 4: Get Session Details
echo -e "\n${GREEN}Test 4: Get Session Details${NC}"
curl -s -X GET "${API_URL}/api/v1/sessions/${SESSION_ID}" \
  -H "x-api-key: ${API_KEY}" | jq .

# Test 5: List All Sessions
echo -e "\n${GREEN}Test 5: List All Sessions${NC}"
curl -s -X GET "${API_URL}/api/v1/sessions?limit=5" \
  -H "x-api-key: ${API_KEY}" | jq .

echo -e "\n========================================"
echo -e "${GREEN}All tests completed!${NC}"
echo "========================================"
