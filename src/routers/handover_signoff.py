"""
Handover Sign-off API Router
Handles acceptance and countersigning of handover drafts
"""
from typing import List
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import UUID4

from ..models.handover import (
    HandoverAcceptRequest,
    HandoverSignRequest,
    HandoverSignoffResponse,
    HandoverDraftState
)
from ..db.supabase_client import SupabaseClient
from ..dependencies import get_db_client, get_current_user
from ..services.signoff_manager import SignoffManager

router = APIRouter(prefix="/api/v1/handover/drafts", tags=["Handover Sign-off"])


@router.post("/{draft_id}/accept", response_model=HandoverSignoffResponse)
async def accept_handover_draft(
    draft_id: UUID4,
    request: HandoverAcceptRequest,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Outgoing user accepts the handover draft (first signature)

    State transition: IN_REVIEW → ACCEPTED

    Rules:
    - Only allowed if current state = IN_REVIEW
    - Must have confirmed = true in request body
    - Records outgoing_user_id + timestamp
    - Creates handover_signoff record with type='outgoing'
    - Transitions draft to ACCEPTED state

    After acceptance, draft is locked for incoming user to countersign.
    """

    if not request.confirmed:
        raise HTTPException(400, "Confirmation flag must be true to accept")

    # Initialize signoff manager
    manager = SignoffManager(db)

    try:
        # Accept draft
        signoff_id = await manager.accept_draft(
            draft_id=str(draft_id),
            user_id=current_user["id"],
            comments=request.comments
        )

        # Fetch signoff record
        result = db.client.table("handover_signoffs") \
            .select("""
                *,
                user:user_profiles(id, full_name)
            """) \
            .eq("id", signoff_id) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(500, "Failed to fetch signoff record")

        return HandoverSignoffResponse(**result.data)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/{draft_id}/sign", response_model=HandoverSignoffResponse)
async def sign_handover_draft(
    draft_id: UUID4,
    request: HandoverSignRequest,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Incoming user countersigns the handover draft (second signature)

    State transition: ACCEPTED → SIGNED

    Rules:
    - Only allowed if current state = ACCEPTED
    - Must have confirmed = true in request body
    - Records incoming_user_id + timestamp
    - Creates handover_signoff record with type='incoming'
    - Transitions draft to SIGNED state
    - Triggers export preparation job

    After countersigning, draft is fully signed and ready for export.
    """

    if not request.confirmed:
        raise HTTPException(400, "Confirmation flag must be true to sign")

    # Initialize signoff manager
    manager = SignoffManager(db)

    try:
        # Countersign draft
        signoff_id = await manager.countersign_draft(
            draft_id=str(draft_id),
            user_id=current_user["id"],
            comments=request.comments
        )

        # Fetch signoff record
        result = db.client.table("handover_signoffs") \
            .select("""
                *,
                user:user_profiles(id, full_name)
            """) \
            .eq("id", signoff_id) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(500, "Failed to fetch signoff record")

        return HandoverSignoffResponse(**result.data)

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/{draft_id}/signoffs", response_model=List[HandoverSignoffResponse])
async def get_draft_signoffs(
    draft_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all signoffs for a draft

    Returns both outgoing and incoming signoffs with metadata.
    """

    # Verify draft exists
    draft_result = db.client.table("handover_drafts") \
        .select("id") \
        .eq("id", str(draft_id)) \
        .single() \
        .execute()

    if not draft_result.data:
        raise HTTPException(404, f"Draft {draft_id} not found")

    # Fetch all signoffs for this draft
    result = db.client.table("handover_signoffs") \
        .select("""
            *,
            user:user_profiles(id, full_name, role)
        """) \
        .eq("draft_id", str(draft_id)) \
        .order("signed_at") \
        .execute()

    signoffs = [HandoverSignoffResponse(**signoff) for signoff in result.data or []]

    return signoffs
