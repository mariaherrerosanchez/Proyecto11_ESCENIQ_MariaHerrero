"""Componentes de visión y definiciones compatibles con YOLO."""

from esceniq.vision.inference import (
    Detection,
    InferenceConfig,
    InferenceError,
    InferenceMode,
    InferenceResult,
    analyze_video,
)
from esceniq.vision.evidence import AUTOMATIC_REVIEW_STATUS, MAX_EVIDENCE_FRAMES, VisualEvidence

__all__ = (
    "Detection",
    "InferenceConfig",
    "InferenceError",
    "InferenceMode",
    "InferenceResult",
    "analyze_video",
    "AUTOMATIC_REVIEW_STATUS",
    "MAX_EVIDENCE_FRAMES",
    "VisualEvidence",
)
