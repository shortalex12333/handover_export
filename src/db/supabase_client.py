"""
Supabase client for database operations
"""
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

from ..config import SupabaseConfig

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Supabase client wrapper for handover operations.
    """

    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.client: Client = create_client(config.url, config.service_key)

    async def create_handover_entry(
        self,
        yacht_id: str,
        user_id: str,
        narrative_text: str,
        primary_domain: str,
        presentation_bucket: str,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        risk_tags: Optional[List[str]] = None,
        is_critical: bool = False
    ) -> Dict[str, Any]:
        """Create a handover entry"""

        data = {
            "yacht_id": yacht_id,
            "created_by_user_id": user_id,
            "narrative_text": narrative_text,
            "primary_domain": primary_domain,
            "presentation_bucket": presentation_bucket,
            "source_entity_type": source_type,
            "source_entity_id": source_id,
            "risk_tags": risk_tags or [],
            "is_critical": is_critical,
            "status": "candidate"
        }

        result = self.client.table("handover_entries").insert(data).execute()
        return result.data[0] if result.data else {}

    async def create_handover_draft(
        self,
        yacht_id: str,
        user_id: str,
        period_start: str,
        period_end: str,
        department: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a handover draft"""

        data = {
            "yacht_id": yacht_id,
            "generated_by_user_id": user_id,
            "period_start": period_start,
            "period_end": period_end,
            "department": department,
            "title": title,
            "state": "DRAFT"
        }

        result = self.client.table("handover_drafts").insert(data).execute()
        return result.data[0] if result.data else {}

    async def add_draft_item(
        self,
        draft_id: str,
        section_bucket: str,
        summary_text: str,
        item_order: int,
        domain_code: Optional[str] = None,
        risk_tags: Optional[List[str]] = None,
        is_critical: bool = False,
        source_entry_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add an item to a handover draft"""

        data = {
            "draft_id": draft_id,
            "section_bucket": section_bucket,
            "summary_text": summary_text,
            "item_order": item_order,
            "domain_code": domain_code,
            "risk_tags": risk_tags or [],
            "is_critical": is_critical,
            "source_entry_ids": source_entry_ids or [],
            "confidence_level": "HIGH"
        }

        result = self.client.table("handover_draft_items").insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get a handover draft by ID"""

        result = self.client.table("handover_drafts").select("*").eq("id", draft_id).execute()
        return result.data[0] if result.data else None

    async def get_draft_items(self, draft_id: str) -> List[Dict[str, Any]]:
        """Get all items for a draft"""

        result = (
            self.client.table("handover_draft_items")
            .select("*")
            .eq("draft_id", draft_id)
            .order("item_order")
            .execute()
        )
        return result.data or []

    async def update_draft_state(self, draft_id: str, state: str) -> Dict[str, Any]:
        """Update draft state"""

        result = (
            self.client.table("handover_drafts")
            .update({"state": state})
            .eq("id", draft_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    async def create_email_extraction_job(
        self,
        yacht_id: str,
        user_id: str,
        query: Optional[str] = None,
        days_back: int = 90,
        max_emails: int = 500
    ) -> Dict[str, Any]:
        """Create an email extraction job"""

        data = {
            "yacht_id": yacht_id,
            "created_by_user_id": user_id,
            "query": query,
            "days_back": days_back,
            "max_emails": max_emails,
            "status": "pending"
        }

        result = self.client.table("email_extraction_jobs").insert(data).execute()
        return result.data[0] if result.data else {}

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        current_stage: Optional[str] = None,
        stage_progress: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update job status"""

        data = {"status": status}
        if current_stage:
            data["current_stage"] = current_stage
        if stage_progress:
            data["stage_progress"] = stage_progress
        if error_message:
            data["error_message"] = error_message

        result = (
            self.client.table("email_extraction_jobs")
            .update(data)
            .eq("id", job_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    async def record_handover_source(
        self,
        yacht_id: str,
        source_type: str,
        external_id: str,
        subject: Optional[str] = None,
        body_preview: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        received_at: Optional[str] = None,
        classification: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Record a handover source (e.g., email)"""

        data = {
            "yacht_id": yacht_id,
            "source_type": source_type,
            "external_id": external_id,
            "subject": subject,
            "body_preview": body_preview,
            "sender_name": sender_name,
            "sender_email": sender_email,
            "received_at": received_at,
            "classification": classification,
            "is_processed": classification is not None
        }

        result = self.client.table("handover_sources").insert(data).execute()
        return result.data[0] if result.data else {}
