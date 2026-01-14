"""
Unit tests for pipeline stages
15 test cases covering success, failure, edge cases, and behavior
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.types import (
    RawEmail, ExtractedEmail, ClassificationResult,
    TopicGroup, MergedHandover, HandoverAction,
    Priority, HandoverCategory
)
from src.pipeline.stages.extract_content import ExtractContentStage
from src.pipeline.stages.classify import ClassifyStage
from src.pipeline.stages.group_topics import GroupTopicsStage
from src.pipeline.stages.merge_summaries import MergeSummariesStage
from src.pipeline.stages.deduplicate import DeduplicateStage
from src.pipeline.stages.format_output import FormatOutputStage


class TestExtractContentStage:
    """Tests for extract content stage"""

    def test_extract_success_basic(self, sample_raw_emails):
        """Test successful extraction of basic emails"""
        stage = ExtractContentStage()
        result = stage.execute(sample_raw_emails)

        assert len(result) == 2
        assert result[0].short_id == "E1"
        assert result[1].short_id == "E2"

    def test_extract_html_stripping(self):
        """Test HTML is properly stripped from body"""
        stage = ExtractContentStage()
        raw_email = RawEmail(
            id="msg-html",
            subject="Test",
            body={"content": "<p>Hello <b>World</b></p>", "contentType": "html"},
            body_preview="Hello World",
            from_address={"emailAddress": {"name": "Test", "address": "test@test.com"}},
            received_datetime="2026-01-14T10:00:00Z",
            conversation_id="conv-1",
            has_attachments=False,
            importance="normal"
        )

        result = stage.execute([raw_email])
        assert "<p>" not in result[0].body_text
        assert "<b>" not in result[0].body_text
        assert "Hello" in result[0].body_text

    def test_extract_empty_list(self):
        """Test extraction with empty email list"""
        stage = ExtractContentStage()
        result = stage.execute([])
        assert result == []

    def test_extract_missing_sender(self):
        """Test extraction handles missing sender gracefully"""
        stage = ExtractContentStage()
        raw_email = RawEmail(
            id="msg-no-sender",
            subject="Test",
            body={"content": "Test body", "contentType": "text"},
            body_preview="Test body",
            from_address={},
            received_datetime="2026-01-14T10:00:00Z",
            conversation_id="conv-1",
            has_attachments=False,
            importance="normal"
        )

        result = stage.execute([raw_email])
        assert result[0].sender_name == ""
        assert result[0].sender_email == ""

    def test_extract_invalid_datetime(self):
        """Test extraction handles invalid datetime"""
        stage = ExtractContentStage()
        raw_email = RawEmail(
            id="msg-bad-date",
            subject="Test",
            body={"content": "Test", "contentType": "text"},
            body_preview="Test",
            from_address={"emailAddress": {"name": "Test", "address": "test@test.com"}},
            received_datetime="not-a-date",
            conversation_id="conv-1",
            has_attachments=False,
            importance="normal"
        )

        result = stage.execute([raw_email])
        assert result[0].received_at is not None  # Should use fallback


class TestClassifyStage:
    """Tests for classify stage"""

    @pytest.mark.asyncio
    async def test_classify_success(self, mock_openai_client, sample_extracted_emails):
        """Test successful classification"""
        stage = ClassifyStage(mock_openai_client)
        result = await stage.execute(sample_extracted_emails)

        assert len(result) == 1
        assert result[0].category == HandoverCategory.ELECTRICAL

    @pytest.mark.asyncio
    async def test_classify_handles_api_error(self, sample_extracted_emails):
        """Test classification handles API errors gracefully"""
        mock_client = MagicMock()
        mock_client.classify_email = AsyncMock(side_effect=Exception("API Error"))

        stage = ClassifyStage(mock_client)
        result = await stage.execute(sample_extracted_emails)

        assert len(result) == 1
        assert result[0].category == HandoverCategory.GENERAL
        assert result[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_classify_invalid_category(self, sample_extracted_emails):
        """Test classification handles invalid category"""
        mock_client = MagicMock()
        mock_client.classify_email = AsyncMock(return_value={
            "shortId": "E1",
            "category": "InvalidCategory",
            "summary": "Test"
        })

        stage = ClassifyStage(mock_client)
        result = await stage.execute(sample_extracted_emails)

        assert result[0].category == HandoverCategory.GENERAL


class TestGroupTopicsStage:
    """Tests for group topics stage"""

    def test_group_by_category_and_subject(self, sample_extracted_emails, sample_classification_results):
        """Test grouping by category and subject"""
        stage = GroupTopicsStage()
        result = stage.execute(sample_classification_results, sample_extracted_emails)

        assert len(result) >= 1

    def test_group_normalizes_subject(self):
        """Test subject normalization removes prefixes"""
        stage = GroupTopicsStage()

        assert stage._normalize_subject("RE: Test Subject") == "test subject"
        assert stage._normalize_subject("FW: Test Subject") == "test subject"
        assert stage._normalize_subject("URGENT: Test") == "test"

    def test_group_empty_input(self):
        """Test grouping with empty input"""
        stage = GroupTopicsStage()
        result = stage.execute([], [])
        assert result == {}

    def test_group_merge_key_generation(self):
        """Test merge key is generated correctly"""
        stage = GroupTopicsStage()
        key = stage._build_merge_key("Electrical", "generator maintenance")
        assert key.isalnum()
        assert "electrical" in key.lower()


class TestDeduplicateStage:
    """Tests for deduplicate stage"""

    def test_dedupe_removes_exact_duplicates(self):
        """Test exact duplicate actions are removed"""
        stage = DeduplicateStage()

        handover = MergedHandover(
            merge_key="test",
            category=HandoverCategory.ELECTRICAL,
            subject_group="test",
            subject="Test",
            summary="Test",
            actions=[
                HandoverAction(priority=Priority.HIGH, task="Do something"),
                HandoverAction(priority=Priority.HIGH, task="Do something"),
            ],
            source_ids=[]
        )

        result = stage.execute([handover])
        assert len(result[0].actions) == 1

    def test_dedupe_preserves_unique_actions(self):
        """Test unique actions are preserved"""
        stage = DeduplicateStage()

        handover = MergedHandover(
            merge_key="test",
            category=HandoverCategory.ELECTRICAL,
            subject_group="test",
            subject="Test",
            summary="Test",
            actions=[
                HandoverAction(priority=Priority.HIGH, task="Task A"),
                HandoverAction(priority=Priority.NORMAL, task="Task B"),
            ],
            source_ids=[]
        )

        result = stage.execute([handover])
        assert len(result[0].actions) == 2

    def test_dedupe_empty_list(self):
        """Test deduplication with empty list"""
        stage = DeduplicateStage()
        result = stage.execute([])
        assert result == []


class TestFormatOutputStage:
    """Tests for format output stage"""

    def test_format_generates_html(self):
        """Test HTML report is generated"""
        stage = FormatOutputStage()

        handovers = [
            MergedHandover(
                merge_key="test",
                category=HandoverCategory.ELECTRICAL,
                subject_group="test",
                subject="Generator Maintenance",
                summary="Test summary",
                actions=[HandoverAction(priority=Priority.HIGH, task="Do task")],
                source_ids=[{"shortId": "E1", "link": "https://test.com"}],
                presentation_bucket="Engineering"
            )
        ]

        result = stage.execute(handovers)

        assert result.html is not None
        assert "Generator Maintenance" in result.html
        assert "HIGH" in result.html

    def test_format_calculates_statistics(self):
        """Test statistics are calculated correctly"""
        stage = FormatOutputStage()

        handovers = [
            MergedHandover(
                merge_key="test1",
                category=HandoverCategory.ELECTRICAL,
                subject_group="test1",
                subject="Test 1",
                summary="Summary 1",
                actions=[
                    HandoverAction(priority=Priority.CRITICAL, task="Critical task"),
                    HandoverAction(priority=Priority.HIGH, task="High task"),
                ],
                source_ids=[{"shortId": "E1", "link": "link1"}, {"shortId": "E2", "link": "link2"}]
            )
        ]

        result = stage.execute(handovers)

        assert result.meta["criticalCount"] == 1
        assert result.meta["highCount"] == 1
        assert result.meta["totalEmails"] == 2

    def test_format_empty_handovers(self):
        """Test formatting with no handovers"""
        stage = FormatOutputStage()
        result = stage.execute([])

        assert result.html is not None
        assert result.meta["totalSections"] == 0
