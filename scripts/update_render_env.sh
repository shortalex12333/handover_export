#!/bin/bash
# Update Render environment variables via API
# Usage: ./scripts/update_render_env.sh

set -e

# Render credentials from env vars file
RENDER_API_KEY="rnd_8BakHjSO36rN90gAbQHgfqTnFjJY"
RENDER_SERVICE_ID="srv-d5fr5hre5dus73d3gdn0"

# Base URL
RENDER_API_URL="https://api.render.com/v1"

echo "🚀 Updating Render environment variables..."
echo "Service ID: ${RENDER_SERVICE_ID}"
echo ""

# Function to update or create env var
update_env_var() {
    local key=$1
    local value=$2

    echo "Setting ${key}..."

    curl -s -X PUT \
        "${RENDER_API_URL}/services/${RENDER_SERVICE_ID}/env-vars/${key}" \
        -H "Authorization: Bearer ${RENDER_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"value\": \"${value}\"}" > /dev/null

    if [ $? -eq 0 ]; then
        echo "✅ ${key} updated"
    else
        echo "❌ Failed to update ${key}"
    fi
}

# Master Supabase
update_env_var "MASTER_SUPABASE_URL" "https://qvzmkaamzaqxpzbewjxe.supabase.co"
update_env_var "MASTER_SUPABASE_SERVICE_KEY" "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q"
update_env_var "MASTER_SUPABASE_JWT_SECRET" "wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw=="
update_env_var "MASTER_DB_PASSWORD" "@-Ei-9Pa.uENn6g"

# Tenant Supabase
update_env_var "yTEST_YACHT_001_SUPABASE_URL" "https://vzsohavtuotocgrfkfyd.supabase.co"
update_env_var "yTEST_YACHT_001_SUPABASE_SERVICE_KEY" "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
update_env_var "yTEST_YACHT_001_SUPABASE_JWT_SECRET" "ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg=="
update_env_var "TENANT_1_DB_PASSWORD" "@-Ei-9Pa.uENn6g"

# Azure OAuth - Get values from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md
# update_env_var "AZURE_CLIENT_ID" "YOUR_AZURE_CLIENT_ID"
# update_env_var "AZURE_CLIENT_SECRET" "YOUR_AZURE_CLIENT_SECRET"
# update_env_var "AZURE_TENANT_ID" "YOUR_AZURE_TENANT_ID"

# OpenAI - Get value from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md
# update_env_var "OPENAI_API_KEY" "YOUR_OPENAI_API_KEY"

echo ""
echo "⚠️  Azure and OpenAI credentials commented out for security"
echo "📝  Get values from: /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md"
echo "    Uncomment and replace placeholders before running"

# Test credentials
update_env_var "TEST_USER_EMAIL" "x@alex-short.com"
update_env_var "TEST_YACHT_ID" "85fe1119-b04c-41ac-80f1-829d23322598"

echo ""
echo "✅ All environment variables updated!"
echo ""
echo "⚠️  Note: Render may require a manual redeploy to pick up changes"
echo "Visit: https://dashboard.render.com/web/${RENDER_SERVICE_ID}"
