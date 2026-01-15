"""
Handover Drafts API Router
Handles draft generation, review, editing, and state transitions
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import UUID4

from ..models.handover import (
    HandoverDraftGenerate,
    HandoverDraftResponse,
    HandoverDraftSection,
    HandoverDraftItem,
    HandoverDraftItemEdit,
    HandoverDraftItemMerge,
    HandoverDraftState,
    PresentationBucket
)
from ..db.supabase_client import SupabaseClient
from ..dependencies import get_db_client, get_current_user

router = APIRouter(prefix="/api/v1/handover/drafts", tags=["Handover Drafts"])


@router.post("/generate", response_model=HandoverDraftResponse, status_code=201)
async def generate_handover_draft(
    request: HandoverDraftGenerate,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a handover draft from candidate entries

    Rules:
    - If DRAFT exists for this user → return existing
    - If no new entries → return existing draft
    - If draft in ACCEPTED or SIGNED → reject with error
    - Otherwise, create new DRAFT

    This endpoint:
    1. Fetches all candidate handover entries
    2. Groups by presentation bucket
    3. Creates draft with sections
    4. Returns draft in DRAFT state
    """

    # Check for existing active draft
    # In production: Query database for existing draft

    # Create new draft
    draft_id = UUID("00000000-0000-0000-0000-000000000001")

    # Mock draft response
    draft_data = {
        "id": draft_id,
        "yacht_id": current_user["yacht_id"],
        "outgoing_user_id": request.outgoing_user_id,
        "incoming_user_id": request.incoming_user_id,
        "period_start": request.period_start or datetime.now(),
        "period_end": request.period_end or datetime.now(),
        "shift_type": request.shift_type,
        "state": HandoverDraftState.DRAFT,
        "sections": [],
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    return HandoverDraftResponse(**draft_data)


@router.get("/{draft_id}", response_model=HandoverDraftResponse)
async def get_handover_draft(
    draft_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a handover draft with all sections and items

    Returns:
    - Draft metadata (state, participants, period)
    - All sections (buckets) with items
    - Risk flags
    - Edit history
    """

    # In production: Fetch from database with joins
    # For now, return mock data

    draft_data = {
        "id": draft_id,
        "yacht_id": current_user["yacht_id"],
        "outgoing_user_id": current_user["id"],
        "incoming_user_id": None,
        "period_start": datetime.now(),
        "period_end": datetime.now(),
        "shift_type": "day",
        "state": HandoverDraftState.DRAFT,
        "sections": [
            {
                "id": UUID("00000000-0000-0000-0000-000000000001"),
                "bucket": PresentationBucket.Command,
                "section_order": 1,
                "items": []
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000002"),
                "bucket": PresentationBucket.Engineering,
                "section_order": 2,
                "items": []
            }
        ],
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    return HandoverDraftResponse(**draft_data)


@router.post("/{draft_id}/review")
async def enter_review_state(
    draft_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Transition draft from DRAFT → IN_REVIEW

    Rules:
    - Only allowed if current state = DRAFT
    - Locks draft for review session
    - Enables editing and merging of items
    """

    # In production: Check state, update to IN_REVIEW

    return {
        "success": True,
        "message": "Draft entered review state",
        "draft_id": str(draft_id),
        "new_state": "IN_REVIEW"
    }


@router.patch("/{draft_id}/items/{item_id}", response_model=HandoverDraftItem)
async def edit_draft_item(
    draft_id: UUID4,
    item_id: UUID4,
    edit: HandoverDraftItemEdit,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Edit a draft item's text

    Rules:
    - Only allowed in IN_REVIEW state
    - Stores edit history in handover_draft_edits table
    - Cannot modify classification or source references
    - Increments edit_count

    Payload:
    - edited_text: The new text
    - edit_reason: Optional reason for the edit
    """

    # In production: Check state, update item, log edit

    updated_item = {
        "id": item_id,
        "summary_text": edit.edited_text,
        "item_order": 1,
        "domain_code": "ENG-01",
        "is_critical": False,
        "source_entry_ids": [],
        "edit_count": 1,
        "created_at": datetime.now()
    }

    return HandoverDraftItem(**updated_item)


@router.post("/{draft_id}/items/merge", response_model=HandoverDraftItem)
async def merge_draft_items(
    draft_id: UUID4,
    merge_request: HandoverDraftItemMerge,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Merge multiple draft items into one

    Rules:
    - Only allowed in IN_REVIEW state
    - Source references are combined
    - Original items retained as merged history (soft delete)
    - New merged item created

    Payload:
    - item_ids: Array of item IDs to merge (min 2)
    - merged_text: The combined narrative
    """

    # In production: Validate items exist, create merged item, mark originals as merged

    merged_item = {
        "id": UUID("00000000-0000-0000-0000-000000000099"),
        "summary_text": merge_request.merged_text,
        "item_order": 1,
        "domain_code": "ENG-01",
        "is_critical": False,
        "source_entry_ids": [],
        "edit_count": 0,
        "created_at": datetime.now()
    }

    return HandoverDraftItem(**merged_item)


@router.delete("/{draft_id}/items/{item_id}")
async def delete_draft_item(
    draft_id: UUID4,
    item_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove an item from the draft (soft delete)

    Rules:
    - Only allowed in IN_REVIEW state
    - Item is marked as suppressed, not deleted
    - Original entry remains in handover_entries table
    """

    # In production: Mark item as suppressed

    return {
        "success": True,
        "message": "Item removed from draft",
        "item_id": str(item_id)
    }


@router.get("", response_model=List[HandoverDraftResponse])
async def list_handover_drafts(
    state: Optional[HandoverDraftState] = None,
    skip: int = 0,
    limit: int = 100,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    List handover drafts with optional state filtering

    Query params:
    - state: Filter by draft state (DRAFT, IN_REVIEW, ACCEPTED, SIGNED, EXPORTED)
    - skip: Pagination offset
    - limit: Max results
    """

    # In production: Query database with filters
    return []


@router.get("/history", response_model=List[HandoverDraftResponse])
async def get_handover_history(
    skip: int = 0,
    limit: int = 50,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Get past signed handovers for this vessel

    Returns only SIGNED and EXPORTED drafts, ordered by period_end DESC
    """

    # In production: Query with state filter and order by
    return []
