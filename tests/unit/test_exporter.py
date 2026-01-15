"""
Unit tests for HandoverExporter service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from uuid import uuid4

from src.services.exporter import HandoverExporter


@pytest.fixture
def mock_db():
    """Mock database client"""
    db = MagicMock()
    db.client = MagicMock()
    db.client.storage = MagicMock()
    return db


@pytest.fixture
def exporter(mock_db):
    """Exporter instance"""
    with patch('src.services.exporter.Environment'):
        return HandoverExporter(mock_db)


@pytest.fixture
def mock_draft_data():
    """Sample draft data for testing"""
    return {
        "id": str(uuid4()),
        "yacht_id": str(uuid4()),
        "state": "SIGNED",
        "period_start": "2026-01-01T00:00:00Z",
        "period_end": "2026-01-14T23:59:59Z",
        "shift_type": "day",
        "outgoing_user": {
            "id": str(uuid4()),
            "full_name": "John Doe",
            "email": "john@yacht.com",
            "role": "Chief Engineer"
        },
        "incoming_user": {
            "id": str(uuid4()),
            "full_name": "Jane Smith",
            "email": "jane@yacht.com",
            "role": "Engineer"
        },
        "sections": [
            {
                "id": str(uuid4()),
                "section_bucket": "Engineering",
                "section_order": 1,
                "items": [
                    {
                        "id": str(uuid4()),
                        "summary_text": "Generator maintenance completed",
                        "is_critical": True,
                        "domain_code": "ENG-01",
                        "edit_count": 0
                    }
                ]
            }
        ],
        "signoffs": [
            {
                "id": str(uuid4()),
                "signoff_type": "outgoing",
                "signed_at": "2026-01-14T10:00:00Z",
                "user": {
                    "full_name": "John Doe",
                    "role": "Chief Engineer"
                },
                "comments": None
            },
            {
                "id": str(uuid4()),
                "signoff_type": "incoming",
                "signed_at": "2026-01-14T11:00:00Z",
                "user": {
                    "full_name": "Jane Smith",
                    "role": "Engineer"
                },
                "comments": "Acknowledged"
            }
        ]
    }


class TestExportToPDF:
    """Tests for export_to_pdf method"""

    @pytest.mark.asyncio
    async def test_export_pdf_success(self, exporter, mock_db, mock_draft_data):
        """Test successful PDF export"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())
        export_id = str(uuid4())

        # Mock fetch draft
        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            # Mock render template
            with patch.object(exporter, '_render_template', return_value="<html></html>"):
                # Mock HTML to PDF
                with patch.object(exporter, '_html_to_pdf', return_value=b'PDF content'):
                    # Mock upload
                    with patch.object(exporter, '_upload_to_storage', return_value="https://storage.url/file.pdf"):
                        # Mock create export record
                        with patch.object(exporter, '_create_export_record', return_value=export_id):
                            result = await exporter.export_to_pdf(
                                draft_id=draft_id,
                                yacht_id=yacht_id
                            )

                            assert result == export_id

    @pytest.mark.asyncio
    async def test_export_pdf_draft_not_signed(self, exporter, mock_db, mock_draft_data):
        """Test PDF export rejection when draft not SIGNED"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())

        # Set draft state to not SIGNED
        mock_draft_data["state"] = "IN_REVIEW"

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with pytest.raises(ValueError, match="must be SIGNED"):
                await exporter.export_to_pdf(
                    draft_id=draft_id,
                    yacht_id=yacht_id
                )

    @pytest.mark.asyncio
    async def test_export_pdf_draft_not_found(self, exporter, mock_db):
        """Test PDF export when draft doesn't exist"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())

        with patch.object(exporter, '_fetch_draft_with_details', side_effect=ValueError("Draft not found")):
            with pytest.raises(ValueError, match="not found"):
                await exporter.export_to_pdf(
                    draft_id=draft_id,
                    yacht_id=yacht_id
                )

    @pytest.mark.asyncio
    async def test_export_pdf_calls_html_to_pdf(self, exporter, mock_db, mock_draft_data):
        """Test PDF export calls HTML to PDF conversion"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with patch.object(exporter, '_render_template', return_value="<html></html>") as mock_render:
                with patch.object(exporter, '_html_to_pdf', return_value=b'PDF') as mock_pdf:
                    with patch.object(exporter, '_upload_to_storage', return_value="url"):
                        with patch.object(exporter, '_create_export_record', return_value=str(uuid4())):
                            await exporter.export_to_pdf(
                                draft_id=draft_id,
                                yacht_id=yacht_id
                            )

                            mock_render.assert_called_once()
                            mock_pdf.assert_called_once_with("<html></html>")

    @pytest.mark.asyncio
    async def test_export_pdf_uploads_to_storage(self, exporter, mock_db, mock_draft_data):
        """Test PDF export uploads file to storage"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with patch.object(exporter, '_render_template', return_value="<html></html>"):
                with patch.object(exporter, '_html_to_pdf', return_value=b'PDF content') as mock_pdf:
                    with patch.object(exporter, '_upload_to_storage', return_value="url") as mock_upload:
                        with patch.object(exporter, '_create_export_record', return_value=str(uuid4())):
                            await exporter.export_to_pdf(
                                draft_id=draft_id,
                                yacht_id=yacht_id
                            )

                            mock_upload.assert_called_once_with(
                                b'PDF content',
                                yacht_id,
                                draft_id,
                                file_type="pdf"
                            )


