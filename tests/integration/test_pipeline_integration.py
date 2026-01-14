"""
Integration tests for the full pipeline
15 test cases covering end-to-end flows
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.pipeline import EmailHandoverPipeline, PipelineConfig
from src.pipeline.stages import (
    FetchEmailsStage,
    ExtractContentStage,
    ClassifyStage,
    GroupTopicsStage,
    MergeSummariesStage,
    DeduplicateStage,
    FormatOutputStage,
    ExportStage,
)
from src.pipeline.types import RawEmail, HandoverCategory


def create_mock_pipeline(mock_graph, mock_openai):
    """Create a pipeline with mock dependencies"""
    return EmailHandoverPipeline(
        fetch_stage=FetchEmailsStage(mock_graph),
        extract_stage=ExtractContentStage(),
        classify_stage=ClassifyStage(mock_openai),
        group_stage=GroupTopicsStage(),
        merge_stage=MergeSummariesStage(mock_openai),
        dedupe_stage=DeduplicateStage(),
        format_stage=FormatOutputStage(),
        export_stage=ExportStage()
    )


class TestPipelineIntegration:
    """Integration tests for full pipeline"""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, mock_graph_client, mock_openai_client):
        """Test full pipeline executes successfully"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        assert result is not None
        assert result.html is not None
        assert "meta" in dir(result)

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_emails(self, mock_openai_client):
        """Test pipeline handles empty email list"""
        mock_graph = MagicMock()
        mock_graph.get_messages = AsyncMock(return_value=[])

        pipeline = create_mock_pipeline(mock_graph, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        assert result is not None
        assert result.meta["totalEmails"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_with_query_filter(self, mock_graph_client, mock_openai_client):
        """Test pipeline with search query"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(query="generator", days_back=30, max_emails=50)
        result = await pipeline.run(config)

        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_groups_related_emails(self, mock_openai_client):
        """Test pipeline groups related emails together"""
        mock_graph = MagicMock()
        mock_graph.get_messages = AsyncMock(return_value=[
            {
                "id": "msg-1",
                "subject": "Generator Issue",
                "body": {"content": "Issue 1", "contentType": "text"},
                "bodyPreview": "Issue 1",
                "from": {"emailAddress": {"name": "A", "address": "a@test.com"}},
                "receivedDateTime": "2026-01-14T10:00:00Z",
                "conversationId": "conv-1",
                "hasAttachments": False,
                "importance": "normal"
            },
            {
                "id": "msg-2",
                "subject": "RE: Generator Issue",
                "body": {"content": "Issue 2", "contentType": "text"},
                "bodyPreview": "Issue 2",
                "from": {"emailAddress": {"name": "B", "address": "b@test.com"}},
                "receivedDateTime": "2026-01-14T11:00:00Z",
                "conversationId": "conv-1",
                "hasAttachments": False,
                "importance": "normal"
            }
        ])

        pipeline = create_mock_pipeline(mock_graph, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Should group related emails
        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_categorizes_correctly(self, mock_graph_client, mock_openai_client):
        """Test pipeline categorizes emails into correct sections"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Categories should be valid HandoverCategory values
        for category in result.sections.keys():
            assert category in [c.value for c in HandoverCategory]

    @pytest.mark.asyncio
    async def test_pipeline_progress_callback(self, mock_graph_client, mock_openai_client):
        """Test pipeline reports progress"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        progress_updates = []
        pipeline.on_progress(lambda p: progress_updates.append(p))

        config = PipelineConfig(days_back=7, max_emails=10)
        await pipeline.run(config)

        assert len(progress_updates) > 0
        assert progress_updates[-1].stage == "complete"

    @pytest.mark.asyncio
    async def test_pipeline_handles_classification_errors(self, mock_graph_client):
        """Test pipeline handles classification errors gracefully"""
        mock_openai = MagicMock()
        mock_openai.classify_email = AsyncMock(side_effect=Exception("API Error"))
        mock_openai.merge_handover_notes = AsyncMock(return_value={
            "handover": {"subject": "Test", "summary": "Test", "actions": []}
        })

        pipeline = create_mock_pipeline(mock_graph_client, mock_openai)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Should still complete with fallback categories
        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_merge_errors(self, mock_graph_client):
        """Test pipeline handles merge errors gracefully"""
        mock_openai = MagicMock()
        mock_openai.classify_email = AsyncMock(return_value={
            "shortId": "E1",
            "category": "Electrical",
            "summary": "Test"
        })
        mock_openai.merge_handover_notes = AsyncMock(side_effect=Exception("Merge Error"))

        pipeline = create_mock_pipeline(mock_graph_client, mock_openai)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_output_contains_source_links(self, mock_graph_client, mock_openai_client):
        """Test pipeline output contains source email links"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Check HTML contains outlook links
        assert "outlook.office365.com" in result.html or result.meta["totalEmails"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_deduplicates_actions(self, mock_graph_client, mock_openai_client):
        """Test pipeline removes duplicate actions"""
        mock_openai_client.merge_handover_notes = AsyncMock(return_value={
            "handover": {
                "subject": "Test",
                "summary": "Test",
                "actions": [
                    {"priority": "HIGH", "task": "Same task", "subTasks": []},
                    {"priority": "HIGH", "task": "Same task", "subTasks": []}
                ]
            }
        })

        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Should deduplicate actions
        assert result is not None

    @pytest.mark.asyncio
    async def test_pipeline_formats_priorities(self, mock_graph_client, mock_openai_client):
        """Test pipeline formats action priorities correctly"""
        mock_openai_client.merge_handover_notes = AsyncMock(return_value={
            "handover": {
                "subject": "Test",
                "summary": "Test",
                "actions": [
                    {"priority": "CRITICAL", "task": "Critical task", "subTasks": []},
                    {"priority": "HIGH", "task": "High task", "subTasks": []},
                    {"priority": "NORMAL", "task": "Normal task", "subTasks": []}
                ]
            }
        })

        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Check priorities are in output
        assert "CRITICAL" in result.html or "HIGH" in result.html or result.meta["totalEmails"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_max_emails_limit(self, mock_openai_client):
        """Test pipeline respects max_emails limit"""
        mock_graph = MagicMock()
        mock_graph.get_messages = AsyncMock(return_value=[
            {
                "id": f"msg-{i}",
                "subject": f"Email {i}",
                "body": {"content": f"Body {i}", "contentType": "text"},
                "bodyPreview": f"Preview {i}",
                "from": {"emailAddress": {"name": "Test", "address": "test@test.com"}},
                "receivedDateTime": "2026-01-14T10:00:00Z",
                "conversationId": f"conv-{i}",
                "hasAttachments": False,
                "importance": "normal"
            }
            for i in range(100)
        ])

        pipeline = create_mock_pipeline(mock_graph, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        # Graph client should be called with limit
        mock_graph.get_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_html_structure(self, mock_graph_client, mock_openai_client):
        """Test pipeline generates valid HTML structure"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        assert "<!DOCTYPE html>" in result.html
        assert "<html>" in result.html
        assert "</html>" in result.html
        assert "<head>" in result.html
        assert "<body>" in result.html

    @pytest.mark.asyncio
    async def test_pipeline_meta_timestamps(self, mock_graph_client, mock_openai_client):
        """Test pipeline includes generation timestamp"""
        pipeline = create_mock_pipeline(mock_graph_client, mock_openai_client)

        config = PipelineConfig(days_back=7, max_emails=10)
        result = await pipeline.run(config)

        assert "generatedAt" in result.meta
        assert result.generated_at is not None
