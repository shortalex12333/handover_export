"""
Handover Exports API Router
Handles PDF/HTML/Email export of signed handover drafts
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import UUID4

from ..models.handover import (
    HandoverExportRequest,
    HandoverExportResponse,
    ExportType,
    HandoverDraftState
)
from ..db.supabase_client import SupabaseClient
from ..dependencies import get_db_client, get_current_user
from ..services.exporter import HandoverExporter

router = APIRouter(prefix="/api/v1/handover", tags=["Handover Exports"])


@router.post("/drafts/{draft_id}/export", response_model=HandoverExportResponse, status_code=201)
async def export_handover_draft(
    draft_id: UUID4,
    request: HandoverExportRequest,
    background_tasks: BackgroundTasks,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Request export of a signed handover draft

    Export types:
    - pdf: Generate PDF document
    - html: Generate HTML document
    - email: Send via email to recipients

    Rules:
    - Only allowed if draft state = SIGNED
    - Creates export record in database
    - Triggers background rendering job
    - Returns export record with job ID

    For email exports, requires recipients array.
    """

    if request.export_type == ExportType.email and not request.recipients:
        raise HTTPException(400, "Recipients required for email export")

    # Initialize exporter
    exporter = HandoverExporter(db)

    try:
        # Export based on type
        if request.export_type == ExportType.pdf:
            export_id = await exporter.export_to_pdf(
                draft_id=str(draft_id),
                yacht_id=current_user["yacht_id"]
            )
        elif request.export_type == ExportType.html:
            export_id = await exporter.export_to_html(
                draft_id=str(draft_id),
                yacht_id=current_user["yacht_id"]
            )
        elif request.export_type == ExportType.email:
            export_id = await exporter.export_to_email(
                draft_id=str(draft_id),
                yacht_id=current_user["yacht_id"],
                recipients=request.recipients
            )
        else:
            raise HTTPException(400, f"Unknown export type: {request.export_type}")

        # Fetch export record
        result = db.client.table("handover_exports") \
            .select("*") \
            .eq("id", export_id) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(500, "Failed to fetch export record")

        return HandoverExportResponse(**result.data)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/exports/{export_id}", response_model=HandoverExportResponse)
async def get_export(
    export_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Get export record with download URL

    Returns:
    - Export metadata
    - Time-limited signed URL for download (if PDF/HTML)
    - Email delivery status (if email)
    """

    # Fetch export record
    result = db.client.table("handover_exports") \
        .select("*") \
        .eq("id", str(export_id)) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(404, f"Export {export_id} not found")

    export_data = result.data

    # If file URL exists and is from Supabase Storage, generate signed URL
    if export_data.get("file_url") and "supabase" in export_data["file_url"]:
        # Generate time-limited signed URL (24 hours)
        try:
            # Extract path from URL
            file_path = export_data["file_url"].split("/handovers/")[-1]
            signed_url = db.client.storage.from_("handover-exports").create_signed_url(
                f"handovers/{file_path}",
                expires_in=86400  # 24 hours
            )
            export_data["file_url"] = signed_url.get("signedURL", export_data["file_url"])
        except:
            # If signed URL generation fails, keep original URL
            pass

    return HandoverExportResponse(**export_data)


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Download export file directly

    Returns PDF or HTML file with appropriate content-type.
    """

    # Fetch export record
    result = db.client.table("handover_exports") \
        .select("*") \
        .eq("id", str(export_id)) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(404, f"Export {export_id} not found")

    export_data = result.data

    # Email exports don't have files to download
    if export_data["export_type"] == "email":
        raise HTTPException(400, "Email exports cannot be downloaded. Use GET /exports/{id} for email status.")

    # Verify file URL exists
    if not export_data.get("file_url"):
        raise HTTPException(404, "Export file not found in storage")

    # For Supabase Storage, generate download URL
    if "supabase" in export_data["file_url"]:
        try:
            file_path = export_data["file_url"].split("/handovers/")[-1]
            signed_url_response = db.client.storage.from_("handover-exports").create_signed_url(
                f"handovers/{file_path}",
                expires_in=3600  # 1 hour for download
            )
            download_url = signed_url_response.get("signedURL")

            if download_url:
                # Redirect to signed URL for download
                return RedirectResponse(url=download_url)
        except Exception as e:
            raise HTTPException(500, f"Failed to generate download URL: {str(e)}")

    # If not Supabase Storage, return the direct URL as redirect
    return RedirectResponse(url=export_data["file_url"])


@router.get("/signed/{draft_id}")
async def get_signed_handover(
    draft_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Get signed handover snapshot metadata

    Returns:
    - Signed draft metadata
    - Storage URLs (time-limited)
    - Signoff records
    """

    # Fetch draft
    draft_result = db.client.table("handover_drafts") \
        .select("""
            *,
            outgoing_user:user_profiles!outgoing_user_id(id, full_name, role),
            incoming_user:user_profiles!incoming_user_id(id, full_name, role)
        """) \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not draft_result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    draft = draft_result.data

    # Verify draft is signed
    if draft["state"] not in ["SIGNED", "EXPORTED"]:
        raise HTTPException(400, f"Draft is not signed. Current state: {draft['state']}")

    # Fetch signoffs
    signoffs_result = db.client.table("handover_signoffs") \
        .select("""
            *,
            user:user_profiles(id, full_name, role)
        """) \
        .eq("draft_id", str(draft_id)) \
        .order("signed_at") \
        .execute()

    # Fetch exports
    exports_result = db.client.table("handover_exports") \
        .select("*") \
        .eq("draft_id", str(draft_id)) \
        .order("created_at", desc=True) \
        .execute()

    # Generate signed URLs for exports
    exports = []
    for export in exports_result.data or []:
        if export.get("file_url") and "supabase" in export["file_url"]:
            try:
                file_path = export["file_url"].split("/handovers/")[-1]
                signed_url_response = db.client.storage.from_("handover-exports").create_signed_url(
                    f"handovers/{file_path}",
                    expires_in=86400  # 24 hours
                )
                export["file_url"] = signed_url_response.get("signedURL", export["file_url"])
            except:
                pass
        exports.append(export)

    return {
        "draft": draft,
        "signoffs": signoffs_result.data or [],
        "exports": exports
    }


@router.get("/exports", response_model=List[HandoverExportResponse])
async def list_exports(
    draft_id: Optional[UUID4] = None,
    export_type: Optional[ExportType] = None,
    skip: int = 0,
    limit: int = 100,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    List all exports with optional filtering

    Query params:
    - draft_id: Filter by specific draft
    - export_type: Filter by export type (pdf, html, email)
    - skip: Pagination offset
    - limit: Max results
    """

    # Build query - filter by yacht_id through draft relationship
    # First, get draft IDs for this yacht
    drafts_result = db.client.table("handover_drafts") \
        .select("id") \
        .eq("yacht_id", current_user["yacht_id"]) \
        .execute()

    draft_ids = [draft["id"] for draft in drafts_result.data or []]

    if not draft_ids:
        return []

    # Build exports query
    query = db.client.table("handover_exports") \
        .select("*") \
        .in_("draft_id", draft_ids)

    # Apply filters
    if draft_id:
        query = query.eq("draft_id", str(draft_id))

    if export_type:
        query = query.eq("export_type", export_type.value)

    # Apply pagination
    query = query.range(skip, skip + limit - 1) \
        .order("created_at", desc=True)

    result = query.execute()

    exports = [HandoverExportResponse(**export) for export in result.data or []]

    return exports
