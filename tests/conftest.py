"""
Pytest configuration and fixtures
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Set test environment
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture
def mock_graph_client():
    """Mock Microsoft Graph client"""
    client = MagicMock()
    client.get_messages = AsyncMock(return_value=[
        {
            "id": "msg-1",
            "subject": "Generator 1 Maintenance Required",
            "body": {"content": "The generator needs service", "contentType": "text"},
            "bodyPreview": "The generator needs service",
            "from": {"emailAddress": {"name": "Engineer", "address": "engineer@yacht.com"}},
            "receivedDateTime": "2026-01-14T10:00:00Z",
            "conversationId": "conv-1",
            "hasAttachments": False,
            "importance": "normal"
        },
        {
            "id": "msg-2",
            "subject": "RE: Generator 1 Maintenance Required",
            "body": {"content": "Parts ordered", "contentType": "text"},
            "bodyPreview": "Parts ordered",
            "from": {"emailAddress": {"name": "Supplier", "address": "supplier@parts.com"}},
            "receivedDateTime": "2026-01-14T11:00:00Z",
            "conversationId": "conv-1",
            "hasAttachments": True,
            "importance": "high"
        }
    ])
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = MagicMock()
    client.classify_email = AsyncMock(return_value={
        "shortId": "E1",
        "category": "Electrical",
        "summary": "You need to schedule maintenance for Generator 1."
    })
    client.merge_handover_notes = AsyncMock(return_value={
        "handover": {
            "subject": "Generator 1 Maintenance",
            "summary": "Generator 1 requires scheduled maintenance. Parts have been ordered.",
            "actions": [
                {"priority": "HIGH", "task": "Schedule maintenance window", "subTasks": []},
                {"priority": "NORMAL", "task": "Confirm parts delivery", "subTasks": []}
            ]
        }
    })
    return client


@pytest.fixture
def mock_db_client():
    """Mock Supabase client"""
    client = MagicMock()
    client.create_handover_entry = AsyncMock(return_value={"id": "entry-1"})
    client.create_handover_draft = AsyncMock(return_value={"id": "draft-1"})
    client.add_draft_item = AsyncMock(return_value={"id": "item-1"})
    client.get_draft = AsyncMock(return_value={"id": "draft-1", "state": "DRAFT"})
    client.get_draft_items = AsyncMock(return_value=[])
    client.update_draft_state = AsyncMock(return_value={"id": "draft-1", "state": "IN_REVIEW"})
    client.create_email_extraction_job = AsyncMock(return_value={"id": "job-1"})
    client.update_job_status = AsyncMock(return_value={"id": "job-1"})
    return client


@pytest.fixture
def sample_raw_emails():
    """Sample raw emails for testing"""
    from src.pipeline.types import RawEmail
    return [
        RawEmail(
            id="msg-1",
            subject="Generator 1 Maintenance",
            body={"content": "Generator needs service", "contentType": "text"},
            body_preview="Generator needs service",
            from_address={"emailAddress": {"name": "Engineer", "address": "eng@yacht.com"}},
            received_datetime="2026-01-14T10:00:00Z",
            conversation_id="conv-1",
            has_attachments=False,
            importance="normal"
        ),
        RawEmail(
            id="msg-2",
            subject="Fire Safety Inspection",
            body={"content": "Annual inspection due", "contentType": "text"},
            body_preview="Annual inspection due",
            from_address={"emailAddress": {"name": "Safety", "address": "safety@yacht.com"}},
            received_datetime="2026-01-14T11:00:00Z",
            conversation_id="conv-2",
            has_attachments=True,
            importance="high"
        )
    ]


@pytest.fixture
def sample_extracted_emails():
    """Sample extracted emails for testing"""
    from src.pipeline.types import ExtractedEmail
    return [
        ExtractedEmail(
            short_id="E1",
            email_id="msg-1",
            conversation_id="conv-1",
            subject="Generator 1 Maintenance",
            body_text="Generator needs service",
            body_preview="Generator needs service",
            sender_name="Engineer",
            sender_email="eng@yacht.com",
            received_at=datetime(2026, 1, 14, 10, 0, 0),
            has_attachments=False,
            outlook_link="https://outlook.office365.com/mail/deeplink/read/msg-1"
        )
    ]


@pytest.fixture
def sample_classification_results():
    """Sample classification results"""
    from src.pipeline.types import ClassificationResult, HandoverCategory
    return [
        ClassificationResult(
            short_id="E1",
            category=HandoverCategory.ELECTRICAL,
            summary="You need to schedule generator maintenance.",
            confidence=0.9
        ),
        ClassificationResult(
            short_id="E2",
            category=HandoverCategory.FIRE_SAFETY,
            summary="Annual fire safety inspection is due.",
            confidence=0.85
        )
    ]
