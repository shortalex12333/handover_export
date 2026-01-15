"""
Handover Drafts API Router
Handles draft generation, review, editing, and state transitions
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

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
from ..services.draft_generator import DraftGenerator

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

    # Initialize draft generator
    generator = DraftGenerator(db)

    # Generate draft
    draft_id = await generator.generate_draft(
        yacht_id=current_user["yacht_id"],
        outgoing_user_id=str(request.outgoing_user_id),
        incoming_user_id=str(request.incoming_user_id) if request.incoming_user_id else None,
        period_start=request.period_start,
        period_end=request.period_end,
        shift_type=request.shift_type
    )

    # Fetch created draft
    result = db.client.table("handover_drafts") \
        .select("""
            *,
            outgoing_user:user_profiles!outgoing_user_id(id, full_name),
            incoming_user:user_profiles!incoming_user_id(id, full_name)
        """) \
        .eq("id", draft_id) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(500, "Failed to fetch created draft")

    # Fetch sections
    sections_result = db.client.table("handover_draft_sections") \
        .select("id, section_bucket, section_order") \
        .eq("draft_id", draft_id) \
        .order("section_order") \
        .execute()

    sections = []
    for section in sections_result.data or []:
        # Fetch items for section
        items_result = db.client.table("handover_draft_items") \
            .select("*") \
            .eq("section_id", section["id"]) \
            .order("item_order") \
            .execute()

        sections.append(HandoverDraftSection(
            id=section["id"],
            bucket=PresentationBucket(section["section_bucket"]),
            section_order=section["section_order"],
            items=[HandoverDraftItem(**item) for item in items_result.data or []]
        ))

    draft_response = HandoverDraftResponse(
        **result.data,
        sections=sections
    )

    return draft_response


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

    # Fetch draft with user details
    result = db.client.table("handover_drafts") \
        .select("""
            *,
            outgoing_user:user_profiles!outgoing_user_id(id, full_name),
            incoming_user:user_profiles!incoming_user_id(id, full_name)
        """) \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    # Fetch sections
    sections_result = db.client.table("handover_draft_sections") \
        .select("id, section_bucket, section_order") \
        .eq("draft_id", str(draft_id)) \
        .order("section_order") \
        .execute()

    sections = []
    for section in sections_result.data or []:
        # Fetch items for section
        items_result = db.client.table("handover_draft_items") \
            .select("*") \
            .eq("section_id", section["id"]) \
            .order("item_order") \
            .execute()

        sections.append(HandoverDraftSection(
            id=section["id"],
            bucket=PresentationBucket(section["section_bucket"]),
            section_order=section["section_order"],
            items=[HandoverDraftItem(**item) for item in items_result.data or []]
        ))

    draft_response = HandoverDraftResponse(
        **result.data,
        sections=sections
    )

    return draft_response


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

    # Fetch current draft
    result = db.client.table("handover_drafts") \
        .select("id, state") \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    # Validate current state
    if result.data["state"] != "DRAFT":
        raise HTTPException(
            400,
            f"Cannot enter review from state {result.data['state']}. Must be DRAFT."
        )

    # Update to IN_REVIEW
    update_result = db.client.table("handover_drafts") \
        .update({"state": "IN_REVIEW", "updated_at": datetime.now().isoformat()}) \
        .eq("id", str(draft_id)) \
        .execute()

    if not update_result.data:
        raise HTTPException(500, "Failed to update draft state")

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

    # Verify draft is in IN_REVIEW state
    draft_result = db.client.table("handover_drafts") \
        .select("id, state") \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not draft_result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    if draft_result.data["state"] != "IN_REVIEW":
        raise HTTPException(
            400,
            f"Cannot edit items in state {draft_result.data['state']}. Must be IN_REVIEW."
        )

    # Fetch current item
    item_result = db.client.table("handover_draft_items") \
        .select("*") \
        .eq("id", str(item_id)) \
        .single() \
        .execute()

    if not item_result.data:
        raise HTTPException(404, f"Item {item_id} not found")

    current_item = item_result.data

    # Log edit to history table
    db.client.table("handover_draft_edits").insert({
        "id": str(uuid4()),
        "item_id": str(item_id),
        "editor_user_id": current_user["id"],
        "original_text": current_item["summary_text"],
        "edited_text": edit.edited_text,
        "edit_reason": edit.edit_reason,
        "created_at": datetime.now().isoformat()
    }).execute()

    # Update item
    update_result = db.client.table("handover_draft_items") \
        .update({
            "summary_text": edit.edited_text,
            "edit_count": current_item.get("edit_count", 0) + 1
        }) \
        .eq("id", str(item_id)) \
        .execute()

    if not update_result.data:
        raise HTTPException(500, "Failed to update item")

    return HandoverDraftItem(**update_result.data[0])


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

    if len(merge_request.item_ids) < 2:
        raise HTTPException(400, "Must provide at least 2 items to merge")

    # Verify draft is in IN_REVIEW state
    draft_result = db.client.table("handover_drafts") \
        .select("id, state") \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not draft_result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    if draft_result.data["state"] != "IN_REVIEW":
        raise HTTPException(
            400,
            f"Cannot merge items in state {draft_result.data['state']}. Must be IN_REVIEW."
        )

    # Fetch all items to merge
    items_result = db.client.table("handover_draft_items") \
        .select("*") \
        .in_("id", [str(item_id) for item_id in merge_request.item_ids]) \
        .execute()

    if not items_result.data or len(items_result.data) != len(merge_request.item_ids):
        raise HTTPException(404, "One or more items not found")

    items = items_result.data

    # Combine source entry IDs
    combined_source_ids = []
    section_id = None
    is_critical = False
    domain_code = items[0].get("domain_code")

    for item in items:
        if section_id is None:
            section_id = item["section_id"]
        combined_source_ids.extend(item.get("source_entry_ids", []))
        if item.get("is_critical"):
            is_critical = True

    # Create new merged item
    merged_item_data = {
        "id": str(uuid4()),
        "section_id": section_id,
        "summary_text": merge_request.merged_text,
        "item_order": items[0]["item_order"],
        "domain_code": domain_code,
        "is_critical": is_critical,
        "source_entry_ids": list(set(combined_source_ids)),
        "edit_count": 0,
        "created_at": datetime.now().isoformat()
    }

    insert_result = db.client.table("handover_draft_items") \
        .insert(merged_item_data) \
        .execute()

    if not insert_result.data:
        raise HTTPException(500, "Failed to create merged item")

    # Mark original items as suppressed (soft delete)
    db.client.table("handover_draft_items") \
        .update({"is_suppressed": True}) \
        .in_("id", [str(item_id) for item_id in merge_request.item_ids]) \
        .execute()

    return HandoverDraftItem(**insert_result.data[0])


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

    # Verify draft is in IN_REVIEW state
    draft_result = db.client.table("handover_drafts") \
        .select("id, state") \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not draft_result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    if draft_result.data["state"] != "IN_REVIEW":
        raise HTTPException(
            400,
            f"Cannot delete items in state {draft_result.data['state']}. Must be IN_REVIEW."
        )

    # Verify item exists
    item_result = db.client.table("handover_draft_items") \
        .select("id") \
        .eq("id", str(item_id)) \
        .single() \
        .execute()

    if not item_result.data:
        raise HTTPException(404, f"Item {item_id} not found")

    # Mark as suppressed (soft delete)
    update_result = db.client.table("handover_draft_items") \
        .update({"is_suppressed": True}) \
        .eq("id", str(item_id)) \
        .execute()

    if not update_result.data:
        raise HTTPException(500, "Failed to suppress item")

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

    # Build query
    query = db.client.table("handover_drafts") \
        .select("""
            *,
            outgoing_user:user_profiles!outgoing_user_id(id, full_name),
            incoming_user:user_profiles!incoming_user_id(id, full_name)
        """) \
        .eq("yacht_id", current_user["yacht_id"])

    # Apply state filter if provided
    if state:
        query = query.eq("state", state.value)

    # Apply pagination
    query = query.range(skip, skip + limit - 1) \
        .order("created_at", desc=True)

    result = query.execute()

    # For list view, return simplified response without sections
    drafts = []
    for draft_data in result.data or []:
        # Create simplified response (sections will be empty for list view)
        draft_response = HandoverDraftResponse(
            **draft_data,
            sections=[]
        )
        drafts.append(draft_response)

    return drafts


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

    # Query for SIGNED and EXPORTED drafts
    result = db.client.table("handover_drafts") \
        .select("""
            *,
            outgoing_user:user_profiles!outgoing_user_id(id, full_name),
            incoming_user:user_profiles!incoming_user_id(id, full_name)
        """) \
        .eq("yacht_id", current_user["yacht_id"]) \
        .in_("state", ["SIGNED", "EXPORTED"]) \
        .range(skip, skip + limit - 1) \
        .order("period_end", desc=True) \
        .execute()

    # Return simplified response without sections
    drafts = []
    for draft_data in result.data or []:
        draft_response = HandoverDraftResponse(
            **draft_data,
            sections=[]
        )
        drafts.append(draft_response)

    return drafts
