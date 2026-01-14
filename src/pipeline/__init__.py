# Pipeline module
from .types import (
    RawEmail,
    ExtractedEmail,
    ClassificationResult,
    TopicGroup,
    MergedHandover,
    HandoverAction,
    FormattedReport,
    Priority,
    HandoverCategory,
)
from .orchestrator import EmailHandoverPipeline, PipelineConfig, PipelineProgress

__all__ = [
    "RawEmail",
    "ExtractedEmail",
    "ClassificationResult",
    "TopicGroup",
    "MergedHandover",
    "HandoverAction",
    "FormattedReport",
    "Priority",
    "HandoverCategory",
    "EmailHandoverPipeline",
    "PipelineConfig",
    "PipelineProgress",
]
