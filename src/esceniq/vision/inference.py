"""Inferencia YOLO local y trazable sobre muestras de un vídeo MP4."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping, Protocol, Sequence

from esceniq.video import VideoMetadata, VideoValidationError, probe_video
from esceniq.vision.brand_classes import (
    BrandClassValidationError,
    brand_name_for_yolo_id,
    validate_yolo_names,
)
from esceniq.vision.evidence import EvidenceCollector, VisualEvidence


class InferenceError(RuntimeError):
    """Indica que no se pudo completar una inferencia local."""


class InferenceMode(StrEnum):
    """Semántica con la que se interpretan las clases del modelo."""

    TECHNICAL_TEST = "technical_test"
    ESCENIQ = "esceniq"
    EGGO_EXPERIMENTAL = "eggo_experimental"


@dataclass(frozen=True)
class InferenceConfig:
    """Parámetros reproducibles de una ejecución de inferencia."""

    model_path: Path
    confidence_threshold: float = 0.25
    sample_interval_seconds: float = 1.0
    mode: InferenceMode = InferenceMode.TECHNICAL_TEST

    def validate(self) -> None:
        if not isinstance(self.mode, InferenceMode):
            raise InferenceError("El modo de inferencia no es válido.")
        if not math.isfinite(self.confidence_threshold) or not 0 <= self.confidence_threshold <= 1:
            raise InferenceError("El umbral de confianza debe estar entre 0 y 1.")
        if not math.isfinite(self.sample_interval_seconds) or self.sample_interval_seconds <= 0:
            raise InferenceError("El intervalo de muestreo debe ser un número positivo de segundos.")
        if not Path(self.model_path).is_file():
            raise InferenceError("No se encontró el archivo de pesos del modelo seleccionado.")


@dataclass(frozen=True)
class Detection:
    """Una caja YOLO producida para un fotograma muestreado."""

    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    frame_index: int
    timestamp_seconds: float
    brand_name: str | None


@dataclass(frozen=True)
class InferenceResult:
    """Resultado completo de una ejecución local, aún sin métricas de exposición."""

    video_metadata: VideoMetadata
    model_path: Path
    mode: InferenceMode
    model_class_names: Mapping[int, str]
    confidence_threshold: float
    sample_interval_seconds: float
    analyzed_frame_count: int
    elapsed_seconds: float
    detections: tuple[Detection, ...]
    evidences: tuple[VisualEvidence, ...] = ()


class YOLOModel(Protocol):
    """Parte mínima de la API Ultralytics necesaria por este servicio."""

    names: Mapping[int, str] | Sequence[str]

    def predict(self, source: Any, *, conf: float, verbose: bool) -> Sequence[Any]: ...


ModelLoader = Callable[[Path], YOLOModel]
VideoProbe = Callable[[Path], VideoMetadata]
Clock = Callable[[], float]
ProgressCallback = Callable[[int, int], None]


def _load_opencv() -> Any:
    try:
        import cv2
    except ImportError as error:
        raise InferenceError("OpenCV no está instalado. Instala las dependencias del proyecto.") from error
    return cv2


def _load_yolo_model(model_path: Path) -> YOLOModel:
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise InferenceError(
            "Ultralytics no está instalado. Ejecuta 'python -m pip install -r requirements.txt'."
        ) from error
    try:
        return YOLO(str(model_path))
    except Exception as error:  # El error concreto depende de los pesos y de PyTorch.
        raise InferenceError("No se pudieron cargar los pesos YOLO seleccionados.") from error


def _normalize_model_names(names: Mapping[int, str] | Sequence[str]) -> dict[int, str]:
    if isinstance(names, Mapping):
        normalized = {int(class_id): str(class_name) for class_id, class_name in names.items()}
    elif isinstance(names, Sequence) and not isinstance(names, str):
        normalized = {class_id: str(class_name) for class_id, class_name in enumerate(names)}
    else:
        raise InferenceError("El modelo no expone un mapa de clases válido.")
    if not normalized or any(class_id < 0 or not class_name for class_id, class_name in normalized.items()):
        raise InferenceError("El modelo no expone un mapa de clases válido.")
    return normalized


def _validate_mode_classes(mode: InferenceMode, model_names: Mapping[int, str]) -> None:
    if mode is InferenceMode.TECHNICAL_TEST:
        return
    if mode is InferenceMode.EGGO_EXPERIMENTAL:
        if dict(model_names) != {0: "eggo"}:
            raise InferenceError(
                "El modo Eggo experimental exige exclusivamente la clase 0=eggo; "
                "no puede interpretarse como modelo oficial ESCENIQ."
            )
        return
    try:
        validate_yolo_names(model_names)
    except BrandClassValidationError as error:
        raise InferenceError(
            "El modelo no coincide con las cinco clases oficiales de ESCENIQ; "
            "no puede interpretarse como detección de marcas."
        ) from error


def _brand_name_for_detection(mode: InferenceMode, class_id: int) -> str | None:
    """Normaliza únicamente las clases permitidas por el modo seleccionado."""
    if mode is InferenceMode.TECHNICAL_TEST:
        return None
    if mode is InferenceMode.EGGO_EXPERIMENTAL:
        if class_id != 0:
            raise InferenceError("El modelo experimental devolvió una clase distinta de 0=eggo.")
        return "Eggo"
    return brand_name_for_yolo_id(class_id)


def _as_list(value: Any) -> list[Any]:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value)


def _parse_detections(
    results: Sequence[Any],
    *,
    model_names: Mapping[int, str],
    config: InferenceConfig,
    frame_index: int,
    timestamp_seconds: float,
) -> list[Detection]:
    detections: list[Detection] = []
    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        class_ids = _as_list(boxes.cls)
        confidences = _as_list(boxes.conf)
        coordinates = _as_list(boxes.xyxy)
        if not (len(class_ids) == len(confidences) == len(coordinates)):
            raise InferenceError("El modelo devolvió cajas YOLO inconsistentes.")
        for class_id_value, confidence_value, bbox_value in zip(class_ids, confidences, coordinates, strict=True):
            class_id = int(class_id_value)
            confidence = float(confidence_value)
            if not math.isfinite(confidence) or confidence < config.confidence_threshold:
                continue
            if class_id not in model_names:
                raise InferenceError("El modelo devolvió una clase ausente de su mapa de clases.")
            bbox = tuple(float(value) for value in bbox_value)
            if len(bbox) != 4 or not all(math.isfinite(value) for value in bbox):
                raise InferenceError("El modelo devolvió una caja delimitadora inválida.")
            brand_name = _brand_name_for_detection(config.mode, class_id)
            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=model_names[class_id],
                    confidence=confidence,
                    bbox_xyxy=bbox,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    brand_name=brand_name,
                )
            )
    return detections


def analyze_video(
    video_path: Path,
    config: InferenceConfig,
    *,
    model_loader: ModelLoader = _load_yolo_model,
    video_probe: VideoProbe = probe_video,
    cv2_loader: Callable[[], Any] = _load_opencv,
    clock: Clock = perf_counter,
    progress_callback: ProgressCallback | None = None,
) -> InferenceResult:
    """Analiza muestras de un MP4 sin cargar el vídeo completo en memoria."""
    config.validate()
    path = Path(video_path)
    try:
        metadata = video_probe(path)
    except VideoValidationError as error:
        raise InferenceError(str(error)) from error

    model = model_loader(Path(config.model_path))
    model_names = _normalize_model_names(model.names)
    _validate_mode_classes(config.mode, model_names)
    sample_every_frames = max(1, round(metadata.fps * config.sample_interval_seconds))
    expected_sample_count = math.ceil(metadata.frame_count / sample_every_frames)
    cv2 = cv2_loader()
    capture = cv2.VideoCapture(str(path))
    start_time = clock()
    detections: list[Detection] = []
    evidence_collector = EvidenceCollector(metadata.frame_count, cv2)
    analyzed_frame_count = 0
    frame_index = 0
    try:
        if not capture.isOpened():
            raise InferenceError("No se pudo abrir el vídeo para ejecutar la inferencia.")
        while True:
            decoded, frame = capture.read()
            if not decoded or frame is None:
                if frame_index < metadata.frame_count:
                    raise InferenceError("La lectura del vídeo se interrumpió antes de terminar la inferencia.")
                break
            if frame_index % sample_every_frames == 0:
                try:
                    results = model.predict(frame, conf=config.confidence_threshold, verbose=False)
                except Exception as error:
                    raise InferenceError("La inferencia YOLO falló al procesar un fotograma.") from error
                frame_detections = _parse_detections(
                        results,
                        model_names=model_names,
                        config=config,
                        frame_index=frame_index,
                        timestamp_seconds=frame_index / metadata.fps,
                    )
                detections.extend(frame_detections)
                try:
                    evidence_collector.add(frame, frame_detections)
                except (AttributeError, ValueError) as error:
                    raise InferenceError("No se pudo generar la evidencia visual del fotograma.") from error
                analyzed_frame_count += 1
                if progress_callback is not None:
                    progress_callback(analyzed_frame_count, expected_sample_count)
            frame_index += 1
    finally:
        capture.release()

    return InferenceResult(
        video_metadata=metadata,
        model_path=Path(config.model_path),
        mode=config.mode,
        model_class_names=model_names,
        confidence_threshold=config.confidence_threshold,
        sample_interval_seconds=config.sample_interval_seconds,
        analyzed_frame_count=analyzed_frame_count,
        elapsed_seconds=clock() - start_time,
        detections=tuple(detections),
        evidences=evidence_collector.build(),
    )
