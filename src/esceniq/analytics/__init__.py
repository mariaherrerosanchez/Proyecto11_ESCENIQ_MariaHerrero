"""Cálculos de métricas derivados de resultados de inferencia."""

from esceniq.analytics.comparison import AnalysisComparison, ComparedMetric, build_analysis_comparison
from esceniq.analytics.exposure import ExposureError, ExposureMetric, ExposureSummary, calculate_exposure
from esceniq.analytics.timeline import AppearanceInterval, TimelineError, build_appearance_intervals

__all__ = (
    "AnalysisComparison",
    "AppearanceInterval",
    "ComparedMetric",
    "ExposureError",
    "ExposureMetric",
    "ExposureSummary",
    "TimelineError",
    "build_analysis_comparison",
    "build_appearance_intervals",
    "calculate_exposure",
)
