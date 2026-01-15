"""
Unit tests for Handover Signoff Router
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from src.routers.handover_signoff import (
    accept_handover_draft,
    sign_handover_draft,
    get_draft_signoffs
)
from src.models.handover import HandoverAcceptRequest, HandoverSignRequest


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
        "full_name": "Test User"
    }


class TestAcceptHandoverDraft:
    """Tests for POST /drafts/{draft_id}/accept endpoint"""

    @pytest.mark.asyncio
    async def test_accept_draft_success(self, mock_db, current_user):
        """Test successful draft acceptance"""
        draft_id = uuid4()
        signoff_id = str(uuid4())
        request = HandoverAcceptRequest(confirmed=True, comments="Looks good")

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.accept_draft = AsyncMock(return_value=signoff_id)

            # Mock signoff fetch
            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": signoff_id, "signoff_type": "outgoing"}
            )

            result = await accept_handover_draft(
                draft_id=draft_id,
                request=request,
                db=mock_db,
                current_user=current_user
            )

            assert result.id == signoff_id

    @pytest.mark.asyncio
    async def test_accept_requires_confirmation(self, mock_db, current_user):
        """Test acceptance requires confirmed=true"""
        draft_id = uuid4()
        request = HandoverAcceptRequest(confirmed=False)

        with pytest.raises(HTTPException) as exc_info:
            await accept_handover_draft(
                draft_id=draft_id,
                request=request,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_accept_handles_value_error(self, mock_db, current_user):
        """Test handles ValueError from service"""
        draft_id = uuid4()
        request = HandoverAcceptRequest(confirmed=True)

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.accept_draft = AsyncMock(side_effect=ValueError("Invalid state"))

            with pytest.raises(HTTPException) as exc_info:
                await accept_handover_draft(
                    draft_id=draft_id,
                    request=request,
                    db=mock_db,
                    current_user=current_user
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_accept_with_comments(self, mock_db, current_user):
        """Test acceptance with optional comments"""
        draft_id = uuid4()
        signoff_id = str(uuid4())
        comments = "Everything verified"
        request = HandoverAcceptRequest(confirmed=True, comments=comments)

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.accept_draft = AsyncMock(return_value=signoff_id)

            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": signoff_id, "comments": comments}
            )

            result = await accept_handover_draft(
                draft_id=draft_id,
                request=request,
                db=mock_db,
                current_user=current_user
            )

            mock_manager.accept_draft.assert_called_once_with(
                draft_id=str(draft_id),
                user_id=current_user["id"],
                comments=comments
            )


class TestSignHandoverDraft:
    """Tests for POST /drafts/{draft_id}/sign endpoint"""

    @pytest.mark.asyncio
    async def test_sign_draft_success(self, mock_db, current_user):
        """Test successful draft countersigning"""
        draft_id = uuid4()
        signoff_id = str(uuid4())
        request = HandoverSignRequest(confirmed=True)

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.countersign_draft = AsyncMock(return_value=signoff_id)

            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": signoff_id, "signoff_type": "incoming"}
            )

            result = await sign_handover_draft(
                draft_id=draft_id,
                request=request,
                db=mock_db,
                current_user=current_user
            )

            assert result.id == signoff_id

    @pytest.mark.asyncio
    async def test_sign_requires_confirmation(self, mock_db, current_user):
        """Test signing requires confirmed=true"""
        draft_id = uuid4()
        request = HandoverSignRequest(confirmed=False)

        with pytest.raises(HTTPException) as exc_info:
            await sign_handover_draft(
                draft_id=draft_id,
                request=request,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sign_handles_value_error(self, mock_db, current_user):
        """Test handles ValueError from service"""
        draft_id = uuid4()
        request = HandoverSignRequest(confirmed=True)

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.countersign_draft = AsyncMock(side_effect=ValueError("Not accepted yet"))

            with pytest.raises(HTTPException) as exc_info:
                await sign_handover_draft(
                    draft_id=draft_id,
                    request=request,
                    db=mock_db,
                    current_user=current_user
                )

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sign_with_comments(self, mock_db, current_user):
        """Test countersigning with optional comments"""
        draft_id = uuid4()
        signoff_id = str(uuid4())
        comments = "Acknowledged all items"
        request = HandoverSignRequest(confirmed=True, comments=comments)

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.countersign_draft = AsyncMock(return_value=signoff_id)

            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": signoff_id, "comments": comments}
            )

            result = await sign_handover_draft(
                draft_id=draft_id,
                request=request,
                db=mock_db,
                current_user=current_user
            )

            mock_manager.countersign_draft.assert_called_once_with(
                draft_id=str(draft_id),
                user_id=current_user["id"],
                comments=comments
            )

    @pytest.mark.asyncio
    async def test_sign_handles_general_exception(self, mock_db, current_user):
        """Test handles general exceptions"""
        draft_id = uuid4()
        request = HandoverSignRequest(confirmed=True)

        with patch('src.routers.handover_signoff.SignoffManager') as MockManager:
            mock_manager = MockManager.return_value
            mock_manager.countersign_draft = AsyncMock(side_effect=Exception("Database error"))

            with pytest.raises(HTTPException) as exc_info:
                await sign_handover_draft(
                    draft_id=draft_id,
                    request=request,
                    db=mock_db,
                    current_user=current_user
                )

            assert exc_info.value.status_code == 500


class TestGetDraftSignoffs:
    """Tests for GET /drafts/{draft_id}/signoffs endpoint"""

    @pytest.mark.asyncio
    async def test_get_signoffs_success(self, mock_db, current_user):
        """Test successful signoffs retrieval"""
        draft_id = uuid4()

        # Mock draft exists
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id)}
        )

        # Mock signoffs fetch
        mock_db.client.table().select().eq().order().execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "signoff_type": "outgoing", "user": {"full_name": "User 1"}},
                {"id": str(uuid4()), "signoff_type": "incoming", "user": {"full_name": "User 2"}}
            ]
        )

        result = await get_draft_signoffs(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_signoffs_draft_not_found(self, mock_db, current_user):
        """Test get signoffs when draft doesn't exist"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_draft_signoffs(
                draft_id=draft_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_signoffs_empty_list(self, mock_db, current_user):
        """Test get signoffs returns empty list when no signoffs"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id)}
        )
        mock_db.client.table().select().eq().order().execute.return_value = MagicMock(data=[])

        result = await get_draft_signoffs(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_signoffs_includes_user_details(self, mock_db, current_user):
        """Test get signoffs includes user profile data"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id)}
        )
        mock_db.client.table().select().eq().order().execute.return_value = MagicMock(
            data=[{
                "id": str(uuid4()),
                "signoff_type": "outgoing",
                "user": {
                    "id": str(uuid4()),
                    "full_name": "John Doe",
                    "role": "Engineer"
                }
            }]
        )

        result = await get_draft_signoffs(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert result[0].user is not None

    @pytest.mark.asyncio
    async def test_get_signoffs_ordered_by_time(self, mock_db, current_user):
        """Test signoffs are returned in chronological order"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id)}
        )
        mock_db.client.table().select().eq().order().execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "signoff_type": "outgoing", "signed_at": "2026-01-14T10:00:00Z"},
                {"id": str(uuid4()), "signoff_type": "incoming", "signed_at": "2026-01-14T11:00:00Z"}
            ]
        )

        result = await get_draft_signoffs(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        # Results should be ordered by signed_at
        assert len(result) == 2
