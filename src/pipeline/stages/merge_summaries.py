"""
Stage 5: Merge grouped summaries into handover entries using AI
"""
import asyncio
import logging
from typing import List, Dict

from ...ai.openai_client import OpenAIClient
from ..types import (
    TopicGroup, MergedHandover, HandoverAction,
    Priority, CATEGORY_TO_DOMAIN
)

logger = logging.getLogger(__name__)


class MergeSummariesStage:
    """
    Stage 5: Merge grouped summaries into handover entries using AI

    n8n equivalent: "Prompt Builder2" + "DS Blog2" + "AI Response Processor2"
    """

    def __init__(self, openai_client: OpenAIClient, max_concurrent: int = 5):
        self.ai = openai_client
        self.max_concurrent = max_concurrent

    async def execute(self, groups: Dict[str, TopicGroup]) -> List[MergedHandover]:
        """Merge all groups with concurrency control"""

        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [
            self._merge_with_semaphore(group, semaphore)
            for group in groups.values()
        ]
        return await asyncio.gather(*tasks)

    async def _merge_with_semaphore(
        self,
        group: TopicGroup,
        semaphore: asyncio.Semaphore
    ) -> MergedHandover:
        """Merge single group with semaphore"""
        async with semaphore:
            return await self._merge_single(group)

    async def _merge_single(self, group: TopicGroup) -> MergedHandover:
        """Merge a single topic group"""

        # Format notes for prompt
        notes_text = '\n\n'.join([
            f"({i+1}) Subject: {n['subject']}\nSummary: {n['summary']}"
            for i, n in enumerate(group.notes)
        ])

        try:
            result = await self.ai.merge_handover_notes(
                subject_group=group.subject_group,
                category=group.category.value,
                notes=notes_text
            )

            handover = result.get('handover', {})

            # Parse actions
            actions = [
                HandoverAction(
                    priority=Priority(a.get('priority', 'NORMAL')),
                    task=a.get('task', ''),
                    sub_tasks=a.get('subTasks', [])
                )
                for a in handover.get('actions', [])
            ]

            # Get domain mapping
            domain_code, bucket = CATEGORY_TO_DOMAIN.get(
                group.category,
                (None, None)
            )

            return MergedHandover(
                merge_key=group.merge_key,
                category=group.category,
                subject_group=group.subject_group,
                subject=handover.get('subject', group.subject_group),
                summary=handover.get('summary', ''),
                actions=actions,
                source_ids=group.source_ids,
                domain_code=domain_code,
                presentation_bucket=bucket
            )

        except Exception as e:
            logger.error(f"Merge error for {group.merge_key}: {e}")
            # Fallback on error
            return MergedHandover(
                merge_key=group.merge_key,
                category=group.category,
                subject_group=group.subject_group,
                subject=group.subject_group,
                summary=f"Merge error: {str(e)}",
                actions=[],
                source_ids=group.source_ids,
                domain_code=None,
                presentation_bucket=None
            )
