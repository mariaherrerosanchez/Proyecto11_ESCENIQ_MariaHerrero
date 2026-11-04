"""Almacenamiento local y seguro de JPEGs de evidencia fuera de SQLite."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID


class EvidenceStorageError(RuntimeError):
    """Indica que una evidencia local no se pudo guardar o recuperar."""


def default_evidence_directory() -> Path:
    """Devuelve una carpeta local configurable, fuera del repositorio por defecto."""
    configured_directory = os.environ.get("ESCENIQ_EVIDENCE_DIRECTORY")
    if configured_directory:
        return Path(configured_directory).expanduser()
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local"))
    return local_app_data / "ESCENIQ" / "evidences"


def _is_valid_jpeg(content: bytes) -> bool:
    """Comprueba que el archivo se puede decodificar antes de mostrarlo en la UI."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return content.startswith(b"\xff\xd8") and content.endswith(b"\xff\xd9")
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    return image is not None


class EvidenceFileStore:
    """Gestiona JPEGs por análisis sin sobrescribir evidencias ya existentes."""

    def __init__(self, root_directory: Path | str | None = None) -> None:
        self.root_directory = (
            Path(root_directory) if root_directory is not None else default_evidence_directory()
        )

    @staticmethod
    def _analysis_directory_name(analysis_id: str) -> str:
        try:
            return str(UUID(analysis_id))
        except ValueError as error:
            raise EvidenceStorageError("El identificador del análisis no es válido para guardar evidencias.") from error

    def relative_path(self, analysis_id: str, frame_index: int) -> Path:
        if frame_index < 0:
            raise EvidenceStorageError("El índice de fotograma de evidencia no es válido.")
        return Path(self._analysis_directory_name(analysis_id)) / f"frame_{frame_index:08d}.jpg"

    def write(self, analysis_id: str, frame_index: int, jpeg: bytes) -> str:
        """Guarda una vez el JPEG y devuelve una ruta relativa segura para SQLite."""
        if not jpeg:
            raise EvidenceStorageError("La evidencia JPEG está vacía.")
        relative_path = self.relative_path(analysis_id, frame_index)
        destination = self.root_directory / relative_path
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                target = destination.open("xb")
            except FileExistsError:
                return relative_path.as_posix()
            try:
                with target:
                    target.write(jpeg)
            except OSError:
                destination.unlink(missing_ok=True)
                raise
        except OSError as error:
            raise EvidenceStorageError("No se pudo guardar la evidencia visual local.") from error
        return relative_path.as_posix()

    def read(self, stored_path: str) -> bytes:
        """Recupera un JPEG existente y rechaza rutas inseguras o archivos corruptos."""
        relative_path = Path(stored_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise EvidenceStorageError("La ruta de evidencia almacenada no es válida.")
        root = self.root_directory.resolve()
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
            content = candidate.read_bytes()
        except (OSError, ValueError) as error:
            raise EvidenceStorageError("La evidencia visual guardada no está disponible.") from error
        if not _is_valid_jpeg(content):
            raise EvidenceStorageError("La evidencia visual guardada está corrupta.")
        return content
