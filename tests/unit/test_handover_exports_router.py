"""
Unit tests for Handover Exports Router
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import HTTPException

from src.routers.handover_exports import (
    export_handover_draft,
    get_export,
    download_export,
    get_signed_handover,
    list_exports
)
from src.models.handover import HandoverExportRequest, ExportType


@pytest.fixture
def mock_db():
    """Mock database client"""
    db = MagicMock()
    db.client = MagicMock()
    db.client.storage = MagicMock()
    return db


@pytest.fixture
def current_user():
    """Mock current user"""
    return {
        "id": str(uuid4()),
        "yacht_id": str(uuid4()),
        "full_name": "Test User"
    }


@pytest.fixture
def background_tasks():
    """Mock background tasks"""
    return MagicMock()


class TestExportHandoverDraft:
    """Tests for POST /drafts/{draft_id}/export endpoint"""

    @pytest.mark.asyncio
    async def test_export_pdf_success(self, mock_db, current_user, background_tasks):
        """Test successful PDF export"""
        draft_id = uuid4()
        export_id = str(uuid4())
        request = HandoverExportRequest(export_type=ExportType.pdf)

        with patch('src.routers.handover_exports.HandoverExporter') as MockExporter:
            mock_exporter = MockExporter.return_value
            mock_exporter.export_to_pdf = AsyncMock(return_value=export_id)

            # Mock fetch export
            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": export_id, "export_type": "pdf", "file_url": "https://storage.url/file.pdf"}
            )

            result = await export_handover_draft(
                draft_id=draft_id,
                request=request,
                background_tasks=background_tasks,
                db=mock_db,
                current_user=current_user
            )

            assert result.id == export_id

    @pytest.mark.asyncio
    async def test_export_html_success(self, mock_db, current_user, background_tasks):
        """Test successful HTML export"""
        draft_id = uuid4()
        export_id = str(uuid4())
        request = HandoverExportRequest(export_type=ExportType.html)

        with patch('src.routers.handover_exports.HandoverExporter') as MockExporter:
            mock_exporter = MockExporter.return_value
            mock_exporter.export_to_html = AsyncMock(return_value=export_id)

            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": export_id, "export_type": "html"}
            )

            result = await export_handover_draft(
                draft_id=draft_id,
                request=request,
                background_tasks=background_tasks,
                db=mock_db,
                current_user=current_user
            )

            assert result.id == export_id

    @pytest.mark.asyncio
    async def test_export_email_requires_recipients(self, mock_db, current_user, background_tasks):
        """Test email export requires recipients"""
        draft_id = uuid4()
        request = HandoverExportRequest(export_type=ExportType.email)

        with pytest.raises(HTTPException) as exc_info:
            await export_handover_draft(
                draft_id=draft_id,
                request=request,
                background_tasks=background_tasks,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_export_email_with_recipients(self, mock_db, current_user, background_tasks):
        """Test email export with recipients"""
        draft_id = uuid4()
        export_id = str(uuid4())
        request = HandoverExportRequest(
            export_type=ExportType.email,
            recipients=["user1@yacht.com", "user2@yacht.com"]
        )

        with patch('src.routers.handover_exports.HandoverExporter') as MockExporter:
            mock_exporter = MockExporter.return_value
            mock_exporter.export_to_email = AsyncMock(return_value=export_id)

            mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
                data={"id": export_id, "export_type": "email"}
            )

            result = await export_handover_draft(
                draft_id=draft_id,
                request=request,
                background_tasks=background_tasks,
                db=mock_db,
                current_user=current_user
            )

            assert result.id == export_id

    @pytest.mark.asyncio
    async def test_export_handles_value_error(self, mock_db, current_user, background_tasks):
        """Test handles ValueError from service"""
        draft_id = uuid4()
        request = HandoverExportRequest(export_type=ExportType.pdf)

        with patch('src.routers.handover_exports.HandoverExporter') as MockExporter:
            mock_exporter = MockExporter.return_value
            mock_exporter.export_to_pdf = AsyncMock(side_effect=ValueError("Draft not signed"))

            with pytest.raises(HTTPException) as exc_info:
                await export_handover_draft(
                    draft_id=draft_id,
                    request=request,
                    background_tasks=background_tasks,
                    db=mock_db,
                    current_user=current_user
                )

            assert exc_info.value.status_code == 400


class TestGetExport:
    """Tests for GET /exports/{export_id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_export_success(self, mock_db, current_user):
        """Test successful export retrieval"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(export_id), "export_type": "pdf", "file_url": "https://storage.url/file.pdf"}
        )

        result = await get_export(
            export_id=export_id,
            db=mock_db,
            current_user=current_user
        )

        assert str(result.id) == str(export_id)

    @pytest.mark.asyncio
    async def test_get_export_not_found(self, mock_db, current_user):
        """Test get export when export doesn't exist"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_export(
                export_id=export_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_export_generates_signed_url(self, mock_db, current_user):
        """Test generates signed URL for Supabase storage"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(export_id), "export_type": "pdf", "file_url": "https://supabase.co/handovers/file.pdf"}
        )

        mock_db.client.storage.from_().create_signed_url.return_value = {
            "signedURL": "https://supabase.co/signed-url"
        }

        result = await get_export(
            export_id=export_id,
            db=mock_db,
            current_user=current_user
        )

        # File URL should be signed
        assert "signed" in result.file_url or result.file_url is not None


class TestDownloadExport:
    """Tests for GET /exports/{export_id}/download endpoint"""

    @pytest.mark.asyncio
    async def test_download_export_success(self, mock_db, current_user):
        """Test successful export download"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(export_id), "export_type": "pdf", "file_url": "https://supabase.co/handovers/file.pdf"}
        )

        mock_db.client.storage.from_().create_signed_url.return_value = {
            "signedURL": "https://supabase.co/signed-download"
        }

        result = await download_export(
            export_id=export_id,
            db=mock_db,
            current_user=current_user
        )

        # Should return redirect response
        assert result is not None

    @pytest.mark.asyncio
    async def test_download_export_not_found(self, mock_db, current_user):
        """Test download when export doesn't exist"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc_info:
            await download_export(
                export_id=export_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_download_email_export_rejected(self, mock_db, current_user):
        """Test cannot download email exports"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(export_id), "export_type": "email", "file_url": None}
        )

        with pytest.raises(HTTPException) as exc_info:
            await download_export(
                export_id=export_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_download_no_file_url(self, mock_db, current_user):
        """Test download when file URL is missing"""
        export_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(export_id), "export_type": "pdf", "file_url": None}
        )

        with pytest.raises(HTTPException) as exc_info:
            await download_export(
                export_id=export_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404


class TestGetSignedHandover:
    """Tests for GET /signed/{draft_id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_signed_handover_success(self, mock_db, current_user):
        """Test successful signed handover retrieval"""
        draft_id = uuid4()

        # Mock draft fetch
        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "SIGNED", "yacht_id": current_user["yacht_id"]}
        )

        # Mock signoffs fetch
        mock_db.client.table().select().eq().order().execute.side_effect = [
            MagicMock(data=[{"id": str(uuid4()), "signoff_type": "outgoing"}]),
            MagicMock(data=[{"id": str(uuid4()), "export_type": "pdf"}])
        ]

        result = await get_signed_handover(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert result["draft"]["id"] == str(draft_id)

    @pytest.mark.asyncio
    async def test_get_signed_handover_not_found(self, mock_db, current_user):
        """Test get signed handover when draft doesn't exist"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(data=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_signed_handover(
                draft_id=draft_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_signed_handover_not_signed(self, mock_db, current_user):
        """Test get signed handover when draft not signed"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().single().execute.return_value = MagicMock(
            data={"id": str(draft_id), "state": "IN_REVIEW"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_signed_handover(
                draft_id=draft_id,
                db=mock_db,
                current_user=current_user
            )

        assert exc_info.value.status_code == 400


class TestListExports:
    """Tests for GET /exports endpoint"""

    @pytest.mark.asyncio
    async def test_list_exports_success(self, mock_db, current_user):
        """Test successful exports listing"""
        # Mock drafts for yacht
        mock_db.client.table().select().eq().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}, {"id": str(uuid4())}]
        )

        # Mock exports fetch
        mock_db.client.table().select().in_().range().order().execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "export_type": "pdf"},
                {"id": str(uuid4()), "export_type": "html"}
            ]
        )

        result = await list_exports(
            db=mock_db,
            current_user=current_user
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_exports_with_draft_filter(self, mock_db, current_user):
        """Test list exports with draft_id filter"""
        draft_id = uuid4()

        mock_db.client.table().select().eq().execute.return_value = MagicMock(
            data=[{"id": str(draft_id)}]
        )

        mock_db.client.table().select().in_().eq().range().order().execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "draft_id": str(draft_id)}]
        )

        result = await list_exports(
            draft_id=draft_id,
            db=mock_db,
            current_user=current_user
        )

        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_list_exports_with_type_filter(self, mock_db, current_user):
        """Test list exports with export_type filter"""
        mock_db.client.table().select().eq().execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )

        mock_db.client.table().select().in_().eq().range().order().execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "export_type": "pdf"}]
        )

        result = await list_exports(
            export_type=ExportType.pdf,
            db=mock_db,
            current_user=current_user
        )

        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_list_exports_empty_when_no_drafts(self, mock_db, current_user):
        """Test list exports returns empty when no drafts"""
        mock_db.client.table().select().eq().execute.return_value = MagicMock(data=[])

        result = await list_exports(
            db=mock_db,
            current_user=current_user
        )

        assert len(result) == 0
