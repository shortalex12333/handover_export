"""
Handover Entries API Router
Handles CRUD operations for handover entries
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import UUID4

from ..models.handover import (
    HandoverEntryCreate,
    HandoverEntryProposal,
    HandoverEntryResponse,
    HandoverEntryStatus,
    ConfidenceLevel,
    PresentationBucket,
    RiskTag
)
from ..db.supabase_client import SupabaseClient
from ..ai.openai_client import OpenAIClient
from ..dependencies import get_db_client, get_openai_client as get_ai_client, get_current_user

router = APIRouter(prefix="/api/v1/handover/entries", tags=["Handover Entries"])


def classify_handover_entry(
    narrative: str,
    ai_client: OpenAIClient,
    user_role: Optional[str] = None
) -> dict:
    """
    Use AI to classify handover entry
    Returns: {domain, bucket, risk_tags, confidence, reasoning}
    """

    # Domain code taxonomy (simplified - should load from DB)
    domain_map = {
        "engine": "ENG-01",
        "generator": "ENG-02",
        "hvac": "ENG-03",
        "electrical": "ETO-01",
        "navigation": "ETO-02",
        "deck": "DECK-01",
        "tender": "DECK-02",
        "interior": "INT-01",
        "housekeeping": "INT-02",
        "galley": "GAL-01",
        "provisions": "GAL-02",
        "security": "SEC-01",
        "compliance": "ADM-01"
    }

    # Simple keyword-based classification (replace with AI)
    narrative_lower = narrative.lower()

    domain = "GEN-01"  # Default general domain
    bucket = PresentationBucket.Command
    risk_tags = [RiskTag.Informational]
    confidence = ConfidenceLevel.MEDIUM

    # Keyword matching (basic implementation)
    if any(word in narrative_lower for word in ["engine", "generator", "machinery"]):
        domain = "ENG-01"
        bucket = PresentationBucket.Engineering
    elif any(word in narrative_lower for word in ["electrical", "avit", "navigation"]):
        domain = "ETO-01"
        bucket = PresentationBucket.ETO_AVIT
    elif any(word in narrative_lower for word in ["deck", "mooring", "anchor"]):
        domain = "DECK-01"
        bucket = PresentationBucket.Deck
    elif any(word in narrative_lower for word in ["cabin", "housekeeping", "interior"]):
        domain = "INT-01"
        bucket = PresentationBucket.Interior
    elif any(word in narrative_lower for word in ["galley", "food", "provisions"]):
        domain = "GAL-01"
        bucket = PresentationBucket.Galley
    elif any(word in narrative_lower for word in ["security", "drill"]):
        domain = "SEC-01"
        bucket = PresentationBucket.Security
    elif any(word in narrative_lower for word in ["compliance", "certificate", "audit"]):
        domain = "ADM-01"
        bucket = PresentationBucket.Admin_Compliance

    # Risk assessment
    if any(word in narrative_lower for word in ["safety", "dangerous", "hazard", "critical"]):
        risk_tags = [RiskTag.Safety_Critical]
        confidence = ConfidenceLevel.HIGH
    elif any(word in narrative_lower for word in ["guest", "charter", "vip"]):
        risk_tags = [RiskTag.Guest_Impacting]
    elif any(word in narrative_lower for word in ["compliance", "regulatory", "class"]):
        risk_tags = [RiskTag.Compliance_Critical]
    elif any(word in narrative_lower for word in ["cost", "budget", "expensive"]):
        risk_tags = [RiskTag.Cost_Impacting]

    return {
        "domain": domain,
        "bucket": bucket,
        "risk_tags": risk_tags,
        "confidence": confidence,
        "reasoning": f"Classified based on keywords in narrative"
    }


@router.post("", response_model=HandoverEntryProposal, status_code=201)
async def create_handover_entry(
    entry: HandoverEntryCreate,
    db: SupabaseClient = Depends(get_db_client),
    ai: OpenAIClient = Depends(get_ai_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new handover entry (returns proposal for confirmation)

    This endpoint:
    1. Accepts narrative text from user
    2. Uses AI to classify domain, bucket, and risk
    3. Returns a proposal for user confirmation
    4. Does NOT save to database until confirmed via /confirm endpoint
    """

    # Classify the entry
    classification = classify_handover_entry(
        entry.narrative_text,
        ai,
        current_user.get("role")
    )

    # Create proposal record (temporary, pending confirmation)
    from uuid import UUID, uuid4
    proposal_data = {
        "id": uuid4(),  # Generate temporary ID
        "narrative_text": entry.narrative_text,
        "suggested_domain": classification["domain"],
        "suggested_bucket": classification["bucket"],
        "suggested_risk_tags": classification["risk_tags"],
        "confidence": classification["confidence"],
        "reasoning": classification["reasoning"]
    }

    # In production, save as pending entry in DB with status='proposed'
    # For now, return the proposal

    return HandoverEntryProposal(**proposal_data)


