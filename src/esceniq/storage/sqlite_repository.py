"""Repositorio SQLite local para análisis completados de ESCENIQ."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from esceniq.analytics import ExposureSummary
from esceniq.vision import InferenceResult
from esceniq.vision.evidence import MAX_EVIDENCE_FRAMES


class StorageError(RuntimeError):
    """Indica que el análisis no se pudo persistir o recuperar de SQLite."""


@dataclass(frozen=True)
class StoredDetection:
    class_id: int
    class_name: str
    brand_name: str | None
    confidence: float
    frame_index: int
    timestamp_seconds: float
    bbox_xyxy: tuple[float, float, float, float]


@dataclass(frozen=True)
class StoredExposure:
    brand_name: str
    positive_sample_count: int
    estimated_seconds: float
    percentage_of_video: float
    first_detection_seconds: float
    last_detection_seconds: float
    appearance_count: int


@dataclass(frozen=True)
class StoredEvidence:
    """Referencia SQLite a un JPEG local anotado, nunca el binario de la imagen."""

    frame_index: int
    timestamp_seconds: float
    brand_name: str | None
    confidence: float | None
    file_path: str
    review_status: str


@dataclass(frozen=True)
class AnalysisListItem:
    analysis_id: str
    created_at: datetime
    video_name: str
    mode: str
    model_path: str
    detection_count: int


@dataclass(frozen=True)
class StoredAnalysis:
    analysis_id: str
    created_at: datetime
    video_name: str
    mode: str
    model_path: str
    confidence_threshold: float
    sample_interval_seconds: float
    duration_seconds: float
    fps: float
    width: int
    height: int
    analyzed_frame_count: int
    elapsed_seconds: float
    detections: tuple[StoredDetection, ...]
    exposures: tuple[StoredExposure, ...]
    evidences: tuple[StoredEvidence, ...]


def default_database_path() -> Path:
    """Devuelve una ruta local configurable y fuera del repositorio por defecto."""
    configured_path = os.environ.get("ESCENIQ_DATABASE_PATH")
    if configured_path:
        return Path(configured_path).expanduser()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local"))
    return local_app_data / "ESCENIQ" / "esceniq.sqlite3"


class SqliteAnalysisRepository:
    """Guarda análisis completados en SQLite sin almacenar el vídeo ni evidencias pesadas."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = Path(database_path) if database_path is not None else default_database_path()

    def _connect(self) -> sqlite3.Connection:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error as error:
            raise StorageError("No se pudo abrir la base de datos local de ESCENIQ.") from error
        except OSError as error:
            raise StorageError("No se pudo preparar la ruta de la base de datos local.") from error

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Gestiona la transacción y cierra siempre SQLite, también en Windows."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            deduplication_key TEXT NOT NULL UNIQUE,
            video_name TEXT NOT NULL,
            mode TEXT NOT NULL,
            model_path TEXT NOT NULL,
            confidence_threshold REAL NOT NULL,
            sample_interval_seconds REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            fps REAL NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            analyzed_frame_count INTEGER NOT NULL,
            elapsed_seconds REAL NOT NULL,
            detection_count INTEGER NOT NULL,
            status TEXT NOT NULL CHECK (status = 'completed')
        );
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY,
            analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            class_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            brand_name TEXT,
            confidence REAL NOT NULL,
            frame_index INTEGER NOT NULL,
            timestamp_seconds REAL NOT NULL,
            bbox_left REAL NOT NULL,
            bbox_top REAL NOT NULL,
            bbox_right REAL NOT NULL,
            bbox_bottom REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS brand_exposures (
            analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            brand_name TEXT NOT NULL,
            positive_sample_count INTEGER NOT NULL,
            estimated_seconds REAL NOT NULL,
            percentage_of_video REAL NOT NULL,
            first_detection_seconds REAL NOT NULL,
            last_detection_seconds REAL NOT NULL,
            appearance_count INTEGER NOT NULL,
            PRIMARY KEY (analysis_id, brand_name)
        );
        CREATE TABLE IF NOT EXISTS evidences (
            analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
            frame_index INTEGER NOT NULL,
            timestamp_seconds REAL NOT NULL,
            brand_name TEXT,
            confidence REAL,
            file_path TEXT NOT NULL,
            review_status TEXT NOT NULL,
            PRIMARY KEY (analysis_id, frame_index)
        );
        CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
        """
        try:
            with self._connection() as connection:
                connection.executescript(schema)
        except sqlite3.Error as error:
            raise StorageError("No se pudo inicializar la base de datos local de ESCENIQ.") from error

    def save_completed_analysis(
        self,
        result: InferenceResult,
        exposure: ExposureSummary | None,
        *,
        video_name: str,
        deduplication_key: str,
    ) -> str:
        """Guarda un análisis real y devuelve el id existente si el rerun lo repite."""
        if not video_name.strip() or not deduplication_key.strip():
            raise StorageError("El análisis necesita un vídeo y una clave de persistencia válidos.")
        self.initialize()
        analysis_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            with self._connection() as connection:
                existing = connection.execute(
                    "SELECT id FROM analyses WHERE deduplication_key = ?", (deduplication_key,)
                ).fetchone()
                if existing is not None:
                    return str(existing["id"])
                metadata = result.video_metadata
                connection.execute(
                    """
                    INSERT INTO analyses (
                        id, created_at, deduplication_key, video_name, mode, model_path,
                        confidence_threshold, sample_interval_seconds, duration_seconds,
                        fps, width, height, analyzed_frame_count, elapsed_seconds,
                        detection_count, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
                    """,
                    (
                        analysis_id,
                        created_at,
                        deduplication_key,
                        video_name,
                        result.mode.value,
                        str(result.model_path),
                        result.confidence_threshold,
                        result.sample_interval_seconds,
                        metadata.duration_seconds,
                        metadata.fps,
                        metadata.width,
                        metadata.height,
                        result.analyzed_frame_count,
                        result.elapsed_seconds,
                        len(result.detections),
                    ),
                )
                self._insert_detections(connection, analysis_id, result)
                if exposure is not None:
                    self._insert_exposures(connection, analysis_id, exposure)
            return analysis_id
        except sqlite3.Error as error:
            raise StorageError("No se pudo guardar el análisis en la base de datos local.") from error

    @staticmethod
    def _insert_detections(
        connection: sqlite3.Connection, analysis_id: str, result: InferenceResult
    ) -> None:
        connection.executemany(
            """
            INSERT INTO detections (
                analysis_id, class_id, class_name, brand_name, confidence, frame_index,
                timestamp_seconds, bbox_left, bbox_top, bbox_right, bbox_bottom
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    analysis_id,
                    detection.class_id,
                    detection.class_name,
                    detection.brand_name,
                    detection.confidence,
                    detection.frame_index,
                    detection.timestamp_seconds,
                    *detection.bbox_xyxy,
                )
                for detection in result.detections
            ),
        )

    @staticmethod
    def _insert_exposures(
        connection: sqlite3.Connection, analysis_id: str, exposure: ExposureSummary
    ) -> None:
        connection.executemany(
            """
            INSERT INTO brand_exposures (
                analysis_id, brand_name, positive_sample_count, estimated_seconds,
                percentage_of_video, first_detection_seconds, last_detection_seconds, appearance_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    analysis_id,
                    metric.brand_name,
                    metric.positive_sample_count,
                    metric.estimated_seconds,
                    metric.percentage_of_video,
                    metric.first_detection_seconds,
                    metric.last_detection_seconds,
                    metric.appearance_count,
                )
                for metric in exposure.metrics
            ),
        )

    def list_analyses(self) -> tuple[AnalysisListItem, ...]:
        """Lista análisis completados del más reciente al más antiguo."""
        self.initialize()
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    """
                    SELECT id, created_at, video_name, mode, model_path, detection_count
                    FROM analyses ORDER BY created_at DESC, id DESC
                    """
                ).fetchall()
        except sqlite3.Error as error:
            raise StorageError("No se pudieron listar los análisis guardados.") from error
        return tuple(
            AnalysisListItem(
                analysis_id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                video_name=row["video_name"],
                mode=row["mode"],
                model_path=row["model_path"],
                detection_count=row["detection_count"],
            )
            for row in rows
        )

    def save_evidence(
        self,
        analysis_id: str,
        *,
        frame_index: int,
        timestamp_seconds: float,
        brand_name: str | None,
        confidence: float | None,
        file_path: str,
        review_status: str,
    ) -> bool:
        """Registra una evidencia externa y evita duplicados de reruns por fotograma."""
        self.initialize()
        try:
            with self._connection() as connection:
                existing = connection.execute(
                    "SELECT 1 FROM evidences WHERE analysis_id = ? AND frame_index = ?",
                    (analysis_id, frame_index),
                ).fetchone()
                if existing is not None:
                    return False
                count = connection.execute(
                    "SELECT COUNT(*) AS count FROM evidences WHERE analysis_id = ?", (analysis_id,)
                ).fetchone()["count"]
                if count >= MAX_EVIDENCE_FRAMES:
                    return False
                connection.execute(
                    """
                    INSERT INTO evidences (
                        analysis_id, frame_index, timestamp_seconds, brand_name, confidence,
                        file_path, review_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis_id,
                        frame_index,
                        timestamp_seconds,
                        brand_name,
                        confidence,
                        file_path,
                        review_status,
                    ),
                )
        except sqlite3.Error as error:
            raise StorageError("No se pudo guardar la referencia de evidencia visual.") from error
        return True

    def get_analysis(self, analysis_id: str) -> StoredAnalysis | None:
        """Recupera un análisis completo por identificador, listo para la futura Biblioteca."""
        self.initialize()
        try:
            with self._connection() as connection:
                analysis = connection.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
                if analysis is None:
                    return None
                detections = connection.execute(
                    "SELECT * FROM detections WHERE analysis_id = ? ORDER BY id", (analysis_id,)
                ).fetchall()
                exposures = connection.execute(
                    "SELECT * FROM brand_exposures WHERE analysis_id = ? ORDER BY brand_name", (analysis_id,)
                ).fetchall()
                evidences = connection.execute(
                    "SELECT * FROM evidences WHERE analysis_id = ? ORDER BY frame_index", (analysis_id,)
                ).fetchall()
        except sqlite3.Error as error:
            raise StorageError("No se pudo recuperar el análisis guardado.") from error
        return StoredAnalysis(
            analysis_id=analysis["id"],
            created_at=datetime.fromisoformat(analysis["created_at"]),
            video_name=analysis["video_name"],
            mode=analysis["mode"],
            model_path=analysis["model_path"],
            confidence_threshold=analysis["confidence_threshold"],
            sample_interval_seconds=analysis["sample_interval_seconds"],
            duration_seconds=analysis["duration_seconds"],
            fps=analysis["fps"],
            width=analysis["width"],
            height=analysis["height"],
            analyzed_frame_count=analysis["analyzed_frame_count"],
            elapsed_seconds=analysis["elapsed_seconds"],
            detections=tuple(self._stored_detection(row) for row in detections),
            exposures=tuple(self._stored_exposure(row) for row in exposures),
            evidences=tuple(self._stored_evidence(row) for row in evidences),
        )

    @staticmethod
    def _stored_detection(row: sqlite3.Row) -> StoredDetection:
        return StoredDetection(
            class_id=row["class_id"],
            class_name=row["class_name"],
            brand_name=row["brand_name"],
            confidence=row["confidence"],
            frame_index=row["frame_index"],
            timestamp_seconds=row["timestamp_seconds"],
            bbox_xyxy=(row["bbox_left"], row["bbox_top"], row["bbox_right"], row["bbox_bottom"]),
        )

    @staticmethod
    def _stored_exposure(row: sqlite3.Row) -> StoredExposure:
        return StoredExposure(
            brand_name=row["brand_name"],
            positive_sample_count=row["positive_sample_count"],
            estimated_seconds=row["estimated_seconds"],
            percentage_of_video=row["percentage_of_video"],
            first_detection_seconds=row["first_detection_seconds"],
            last_detection_seconds=row["last_detection_seconds"],
            appearance_count=row["appearance_count"],
        )

    @staticmethod
    def _stored_evidence(row: sqlite3.Row) -> StoredEvidence:
        return StoredEvidence(
            frame_index=row["frame_index"],
            timestamp_seconds=row["timestamp_seconds"],
            brand_name=row["brand_name"],
            confidence=row["confidence"],
            file_path=row["file_path"],
            review_status=row["review_status"],
        )
