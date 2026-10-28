"""Validación local y lectura de metadatos de vídeos MP4 mediante OpenCV."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class VideoValidationError(ValueError):
    """Indica que un vídeo no es apto para el flujo de análisis."""


@dataclass(frozen=True)
class VideoMetadata:
    """Contrato de vídeo reutilizable por los servicios futuros de inferencia."""

    path: Path
    fps: float
    frame_count: int
    width: int
    height: int
    duration_seconds: float

    @property
    def resolution(self) -> str:
        return f"{self.width} × {self.height}"


def _load_opencv() -> Any:
    try:
        import cv2
    except ImportError as error:
        raise VideoValidationError(
            "OpenCV no está instalado. Instala las dependencias del proyecto antes de validar vídeos."
        ) from error
    return cv2


def _positive_int(value: float, label: str) -> int:
    if not math.isfinite(value) or value <= 0:
        raise VideoValidationError(f"El vídeo no tiene {label} válido.")
    return int(round(value))


def probe_video(video_path: Path) -> VideoMetadata:
    """Abre, decodifica un fotograma y devuelve metadatos fiables de un MP4 local."""
    path = Path(video_path)
    if path.suffix.casefold() != ".mp4":
        raise VideoValidationError("Selecciona un archivo con extensión .mp4.")
    if not path.is_file():
        raise VideoValidationError("No se encontró el archivo de vídeo seleccionado.")
    if path.stat().st_size <= 0:
        raise VideoValidationError("El archivo de vídeo está vacío.")

    cv2 = _load_opencv()
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise VideoValidationError("No se pudo abrir el MP4. Puede estar corrupto o usar un códec no compatible.")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0:
            raise VideoValidationError("El vídeo no tiene FPS válido.")
        frame_count = _positive_int(float(capture.get(cv2.CAP_PROP_FRAME_COUNT)), "número de fotogramas")
        width = _positive_int(float(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), "ancho")
        height = _positive_int(float(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)), "alto")
        decoded, frame = capture.read()
        if not decoded or frame is None:
            raise VideoValidationError("El MP4 se abre, pero no se puede decodificar ningún fotograma.")
        duration_seconds = frame_count / fps
        if not math.isfinite(duration_seconds) or duration_seconds <= 0:
            raise VideoValidationError("No se pudo calcular una duración válida para el vídeo.")
        return VideoMetadata(path, fps, frame_count, width, height, duration_seconds)
    finally:
        capture.release()
