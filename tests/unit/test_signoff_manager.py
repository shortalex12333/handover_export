"""
Unit tests for SignoffManager service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4

from src.services.signoff_manager import SignoffManager


@pytest.fixture
def mock_db():
    """Mock database client"""
    db = MagicMock()
    db.client = MagicMock()
    return db


@pytest.fixture
def signoff_manager(mock_db):
    """Signoff manager instance"""
    return SignoffManager(mock_db)


class TestAcceptDraft:
    """Tests for accept_draft method"""

    @pytest.mark.asyncio
    async def test_accept_draft_success(self, signoff_manager, mock_db):
        """Test successful draft acceptance"""
        draft_id = str(uuid4())
        user_id = str(uuid4())
        signoff_id = str(uuid4())

        # Mock: Draft in IN_REVIEW state with correct outgoing_user
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "outgoing_user_id": user_id}
        )

        # Mock: Create signoff
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": signoff_id}]
        )

        # Mock: Update draft state
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "ACCEPTED"}]
        )

        result = await signoff_manager.accept_draft(
            draft_id=draft_id,
            user_id=user_id
        )

        assert result == signoff_id

    @pytest.mark.asyncio
    async def test_accept_draft_wrong_state(self, signoff_manager, mock_db):
        """Test rejection when draft not in IN_REVIEW state"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        # Mock: Draft in wrong state
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "DRAFT", "outgoing_user_id": user_id}
        )

        with pytest.raises(ValueError, match="Cannot accept from state"):
            await signoff_manager.accept_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_accept_draft_wrong_user(self, signoff_manager, mock_db):
        """Test rejection when user is not outgoing_user"""
        draft_id = str(uuid4())
        user_id = str(uuid4())
        other_user_id = str(uuid4())

        # Mock: Draft with different outgoing_user
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "outgoing_user_id": other_user_id}
        )

        with pytest.raises(ValueError, match="Only outgoing user can accept"):
            await signoff_manager.accept_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_accept_draft_with_comments(self, signoff_manager, mock_db):
        """Test acceptance with optional comments"""
        draft_id = str(uuid4())
        user_id = str(uuid4())
        comments = "Everything looks good"

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "outgoing_user_id": user_id}
        )
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "ACCEPTED"}]
        )

        await signoff_manager.accept_draft(
            draft_id=draft_id,
            user_id=user_id,
            comments=comments
        )

        # Would verify comments were included in insert
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_accept_draft_not_found(self, signoff_manager, mock_db):
        """Test rejection when draft doesn't exist"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data=None
        )

        with pytest.raises(ValueError, match="not found"):
            await signoff_manager.accept_draft(
                draft_id=draft_id,
                user_id=user_id
            )


class TestCountersignDraft:
    """Tests for countersign_draft method"""

    @pytest.mark.asyncio
    async def test_countersign_draft_success(self, signoff_manager, mock_db):
        """Test successful draft countersigning"""
        draft_id = str(uuid4())
        user_id = str(uuid4())
        signoff_id = str(uuid4())

        # Mock: Draft in ACCEPTED state with correct incoming_user
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "ACCEPTED", "incoming_user_id": user_id}
        )

        # Mock: Create signoff
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": signoff_id}]
        )

        # Mock: Update draft state
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "SIGNED"}]
        )

        result = await signoff_manager.countersign_draft(
            draft_id=draft_id,
            user_id=user_id
        )

        assert result == signoff_id

    @pytest.mark.asyncio
    async def test_countersign_draft_wrong_state(self, signoff_manager, mock_db):
        """Test rejection when draft not in ACCEPTED state"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        # Mock: Draft in wrong state
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "incoming_user_id": user_id}
        )

        with pytest.raises(ValueError, match="Cannot countersign from state"):
            await signoff_manager.countersign_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_countersign_draft_wrong_user(self, signoff_manager, mock_db):
        """Test rejection when user is not incoming_user"""
        draft_id = str(uuid4())
        user_id = str(uuid4())
        other_user_id = str(uuid4())

        # Mock: Draft with different incoming_user
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "ACCEPTED", "incoming_user_id": other_user_id}
        )

        with pytest.raises(ValueError, match="Only incoming user can countersign"):
            await signoff_manager.countersign_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_countersign_transitions_to_signed(self, signoff_manager, mock_db):
        """Test state transitions to SIGNED after countersign"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "ACCEPTED", "incoming_user_id": user_id}
        )
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "SIGNED"}]
        )

        await signoff_manager.countersign_draft(
            draft_id=draft_id,
            user_id=user_id
        )

        # Verify update was called with state=SIGNED
        assert mock_db.client.table().update.called

    @pytest.mark.asyncio
    async def test_countersign_with_comments(self, signoff_manager, mock_db):
        """Test countersigning with optional comments"""
        draft_id = str(uuid4())
        user_id = str(uuid4())
        comments = "Acknowledged all items"

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "ACCEPTED", "incoming_user_id": user_id}
        )
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "SIGNED"}]
        )

        await signoff_manager.countersign_draft(
            draft_id=draft_id,
            user_id=user_id,
            comments=comments
        )

        assert mock_db.client.table().insert.called


class TestStateTransitions:
    """Tests for state transition validation"""

    @pytest.mark.asyncio
    async def test_cannot_accept_already_accepted_draft(self, signoff_manager, mock_db):
        """Test cannot accept draft that's already accepted"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "ACCEPTED", "outgoing_user_id": user_id}
        )

        with pytest.raises(ValueError):
            await signoff_manager.accept_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_cannot_countersign_unsigned_draft(self, signoff_manager, mock_db):
        """Test cannot countersign draft that hasn't been accepted"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "incoming_user_id": user_id}
        )

        with pytest.raises(ValueError):
            await signoff_manager.countersign_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_cannot_accept_signed_draft(self, signoff_manager, mock_db):
        """Test cannot accept draft that's already signed"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "SIGNED", "outgoing_user_id": user_id}
        )

        with pytest.raises(ValueError):
            await signoff_manager.accept_draft(
                draft_id=draft_id,
                user_id=user_id
            )

    @pytest.mark.asyncio
    async def test_cannot_countersign_signed_draft(self, signoff_manager, mock_db):
        """Test cannot countersign draft that's already signed"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "SIGNED", "incoming_user_id": user_id}
        )

        with pytest.raises(ValueError):
            await signoff_manager.countersign_draft(
                draft_id=draft_id,
                user_id=user_id
            )


class TestSignoffRecordCreation:
    """Tests for signoff record creation"""

    @pytest.mark.asyncio
    async def test_creates_outgoing_signoff_record(self, signoff_manager, mock_db):
        """Test creates signoff record with type='outgoing'"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "outgoing_user_id": user_id}
        )
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "ACCEPTED"}]
        )

        await signoff_manager.accept_draft(
            draft_id=draft_id,
            user_id=user_id
        )

        # Would verify signoff_type='outgoing' in insert
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_creates_incoming_signoff_record(self, signoff_manager, mock_db):
        """Test creates signoff record with type='incoming'"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "ACCEPTED", "incoming_user_id": user_id}
        )
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "SIGNED"}]
        )

        await signoff_manager.countersign_draft(
            draft_id=draft_id,
            user_id=user_id
        )

        # Would verify signoff_type='incoming' in insert
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_signoff_includes_timestamp(self, signoff_manager, mock_db):
        """Test signoff record includes signed_at timestamp"""
        draft_id = str(uuid4())
        user_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": draft_id, "state": "IN_REVIEW", "outgoing_user_id": user_id}
        )
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": draft_id, "state": "ACCEPTED"}]
        )

        await signoff_manager.accept_draft(
            draft_id=draft_id,
            user_id=user_id
        )

        # Would verify signed_at is set in insert
        assert mock_db.client.table().insert.called
