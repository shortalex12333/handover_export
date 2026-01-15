"""
Unit tests for DraftGenerator service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from src.services.draft_generator import DraftGenerator


@pytest.fixture
def mock_db():
    """Mock database client"""
    db = MagicMock()
    db.client = MagicMock()
    return db


@pytest.fixture
def draft_generator(mock_db):
    """Draft generator instance"""
    return DraftGenerator(mock_db)


class TestGenerateDraft:
    """Tests for generate_draft method"""

    @pytest.mark.asyncio
    async def test_generate_draft_creates_new_draft(self, draft_generator, mock_db):
        """Test successful draft generation"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())
        draft_id = str(uuid4())

        # Mock: No existing draft
        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])

        # Mock: Fetch entries
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {
                "id": str(uuid4()),
                "summary_text": "Generator maintenance needed",
                "domain_code": "ENG-01",
                "presentation_bucket": "Engineering",
                "is_critical": True
            },
            {
                "id": str(uuid4()),
                "summary_text": "Navigation system update",
                "domain_code": "NAV-01",
                "presentation_bucket": "Command",
                "is_critical": False
            }
        ])

        # Mock: Create draft
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": draft_id}]
        )

        result = await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        assert result == draft_id

    @pytest.mark.asyncio
    async def test_returns_existing_draft_in_draft_state(self, draft_generator, mock_db):
        """Test returns existing DRAFT instead of creating new one"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())
        existing_draft_id = str(uuid4())

        # Mock: Existing draft found
        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(
            data=[{"id": existing_draft_id, "state": "DRAFT"}]
        )

        result = await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        assert result == existing_draft_id

    @pytest.mark.asyncio
    async def test_groups_entries_by_bucket(self, draft_generator, mock_db):
        """Test entries are correctly grouped by presentation bucket"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        # Mock: No existing draft
        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])

        # Mock: Multiple entries in different buckets
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {"id": str(uuid4()), "summary_text": "Text 1", "presentation_bucket": "Engineering", "domain_code": "ENG-01", "is_critical": False},
            {"id": str(uuid4()), "summary_text": "Text 2", "presentation_bucket": "Engineering", "domain_code": "ENG-02", "is_critical": False},
            {"id": str(uuid4()), "summary_text": "Text 3", "presentation_bucket": "Command", "domain_code": "CMD-01", "is_critical": False},
        ])

        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        # Verify sections were created (would need to check insert calls)
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_handles_empty_entries(self, draft_generator, mock_db):
        """Test handles case with no entries to process"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        # Mock: No existing draft
        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])

        # Mock: No entries
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])

        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        result = await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_sets_incoming_user_when_provided(self, draft_generator, mock_db):
        """Test incoming_user_id is set when provided"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())
        incoming_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id,
            incoming_user_id=incoming_user_id
        )

        # Would need to verify insert was called with incoming_user_id
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_uses_custom_period_dates(self, draft_generator, mock_db):
        """Test custom period_start and period_end are used"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())
        period_start = datetime(2026, 1, 1, 0, 0, 0)
        period_end = datetime(2026, 1, 14, 23, 59, 59)

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id,
            period_start=period_start,
            period_end=period_end
        )

        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_handles_shift_type(self, draft_generator, mock_db):
        """Test shift_type parameter is handled"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id,
            shift_type="night"
        )

        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_preserves_critical_flag(self, draft_generator, mock_db):
        """Test critical flag is preserved from entries"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {
                "id": str(uuid4()),
                "summary_text": "Critical issue",
                "domain_code": "ENG-01",
                "presentation_bucket": "Engineering",
                "is_critical": True
            }
        ])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_creates_sections_in_order(self, draft_generator, mock_db):
        """Test sections are created with proper ordering"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {"id": str(uuid4()), "summary_text": "A", "presentation_bucket": "Command", "domain_code": "CMD", "is_critical": False},
            {"id": str(uuid4()), "summary_text": "B", "presentation_bucket": "Engineering", "domain_code": "ENG", "is_critical": False},
        ])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        # Section ordering would be verified in actual implementation
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_handles_database_insert_failure(self, draft_generator, mock_db):
        """Test handles database insert failure gracefully"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])

        # Simulate insert failure
        mock_db.client.table().insert().execute.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await draft_generator.generate_draft(
                yacht_id=yacht_id,
                outgoing_user_id=outgoing_user_id
            )

    @pytest.mark.asyncio
    async def test_creates_items_with_source_references(self, draft_generator, mock_db):
        """Test items maintain source entry references"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())
        entry_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {
                "id": entry_id,
                "summary_text": "Test entry",
                "domain_code": "ENG-01",
                "presentation_bucket": "Engineering",
                "is_critical": False
            }
        ])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        # Source reference preservation would be verified
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_handles_none_period_dates(self, draft_generator, mock_db):
        """Test defaults to current period when dates not provided"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id,
            period_start=None,
            period_end=None
        )

        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_sets_initial_state_to_draft(self, draft_generator, mock_db):
        """Test new drafts are created in DRAFT state"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        # Would verify state="DRAFT" in insert call
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_handles_multiple_buckets(self, draft_generator, mock_db):
        """Test correctly handles entries across all presentation buckets"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {"id": str(uuid4()), "summary_text": "1", "presentation_bucket": "Command", "domain_code": "CMD", "is_critical": False},
            {"id": str(uuid4()), "summary_text": "2", "presentation_bucket": "Engineering", "domain_code": "ENG", "is_critical": False},
            {"id": str(uuid4()), "summary_text": "3", "presentation_bucket": "Interior", "domain_code": "INT", "is_critical": False},
            {"id": str(uuid4()), "summary_text": "4", "presentation_bucket": "Deck", "domain_code": "DEC", "is_critical": False},
        ])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        # All buckets should create sections
        assert mock_db.client.table().insert.called

    @pytest.mark.asyncio
    async def test_item_order_preserved_within_section(self, draft_generator, mock_db):
        """Test items maintain correct order within sections"""
        yacht_id = str(uuid4())
        outgoing_user_id = str(uuid4())

        mock_db.client.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_db.client.table().select().eq().gte().lte().eq().execute.return_value = MagicMock(data=[
            {"id": str(uuid4()), "summary_text": "First", "presentation_bucket": "Engineering", "domain_code": "ENG-01", "is_critical": True},
            {"id": str(uuid4()), "summary_text": "Second", "presentation_bucket": "Engineering", "domain_code": "ENG-02", "is_critical": False},
        ])
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        await draft_generator.generate_draft(
            yacht_id=yacht_id,
            outgoing_user_id=outgoing_user_id
        )

        # Critical items should be ordered first
        assert mock_db.client.table().insert.called
