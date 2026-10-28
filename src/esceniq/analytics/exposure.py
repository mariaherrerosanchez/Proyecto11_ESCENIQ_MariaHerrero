"""Estimación de exposición de marca a partir de muestras de inferencia.

Cada muestra positiva representa el intervalo ``[timestamp, timestamp + intervalo)``.
El final se limita a la duración real del vídeo y los intervalos solapados de una
misma marca se fusionan. Es una estimación dependiente del muestreo, no una
medición continua de presencia en pantalla.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from esceniq.vision.brand_classes import OFFICIAL_BRAND_NAMES, brand_name_for_yolo_id
from esceniq.vision.inference import Detection, InferenceMode, InferenceResult


class ExposureError(ValueError):
    """Indica que un resultado no se puede convertir con seguridad en exposición."""


@dataclass(frozen=True)
class ExposureMetric:
    """Exposición estimada de una marca dentro de un vídeo."""

    brand_name: str
    positive_sample_count: int
    estimated_seconds: float
    percentage_of_video: float
    first_detection_seconds: float
    last_detection_seconds: float
    appearance_count: int


@dataclass(frozen=True)
class ExposureSummary:
    """Métricas calculadas a partir de un resultado ESCENIQ válido."""

    video_duration_seconds: float
    sample_interval_seconds: float
    metrics: tuple[ExposureMetric, ...]


Interval = tuple[float, float]


def _validate_result(result: InferenceResult) -> None:
    duration = result.video_metadata.duration_seconds
    if not math.isfinite(duration) or duration <= 0:
        raise ExposureError("La duración del vídeo debe ser positiva y finita.")
    if not math.isfinite(result.sample_interval_seconds) or result.sample_interval_seconds <= 0:
        raise ExposureError("El intervalo de muestreo debe ser positivo y finito.")
    if result.mode is not InferenceMode.ESCENIQ:
        raise ExposureError(
            "Las inferencias de prueba técnica no se pueden convertir en métricas de marca ESCENIQ."
        )


def _validate_detection(detection: Detection, duration_seconds: float) -> str:
    if detection.brand_name not in OFFICIAL_BRAND_NAMES:
        raise ExposureError("La detección no contiene una marca ESCENIQ oficial válida.")
    try:
        expected_brand = brand_name_for_yolo_id(detection.class_id)
    except LookupError as error:
        raise ExposureError("La detección contiene un identificador de clase no reconocido.") from error
    if detection.brand_name != expected_brand:
        raise ExposureError("La marca de la detección no coincide con su identificador de clase oficial.")
    if not math.isfinite(detection.timestamp_seconds) or not 0 <= detection.timestamp_seconds < duration_seconds:
        raise ExposureError("La detección tiene un timestamp fuera de la duración real del vídeo.")
    return detection.brand_name


def _merge_intervals(intervals: Iterable[Interval]) -> tuple[Interval, ...]:
    ordered = sorted(intervals)
    if not ordered:
        return ()
    merged: list[Interval] = []
    start, end = ordered[0]
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
            continue
        merged.append((start, end))
        start, end = next_start, next_end
    merged.append((start, end))
    return tuple(merged)


def calculate_exposure(result: InferenceResult) -> ExposureSummary:
    """Calcula estimaciones de exposición por marca para un resultado ESCENIQ.

    Varias cajas de una marca en el mismo fotograma forman una única muestra
    positiva. Muestras de marcas distintas se calculan de manera independiente,
    por lo que sus exposiciones pueden solaparse.
    """
    _validate_result(result)
    duration = result.video_metadata.duration_seconds
    interval = result.sample_interval_seconds
    sample_timestamps_by_brand: dict[str, set[tuple[int, float]]] = {}
    for detection in result.detections:
        brand_name = _validate_detection(detection, duration)
        sample_timestamps_by_brand.setdefault(brand_name, set()).add(
            (detection.frame_index, detection.timestamp_seconds)
        )

    metrics: list[ExposureMetric] = []
    for brand_name in OFFICIAL_BRAND_NAMES:
        samples = sample_timestamps_by_brand.get(brand_name)
        if not samples:
            continue
        ordered_samples = sorted(samples, key=lambda sample: (sample[1], sample[0]))
        intervals = _merge_intervals(
            (timestamp, min(timestamp + interval, duration)) for _, timestamp in ordered_samples
        )
        estimated_seconds = sum(end - start for start, end in intervals)
        metrics.append(
            ExposureMetric(
                brand_name=brand_name,
                positive_sample_count=len(ordered_samples),
                estimated_seconds=estimated_seconds,
                percentage_of_video=100 * estimated_seconds / duration,
                first_detection_seconds=ordered_samples[0][1],
                last_detection_seconds=ordered_samples[-1][1],
                appearance_count=len(intervals),
            )
        )
    return ExposureSummary(duration, interval, tuple(metrics))
