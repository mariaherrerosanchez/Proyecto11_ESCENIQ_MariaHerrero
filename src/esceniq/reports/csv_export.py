"""Exportación CSV de métricas reales de un único análisis."""
from __future__ import annotations

import csv
from collections import Counter
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from esceniq.analytics import ExposureSummary
    from esceniq.storage import StoredAnalysis
    from esceniq.vision import InferenceResult


CSV_HEADERS = (
    "Vídeo",
    "Marca",
    "Número de detecciones",
    "Muestras positivas",
    "Exposición estimada (s)",
    "Exposición (%)",
    "Apariciones",
    "Modelo",
    "Umbral de confianza",
    "Intervalo de muestreo (s)",
)


def _spanish_decimal(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _build_csv_rows(
    metrics: tuple[object, ...],
    detection_counts: Counter[str],
    *,
    video_name: str,
    model_path: str,
    confidence_threshold: float,
    sample_interval_seconds: float,
) -> bytes | None:
    """Codifica métricas ya agregadas, sin recalcular exposición ni inferencia."""
    if not metrics:
        return None

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS, delimiter=";", lineterminator="\r\n")
    writer.writeheader()
    for metric in metrics:
        writer.writerow(
            {
                "Vídeo": video_name,
                "Marca": metric.brand_name,
                "Número de detecciones": detection_counts[metric.brand_name],
                "Muestras positivas": metric.positive_sample_count,
                "Exposición estimada (s)": _spanish_decimal(metric.estimated_seconds),
                "Exposición (%)": _spanish_decimal(metric.percentage_of_video),
                "Apariciones": metric.appearance_count,
                "Modelo": model_path,
                "Umbral de confianza": _spanish_decimal(confidence_threshold),
                "Intervalo de muestreo (s)": _spanish_decimal(sample_interval_seconds),
            }
        )
    return buffer.getvalue().encode("utf-8-sig")


def build_results_csv(
    result: InferenceResult,
    exposure: ExposureSummary,
    *,
    video_name: str | None,
) -> bytes | None:
    """Devuelve un CSV UTF-8 BOM de las marcas realmente agregadas.

    Un resumen vacío no genera un archivo descargable: no existen filas reales
    que exportar. Las métricas se reciben ya calculadas para no repetir ni la
    inferencia ni la agregación temporal.
    """
    detection_counts = Counter(
        detection.brand_name for detection in result.detections if detection.brand_name is not None
    )
    return _build_csv_rows(
        exposure.metrics,
        detection_counts,
        video_name=video_name or "",
        model_path=str(result.model_path),
        confidence_threshold=result.confidence_threshold,
        sample_interval_seconds=result.sample_interval_seconds,
    )


def build_stored_results_csv(analysis: StoredAnalysis) -> bytes | None:
    """Exporta un análisis SQLite sin volver a ejecutar YOLO."""
    detection_counts = Counter(
        detection.brand_name for detection in analysis.detections if detection.brand_name is not None
    )
    return _build_csv_rows(
        analysis.exposures,
        detection_counts,
        video_name=analysis.video_name,
        model_path=analysis.model_path,
        confidence_threshold=analysis.confidence_threshold,
        sample_interval_seconds=analysis.sample_interval_seconds,
    )
