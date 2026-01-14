"""
Stage 3: Classify emails using AI
"""
import asyncio
import logging
from typing import List

from ...ai.openai_client import OpenAIClient
from ..types import ExtractedEmail, ClassificationResult, HandoverCategory

logger = logging.getLogger(__name__)


class ClassifyStage:
    """
    Stage 3: Classify emails using AI

    n8n equivalent: "Prompt Email Extraction" + "DS Blog" + "AI Process Response1"
    """

    def __init__(self, openai_client: OpenAIClient, max_concurrent: int = 10):
        self.ai = openai_client
        self.max_concurrent = max_concurrent

    async def execute(self, emails: List[ExtractedEmail]) -> List[ClassificationResult]:
        """Classify all emails with concurrency control"""

        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [self._classify_with_semaphore(email, semaphore) for email in emails]
        return await asyncio.gather(*tasks)

    async def _classify_with_semaphore(
        self,
        email: ExtractedEmail,
        semaphore: asyncio.Semaphore
    ) -> ClassificationResult:
        """Classify single email with semaphore"""
        async with semaphore:
            return await self._classify_single(email)

    async def _classify_single(self, email: ExtractedEmail) -> ClassificationResult:
        """Classify a single email"""

        try:
            result = await self.ai.classify_email(
                subject=email.subject,
                body=email.body_text,
                short_id=email.short_id
            )

            # Validate and map category
            category_str = result.get('category', 'General Outstanding')
            try:
                category = HandoverCategory(category_str)
            except ValueError:
                category = HandoverCategory.GENERAL

            return ClassificationResult(
                short_id=result.get('shortId', email.short_id),
                category=category,
                summary=result.get('summary', 'No summary generated.'),
                confidence=0.9
            )

        except Exception as e:
            logger.error(f"Classification error for {email.short_id}: {e}")
            # Fallback on error
            return ClassificationResult(
                short_id=email.short_id,
                category=HandoverCategory.GENERAL,
                summary=f"Classification error: {str(e)}",
                confidence=0.0
            )
