"""
Draft Generator Service
Assembles handover entries into structured drafts organized by presentation buckets
"""
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID, uuid4

from ..db.supabase_client import SupabaseClient


class DraftGenerator:
    """
    Generates handover drafts from candidate entries

    Workflow:
    1. Fetch all candidate entries for period
    2. Group by presentation_bucket
    3. Sort by priority/risk within each bucket
    4. Create draft record
    5. Create sections for each bucket
    6. Create items from entries
    """

    def __init__(self, db_client: SupabaseClient):
        self.db = db_client

    # Bucket ordering (display order in draft)
    BUCKET_ORDER = [
        "Command",
        "Engineering",
        "ETO_AVIT",
        "Deck",
        "Interior",
        "Galley",
        "Security",
        "Admin_Compliance"
    ]

    async def generate_draft(
        self,
        yacht_id: str,
        outgoing_user_id: str,
        incoming_user_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        shift_type: str = "day"
    ) -> str:
        """
        Generate a handover draft from candidate entries

        Args:
            yacht_id: Vessel ID
            outgoing_user_id: User creating handover
            incoming_user_id: User receiving handover (optional)
            period_start: Start of handover period
            period_end: End of handover period
            shift_type: Type of shift (day, night, weekly)

        Returns:
            draft_id: UUID of created draft
        """

        # Default period to last 24 hours if not specified
        if not period_end:
            period_end = datetime.now()
        if not period_start:
            period_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Check for existing draft in DRAFT state
        existing = await self._get_active_draft(yacht_id, outgoing_user_id)
        if existing:
            return existing["id"]

        # Fetch candidate entries
        entries = await self._fetch_candidate_entries(
            yacht_id,
            period_start,
            period_end
        )

        if not entries:
            # Still create draft even if no entries
            pass

        # Create draft record
        draft_id = await self._create_draft_record(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id,
            incoming_user_id=incoming_user_id,
            period_start=period_start,
            period_end=period_end,
            shift_type=shift_type
        )

        # Group entries by bucket
        bucketed_entries = self._group_by_bucket(entries)

        # Create sections and items
        await self._create_sections_and_items(draft_id, bucketed_entries)

        return draft_id

    async def _get_active_draft(
        self,
        yacht_id: str,
        outgoing_user_id: str
    ) -> Optional[Dict]:
        """Check for existing draft in DRAFT state"""

        result = self.db.client.table("handover_drafts") \
            .select("id, state") \
            .eq("yacht_id", yacht_id) \
            .eq("outgoing_user_id", outgoing_user_id) \
            .eq("state", "DRAFT") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0]
        return None

    async def _fetch_candidate_entries(
        self,
        yacht_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> List[Dict]:
        """
        Fetch all candidate handover entries for the period

        Filters:
        - yacht_id matches
        - status = 'candidate'
        - created_at within period

        Orders by:
        - Risk tags (critical first)
        - Created timestamp (newest first)
        """

        result = self.db.client.table("handover_entries") \
            .select("*") \
            .eq("yacht_id", yacht_id) \
            .eq("status", "candidate") \
            .gte("created_at", period_start.isoformat()) \
            .lte("created_at", period_end.isoformat()) \
            .order("created_at", desc=True) \
            .execute()

        return result.data or []

    async def _create_draft_record(
        self,
        yacht_id: str,
        outgoing_user_id: str,
        incoming_user_id: Optional[str],
        period_start: datetime,
        period_end: datetime,
        shift_type: str
    ) -> str:
        """Create handover_drafts record"""

        draft_data = {
            "id": str(uuid4()),
            "yacht_id": yacht_id,
            "outgoing_user_id": outgoing_user_id,
            "incoming_user_id": incoming_user_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "shift_type": shift_type,
            "state": "DRAFT",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        result = self.db.client.table("handover_drafts") \
            .insert(draft_data) \
            .execute()

        if result.data:
            return result.data[0]["id"]

        raise Exception("Failed to create draft record")

    def _group_by_bucket(self, entries: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group entries by presentation_bucket

        Returns:
            Dict with bucket names as keys, lists of entries as values
        """

        bucketed = {bucket: [] for bucket in self.BUCKET_ORDER}

        for entry in entries:
            bucket = entry.get("presentation_bucket", "Command")
            if bucket in bucketed:
                bucketed[bucket].append(entry)
            else:
                # Default to Command if unknown bucket
                bucketed["Command"].append(entry)

        return bucketed

    async def _create_sections_and_items(
        self,
        draft_id: str,
        bucketed_entries: Dict[str, List[Dict]]
    ):
        """
        Create handover_draft_sections and handover_draft_items

        For each bucket:
        1. Create section record
        2. Create items from entries in that section
        """

        section_order = 1

        for bucket in self.BUCKET_ORDER:
            entries = bucketed_entries.get(bucket, [])

            if not entries:
                # Skip empty sections
                continue

            # Create section
            section_id = await self._create_section(
                draft_id=draft_id,
                bucket=bucket,
                section_order=section_order
            )

            # Create items
            item_order = 1
            for entry in entries:
                await self._create_item(
                    draft_id=draft_id,
                    section_id=section_id,
                    entry=entry,
                    item_order=item_order
                )
                item_order += 1

            section_order += 1

    async def _create_section(
        self,
        draft_id: str,
        bucket: str,
        section_order: int
    ) -> str:
        """Create handover_draft_sections record"""

        section_data = {
            "id": str(uuid4()),
            "draft_id": draft_id,
            "section_bucket": bucket,
            "section_order": section_order,
            "created_at": datetime.now().isoformat()
        }

        result = self.db.client.table("handover_draft_sections") \
            .insert(section_data) \
            .execute()

        if result.data:
            return result.data[0]["id"]

        raise Exception(f"Failed to create section for bucket {bucket}")

    async def _create_item(
        self,
        draft_id: str,
        section_id: str,
        entry: Dict,
        item_order: int
    ):
        """Create handover_draft_items record from entry"""

        # Determine if critical based on risk tags
        is_critical = self._is_critical(entry)

        item_data = {
            "id": str(uuid4()),
            "draft_id": draft_id,
            "section_id": section_id,
            "summary_text": entry.get("summary_text") or entry.get("narrative_text"),
            "item_order": item_order,
            "domain_code": entry.get("primary_domain"),
            "is_critical": is_critical,
            "source_entry_ids": [entry["id"]],
            "edit_count": 0,
            "created_at": datetime.now().isoformat()
        }

        self.db.client.table("handover_draft_items") \
            .insert(item_data) \
            .execute()

    def _is_critical(self, entry: Dict) -> bool:
        """
        Determine if entry is critical based on risk tags

        Critical risk tags:
        - Safety_Critical
        - Compliance_Critical
        """

        risk_tags = entry.get("risk_tags", [])

        critical_tags = ["Safety_Critical", "Compliance_Critical"]

        return any(tag in critical_tags for tag in risk_tags)

    async def add_entry_to_existing_draft(
        self,
        draft_id: str,
        entry_id: str
    ) -> bool:
        """
        Add a single entry to an existing draft

        Args:
            draft_id: Existing draft ID
            entry_id: Entry to add

        Returns:
            True if successful
        """

        # Fetch entry
        entry_result = self.db.client.table("handover_entries") \
            .select("*") \
            .eq("id", entry_id) \
            .single() \
            .execute()

        if not entry_result.data:
            raise Exception(f"Entry {entry_id} not found")

        entry = entry_result.data
        bucket = entry.get("presentation_bucket", "Command")

        # Find or create section for this bucket
        section_id = await self._get_or_create_section(draft_id, bucket)

        # Get next item order
        item_order = await self._get_next_item_order(section_id)

        # Create item
        await self._create_item(
            draft_id=draft_id,
            section_id=section_id,
            entry=entry,
            item_order=item_order
        )

        # Update entry status to 'included'
        self.db.client.table("handover_entries") \
            .update({"status": "included"}) \
            .eq("id", entry_id) \
            .execute()

        return True

    async def _get_or_create_section(
        self,
        draft_id: str,
        bucket: str
    ) -> str:
        """Get existing section or create new one"""

        # Try to find existing section
        result = self.db.client.table("handover_draft_sections") \
            .select("id") \
            .eq("draft_id", draft_id) \
            .eq("section_bucket", bucket) \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0]["id"]

        # Create new section
        section_order = await self._get_next_section_order(draft_id)
        return await self._create_section(draft_id, bucket, section_order)

    async def _get_next_section_order(self, draft_id: str) -> int:
        """Get next section_order value"""

        result = self.db.client.table("handover_draft_sections") \
            .select("section_order") \
            .eq("draft_id", draft_id) \
            .order("section_order", desc=True) \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0]["section_order"] + 1

        return 1

    async def _get_next_item_order(self, section_id: str) -> int:
        """Get next item_order value within section"""

        result = self.db.client.table("handover_draft_items") \
            .select("item_order") \
            .eq("section_id", section_id) \
            .order("item_order", desc=True) \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0]["item_order"] + 1

        return 1
