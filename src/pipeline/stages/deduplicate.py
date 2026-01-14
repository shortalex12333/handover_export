"""
Stage 6: Deduplicate summaries and actions
"""
from typing import List

from ..types import MergedHandover, HandoverAction


class DeduplicateStage:
    """
    Stage 6: Deduplicate summaries and actions

    n8n equivalent: "Deduplicate Summaries & Actions"
    """

    def __init__(self, similarity_threshold: float = 0.9):
        self.threshold = similarity_threshold

    def execute(self, handovers: List[MergedHandover]) -> List[MergedHandover]:
        """Deduplicate handovers and their actions"""

        deduplicated = []

        for handover in handovers:
            # Deduplicate actions within handover
            unique_actions = self._dedupe_actions(handover.actions)

            deduplicated.append(MergedHandover(
                merge_key=handover.merge_key,
                category=handover.category,
                subject_group=handover.subject_group,
                subject=handover.subject,
                summary=handover.summary,
                actions=unique_actions,
                source_ids=handover.source_ids,
                domain_code=handover.domain_code,
                presentation_bucket=handover.presentation_bucket
            ))

        return deduplicated

    def _dedupe_actions(self, actions: List[HandoverAction]) -> List[HandoverAction]:
        """Remove duplicate actions"""
        unique = []
        seen_tasks = set()

        for action in actions:
            normalized = self._normalize(action.task)
            if normalized not in seen_tasks:
                seen_tasks.add(normalized)
                unique.append(action)

        return unique

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison"""
        return ''.join(c.lower() for c in text if c.isalnum())

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) == 0:
            return len(s2)
        if len(s2) == 0:
            return len(s1)

        matrix = [[0] * (len(s2) + 1) for _ in range(len(s1) + 1)]

        for i in range(len(s1) + 1):
            matrix[i][0] = i
        for j in range(len(s2) + 1):
            matrix[0][j] = j

        for i in range(1, len(s1) + 1):
            for j in range(1, len(s2) + 1):
                if s1[i-1] == s2[j-1]:
                    matrix[i][j] = matrix[i-1][j-1]
                else:
                    matrix[i][j] = min(
                        matrix[i-1][j-1] + 1,
                        matrix[i][j-1] + 1,
                        matrix[i-1][j] + 1
                    )

        return matrix[len(s1)][len(s2)]

    def _is_near_duplicate(self, text1: str, text2: str) -> bool:
        """Check if two strings are near-duplicates"""
        norm1 = self._normalize(text1)
        norm2 = self._normalize(text2)

        max_len = max(len(norm1), len(norm2))
        if max_len == 0:
            return True

        distance = self._levenshtein_distance(norm1, norm2)
        similarity = 1 - (distance / max_len)

        return similarity >= self.threshold
