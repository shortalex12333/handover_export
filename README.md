# Handover Export Service

Email-to-handover pipeline for CelesteOS yacht management system.

## Overview

This service transforms emails from Microsoft Graph API into structured handover entries for crew shift changes on yachts.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EMAIL-TO-HANDOVER PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   STAGE 1   │    │   STAGE 2   │    │   STAGE 3   │    │   STAGE 4   │       │
│  │   FETCH     │───>│   EXTRACT   │───>│  CLASSIFY   │───>│   GROUP     │       │
│  │   EMAILS    │    │   CONTENT   │    │   (AI)      │    │   BY TOPIC  │       │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   STAGE 5   │    │   STAGE 6   │    │   STAGE 7   │    │   STAGE 8   │       │
│  │   MERGE     │───>│  DEDUPE     │───>│   FORMAT    │───>│   EXPORT    │       │
│  │   (AI)      │    │             │    │   OUTPUT    │    │   (HTML/PDF)│       │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run the server: `uvicorn src.main:app --reload`

## API Endpoints

- `GET /health` - Health check
- `POST /api/pipeline/run` - Start pipeline job
- `GET /api/pipeline/job/{job_id}` - Get job status
- `GET /api/pipeline/report/{job_id}` - Get HTML report

## Database Migrations

Migrations are in `supabase/migrations/`. Apply with Supabase CLI:

```bash
supabase db push
```

## Testing

```bash
pytest tests/ -v
```

## Deployment

Deployed to Render via GitHub integration. See `render.yaml` for configuration.

## Environment Variables

See `.env.example` for required environment variables.
