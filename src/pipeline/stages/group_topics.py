"""
Stage 4: Group classified emails by category and subject
"""
import re
from typing import List, Dict

from ..types import ExtractedEmail, ClassificationResult, TopicGroup


class GroupTopicsStage:
    """
    Stage 4: Group classified emails by category and subject

    n8n equivalent: "Group Emails by Equipment" + "Batch Summaries" + "Group summaries by category + subject"
    """

    def execute(
        self,
        classifications: List[ClassificationResult],
        emails: List[ExtractedEmail]
    ) -> Dict[str, TopicGroup]:
        """Group classifications by category and normalized subject"""

        email_map = {e.short_id: e for e in emails}
        groups: Dict[str, TopicGroup] = {}

        for cls in classifications:
            email = email_map.get(cls.short_id)
            if not email:
                continue

            subject_group = self._normalize_subject(email.subject)
            key = f"{cls.category.value}::{subject_group}"
            merge_key = self._build_merge_key(cls.category.value, subject_group)

            if key not in groups:
                groups[key] = TopicGroup(
                    merge_key=merge_key,
                    category=cls.category,
                    subject_group=subject_group,
                    notes=[],
                    source_ids=[]
                )

            # Add note
            groups[key].notes.append({
                'subject': email.subject,
                'summary': cls.summary
            })

            # Add source reference
            summary_id = f"S{len(groups[key].source_ids) + 1}"
            groups[key].source_ids.append({
                'shortId': email.short_id,
                'summaryId': summary_id,
                'link': email.outlook_link
            })

        return groups

    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject for grouping"""
        normalized = subject.lower()
        # Remove common prefixes
        normalized = re.sub(r'^(re:|fw:|fwd:)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'urgent[:\-]?\s*', '', normalized, flags=re.IGNORECASE)
        # Remove non-alphanumeric
        normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
        return normalized.strip()

    def _build_merge_key(self, category: str, subject_group: str) -> str:
        """Build unique merge key"""
        combined = f"{category}_{subject_group}"
        return re.sub(r'[^a-z0-9]', '', combined.lower())
