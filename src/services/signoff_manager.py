"""
Sign-off Manager Service
Handles handover draft state transitions and signature management
"""
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4

from ..db.supabase_client import SupabaseClient


class SignoffManager:
    """
    Manages handover draft lifecycle and sign-offs

    State Machine:
    DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED

    Rules:
    - Only outgoing_user can accept (DRAFT → ACCEPTED)
    - Only incoming_user can countersign (ACCEPTED → SIGNED)
    - State transitions are unidirectional (no rollback)
    - Each transition creates a signoff record
    """

    def __init__(self, db_client: SupabaseClient):
        self.db = db_client

    # Valid state transitions
    STATE_TRANSITIONS = {
        "DRAFT": ["IN_REVIEW"],
        "IN_REVIEW": ["ACCEPTED"],
        "ACCEPTED": ["SIGNED"],
        "SIGNED": ["EXPORTED"],
        "EXPORTED": []  # Terminal state
    }

    async def enter_review(
        self,
        draft_id: str,
        user_id: str
    ) -> bool:
        """
        Transition draft from DRAFT → IN_REVIEW

        Args:
            draft_id: Draft to review
            user_id: User initiating review

        Returns:
            True if successful

        Raises:
            ValueError if invalid state transition
        """

        draft = await self._get_draft(draft_id)

        # Validate current state
        if draft["state"] != "DRAFT":
            raise ValueError(
                f"Cannot enter review from state {draft['state']}. "
                f"Draft must be in DRAFT state."
            )

        # Verify user is outgoing_user
        if draft["outgoing_user_id"] != user_id:
            raise ValueError("Only outgoing user can enter review")

        # Update state
        await self._update_draft_state(draft_id, "IN_REVIEW")

        return True

    async def accept_draft(
        self,
        draft_id: str,
        user_id: str,
        comments: Optional[str] = None
    ) -> str:
        """
        Outgoing user accepts draft (first signature)

        State transition: IN_REVIEW → ACCEPTED

        Args:
            draft_id: Draft to accept
            user_id: Outgoing user ID
            comments: Optional acceptance comments

        Returns:
            signoff_id: UUID of created signoff record

        Raises:
            ValueError if invalid state or wrong user
        """

        draft = await self._get_draft(draft_id)

        # Validate current state
        if draft["state"] != "IN_REVIEW":
            raise ValueError(
                f"Cannot accept from state {draft['state']}. "
                f"Draft must be in IN_REVIEW state."
            )

        # Verify user is outgoing_user
        if draft["outgoing_user_id"] != user_id:
            raise ValueError("Only outgoing user can accept draft")

        # Create signoff record
        signoff_id = await self._create_signoff(
            draft_id=draft_id,
            user_id=user_id,
            signoff_type="outgoing",
            comments=comments
        )

        # Update draft state
        await self._update_draft_state(draft_id, "ACCEPTED")

        # Log ledger event (if ledger system is implemented)
        await self._log_ledger_event(
            event_type="handover_accepted",
            draft_id=draft_id,
            user_id=user_id
        )

        return signoff_id

    async def countersign_draft(
        self,
        draft_id: str,
        user_id: str,
        comments: Optional[str] = None
    ) -> str:
        """
        Incoming user countersigns draft (second signature)

        State transition: ACCEPTED → SIGNED

        Args:
            draft_id: Draft to sign
            user_id: Incoming user ID
            comments: Optional sign-off comments

        Returns:
            signoff_id: UUID of created signoff record

        Raises:
            ValueError if invalid state or wrong user
        """

        draft = await self._get_draft(draft_id)

        # Validate current state
        if draft["state"] != "ACCEPTED":
            raise ValueError(
                f"Cannot countersign from state {draft['state']}. "
                f"Draft must be in ACCEPTED state."
            )

        # Verify user is incoming_user
        if not draft.get("incoming_user_id"):
            raise ValueError("No incoming user specified for this draft")

        if draft["incoming_user_id"] != user_id:
            raise ValueError("Only incoming user can countersign draft")

        # Create signoff record
        signoff_id = await self._create_signoff(
            draft_id=draft_id,
            user_id=user_id,
            signoff_type="incoming",
            comments=comments
        )

        # Update draft state
        await self._update_draft_state(draft_id, "SIGNED")

        # Log ledger event
        await self._log_ledger_event(
            event_type="handover_signed",
            draft_id=draft_id,
            user_id=user_id
        )

        return signoff_id

    async def mark_exported(
        self,
        draft_id: str,
        export_id: str
    ) -> bool:
        """
        Mark draft as exported after PDF/email generation

        State transition: SIGNED → EXPORTED

        Args:
            draft_id: Draft that was exported
            export_id: Export record ID

        Returns:
            True if successful
        """

        draft = await self._get_draft(draft_id)

        # Validate current state
        if draft["state"] != "SIGNED":
            raise ValueError(
                f"Cannot export from state {draft['state']}. "
                f"Draft must be in SIGNED state."
            )

        # Update state
        await self._update_draft_state(draft_id, "EXPORTED")

        # Link export to draft
        self.db.client.table("handover_exports") \
            .update({"draft_id": draft_id}) \
            .eq("id", export_id) \
            .execute()

        return True

    async def _get_draft(self, draft_id: str) -> Dict:
        """Fetch draft record"""

        result = self.db.client.table("handover_drafts") \
            .select("*") \
            .eq("id", draft_id) \
            .single() \
            .execute()

        if not result.data:
            raise ValueError(f"Draft {draft_id} not found")

        return result.data

    async def _update_draft_state(
        self,
        draft_id: str,
        new_state: str
    ):
        """Update draft state and timestamp"""

        self.db.client.table("handover_drafts") \
            .update({
                "state": new_state,
                "updated_at": datetime.now().isoformat()
            }) \
            .eq("id", draft_id) \
            .execute()

    async def _create_signoff(
        self,
        draft_id: str,
        user_id: str,
        signoff_type: str,
        comments: Optional[str] = None
    ) -> str:
        """Create handover_signoffs record"""

        signoff_data = {
            "id": str(uuid4()),
            "draft_id": draft_id,
            "user_id": user_id,
            "signoff_type": signoff_type,
            "signed_at": datetime.now().isoformat(),
            "comments": comments
        }

        result = self.db.client.table("handover_signoffs") \
            .insert(signoff_data) \
            .execute()

        if result.data:
            return result.data[0]["id"]

        raise Exception("Failed to create signoff record")

    async def _log_ledger_event(
        self,
        event_type: str,
        draft_id: str,
        user_id: str
    ):
        """
        Log event to immutable ledger (if implemented)

        This is a placeholder for integration with the ledger system
        from migration 00003_tenant_db_ledger.sql
        """

        # Check if ledger_events table exists
        try:
            ledger_data = {
                "id": str(uuid4()),
                "event_type": event_type,
                "entity_type": "handover_draft",
                "entity_id": draft_id,
                "user_id": user_id,
                "event_timestamp": datetime.now().isoformat(),
                "event_data": {
                    "draft_id": draft_id,
                    "action": event_type
                }
            }

            self.db.client.table("ledger_events") \
                .insert(ledger_data) \
                .execute()

        except Exception as e:
            # Silently fail if ledger not implemented yet
            pass

    async def get_signoffs(self, draft_id: str) -> list:
        """
        Get all signoffs for a draft

        Returns:
            List of signoff records with user details
        """

        result = self.db.client.table("handover_signoffs") \
            .select("""
                *,
                user:user_profiles(id, full_name, email)
            """) \
            .eq("draft_id", draft_id) \
            .order("signed_at", desc=False) \
            .execute()

        return result.data or []

    async def can_transition(
        self,
        draft_id: str,
        to_state: str
    ) -> bool:
        """
        Check if draft can transition to new state

        Args:
            draft_id: Draft ID
            to_state: Target state

        Returns:
            True if transition is valid
        """

        draft = await self._get_draft(draft_id)
        current_state = draft["state"]

        valid_transitions = self.STATE_TRANSITIONS.get(current_state, [])

        return to_state in valid_transitions

    async def get_available_actions(
        self,
        draft_id: str,
        user_id: str
    ) -> list:
        """
        Get available actions for current user and draft state

        Returns:
            List of action objects with label, endpoint, etc.
        """

        draft = await self._get_draft(draft_id)
        state = draft["state"]
        actions = []

        if state == "DRAFT":
            if draft["outgoing_user_id"] == user_id:
                actions.append({
                    "action": "enter_review",
                    "label": "Enter Review",
                    "endpoint": f"/api/v1/handover/drafts/{draft_id}/review",
                    "method": "POST"
                })

        elif state == "IN_REVIEW":
            if draft["outgoing_user_id"] == user_id:
                actions.append({
                    "action": "accept",
                    "label": "Accept Draft",
                    "endpoint": f"/api/v1/handover/drafts/{draft_id}/accept",
                    "method": "POST",
                    "requires_confirmation": True
                })

        elif state == "ACCEPTED":
            if draft.get("incoming_user_id") == user_id:
                actions.append({
                    "action": "countersign",
                    "label": "Countersign Draft",
                    "endpoint": f"/api/v1/handover/drafts/{draft_id}/sign",
                    "method": "POST",
                    "requires_confirmation": True
                })

        elif state == "SIGNED":
            # Anyone can export
            actions.append({
                "action": "export",
                "label": "Export PDF",
                "endpoint": f"/api/v1/handover/drafts/{draft_id}/export",
                "method": "POST"
            })

        return actions
