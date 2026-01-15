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

    # In production:
    # 1. Check draft exists and state = IN_REVIEW
    # 2. Verify current_user is the outgoing_user_id
    # 3. Create signoff record
    # 4. Update draft state to ACCEPTED
    # 5. Record ledger event

    signoff_id = UUID("00000000-0000-0000-0000-000000000001")

    signoff_data = {
        "id": signoff_id,
        "draft_id": draft_id,
        "signoff_type": "outgoing",
        "user_id": current_user["id"],
        "signed_at": datetime.now(),
        "comments": request.comments
    }

    return HandoverSignoffResponse(**signoff_data)


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

    # In production:
    # 1. Check draft exists and state = ACCEPTED
    # 2. Verify current_user is the incoming_user_id
    # 3. Create signoff record
    # 4. Update draft state to SIGNED
    # 5. Record ledger event
    # 6. Trigger background export job (optional auto-export)

    signoff_id = UUID("00000000-0000-0000-0000-000000000002")

    signoff_data = {
        "id": signoff_id,
        "draft_id": draft_id,
        "signoff_type": "incoming",
        "user_id": current_user["id"],
        "signed_at": datetime.now(),
        "comments": request.comments
    }

    return HandoverSignoffResponse(**signoff_data)


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

    # In production: Query handover_signoffs table

    return []
