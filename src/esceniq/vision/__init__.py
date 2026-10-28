"""Componentes de visión y definiciones compatibles con YOLO."""

from esceniq.vision.inference import (
    Detection,
    InferenceConfig,
    InferenceError,
    InferenceMode,
    InferenceResult,
    analyze_video,
)

__all__ = (
    "Detection",
    "InferenceConfig",
    "InferenceError",
    "InferenceMode",
    "InferenceResult",
    "analyze_video",
)
