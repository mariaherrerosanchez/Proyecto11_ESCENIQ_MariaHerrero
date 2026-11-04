"""Cálculos de métricas derivados de resultados de inferencia."""

from esceniq.analytics.exposure import ExposureError, ExposureMetric, ExposureSummary, calculate_exposure
from esceniq.analytics.timeline import AppearanceInterval, TimelineError, build_appearance_intervals

__all__ = (
    "AppearanceInterval",
    "ExposureError",
    "ExposureMetric",
    "ExposureSummary",
    "TimelineError",
    "build_appearance_intervals",
    "calculate_exposure",
)
