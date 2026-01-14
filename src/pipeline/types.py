"""
Core data types for the email-to-handover pipeline
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """Action priority levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"


class HandoverCategory(str, Enum):
    """Handover classification categories"""
    ELECTRICAL = "Electrical"
    PROJECTS = "Projects"
    FINANCIAL = "Financial"
    GALLEY_LAUNDRY = "Galley Laundry"
    RISK = "Risk"
    ADMIN = "Admin"
    FIRE_SAFETY = "Fire Safety"
    TENDERS = "Tenders"
    LOGISTICS = "Logistics"
    DECK = "Deck"
    GENERAL = "General Outstanding"


@dataclass
class RawEmail:
    """Raw email from Microsoft Graph API"""
    id: str
    subject: str
    body: Dict[str, Any]  # {content, contentType}
    body_preview: str
    from_address: Dict[str, Any]  # {emailAddress: {name, address}}
    received_datetime: str
    conversation_id: str
    has_attachments: bool
    importance: str


@dataclass
class ExtractedEmail:
    """Extracted and normalized email"""
    short_id: str              # E1, E2, etc.
    email_id: str
    conversation_id: str
    subject: str
    body_text: str             # HTML stripped
    body_preview: str
    sender_name: str
    sender_email: str
    received_at: datetime
    has_attachments: bool
    outlook_link: str


@dataclass
class ClassificationResult:
    """AI classification result"""
    short_id: str
    category: HandoverCategory
    summary: str
    confidence: float = 0.9


@dataclass
class TopicGroup:
    """Group of emails on the same topic"""
    merge_key: str
    category: HandoverCategory
    subject_group: str         # Normalized subject
    notes: List[Dict[str, str]]  # [{subject, summary}]
    source_ids: List[Dict[str, str]]  # [{shortId, summaryId, link}]


@dataclass
class HandoverAction:
    """Action item from handover"""
    priority: Priority
    task: str
    sub_tasks: List[str] = field(default_factory=list)


@dataclass
class MergedHandover:
    """Merged handover entry"""
    merge_key: str
    category: HandoverCategory
    subject_group: str
    subject: str
    summary: str
    actions: List[HandoverAction]
    source_ids: List[Dict[str, str]]
    domain_code: Optional[str] = None
    presentation_bucket: Optional[str] = None


@dataclass
class FormattedReport:
    """Final formatted report"""
    meta: Dict[str, Any]
    sections: Dict[str, List[MergedHandover]]
    html: str
    generated_at: datetime


# Domain code mapping
CATEGORY_TO_DOMAIN = {
    HandoverCategory.ELECTRICAL: ('ENG-03', 'Engineering'),
    HandoverCategory.PROJECTS: ('ADM-04', 'Admin_Compliance'),
    HandoverCategory.FINANCIAL: ('ADM-03', 'Admin_Compliance'),
    HandoverCategory.GALLEY_LAUNDRY: ('INT-02', 'Interior'),
    HandoverCategory.RISK: ('CMD-01', 'Command'),
    HandoverCategory.ADMIN: ('ADM-01', 'Admin_Compliance'),
    HandoverCategory.FIRE_SAFETY: ('ENG-08', 'Engineering'),
    HandoverCategory.TENDERS: ('DECK-03', 'Deck'),
    HandoverCategory.LOGISTICS: ('ADM-05', 'Admin_Compliance'),
    HandoverCategory.DECK: ('DECK-01', 'Deck'),
    HandoverCategory.GENERAL: (None, None),
}
