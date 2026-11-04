"""Comparación de métricas ya persistidas, sin inferencia ni recálculo de exposición."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, Sequence


class ExposureLike(Protocol):
    brand_name: str
    positive_sample_count: int
    estimated_seconds: float
    percentage_of_video: float
    appearance_count: int


class AnalysisLike(Protocol):
    video_name: str
    mode: str
    model_path: str
    confidence_threshold: float
    sample_interval_seconds: float
    duration_seconds: float
    exposures: Sequence[ExposureLike]


@dataclass(frozen=True)
class ComparedMetric:
    """Métrica de una marca para los dos análisis, sin alterar su valor original."""

    brand_name: str
    left: ExposureLike | None
    right: ExposureLike | None
    left_available: bool
    right_available: bool
    higher_exposure: str | None


@dataclass(frozen=True)
class AnalysisComparison:
    """Resultado de comparar dos análisis persistidos y su contexto reproducible."""

    left: AnalysisLike
    right: AnalysisLike
    configuration_differences: tuple[str, ...]
    metrics: tuple[ComparedMetric, ...]

    @property
    def is_directly_comparable(self) -> bool:
        return not self.configuration_differences


_BRAND_CAPABLE_MODES = {"esceniq", "eggo_experimental", "cocacola_experimental"}


def _valid_metric(metric: ExposureLike) -> bool:
    return (
        isinstance(metric.brand_name, str)
        and bool(metric.brand_name.strip())
        and isinstance(metric.positive_sample_count, int)
        and metric.positive_sample_count >= 0
        and isinstance(metric.appearance_count, int)
        and metric.appearance_count >= 0
        and all(math.isfinite(float(value)) and float(value) >= 0 for value in (
            metric.estimated_seconds,
            metric.percentage_of_video,
        ))
    )


def _metrics_by_brand(analysis: AnalysisLike) -> tuple[dict[str, ExposureLike], bool]:
    """Devuelve métricas utilizables y si la ausencia equivale a cero o a dato no disponible."""
    raw_metrics = getattr(analysis, "exposures", None)
    if not isinstance(raw_metrics, Sequence) or isinstance(raw_metrics, (str, bytes)):
        return {}, False
    if analysis.mode not in _BRAND_CAPABLE_MODES:
        return {}, False
    metrics: dict[str, ExposureLike] = {}
    for metric in raw_metrics:
        if not _valid_metric(metric):
            return {}, False
        metrics[metric.brand_name] = metric
    return metrics, True


def _configuration_differences(left: AnalysisLike, right: AnalysisLike) -> tuple[str, ...]:
    differences: list[str] = []
    if left.mode != right.mode:
        differences.append("modo de inferencia")
    if left.model_path != right.model_path:
        differences.append("modelo")
    if not math.isclose(left.confidence_threshold, right.confidence_threshold, abs_tol=1e-12):
        differences.append("umbral de confianza")
    if not math.isclose(left.sample_interval_seconds, right.sample_interval_seconds, abs_tol=1e-12):
        differences.append("intervalo de muestreo")
    for analysis, side in ((left, "primer"), (right, "segundo")):
        if not math.isfinite(analysis.duration_seconds) or analysis.duration_seconds <= 0:
            differences.append(f"duración inválida en el {side} análisis")
    return tuple(differences)


def build_analysis_comparison(left: AnalysisLike, right: AnalysisLike) -> AnalysisComparison:
    """Compara exposiciones persistidas; nunca calcula nuevas detecciones ni segundos."""
    left_metrics, left_available = _metrics_by_brand(left)
    right_metrics, right_available = _metrics_by_brand(right)
    differences = _configuration_differences(left, right)
    metrics: list[ComparedMetric] = []
    for brand_name in sorted(set(left_metrics) | set(right_metrics)):
        left_metric = left_metrics.get(brand_name)
        right_metric = right_metrics.get(brand_name)
        if differences or not left_available or not right_available:
            higher_exposure = None
        elif left_metric is None and right_metric is None:
            higher_exposure = None
        elif left_metric is None:
            higher_exposure = "right"
        elif right_metric is None:
            higher_exposure = "left"
        elif math.isclose(left_metric.estimated_seconds, right_metric.estimated_seconds, abs_tol=1e-12):
            higher_exposure = "equal"
        else:
            higher_exposure = "left" if left_metric.estimated_seconds > right_metric.estimated_seconds else "right"
        metrics.append(
            ComparedMetric(
                brand_name=brand_name,
                left=left_metric,
                right=right_metric,
                left_available=left_available,
                right_available=right_available,
                higher_exposure=higher_exposure,
            )
        )
    return AnalysisComparison(left, right, differences, tuple(metrics))