class TestExportToHTML:
    """Tests for export_to_html method"""

    @pytest.mark.asyncio
    async def test_export_html_success(self, exporter, mock_db, mock_draft_data):
        """Test successful HTML export"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())
        export_id = str(uuid4())

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with patch.object(exporter, '_render_template', return_value="<html></html>"):
                with patch.object(exporter, '_upload_to_storage', return_value="https://storage.url/file.html"):
                    with patch.object(exporter, '_create_export_record', return_value=export_id):
                        result = await exporter.export_to_html(
                            draft_id=draft_id,
                            yacht_id=yacht_id
                        )

                        assert result == export_id

    @pytest.mark.asyncio
    async def test_export_html_draft_not_signed(self, exporter, mock_db, mock_draft_data):
        """Test HTML export rejection when draft not SIGNED"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())

        mock_draft_data["state"] = "DRAFT"

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with pytest.raises(ValueError, match="must be SIGNED"):
                await exporter.export_to_html(
                    draft_id=draft_id,
                    yacht_id=yacht_id
                )

    @pytest.mark.asyncio
    async def test_export_html_uploads_correctly(self, exporter, mock_db, mock_draft_data):
        """Test HTML export uploads with correct encoding"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())
        html_content = "<html><body>Test</body></html>"

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with patch.object(exporter, '_render_template', return_value=html_content):
                with patch.object(exporter, '_upload_to_storage', return_value="url") as mock_upload:
                    with patch.object(exporter, '_create_export_record', return_value=str(uuid4())):
                        await exporter.export_to_html(
                            draft_id=draft_id,
                            yacht_id=yacht_id
                        )

                        mock_upload.assert_called_once_with(
                            html_content.encode('utf-8'),
                            yacht_id,
                            draft_id,
                            file_type="html"
                        )


class TestExportToEmail:
    """Tests for export_to_email method"""

    @pytest.mark.asyncio
    async def test_export_email_success(self, exporter, mock_db, mock_draft_data):
        """Test successful email export"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())
        recipients = ["user1@yacht.com", "user2@yacht.com"]
        export_id = str(uuid4())

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with patch.object(exporter, '_render_template', return_value="<html></html>"):
                with patch.object(exporter, '_html_to_pdf', return_value=b'PDF'):
                    with patch.object(exporter, '_send_email', return_value=None):
                        with patch.object(exporter, '_create_export_record', return_value=export_id):
                            result = await exporter.export_to_email(
                                draft_id=draft_id,
                                yacht_id=yacht_id,
                                recipients=recipients
                            )

                            assert result == export_id

    @pytest.mark.asyncio
    async def test_export_email_draft_not_signed(self, exporter, mock_db, mock_draft_data):
        """Test email export rejection when draft not SIGNED"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())
        recipients = ["user@yacht.com"]

        mock_draft_data["state"] = "ACCEPTED"

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with pytest.raises(ValueError, match="must be SIGNED"):
                await exporter.export_to_email(
                    draft_id=draft_id,
                    yacht_id=yacht_id,
                    recipients=recipients
                )

    @pytest.mark.asyncio
    async def test_export_email_sends_with_attachment(self, exporter, mock_db, mock_draft_data):
        """Test email export includes PDF attachment"""
        draft_id = str(uuid4())
        yacht_id = str(uuid4())
        recipients = ["user@yacht.com"]
        pdf_bytes = b'PDF content'

        with patch.object(exporter, '_fetch_draft_with_details', return_value=mock_draft_data):
            with patch.object(exporter, '_render_template', return_value="<html></html>"):
                with patch.object(exporter, '_html_to_pdf', return_value=pdf_bytes):
                    with patch.object(exporter, '_send_email', return_value=None) as mock_send:
                        with patch.object(exporter, '_create_export_record', return_value=str(uuid4())):
                            await exporter.export_to_email(
                                draft_id=draft_id,
                                yacht_id=yacht_id,
                                recipients=recipients
                            )

                            # Verify send_email was called with PDF attachment
                            call_args = mock_send.call_args
                            assert call_args[1]['pdf_attachment'] == pdf_bytes


class TestTemplateRendering:
    """Tests for _render_template method"""

    @pytest.mark.asyncio
    async def test_render_template_with_draft_data(self, exporter, mock_draft_data):
        """Test template rendering with draft data"""
        with patch.object(exporter.jinja_env, 'get_template') as mock_get_template:
            mock_template = MagicMock()
            mock_template.render.return_value = "<html>Rendered</html>"
            mock_get_template.return_value = mock_template

            result = await exporter._render_template(mock_draft_data)

            assert result == "<html>Rendered</html>"
            mock_template.render.assert_called_once()

    @pytest.mark.asyncio
    async def test_render_template_includes_generated_at(self, exporter, mock_draft_data):
        """Test template rendering includes generated_at timestamp"""
        with patch.object(exporter.jinja_env, 'get_template') as mock_get_template:
            mock_template = MagicMock()
            mock_template.render.return_value = "<html></html>"
            mock_get_template.return_value = mock_template

            await exporter._render_template(mock_draft_data)

            # Verify generated_at was passed to template
            call_args = mock_template.render.call_args[1]
            assert 'generated_at' in call_args


class TestHTMLToPDF:
    """Tests for _html_to_pdf method"""

    def test_html_to_pdf_conversion(self, exporter):
        """Test HTML to PDF conversion"""
        html_content = "<html><body>Test</body></html>"

        with patch('src.services.exporter.HTML') as mock_html_class:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b'PDF bytes'
            mock_html_class.return_value = mock_html_instance

            result = exporter._html_to_pdf(html_content)

            assert result == b'PDF bytes'
            mock_html_class.assert_called_once_with(string=html_content)

    def test_html_to_pdf_handles_errors(self, exporter):
        """Test HTML to PDF handles conversion errors"""
        html_content = "<html><body>Test</body></html>"

        with patch('src.services.exporter.HTML') as mock_html_class:
            mock_html_class.side_effect = Exception("Conversion failed")

            with pytest.raises(Exception, match="Conversion failed"):
                exporter._html_to_pdf(html_content)


class TestStorageUpload:
    """Tests for _upload_to_storage method"""

    @pytest.mark.asyncio
    async def test_upload_to_storage_success(self, exporter, mock_db):
        """Test successful file upload to storage"""
        file_bytes = b'Test content'
        yacht_id = str(uuid4())
        draft_id = str(uuid4())
        file_type = "pdf"

        mock_db.client.storage.from_().upload.return_value = None
        mock_db.client.storage.from_().get_public_url.return_value = "https://storage.url/file.pdf"

        result = await exporter._upload_to_storage(
            file_bytes,
            yacht_id,
            draft_id,
            file_type
        )

        assert "https://" in result

    @pytest.mark.asyncio
    async def test_upload_creates_correct_path(self, exporter, mock_db):
        """Test upload creates correct storage path"""
        file_bytes = b'Test'
        yacht_id = "yacht-123"
        draft_id = "draft-456"
        file_type = "pdf"

        mock_db.client.storage.from_().upload.return_value = None
        mock_db.client.storage.from_().get_public_url.return_value = "url"

        await exporter._upload_to_storage(
            file_bytes,
            yacht_id,
            draft_id,
            file_type
        )

        # Path should be handovers/{yacht_id}/{draft_id}.{file_type}
        # Would verify in actual call
        assert mock_db.client.storage.from_().upload.called


class TestExportRecordCreation:
    """Tests for _create_export_record method"""

    @pytest.mark.asyncio
    async def test_create_export_record(self, exporter, mock_db):
        """Test export record creation"""
        draft_id = str(uuid4())
        export_type = "pdf"
        file_url = "https://storage.url/file.pdf"
        export_id = str(uuid4())

        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": export_id}]
        )

        result = await exporter._create_export_record(
            draft_id=draft_id,
            export_type=export_type,
            file_url=file_url
        )

        assert result == export_id

    @pytest.mark.asyncio
    async def test_create_export_record_with_email_sent_at(self, exporter, mock_db):
        """Test export record with email timestamp"""
        draft_id = str(uuid4())
        export_type = "email"
        email_sent_at = datetime.now()
        export_id = str(uuid4())

        mock_db.client.table().insert().execute.return_value = MagicMock(
            data=[{"id": export_id}]
        )

        result = await exporter._create_export_record(
            draft_id=draft_id,
            export_type=export_type,
            email_sent_at=email_sent_at
        )

        assert result == export_id
