"""Evidencias visuales temporales, sin duplicar los resultados de inferencia."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

if TYPE_CHECKING:
    from esceniq.vision.inference import Detection


MAX_EVIDENCE_FRAMES = 24
MAX_EVIDENCE_WIDTH_PX = 960
MAX_EVIDENCE_HEIGHT_PX = 540
AUTOMATIC_REVIEW_STATUS = "Detección automática — sin verificar"


@dataclass(frozen=True)
class VisualEvidence:
    """Fotograma base temporal; las cajas se dibujan solo para la visualización."""

    frame_index: int
    timestamp_seconds: float
    source_jpeg: bytes
    source_width: int
    source_height: int
    review_status: str = AUTOMATIC_REVIEW_STATUS


def evidence_slot(frame_index: int, frame_count: int, maximum: int = MAX_EVIDENCE_FRAMES) -> int:
    """Asigna un fotograma a una franja temporal para distribuir la galería."""
    if frame_count <= 0 or maximum <= 0 or not 0 <= frame_index < frame_count:
        raise ValueError("Los límites del fotograma de evidencia no son válidos.")
    return min(maximum - 1, frame_index * maximum // frame_count)


def detection_label(detection: Detection) -> str:
    name = detection.brand_name or detection.class_name
    return f"{name} · {detection.confidence:.0%}"


def visible_detections(detections: Sequence[Detection], minimum_confidence: float) -> tuple[Detection, ...]:
    """Filtra únicamente la vista; nunca modifica las detecciones de inferencia."""
    return tuple(detection for detection in detections if detection.confidence >= minimum_confidence)


def _scaled_size(width: int, height: int) -> tuple[int, int]:
    scale = min(1.0, MAX_EVIDENCE_WIDTH_PX / width, MAX_EVIDENCE_HEIGHT_PX / height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def encode_base_evidence(frame: Any, cv2: Any) -> bytes:
    """Codifica una única copia JPEG reducida del frame, aún sin anotaciones."""
    height, width = frame.shape[:2]
    target_size = _scaled_size(width, height)
    image = cv2.resize(frame, target_size) if target_size != (width, height) else frame
    encoded, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not encoded:
        raise ValueError("No se pudo codificar la evidencia visual.")
    return bytes(buffer)


def render_evidence_jpeg(
    evidence: VisualEvidence,
    detections: Sequence[Detection],
    *,
    show_labels: bool,
    cv2: Any,
) -> bytes:
    """Dibuja una vista efímera sobre el JPEG base según los filtros actuales."""
    image = cv2.imdecode(np.frombuffer(evidence.source_jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("No se pudo decodificar la evidencia visual almacenada.")
    height, width = image.shape[:2]
    scale_x, scale_y = width / evidence.source_width, height / evidence.source_height
    for detection in detections:
        left, top, right, bottom = detection.bbox_xyxy
        start = (round(left * scale_x), round(top * scale_y))
        end = (round(right * scale_x), round(bottom * scale_y))
        cv2.rectangle(image, start, end, (0, 220, 255), 2)
        if show_labels:
            cv2.putText(
                image,
                detection_label(detection),
                (start[0], max(18, start[1] - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 220, 255),
                2,
                cv2.LINE_AA,
            )
    encoded, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not encoded:
        raise ValueError("No se pudo codificar la vista de evidencia.")
    return bytes(buffer)


class EvidenceCollector:
    """Mantiene como máximo una evidencia base por franja temporal del vídeo."""

    def __init__(self, frame_count: int, cv2: Any, maximum: int = MAX_EVIDENCE_FRAMES) -> None:
        self._frame_count = frame_count
        self._cv2 = cv2
        self._maximum = maximum
        self._by_slot: dict[int, VisualEvidence] = {}
        self._confidence_by_slot: dict[int, float] = {}

    def add(self, frame: Any, detections: Sequence[Detection]) -> None:
        if not detections:
            return
        first = detections[0]
        slot = evidence_slot(first.frame_index, self._frame_count, self._maximum)
        confidence = max(item.confidence for item in detections)
        if confidence <= self._confidence_by_slot.get(slot, -1.0):
            return
        height, width = frame.shape[:2]
        self._by_slot[slot] = VisualEvidence(
            frame_index=first.frame_index,
            timestamp_seconds=first.timestamp_seconds,
            source_jpeg=encode_base_evidence(frame, self._cv2),
            source_width=width,
            source_height=height,
        )
        self._confidence_by_slot[slot] = confidence

    def build(self) -> tuple[VisualEvidence, ...]:
        return tuple(sorted(self._by_slot.values(), key=lambda item: item.frame_index))
