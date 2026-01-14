"""
Pipeline Orchestrator - Coordinates all stages of email-to-handover pipeline
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Callable

from .types import FormattedReport
from .stages.fetch_emails import FetchEmailsStage
from .stages.extract_content import ExtractContentStage
from .stages.classify import ClassifyStage
from .stages.group_topics import GroupTopicsStage
from .stages.merge_summaries import MergeSummariesStage
from .stages.deduplicate import DeduplicateStage
from .stages.format_output import FormatOutputStage
from .stages.export import ExportStage


@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    query: Optional[str] = None
    days_back: int = 90
    max_emails: int = 500
    folder_id: Optional[str] = None


@dataclass
class PipelineProgress:
    """Pipeline progress tracking"""
    stage: str
    stage_number: int
    total_stages: int
    items_processed: int
    items_total: int
    started_at: datetime
    message: str


class EmailHandoverPipeline:
    """
    Main pipeline orchestrator.

    Coordinates all stages of the email-to-handover pipeline.
    """

    def __init__(
        self,
        fetch_stage: FetchEmailsStage,
        extract_stage: ExtractContentStage,
        classify_stage: ClassifyStage,
        group_stage: GroupTopicsStage,
        merge_stage: MergeSummariesStage,
        dedupe_stage: DeduplicateStage,
        format_stage: FormatOutputStage,
        export_stage: ExportStage
    ):
        self.fetch = fetch_stage
        self.extract = extract_stage
        self.classify = classify_stage
        self.group = group_stage
        self.merge = merge_stage
        self.dedupe = dedupe_stage
        self.format = format_stage
        self.export = export_stage

        self._progress_callback: Optional[Callable[[PipelineProgress], None]] = None

    def on_progress(self, callback: Callable[[PipelineProgress], None]):
        """Register progress callback"""
        self._progress_callback = callback

    async def run(self, config: PipelineConfig) -> FormattedReport:
        """Run full pipeline"""

        started_at = datetime.now()

        # Stage 1: Fetch Emails
        self._report_progress(
            stage="fetch", stage_number=1, total=8,
            items=0, items_total=0,
            message="Fetching emails from Outlook...",
            started_at=started_at
        )
        raw_emails = await self.fetch.execute(
            query=config.query,
            days_back=config.days_back,
            max_emails=config.max_emails,
            folder_id=config.folder_id
        )

        # Stage 2: Extract Content
        self._report_progress(
            stage="extract", stage_number=2, total=8,
            items=0, items_total=len(raw_emails),
            message=f"Extracting content from {len(raw_emails)} emails...",
            started_at=started_at
        )
        extracted = self.extract.execute(raw_emails)

        # Stage 3: Classify
        self._report_progress(
            stage="classify", stage_number=3, total=8,
            items=0, items_total=len(extracted),
            message=f"Classifying {len(extracted)} emails with AI...",
            started_at=started_at
        )
        classifications = await self.classify.execute(extracted)

        # Stage 4: Group by Topic
        self._report_progress(
            stage="group", stage_number=4, total=8,
            items=len(classifications), items_total=len(classifications),
            message="Grouping emails by topic...",
            started_at=started_at
        )
        groups = self.group.execute(classifications, extracted)

        # Stage 5: Merge Summaries
        self._report_progress(
            stage="merge", stage_number=5, total=8,
            items=0, items_total=len(groups),
            message=f"Merging {len(groups)} topic groups with AI...",
            started_at=started_at
        )
        merged = await self.merge.execute(groups)

        # Stage 6: Deduplicate
        self._report_progress(
            stage="dedupe", stage_number=6, total=8,
            items=len(merged), items_total=len(merged),
            message="Removing duplicates...",
            started_at=started_at
        )
        deduplicated = self.dedupe.execute(merged)

        # Stage 7: Format Output
        self._report_progress(
            stage="format", stage_number=7, total=8,
            items=len(deduplicated), items_total=len(deduplicated),
            message="Formatting final report...",
            started_at=started_at
        )
        report = self.format.execute(deduplicated)

        # Stage 8: Complete
        self._report_progress(
            stage="complete", stage_number=8, total=8,
            items=len(deduplicated), items_total=len(deduplicated),
            message="Pipeline complete!",
            started_at=started_at
        )

        return report

    def _report_progress(
        self,
        stage: str,
        stage_number: int,
        total: int,
        items: int,
        items_total: int,
        message: str,
        started_at: datetime
    ):
        """Report progress to callback"""
        if self._progress_callback:
            self._progress_callback(PipelineProgress(
                stage=stage,
                stage_number=stage_number,
                total_stages=total,
                items_processed=items,
                items_total=items_total,
                started_at=started_at,
                message=message
            ))
