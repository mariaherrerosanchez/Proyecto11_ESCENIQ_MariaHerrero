"""Punto de entrada de la primera pantalla local de ESCENIQ."""
from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path

import cv2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from esceniq.video import VideoValidationError, probe_video, temporary_video_file
from esceniq.vision import (
    AUTOMATIC_REVIEW_STATUS,
    MAX_EVIDENCE_FRAMES,
    InferenceConfig,
    InferenceError,
    InferenceMode,
    analyze_video,
)
from esceniq.vision.evidence import render_evidence_jpeg, visible_detections
from esceniq.analytics import ExposureError, calculate_exposure

MAX_VIDEO_HEIGHT_PX = 480
MAX_VIDEO_WIDTH_PX = 960
EGGO_EXPERIMENTAL_MODEL_PATH = (
    r"C:\ESCENIQ_Datasets\Eggo\training_runs\eggo_yolo11n_pilot_e50_img640_b4_s42\weights\best.pt"
)
MODE_LABELS = {
    "Prueba técnica (clases originales del modelo)": InferenceMode.TECHNICAL_TEST,
    "Eggo experimental (1 clase)": InferenceMode.EGGO_EXPERIMENTAL,
    "ESCENIQ (cinco marcas oficiales)": InferenceMode.ESCENIQ,
}


def format_duration(seconds: float) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remaining_seconds:05.2f}"


def player_width(width: int, height: int) -> int:
    """Calcula un ancho que conserva proporción dentro del tamaño de lectura."""
    scale = min(1, MAX_VIDEO_WIDTH_PX / width, MAX_VIDEO_HEIGHT_PX / height)
    return max(1, round(width * scale))


def inference_mode_from_label(label: str) -> InferenceMode:
    return MODE_LABELS[label]


def suggested_model_path(mode: InferenceMode) -> str:
    """Devuelve una sugerencia editable sin imponer pesos locales a otros modos."""
    return EGGO_EXPERIMENTAL_MODEL_PATH if mode is InferenceMode.EGGO_EXPERIMENTAL else ""


def render_evidence_gallery(result) -> None:
    """Muestra solo las evidencias temporales que produjo la misma inferencia."""
    st.subheader("Evidencias visuales")
    if not result.evidences:
        st.info("No hay evidencias visuales porque el análisis no produjo detecciones.")
        return
    st.caption(
        f"Hasta {MAX_EVIDENCE_FRAMES} fotogramas distribuidos a lo largo del vídeo. "
        "Las imágenes se conservan solo durante esta sesión."
    )
    analysis_key = f"{result.model_path}_{result.elapsed_seconds}_{result.confidence_threshold}"
    visual_confidence = st.number_input(
        "Umbral visual de confianza",
        min_value=float(result.confidence_threshold),
        max_value=1.0,
        value=float(result.confidence_threshold),
        step=0.05,
        key=f"visual_confidence_{analysis_key}",
        help="Solo cambia las cajas visibles en la galería; no altera la inferencia ni las métricas.",
    )
    show_labels = st.checkbox(
        "Mostrar etiquetas de las cajas",
        value=True,
        key=f"show_evidence_labels_{analysis_key}",
    )
    if result.mode is InferenceMode.EGGO_EXPERIMENTAL:
        st.warning(
            "Las detecciones Eggo son candidatas automáticas: revísalas visualmente, pues pueden incluir falsos positivos."
        )
    for start in range(0, len(result.evidences), 3):
        for column, evidence in zip(st.columns(3), result.evidences[start : start + 3], strict=False):
            frame_detections = tuple(
                detection for detection in result.detections if detection.frame_index == evidence.frame_index
            )
            visible = visible_detections(frame_detections, float(visual_confidence))
            column.image(
                render_evidence_jpeg(evidence, visible, show_labels=show_labels, cv2=cv2),
                use_container_width=True,
            )
            column.caption(
                f"{format_duration(evidence.timestamp_seconds)} · {len(visible)} detecciones visibles\n\n"
                f"{AUTOMATIC_REVIEW_STATUS}"
            )


def render_inference_result(result) -> None:
    analyzed, elapsed, detection_count = st.columns(3)
    analyzed.metric("Fotogramas analizados", result.analyzed_frame_count)
    elapsed.metric("Tiempo de ejecución", f"{result.elapsed_seconds:.2f} s")
    detection_count.metric("Detecciones", len(result.detections))
    render_evidence_gallery(result)
    if result.mode is InferenceMode.TECHNICAL_TEST:
        st.info("Resultado de prueba técnica: las clases se conservan tal como las expone el modelo y no son marcas ESCENIQ.")
        return
    exposure = calculate_exposure(result)
    if not exposure.metrics:
        if result.mode is InferenceMode.EGGO_EXPERIMENTAL:
            st.info("El análisis terminó sin detecciones de Eggo. Esto no informa sobre otras marcas del vídeo.")
        else:
            st.info("El análisis terminó correctamente sin detecciones de marcas.")
        return
    st.subheader("Exposición estimada por marca")
    if result.mode is InferenceMode.EGGO_EXPERIMENTAL:
        st.caption("Estimación experimental de Eggo basada en muestras; no representa presencia continua exacta ni evaluación comercial.")
    else:
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
    video_digest = sha256(contents).hexdigest()
    if st.session_state.get("analysis_video_digest") != video_digest:
        st.session_state["analysis_video_digest"] = video_digest
        st.session_state.pop("inference_result", None)
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
                tuple(MODE_LABELS),
                help="La prueba técnica conserva clases genéricas; Eggo experimental admite solo 0=eggo; ESCENIQ exige el catálogo oficial completo.",
            )
            mode = inference_mode_from_label(mode_label)
            if mode is InferenceMode.EGGO_EXPERIMENTAL:
                st.warning(
                    "Detector experimental de una sola marca. Su rendimiento es limitado y sus estimaciones de "
                    "exposición no son fiables para uso comercial. Si no detecta Eggo, no significa que el vídeo "
                    "no contenga otras marcas."
                )
            model_path = st.text_input(
                "Ruta local de los pesos YOLO (.pt)",
                value=suggested_model_path(mode),
                key=f"model_path_{mode.value}",
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
                    mode=mode,
                )
                try:
                    progress = st.progress(0, text="Preparando inferencia local…")

                    def update_progress(completed: int, total: int) -> None:
                        percentage = min(100, round(100 * completed / total))
                        progress.progress(percentage, text=f"Analizando muestra {completed} de {total}…")

                    with st.spinner("Procesando fotogramas localmente…"):
                        result = analyze_video(temporary_path, config, progress_callback=update_progress)
                    progress.progress(100, text="Inferencia terminada.")
                    st.session_state["inference_result"] = result
                except (InferenceError, ExposureError) as error:
                    st.error(str(error))
            result = st.session_state.get("inference_result")
            if result is not None:
                render_inference_result(result)
    except VideoValidationError as error:
        st.error(str(error))
    except OSError:
        st.error("No se pudo preparar el archivo temporal del vídeo. Revisa el espacio y los permisos locales.")


if __name__ == "__main__":
    main()
