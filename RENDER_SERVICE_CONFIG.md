# Render Service Configuration

**Service ID:** srv-d5k0avchg0os738oel2g
**Repository:** https://github.com/shortalex12333/handover_export
**Branch:** main

---

## ❌ Current Configuration (WRONG)

```
Runtime:        python
Root Directory: (empty)
Build Command:  pip install -r requirements.txt
Start Command:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
Dockerfile:     N/A
```

**Problem:** Using Python runtime which doesn't have WeasyPrint system dependencies.

---

## ✅ Correct Configuration (DOCKER)

When recreating the service, use these settings:

### Basic Settings
```
Service Name:   handover-export (or celeste-handover-export)
Repository:     https://github.com/shortalex12333/handover_export
Branch:         main
Root Directory: (leave empty)
```

### Runtime Configuration
```
Runtime:        Docker
Dockerfile Path: ./Dockerfile
```

### Docker Details
**Build Command:**  *(not needed - Dockerfile handles this)*
**Start Command:**  *(not needed - defined in Dockerfile CMD)*

The Dockerfile contains:
- Build: `RUN pip install --no-cache-dir -r requirements.txt`
- Start: `CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}`

### Health Check
```
Health Check Path: /health
```

### Plan & Region
```
Plan:   Starter (free tier)
Region: Oregon (or your preferred region)
```

---

## Environment Variables (13 Required)

Set these in the Render dashboard:

### Azure OAuth (3 vars)
```
AZURE_CLIENT_ID         = [Already set in Render dashboard]
AZURE_CLIENT_SECRET     = [Already set in Render dashboard]
AZURE_TENANT_ID         = [Already set in Render dashboard]
```

### Master Supabase (3 vars)
```
MASTER_SUPABASE_URL         = [Already set in Render dashboard]
MASTER_SUPABASE_SERVICE_KEY = [Already set in Render dashboard]
MASTER_SUPABASE_JWT_SECRET  = [Already set in Render dashboard]
```

### Tenant Supabase (3 vars)
```
yTEST_YACHT_001_SUPABASE_URL         = [Already set in Render dashboard]
yTEST_YACHT_001_SUPABASE_SERVICE_KEY = [Already set in Render dashboard]
yTEST_YACHT_001_SUPABASE_JWT_SECRET  = [Already set in Render dashboard]
```

### OpenAI (1 var)
```
OPENAI_API_KEY = [Already set in Render dashboard]
```

**Note:** All 13 environment variables are already configured in the current Render service.
When recreating, copy them from the old service or refer to your local `.env` file.

### Application (3 vars)
```
ENVIRONMENT = production
LOG_LEVEL   = INFO
PYTHONPATH  = /app
```

**Note:** For Docker runtime, PYTHONPATH must be `/app` (the container's working directory), not `/opt/render/project/src`.

---

## Step-by-Step Recreation Guide

### 1. Delete Current Service
1. Go to https://dashboard.render.com/web/srv-d5k0avchg0os738oel2g
2. Click **Settings** → **Delete Service**
3. Confirm deletion

### 2. Create New Service
1. Go to https://dashboard.render.com/
2. Click **New +** → **Web Service**
3. Connect to GitHub repository: `shortalex12333/handover_export`
4. Configure:
   - **Name:** `handover-export`
   - **Region:** Oregon (or preferred)
   - **Branch:** `main`
   - **Root Directory:** *(leave empty)*
   - **Runtime:** **Docker** ← CRITICAL!
   - **Dockerfile Path:** `./Dockerfile`
   - **Health Check Path:** `/health`
   - **Plan:** Free (Starter)

### 3. Add Environment Variables
Click **Environment** tab and add all 13 variables listed above.

### 4. Deploy
Click **Create Web Service** - it will auto-deploy from main branch.

### 5. Verify
Once deployed, check:
- Health: `https://[your-service].onrender.com/health`
- API Docs: `https://[your-service].onrender.com/docs`

---

## Expected Result

After recreation with Docker runtime:

✅ Build phase: ~2-3 minutes (installs system deps + Python packages)
✅ Deploy phase: ~30 seconds (starts container)
✅ Health check: Returns `{"status":"healthy"}`
✅ Service: Live and accessible

**Verified:** Docker image tested locally and works perfectly.

---

Generated: 2026-01-15 13:10 UTC
