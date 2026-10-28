"""Punto de entrada de la primera pantalla local de ESCENIQ."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from esceniq.video import VideoValidationError, probe_video, temporary_video_file

MAX_VIDEO_HEIGHT_PX = 480
MAX_VIDEO_WIDTH_PX = 960


def format_duration(seconds: float) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remaining_seconds:05.2f}"


def player_width(width: int, height: int) -> int:
    """Calcula un ancho que conserva proporción dentro del tamaño de lectura."""
    scale = min(1, MAX_VIDEO_WIDTH_PX / width, MAX_VIDEO_HEIGHT_PX / height)
    return max(1, round(width * scale))


def main() -> None:
    st.set_page_config(page_title="ESCENIQ · Analizar vídeo", page_icon="◉", layout="wide")
    st.title("ESCENIQ")
    st.caption("Cada aparición cuenta")
    st.header("Analizar vídeo")
    st.write("Carga un MP4 local para comprobar que puede abrirse y mostrar sus metadatos.")
    uploaded_video = st.file_uploader("Vídeo MP4", type=["mp4"], accept_multiple_files=False)
    if uploaded_video is None:
        st.info("Selecciona un vídeo MP4 para comenzar. El archivo no se sube a ningún servicio externo.")
        return

    contents = uploaded_video.getvalue()
    if not contents:
        st.error("El archivo seleccionado está vacío.")
        return
    try:
        with temporary_video_file(contents) as temporary_path:
            metadata = probe_video(temporary_path)
            with st.container(horizontal_alignment="center"):
                st.video(
                    contents,
                    format="video/mp4",
                    width=player_width(metadata.width, metadata.height),
                )
            name, resolution, fps, frames, duration = st.columns(5)
            name.metric("Archivo", uploaded_video.name)
            resolution.metric("Resolución", metadata.resolution)
            fps.metric("FPS", f"{metadata.fps:.2f}")
            frames.metric("Fotogramas", f"{metadata.frame_count:,}")
            duration.metric("Duración", format_duration(metadata.duration_seconds))
    except VideoValidationError as error:
        st.error(str(error))
    except OSError:
        st.error("No se pudo preparar el archivo temporal del vídeo. Revisa el espacio y los permisos locales.")


if __name__ == "__main__":
    main()
