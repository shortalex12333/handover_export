#!/bin/bash
# Test script for handover export API endpoints

BASE_URL="http://localhost:8000"

echo "==================================="
echo "Handover Export API - Endpoint Tests"
echo "==================================="

# Health check
echo -e "\n1. Testing health endpoint..."
curl -s "$BASE_URL/health" | python3 -m json.tool || echo "Failed"

# List handover entries
echo -e "\n2. Testing list handover entries..."
curl -s "$BASE_URL/api/v1/handover/entries" | python3 -m json.tool || echo "Failed"

# Create handover entry
echo -e "\n3. Testing create handover entry..."
curl -s -X POST "$BASE_URL/api/v1/handover/entries" \
  -H "Content-Type: application/json" \
  -d '{"narrative_text": "Engine room check completed successfully"}' | python3 -m json.tool || echo "Failed"

# List drafts
echo -e "\n4. Testing list handover drafts..."
curl -s "$BASE_URL/api/v1/handover/drafts" | python3 -m json.tool || echo "Failed"

# Generate draft
echo -e "\n5. Testing generate handover draft..."
curl -s -X POST "$BASE_URL/api/v1/handover/drafts/generate" \
  -H "Content-Type: application/json" \
  -d '{"outgoing_user_id": "00000000-0000-0000-0000-000000000001"}' | python3 -m json.tool || echo "Failed"

# List exports
echo -e "\n6. Testing list exports..."
curl -s "$BASE_URL/api/v1/handover/exports" | python3 -m json.tool || echo "Failed"

echo -e "\n==================================="
echo "Tests complete!"
echo "==================================="
