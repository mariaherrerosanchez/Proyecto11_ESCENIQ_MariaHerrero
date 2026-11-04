"""Tramos temporales estimados derivados de muestras reales de detección."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Protocol


class TimelineError(ValueError):
    """Indica que faltan datos temporales válidos para construir una línea temporal."""


class TemporalDetection(Protocol):
    """Campos mínimos compartidos por detecciones actuales y recuperadas de SQLite."""

    brand_name: str | None
    frame_index: int
    timestamp_seconds: float


@dataclass(frozen=True)
class AppearanceInterval:
    """Un tramo estimado a partir de una o más muestras positivas de una marca."""

    brand_name: str
    start_seconds: float
    end_seconds: float
    positive_sample_count: int

    @property
    def estimated_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def _validate_time_context(duration_seconds: float, sample_interval_seconds: float) -> None:
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise TimelineError("La duración del vídeo no permite construir la línea temporal.")
    if not math.isfinite(sample_interval_seconds) or sample_interval_seconds <= 0:
        raise TimelineError("El intervalo de muestreo no permite construir la línea temporal.")


def build_appearance_intervals(
    detections: Iterable[TemporalDetection],
    *,
    duration_seconds: float,
    sample_interval_seconds: float,
) -> tuple[AppearanceInterval, ...]:
    """Agrupa muestras de marca en tramos, sin inferir continuidad entre ellas.

    Cada muestra positiva contribuye como máximo ``sample_interval_seconds`` y el
    final se limita a la duración del vídeo. Las cajas de la misma marca en el
    mismo fotograma se deduplican, igual que la exposición estimada.
    """
    _validate_time_context(duration_seconds, sample_interval_seconds)
    samples_by_brand: dict[str, set[tuple[int, float]]] = defaultdict(set)
    for detection in detections:
        brand_name = detection.brand_name
        if brand_name is None:
            continue
        if not isinstance(brand_name, str) or not brand_name.strip():
            raise TimelineError("Una detección contiene una marca temporal inválida.")
        timestamp = float(detection.timestamp_seconds)
        if not math.isfinite(timestamp) or not 0 <= timestamp < duration_seconds:
            raise TimelineError("Una detección contiene un timestamp fuera de la duración del vídeo.")
        frame_index = detection.frame_index
        if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
            raise TimelineError("Una detección contiene un índice de fotograma inválido.")
        samples_by_brand[brand_name].add((frame_index, timestamp))

    appearances: list[AppearanceInterval] = []
    for brand_name in sorted(samples_by_brand):
        samples = sorted(samples_by_brand[brand_name], key=lambda sample: (sample[1], sample[0]))
        start = samples[0][1]
        end = min(start + sample_interval_seconds, duration_seconds)
        count = 1
        for _, timestamp in samples[1:]:
            sample_end = min(timestamp + sample_interval_seconds, duration_seconds)
            if timestamp <= end:
                end = max(end, sample_end)
                count += 1
                continue
            appearances.append(AppearanceInterval(brand_name, start, end, count))
            start, end, count = timestamp, sample_end, 1
        appearances.append(AppearanceInterval(brand_name, start, end, count))
    return tuple(appearances)
