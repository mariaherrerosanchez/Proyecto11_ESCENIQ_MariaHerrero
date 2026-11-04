"""Gestión acotada de archivos de vídeo recibidos desde la interfaz."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temporary_video_file(contents: bytes, suffix: str = ".mp4") -> Iterator[Path]:
    """Expone bytes como archivo temporal y lo elimina al terminar el bloque."""
    descriptor, filename = tempfile.mkstemp(prefix="esceniq-", suffix=suffix)
    path = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(contents)
        yield path
    finally:
        path.unlink(missing_ok=True)
