"""
Pydantic models for handover system
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, UUID4


class HandoverDraftState(str, Enum):
    """Draft lifecycle states"""
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    ACCEPTED = "ACCEPTED"
    SIGNED = "SIGNED"
    EXPORTED = "EXPORTED"


class HandoverEntryStatus(str, Enum):
    """Entry status"""
    candidate = "candidate"
    included = "included"
    suppressed = "suppressed"
    resolved = "resolved"


class PresentationBucket(str, Enum):
    """Handover section buckets"""
    Command = "Command"
    Engineering = "Engineering"
    ETO_AVIT = "ETO_AVIT"
    Deck = "Deck"
    Interior = "Interior"
    Galley = "Galley"
    Security = "Security"
    Admin_Compliance = "Admin_Compliance"


class RiskTag(str, Enum):
    """Risk classification tags"""
    Safety_Critical = "Safety_Critical"
    Compliance_Critical = "Compliance_Critical"
    Guest_Impacting = "Guest_Impacting"
    Cost_Impacting = "Cost_Impacting"
    Operational_Debt = "Operational_Debt"
    Informational = "Informational"


class ConfidenceLevel(str, Enum):
    """AI classification confidence"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ============================================================================
# HANDOVER ENTRIES
# ============================================================================

class HandoverEntryCreate(BaseModel):
    """Request to create a new handover entry"""
    narrative_text: str = Field(..., min_length=1, max_length=10000)
    linked_event_ids: Optional[List[UUID4]] = None
    linked_document_ids: Optional[List[UUID4]] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[UUID4] = None


class HandoverEntryProposal(BaseModel):
    """AI-proposed classification for user confirmation"""
    id: UUID4
    narrative_text: str
    suggested_domain: str
    suggested_bucket: PresentationBucket
    suggested_risk_tags: List[RiskTag]
    confidence: ConfidenceLevel
    reasoning: Optional[str] = None


class HandoverEntryResponse(BaseModel):
    """Confirmed handover entry"""
    id: UUID4
    yacht_id: UUID4
    created_by_user_id: UUID4
    created_by_role: Optional[str]
    created_by_department: Optional[str]

    primary_domain: str
    secondary_domains: Optional[List[str]]
    presentation_bucket: str
    suggested_owner_roles: Optional[List[str]]
    risk_tags: Optional[List[str]]

    narrative_text: str
    summary_text: Optional[str]

    source_event_ids: Optional[List[UUID4]]
    source_document_ids: Optional[List[UUID4]]
    source_entity_type: Optional[str]
    source_entity_id: Optional[UUID4]

    status: HandoverEntryStatus
    classification_confidence: Optional[ConfidenceLevel]
    classification_flagged: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# HANDOVER DRAFTS
# ============================================================================

class HandoverDraftGenerate(BaseModel):
    """Request to generate a handover draft"""
    outgoing_user_id: UUID4
    incoming_user_id: Optional[UUID4] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    shift_type: Optional[str] = "day"  # day, night, weekly


class HandoverDraftSection(BaseModel):
    """A section within a draft (e.g., Engineering, Deck)"""
    id: UUID4
    bucket: PresentationBucket
    section_order: int
    items: List["HandoverDraftItem"] = []


class HandoverDraftItem(BaseModel):
    """An item within a draft section"""
    id: UUID4
    summary_text: str
    item_order: int
    domain_code: Optional[str]
    is_critical: bool
    source_entry_ids: List[UUID4]
    edit_count: int
    created_at: datetime


class HandoverDraftResponse(BaseModel):
    """Complete draft with sections and items"""
    id: UUID4
    yacht_id: UUID4
    outgoing_user_id: UUID4
    incoming_user_id: Optional[UUID4]

    period_start: datetime
    period_end: datetime
    shift_type: str

    state: HandoverDraftState
    sections: List[HandoverDraftSection]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HandoverDraftItemEdit(BaseModel):
    """Edit a draft item"""
    edited_text: str = Field(..., min_length=1, max_length=10000)
    edit_reason: Optional[str] = None


class HandoverDraftItemMerge(BaseModel):
    """Merge multiple draft items"""
    item_ids: List[UUID4] = Field(..., min_items=2)
    merged_text: str = Field(..., min_length=1, max_length=10000)


# ============================================================================
# SIGN-OFF
# ============================================================================

class HandoverAcceptRequest(BaseModel):
    """Outgoing user accepts draft"""
    confirmed: bool = True
    comments: Optional[str] = None


class HandoverSignRequest(BaseModel):
    """Incoming user countersigns draft"""
    confirmed: bool = True
    comments: Optional[str] = None


class HandoverSignoffResponse(BaseModel):
    """Sign-off record"""
    id: UUID4
    draft_id: UUID4
    signoff_type: str  # "outgoing" or "incoming"
    user_id: UUID4
    signed_at: datetime
    comments: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# EXPORTS
# ============================================================================

class ExportType(str, Enum):
    """Export format types"""
    pdf = "pdf"
    html = "html"
    email = "email"


class HandoverExportRequest(BaseModel):
    """Request to export a signed handover"""
    export_type: ExportType
    recipients: Optional[List[str]] = None  # Email addresses if export_type = email


class HandoverExportResponse(BaseModel):
    """Export record with download URL"""
    id: UUID4
    draft_id: UUID4
    export_type: ExportType
    file_url: Optional[str]
    email_sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Update forward refs
HandoverDraftSection.model_rebuild()
