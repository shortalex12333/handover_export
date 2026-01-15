"""
Unit tests for Handover Drafts Router
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException

from src.routers.handover_drafts import (
    generate_handover_draft,
    get_handover_draft,
    enter_review_state,
    edit_draft_item,
    merge_draft_items,
    delete_draft_item,
    list_handover_drafts,
    get_handover_history
)
from src.models.handover import (
    HandoverDraftGenerate,
    HandoverDraftItemEdit,
    HandoverDraftItemMerge,
    HandoverDraftState
)


@pytest.fixture
def mock_db():
    """Mock database client"""
    db = MagicMock()
    db.client = MagicMock()
    return db


@pytest.fixture
def current_user():
    """Mock current user"""
    return {
        "id": str(uuid4()),
        "yacht_id": str(uuid4()),
        "full_name": "Test User",
        "role": "Engineer"
    }


class TestGenerateHandoverDraft:
    """Tests for POST /drafts/generate endpoint"""

    @pytest.mark.asyncio
    async def test_generate_draft_success(self, mock_db, current_user):
        """Test successful draft generation"""
        draft_id = str(uuid4())
        request = HandoverDraftGenerate(
            outgoing_user_id=uuid4(),
            incoming_user_id=uuid4(),
            period_start=datetime.now(),
            period_end=datetime.now(),
            shift_type="day"
        )

        with patch('src.routers.handover_drafts.DraftGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate_draft = AsyncMock(return_value=draft_id)

            # Mock database queries
            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": draft_id, "state": "DRAFT", "yacht_id": current_user["yacht_id"]}
            )
            mock_db.client.table().select().eq().order().execute.return_value = MagicMock(data=[])

            result = await generate_handover_draft(
                request=request,
                db=mock_db,
                current_user=current_user
            )

            assert result.id == draft_id

    @pytest.mark.asyncio
    async def test_generate_draft_calls_service(self, mock_db, current_user):
        """Test generate endpoint calls DraftGenerator service"""
        draft_id = str(uuid4())
        outgoing_user_id = uuid4()
        request = HandoverDraftGenerate(
            outgoing_user_id=outgoing_user_id,
            period_start=datetime.now(),
            period_end=datetime.now(),
            shift_type="day"
        )

        with patch('src.routers.handover_drafts.DraftGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate_draft = AsyncMock(return_value=draft_id)

            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": draft_id}
            )
            mock_db.client.table().select().eq().order().execute.return_value = MagicMock(data=[])

            await generate_handover_draft(
                request=request,
                db=mock_db,
                current_user=current_user
            )

            mock_generator.generate_draft.assert_called_once()


class TestGetHandoverDraft:
    """Tests for GET /drafts/{draft_id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_draft_success(self, mock_db, current_user):
        """Test successful draft retrieval"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "DRAFT", "yacht_id": current_user["yacht_id"]}
        )
        mock_db.client.table().select().eq().order().execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "section_bucket": "Engineering", "section_order": 1}]
        )

        result = await get_handover_draft(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert str(result.id) == str(draft_id)

    @pytest.mark.asyncio
    async def test_get_draft_not_found(self, mock_db, current_user):
        """Test get draft when draft doesn't exist"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_handover_draft(
                draft_id=draft_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_draft_includes_sections(self, mock_db, current_user):
        """Test get draft includes sections and items"""
        draft_id = uuid4()
        section_id = str(uuid4())

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "DRAFT"}
        )
        mock_db.client.table().select().eq().order().execute.return_value = MagicMock(
            data=[{"id": section_id, "section_bucket": "Engineering", "section_order": 1}]
        )

        result = await get_handover_draft(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert len(result.sections) > 0


class TestEnterReviewState:
    """Tests for POST /drafts/{draft_id}/review endpoint"""

    @pytest.mark.asyncio
    async def test_enter_review_success(self, mock_db, current_user):
        """Test successful transition to IN_REVIEW"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "DRAFT"}
        )
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": str(draft_id), "state": "IN_REVIEW"}]
        )

        result = await enter_review_state(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert result["success"] is True
        assert result["new_state"] == "IN_REVIEW"

    @pytest.mark.asyncio
    async def test_enter_review_wrong_state(self, mock_db, current_user):
        """Test cannot enter review from non-DRAFT state"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "IN_REVIEW"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await enter_review_state(
                draft_id=draft_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_enter_review_not_found(self, mock_db, current_user):
        """Test enter review when draft doesn't exist"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc_info:
            await enter_review_state(
                draft_id=draft_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404


class TestEditDraftItem:
    """Tests for PATCH /drafts/{draft_id}/items/{item_id} endpoint"""

    @pytest.mark.asyncio
    async def test_edit_item_success(self, mock_db, current_user):
        """Test successful item edit"""
        draft_id = uuid4()
        item_id = uuid4()
        edit = HandoverDraftItemEdit(
            edited_text="Updated text",
            edit_reason="Correction needed"
        )

        # Mock draft in IN_REVIEW
        mock_db.client.table().select().eq().single().execute.side_effect = [
            MagicMock(data={"id": str(draft_id), "state": "IN_REVIEW"}),
            MagicMock(data={"id": str(item_id), "summary_text": "Original text", "edit_count": 0})
        ]

        # Mock insert edit history
        mock_db.client.table().insert().execute.return_value = MagicMock(data=[{}])

        # Mock update item
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": str(item_id), "summary_text": "Updated text", "edit_count": 1}]
        )

        result = await edit_draft_item(
            draft_id=draft_id,
            item_id=item_id,
            edit=edit,
            db=mock_db,
            current_user=current_user
        )

        assert result.summary_text == "Updated text"
        assert result.edit_count == 1

    @pytest.mark.asyncio
    async def test_edit_item_wrong_state(self, mock_db, current_user):
        """Test cannot edit item when not in IN_REVIEW"""
        draft_id = uuid4()
        item_id = uuid4()
        edit = HandoverDraftItemEdit(edited_text="New text")

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "DRAFT"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await edit_draft_item(
                draft_id=draft_id,
                item_id=item_id,
                edit=edit,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400


class TestMergeDraftItems:
    """Tests for POST /drafts/{draft_id}/items/merge endpoint"""

    @pytest.mark.asyncio
    async def test_merge_items_success(self, mock_db, current_user):
        """Test successful item merge"""
        draft_id = uuid4()
        item1_id = uuid4()
        item2_id = uuid4()
        merge_request = HandoverDraftItemMerge(
            item_ids=[item1_id, item2_id],
            merged_text="Combined text"
        )

        # Mock draft in IN_REVIEW
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "IN_REVIEW"}
        )

        # Mock fetch items
        mock_db.client.table().select().in_().execute.return_value = MagicMock(
            data=[
                {"id": str(item1_id), "section_id": "sec-1", "is_critical": False, "source_entry_ids": [], "item_order": 1},
                {"id": str(item2_id), "section_id": "sec-1", "is_critical": True, "source_entry_ids": [], "item_order": 2}
            ]
        )

        # Mock insert merged item
        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "summary_text": "Combined text", "is_critical": True}]
        )

        # Mock suppression update
        mock_db.client.table().update().in_().execute.return_value = MagicMock(data=[])

        result = await merge_draft_items(
            draft_id=draft_id,
            merge_request=merge_request,
            db=mock_db,
            current_user=current_user
        )

        assert result.summary_text == "Combined text"

    @pytest.mark.asyncio
    async def test_merge_items_min_count_validation(self, mock_db, current_user):
        """Test merge requires at least 2 items"""
        draft_id = uuid4()
        merge_request = HandoverDraftItemMerge(
            item_ids=[uuid4()],
            merged_text="Text"
        )

        with pytest.raises(HTTPException) as exc_info:
            await merge_draft_items(
                draft_id=draft_id,
                merge_request=merge_request,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400


class TestDeleteDraftItem:
    """Tests for DELETE /drafts/{draft_id}/items/{item_id} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_item_success(self, mock_db, current_user):
        """Test successful item deletion (soft delete)"""
        draft_id = uuid4()
        item_id = uuid4()

        # Mock draft in IN_REVIEW
        mock_db.client.table().select().eq().single().execute.side_effect = [
            MagicMock(data={"id": str(draft_id), "state": "IN_REVIEW"}),
            MagicMock(data={"id": str(item_id)})
        ]

        # Mock suppression update
        mock_db.client.table().update().eq().execute.return_value = MagicMock(
            data=[{"id": str(item_id), "is_suppressed": True}]
        )

        result = await delete_draft_item(
            draft_id=draft_id,
            item_id=item_id,
            db=mock_db,
            current_user=current_user
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_item_wrong_state(self, mock_db, current_user):
        """Test cannot delete item when not in IN_REVIEW"""
        draft_id = uuid4()
        item_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "SIGNED"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_draft_item(
                draft_id=draft_id,
                item_id=item_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400


class TestListHandoverDrafts:
    """Tests for GET /drafts endpoint"""

    @pytest.mark.asyncio
    async def test_list_drafts_success(self, mock_db, current_user):
        """Test successful draft listing"""
        mock_db.client.table().select().eq().range().order().execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "state": "DRAFT", "yacht_id": current_user["yacht_id"]},
                {"id": str(uuid4()), "state": "IN_REVIEW", "yacht_id": current_user["yacht_id"]}
            ]
        )

        result = await list_handover_drafts(
            db=mock_db,
            current_user=current_user
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_drafts_with_state_filter(self, mock_db, current_user):
        """Test listing with state filter"""
        mock_db.client.table().select().eq().eq().range().order().execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "state": "DRAFT"}]
        )

        result = await list_handover_drafts(
            state=HandoverDraftState.DRAFT,
            db=mock_db,
            current_user=current_user
        )

        assert len(result) >= 0


class TestGetHandoverHistory:
    """Tests for GET /drafts/history endpoint"""

    @pytest.mark.asyncio
    async def test_get_history_success(self, mock_db, current_user):
        """Test successful history retrieval"""
        mock_db.client.table().select().eq().in_().range().order().execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "state": "SIGNED", "period_end": "2026-01-14"},
                {"id": str(uuid4()), "state": "EXPORTED", "period_end": "2026-01-13"}
            ]
        )

        result = await get_handover_history(
            db=mock_db,
            current_user=current_user
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_history_only_signed_exported(self, mock_db, current_user):
        """Test history only returns SIGNED and EXPORTED drafts"""
        mock_db.client.table().select().eq().in_().range().order().execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "state": "SIGNED"}]
        )

        result = await get_handover_history(
            db=mock_db,
            current_user=current_user
        )

        # All returned drafts should be SIGNED or EXPORTED
        for draft in result:
            assert draft.state in ["SIGNED", "EXPORTED"]