@router.post("/{entry_id}/confirm", response_model=HandoverEntryResponse)
async def confirm_handover_entry(
    entry_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm a proposed handover entry

    This transitions the entry from 'proposed' to 'candidate' status,
    making it visible to draft generation.
    """

    # In production: Update entry status in database
    # For now, return a mock confirmed entry

    confirmed_entry = {
        "id": entry_id,
        "yacht_id": current_user["yacht_id"],
        "created_by_user_id": current_user["id"],
        "created_by_role": current_user.get("role"),
        "created_by_department": current_user.get("department"),
        "primary_domain": "ENG-01",
        "secondary_domains": None,
        "presentation_bucket": "Engineering",
        "suggested_owner_roles": ["Chief Engineer", "Second Engineer"],
        "risk_tags": ["Informational"],
        "narrative_text": "Confirmed handover entry",
        "summary_text": None,
        "source_event_ids": None,
        "source_document_ids": None,
        "source_entity_type": None,
        "source_entity_id": None,
        "status": HandoverEntryStatus.candidate,
        "classification_confidence": ConfidenceLevel.MEDIUM,
        "classification_flagged": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    return HandoverEntryResponse(**confirmed_entry)


@router.post("/{entry_id}/dismiss")
async def dismiss_handover_entry(
    entry_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Dismiss a proposed handover entry

    The entry is not created and the dismissal is logged for analytics.
    """

    # In production: Log dismissal and delete proposed entry

    return {
        "success": True,
        "message": "Handover entry dismissed",
        "entry_id": str(entry_id)
    }


@router.get("", response_model=List[HandoverEntryResponse])
async def list_handover_entries(
    status: Optional[HandoverEntryStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    List handover entries with optional filtering

    Query params:
    - status: Filter by entry status (candidate, included, suppressed, resolved)
    - skip: Pagination offset
    - limit: Max results to return
    """

    # In production: Query database with filters
    # For now, return empty list

    return []


@router.get("/{entry_id}", response_model=HandoverEntryResponse)
async def get_handover_entry(
    entry_id: UUID4,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific handover entry by ID"""

    # In production: Fetch from database
    raise HTTPException(404, "Entry not found")


@router.patch("/{entry_id}", response_model=HandoverEntryResponse)
async def update_handover_entry(
    entry_id: UUID4,
    updates: HandoverEntryCreate,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a handover entry (only allowed for candidate status)

    Note: Only narrative_text can be updated. Classification is re-run.
    """

    # In production: Check status, update narrative, re-classify
    raise HTTPException(403, "Entry cannot be modified")


@router.post("/{entry_id}/flag-classification")
async def flag_classification(
    entry_id: UUID4,
    reason: Optional[str] = None,
    db: SupabaseClient = Depends(get_db_client),
    current_user: dict = Depends(get_current_user)
):
    """
    Flag an entry's classification as incorrect

    This sets classification_flagged = true and logs the correction request.
    No direct modification is allowed - human review required.
    """

    # In production: Update classification_flagged field, create correction log

    return {
        "success": True,
        "message": "Classification flagged for review",
        "entry_id": str(entry_id)
    }
