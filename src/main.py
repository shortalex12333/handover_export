"""
Handover Export Service - FastAPI Application
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .config import get_settings, Settings
from .graph.client import GraphClient
from .ai.openai_client import OpenAIClient
from .db.supabase_client import SupabaseClient
from .pipeline import EmailHandoverPipeline, PipelineConfig
from .pipeline.stages import (
    FetchEmailsStage,
    ExtractContentStage,
    ClassifyStage,
    GroupTopicsStage,
    MergeSummariesStage,
    DeduplicateStage,
    FormatOutputStage,
    ExportStage,
)
from .routers import handover_entries, handover_drafts, handover_signoff, handover_exports
from . import dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
_graph_client: Optional[GraphClient] = None
_openai_client: Optional[OpenAIClient] = None
_db_client: Optional[SupabaseClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global _graph_client, _openai_client, _db_client

    settings = get_settings()

    # Initialize clients
    if settings.azure:
        _graph_client = GraphClient(settings.azure)
        dependencies.set_graph_client(_graph_client)
        logger.info("Graph client initialized")

    if settings.openai_api_key:
        _openai_client = OpenAIClient(settings.openai_api_key)
        dependencies.set_openai_client(_openai_client)
        logger.info("OpenAI client initialized")

    if settings.test_tenant_supabase:
        _db_client = SupabaseClient(settings.test_tenant_supabase)
        dependencies.set_db_client(_db_client)
        logger.info("Supabase client initialized")

    yield

    # Cleanup
    logger.info("Shutting down")


app = FastAPI(
    title="Handover Export Service",
    description="Email-to-handover pipeline for CelesteOS",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(handover_entries.router)
app.include_router(handover_drafts.router)
app.include_router(handover_signoff.router)
app.include_router(handover_exports.router)


# Dependency injection
def get_graph_client() -> GraphClient:
    if not _graph_client:
        raise HTTPException(500, "Graph client not configured")
    return _graph_client


def get_openai_client() -> OpenAIClient:
    if not _openai_client:
        raise HTTPException(500, "OpenAI client not configured")
    return _openai_client


def get_db_client() -> SupabaseClient:
    if not _db_client:
        raise HTTPException(500, "Database client not configured")
    return _db_client


# Request/Response models
class PipelineRequest(BaseModel):
    query: Optional[str] = None
    days_back: int = 90
    max_emails: int = 500
    folder_id: Optional[str] = None
    yacht_id: Optional[str] = None
    user_id: Optional[str] = None


class PipelineResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    message: str
    meta: Optional[dict] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_stage: Optional[str] = None
    stage_progress: Optional[dict] = None
    error_message: Optional[str] = None


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "handover-export"
    }


# Pipeline endpoints
@app.post("/api/pipeline/run", response_model=PipelineResponse)
async def run_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    graph: GraphClient = Depends(get_graph_client),
    ai: OpenAIClient = Depends(get_openai_client),
    db: SupabaseClient = Depends(get_db_client)
):
    """Run the email-to-handover pipeline"""

    if not request.yacht_id or not request.user_id:
        raise HTTPException(400, "yacht_id and user_id are required")

    # Create job record
    job = await db.create_email_extraction_job(
        yacht_id=request.yacht_id,
        user_id=request.user_id,
        query=request.query,
        days_back=request.days_back,
        max_emails=request.max_emails
    )

    job_id = job.get("id")

    # Run pipeline in background
    background_tasks.add_task(
        _run_pipeline_task,
        job_id=job_id,
        config=PipelineConfig(
            query=request.query,
            days_back=request.days_back,
            max_emails=request.max_emails,
            folder_id=request.folder_id
        ),
        yacht_id=request.yacht_id,
        user_id=request.user_id,
        graph=graph,
        ai=ai,
        db=db
    )

    return PipelineResponse(
        success=True,
        job_id=job_id,
        message="Pipeline started"
    )


async def _run_pipeline_task(
    job_id: str,
    config: PipelineConfig,
    yacht_id: str,
    user_id: str,
    graph: GraphClient,
    ai: OpenAIClient,
    db: SupabaseClient
):
    """Background task to run the pipeline"""

    try:
        # Update job status
        await db.update_job_status(job_id, "running", "fetch")

        # Build pipeline
        pipeline = EmailHandoverPipeline(
            fetch_stage=FetchEmailsStage(graph),
            extract_stage=ExtractContentStage(),
            classify_stage=ClassifyStage(ai),
            group_stage=GroupTopicsStage(),
            merge_stage=MergeSummariesStage(ai),
            dedupe_stage=DeduplicateStage(),
            format_stage=FormatOutputStage(),
            export_stage=ExportStage()
        )

        # Progress callback
        async def on_progress(progress):
            await db.update_job_status(
                job_id,
                "running",
                progress.stage,
                {
                    "stage_number": progress.stage_number,
                    "total_stages": progress.total_stages,
                    "items_processed": progress.items_processed,
                    "items_total": progress.items_total,
                    "message": progress.message
                }
            )

        pipeline.on_progress(lambda p: on_progress(p))

        # Run pipeline
        report = await pipeline.run(config)

        # Create draft from report
        draft = await db.create_handover_draft(
            yacht_id=yacht_id,
            user_id=user_id,
            period_start=datetime.now().replace(hour=0, minute=0, second=0).isoformat(),
            period_end=datetime.now().isoformat(),
            title=f"Email Handover - {datetime.now().strftime('%Y-%m-%d')}"
        )

        draft_id = draft.get("id")

        # Add items to draft
        item_order = 1
        for category, handovers in report.sections.items():
            for h in handovers:
                await db.add_draft_item(
                    draft_id=draft_id,
                    section_bucket=h.presentation_bucket or category,
                    summary_text=f"**{h.subject}**\n\n{h.summary}",
                    item_order=item_order,
                    domain_code=h.domain_code,
                    is_critical=any(a.priority.value == "CRITICAL" for a in h.actions)
                )
                item_order += 1

        # Update job as completed
        await db.update_job_status(
            job_id,
            "completed",
            "complete",
            {
                "emails_processed": report.meta.get("totalEmails", 0),
                "sections_created": report.meta.get("totalSections", 0),
                "draft_id": draft_id
            }
        )

        logger.info(f"Pipeline completed for job {job_id}, draft {draft_id}")

    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}")
        await db.update_job_status(job_id, "failed", error_message=str(e))


@app.get("/api/pipeline/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: SupabaseClient = Depends(get_db_client)
):
    """Get job status"""

    result = db.client.table("email_extraction_jobs").select("*").eq("id", job_id).execute()

    if not result.data:
        raise HTTPException(404, "Job not found")

    job = result.data[0]

    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        current_stage=job.get("current_stage"),
        stage_progress=job.get("stage_progress"),
        error_message=job.get("error_message")
    )


@app.get("/api/pipeline/report/{job_id}", response_class=HTMLResponse)
async def get_job_report(
    job_id: str,
    db: SupabaseClient = Depends(get_db_client)
):
    """Get HTML report for completed job"""

    result = db.client.table("email_extraction_jobs").select("*").eq("id", job_id).execute()

    if not result.data:
        raise HTTPException(404, "Job not found")

    job = result.data[0]

    if job["status"] != "completed":
        raise HTTPException(400, f"Job is {job['status']}, not completed")

    draft_id = job.get("stage_progress", {}).get("draft_id")
    if not draft_id:
        raise HTTPException(404, "No draft created for this job")

    # Get draft items and build HTML
    items = await db.get_draft_items(draft_id)

    html_items = "".join([
        f'<div class="item"><p>{item["summary_text"]}</p></div>'
        for item in items
    ])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Handover Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .item {{ margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Handover Report</h1>
        {html_items}
    </body>
    </html>
    """

    return HTMLResponse(content=html)


# Direct pipeline execution (for testing)
@app.post("/api/pipeline/test")
async def test_pipeline(
    request: PipelineRequest,
    graph: GraphClient = Depends(get_graph_client),
    ai: OpenAIClient = Depends(get_openai_client)
):
    """Test pipeline execution (synchronous, for development)"""

    pipeline = EmailHandoverPipeline(
        fetch_stage=FetchEmailsStage(graph),
        extract_stage=ExtractContentStage(),
        classify_stage=ClassifyStage(ai),
        group_stage=GroupTopicsStage(),
        merge_stage=MergeSummariesStage(ai),
        dedupe_stage=DeduplicateStage(),
        format_stage=FormatOutputStage(),
        export_stage=ExportStage()
    )

    config = PipelineConfig(
        query=request.query,
        days_back=request.days_back,
        max_emails=min(request.max_emails, 50),  # Limit for testing
        folder_id=request.folder_id
    )

    report = await pipeline.run(config)

    return {
        "success": True,
        "meta": report.meta,
        "sections": list(report.sections.keys()),
        "html_length": len(report.html)
    }
