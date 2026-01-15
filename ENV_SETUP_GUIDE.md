# Environment Variables Setup Guide

**Date:** January 14, 2026
**Service:** handover_export (Render deployment)

---

## ✅ Local Environment (.env) - UPDATED

The local `.env` file has been updated with correct credentials:

```bash
# Master Supabase
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
MASTER_SUPABASE_JWT_SECRET=wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/ml...
MASTER_DB_PASSWORD=@-Ei-9Pa.uENn6g

# Tenant Supabase (Test Yacht)
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
yTEST_YACHT_001_SUPABASE_JWT_SECRET=ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su1...
TENANT_1_DB_PASSWORD=@-Ei-9Pa.uENn6g

# Test User
TEST_USER_EMAIL=x@alex-short.com
TEST_USER_PASSWORD=Password2!
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598

# Azure OAuth
AZURE_CLIENT_ID=[REDACTED - See env vars file]
AZURE_CLIENT_SECRET=[REDACTED - See env vars file]
AZURE_TENANT_ID=[REDACTED - See env vars file]

# OpenAI
OPENAI_API_KEY=[REDACTED - See env vars file]

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

✅ **Status:** Local .env file is ready to use

---

## 🔄 Render Production Environment Variables

### **Service Details**
- **Service ID:** srv-d5fr5hre5dus73d3gdn0
- **Service Name:** handover-export
- **Dashboard:** https://dashboard.render.com/web/srv-d5fr5hre5dus73d3gdn0

### **Required Environment Variables**

The following variables need to be set in Render Dashboard:

#### **Supabase - Master DB**
```
MASTER_SUPABASE_URL = https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q
MASTER_SUPABASE_JWT_SECRET = wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw==
MASTER_DB_PASSWORD = @-Ei-9Pa.uENn6g
```

#### **Supabase - Tenant DB (Test Yacht)**
```
yTEST_YACHT_001_SUPABASE_URL = https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY
yTEST_YACHT_001_SUPABASE_JWT_SECRET = ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==
TENANT_1_DB_PASSWORD = @-Ei-9Pa.uENn6g
```

#### **Azure OAuth (Email Integration)**
```
AZURE_CLIENT_ID = [Get from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md]
AZURE_CLIENT_SECRET = [Get from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md]
AZURE_TENANT_ID = [Get from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md]
```

#### **OpenAI (AI Classification)**
```
OPENAI_API_KEY = [Get from /Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/env vars.md]
```

#### **Test User Credentials**
```
TEST_USER_EMAIL = x@alex-short.com
TEST_YACHT_ID = 85fe1119-b04c-41ac-80f1-829d23322598
```

#### **Application Settings** (Already set in render.yaml)
```
ENVIRONMENT = production
LOG_LEVEL = INFO
PYTHONPATH = /opt/render/project/src
```

---

## 📝 How to Set Variables in Render

### **Option 1: Via Render Dashboard (Recommended)**

1. Go to: https://dashboard.render.com/web/srv-d5fr5hre5dus73d3gdn0
2. Click on **"Environment"** tab in left sidebar
3. For each variable above:
   - Click **"Add Environment Variable"**
   - Enter **Key** (exact name from above)
   - Enter **Value** (exact value from above)
   - Click **"Save Changes"**
4. After all variables are added, click **"Manual Deploy"** → **"Deploy latest commit"**

### **Option 2: Via Render API (Automated)**

Run the provided script:
```bash
chmod +x scripts/update_render_env.sh
./scripts/update_render_env.sh
```

Then manually trigger a redeploy in the dashboard.

---

## 🔍 Verification Checklist

After setting environment variables:

### **1. Check Render Deployment**
- [ ] Visit: https://dashboard.render.com/web/srv-d5fr5hre5dus73d3gdn0
- [ ] Verify all variables are set (should show 17 total)
- [ ] Check deployment logs for errors

### **2. Test Health Endpoint**
```bash
curl https://handover-export.onrender.com/health
# Expected: {"status":"healthy","timestamp":"..."}
```

### **3. Test API Docs**
- [ ] Visit: https://handover-export.onrender.com/docs
- [ ] Should show FastAPI Swagger UI
- [ ] Should list all 19 endpoints

### **4. Test Database Connection**
```bash
curl https://handover-export.onrender.com/api/v1/handover/drafts
# Should return [] (empty array) or actual drafts if data exists
```

### **5. Check Logs**
Look for these success messages in Render logs:
```
Graph client initialized
OpenAI client initialized
Supabase client initialized
Application startup complete
```

---

## 🐛 Troubleshooting

### **Error: "Graph client not configured"**
**Solution:** Ensure AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID are set

### **Error: "OpenAI client not configured"**
**Solution:** Ensure OPENAI_API_KEY is set

### **Error: "Database client not configured"**
**Solution:** Ensure all yTEST_YACHT_001_* variables are set

### **Error: "Failed to connect to database"**
**Solution:**
1. Check Supabase URL is accessible: `curl https://vzsohavtuotocgrfkfyd.supabase.co`
2. Verify service key is correct
3. Check database password matches

### **Error: Application won't start**
**Solution:**
1. Check Render logs for specific error
2. Verify all required dependencies in requirements.txt
3. Ensure Python version is 3.9+

---

## 🔐 Security Notes

- ⚠️ Never commit `.env` file to git (already in .gitignore)
- ⚠️ Rotate secrets if they're ever exposed publicly
- ⚠️ Use Render's secret management (variables are encrypted at rest)
- ⚠️ Database passwords are same for master and tenant (`@-Ei-9Pa.uENn6g`)

---

## 📊 Current Status

| Item | Status |
|------|--------|
| **Local .env** | ✅ Updated with correct credentials |
| **Render env vars** | ⏳ Pending manual setup |
| **Database migrations** | ⏳ Pending (apply via Supabase Dashboard) |
| **Health check** | ⏳ Verify after Render env setup |

---

**Next Steps:**
1. Set Render environment variables (Option 1 or 2 above)
2. Trigger manual redeploy
3. Verify health endpoint
4. Apply database migrations
5. Run full test suite

---

**Generated:** 2026-01-14
**File Location:** `/Users/celeste7/Documents/handover_export/ENV_SETUP_GUIDE.md`
