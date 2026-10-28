"""Punto de entrada de la primera pantalla local de ESCENIQ."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from esceniq.video import VideoValidationError, probe_video, temporary_video_file
from esceniq.vision import InferenceConfig, InferenceError, InferenceMode, analyze_video
from esceniq.analytics import ExposureError, calculate_exposure

MAX_VIDEO_HEIGHT_PX = 480
MAX_VIDEO_WIDTH_PX = 960


def format_duration(seconds: float) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remaining_seconds:05.2f}"


def player_width(width: int, height: int) -> int:
    """Calcula un ancho que conserva proporción dentro del tamaño de lectura."""
    scale = min(1, MAX_VIDEO_WIDTH_PX / width, MAX_VIDEO_HEIGHT_PX / height)
    return max(1, round(width * scale))


def inference_mode_from_label(label: str) -> InferenceMode:
    return (
        InferenceMode.ESCENIQ
        if label == "ESCENIQ (cinco marcas oficiales)"
        else InferenceMode.TECHNICAL_TEST
    )


def main() -> None:
    st.set_page_config(page_title="ESCENIQ · Analizar vídeo", page_icon="◉", layout="wide")
    st.title("ESCENIQ")
    st.caption("Cada aparición cuenta")
    st.header("Analizar vídeo")
    st.write("Carga un MP4 local para validarlo, consultar sus metadatos y ejecutar inferencia local.")
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
            st.subheader("Inferencia YOLO")
            mode_label = st.radio(
                "Modo de inferencia",
                ("Prueba técnica (clases originales del modelo)", "ESCENIQ (cinco marcas oficiales)"),
                help="La prueba técnica no interpreta clases genéricas como marcas. El modo ESCENIQ exige el catálogo oficial.",
            )
            model_path = st.text_input(
                "Ruta local de los pesos YOLO (.pt)",
                help="Los pesos permanecen locales. ESCENIQ no descarga modelos automáticamente.",
            )
            confidence, sample_interval = st.columns(2)
            confidence_threshold = confidence.number_input(
                "Umbral de confianza", min_value=0.0, max_value=1.0, value=0.25, step=0.05
            )
            sample_interval_seconds = sample_interval.number_input(
                "Intervalo de muestreo (segundos)", min_value=0.1, value=1.0, step=0.1
            )
            if st.button("Ejecutar inferencia", type="primary"):
                config = InferenceConfig(
                    model_path=Path(model_path),
                    confidence_threshold=float(confidence_threshold),
                    sample_interval_seconds=float(sample_interval_seconds),
                    mode=inference_mode_from_label(mode_label),
                )
                try:
                    progress = st.progress(0, text="Preparando inferencia local…")

                    def update_progress(completed: int, total: int) -> None:
                        percentage = min(100, round(100 * completed / total))
                        progress.progress(percentage, text=f"Analizando muestra {completed} de {total}…")

                    with st.spinner("Procesando fotogramas localmente…"):
                        result = analyze_video(temporary_path, config, progress_callback=update_progress)
                    progress.progress(100, text="Inferencia terminada.")
                    analyzed, elapsed, detection_count = st.columns(3)
                    analyzed.metric("Fotogramas analizados", result.analyzed_frame_count)
                    elapsed.metric("Tiempo de ejecución", f"{result.elapsed_seconds:.2f} s")
                    detection_count.metric("Detecciones", len(result.detections))
                    if result.mode is InferenceMode.TECHNICAL_TEST:
                        st.info("Resultado de prueba técnica: las clases se conservan tal como las expone el modelo y no son marcas ESCENIQ.")
                    else:
                        exposure = calculate_exposure(result)
                        if not exposure.metrics:
                            st.info("El análisis terminó correctamente sin detecciones de marcas.")
                        else:
                            st.subheader("Exposición estimada por marca")
                            st.caption("Estimación basada en muestras; no representa presencia continua exacta.")
                            st.dataframe(
                                [
                                    {
                                        "Marca": metric.brand_name,
                                        "Muestras positivas": metric.positive_sample_count,
                                        "Exposición estimada (s)": round(metric.estimated_seconds, 2),
                                        "Vídeo (%)": round(metric.percentage_of_video, 2),
                                        "Apariciones": metric.appearance_count,
                                    }
                                    for metric in exposure.metrics
                                ],
                                hide_index=True,
                                use_container_width=True,
                            )
                except (InferenceError, ExposureError) as error:
                    st.error(str(error))
    except VideoValidationError as error:
        st.error(str(error))
    except OSError:
        st.error("No se pudo preparar el archivo temporal del vídeo. Revisa el espacio y los permisos locales.")


if __name__ == "__main__":
    main()
