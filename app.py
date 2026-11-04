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
    experimental_brand_name,
)
from esceniq.vision.evidence import render_evidence_jpeg, visible_detections
from esceniq.analytics import ExposureError, calculate_exposure
from esceniq.reports import build_results_csv, build_stored_results_csv
from esceniq.storage import (
    EvidenceFileStore,
    EvidenceStorageError,
    SqliteAnalysisRepository,
    StorageError,
)
from esceniq.ui import (
    apply_brand_styles,
    render_capability_showcase,
    render_cinematic_header,
    render_empty_state,
    render_information_cards,
    render_home_cinematic_hero,
    render_metric_cards,
    render_page_intro,
)

MAX_VIDEO_HEIGHT_PX = 480
MAX_VIDEO_WIDTH_PX = 960
ASSETS_DIRECTORY = Path(__file__).resolve().parent / "assets"
SIDEBAR_LOGO_PATH = ASSETS_DIRECTORY / "esceniq-logo-compact.png"
FAVICON_PATH = ASSETS_DIRECTORY / "esceniq-shutter-favicon.png"
HERO_IMAGE_PATH = ASSETS_DIRECTORY / "esceniq-hero-cinematic.png"
EGGO_EXPERIMENTAL_MODEL_PATH = (
    r"C:\ESCENIQ_Datasets\Eggo\training_runs\eggo_yolo11n_pilot_e50_img640_b4_s42\weights\best.pt"
)
COCACOLA_EXPERIMENTAL_MODEL_PATH = (
    r"C:\ESCENIQ_Datasets\CocaCola_training_runs\cocacola_yolo11n_pilot_e50_img640_b8_s42\weights\best.pt"
)
MODE_LABELS = {
    "Prueba técnica (clases originales del modelo)": InferenceMode.TECHNICAL_TEST,
    "Eggo experimental (1 clase)": InferenceMode.EGGO_EXPERIMENTAL,
    "Coca-Cola experimental (1 clase)": InferenceMode.COCACOLA_EXPERIMENTAL,
    "ESCENIQ (cinco marcas oficiales)": InferenceMode.ESCENIQ,
}
NAVIGATION_PAGES = (
    "Inicio",
    "Analizar vídeo",
    "Resultados",
    "Biblioteca",
    "Informes",
    "Modelos e IA",
    "Configuración",
)
NAVIGATION_LABELS = {
    "Inicio": "⌂  Inicio",
    "Analizar vídeo": "◉  Analizar vídeo",
    "Resultados": "▦  Resultados",
    "Biblioteca": "▣  Biblioteca",
    "Informes": "↗  Informes · Próximamente",
    "Modelos e IA": "✦  Modelos e IA",
    "Configuración": "⚙  Configuración · Próximamente",
}
MODEL_INFORMATION_CARDS = (
    (
        "EXPERIMENTAL · 1 CLASE · YOLO11N",
        "Coca-Cola experimental",
        "Usa un peso local YOLO11n monoclase que acepta exclusivamente `0 = coca-cola` para localizar productos o logotipos de Coca-Cola.",
        "Es experimental. No hay en el repositorio un artefacto de evaluación independiente verificable, por lo que no se muestran métricas ni se garantiza su comportamiento en películas o series.",
    ),
    (
        "EXPERIMENTAL · 1 CLASE · YOLO11N",
        "Eggo experimental",
        "Usa un peso local específico para la única clase `0 = eggo`; permite revisar detecciones y una estimación temporal de Eggo.",
        "Presenta falsos positivos observados, incluso de confianza alta. El piloto documentado obtuvo resultados débiles en test y no debe considerarse un detector validado.",
    ),
    (
        "DIAGNÓSTICO · SIN MARCAS",
        "Prueba técnica",
        "Ejecuta el detector con sus clases originales para comprobar cajas, confianza y comportamiento técnico.",
        "No identifica marcas ESCENIQ ni calcula exposición comercial; sus clases no se deben interpretar como resultados de marca.",
    ),
    (
        "OBJETIVO · 5 CLASES",
        "ESCENIQ multiclase",
        "El catálogo objetivo reúne Eggo, Coca-Cola, Pepsi, FedEx y Wilson; Coca-Cola incluye Coke y New Coke, y Wilson su logotipo o W inequívoca.",
        "Todavía no existe un peso multiclase completo entrenado y evaluado. La validación del catálogo no afirma que haya un modelo oficial disponible.",
    ),
)


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
    experimental_paths = {
        InferenceMode.EGGO_EXPERIMENTAL: EGGO_EXPERIMENTAL_MODEL_PATH,
        InferenceMode.COCACOLA_EXPERIMENTAL: COCACOLA_EXPERIMENTAL_MODEL_PATH,
    }
    return experimental_paths.get(mode, "")


def render_evidence_gallery(result) -> None:
    """Muestra solo las evidencias temporales que produjo la misma inferencia."""
    st.subheader("Evidencias visuales")
    if not result.evidences:
        st.info("No hay evidencias visuales porque el análisis no produjo detecciones.")
        return
    st.caption(
        f"Muestras reales con detecciones · hasta {MAX_EVIDENCE_FRAMES} fotogramas distribuidos a lo largo del vídeo. "
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
    experimental_brand = experimental_brand_name(result.mode)
    if experimental_brand is not None:
        st.warning(
            f"Las detecciones de {experimental_brand} son candidatas automáticas: revísalas visualmente, "
            "pues pueden incluir falsos positivos."
        )
    for start in range(0, len(result.evidences), 3):
        for column, evidence in zip(st.columns(3), result.evidences[start : start + 3], strict=False):
            frame_detections = tuple(
                detection for detection in result.detections if detection.frame_index == evidence.frame_index
            )
            visible = visible_detections(frame_detections, float(visual_confidence))
            with column.container(border=True):
                column.image(
                    render_evidence_jpeg(evidence, visible, show_labels=show_labels, cv2=cv2),
                    use_container_width=True,
                )
                column.caption(
                    f"{format_duration(evidence.timestamp_seconds)} · {len(visible)} detecciones visibles\n\n"
                    f"{AUTOMATIC_REVIEW_STATUS}"
                )


def clear_inference_result() -> None:
    """Evita que un análisis anterior se presente durante una nueva ejecución."""
    st.session_state.pop("inference_result", None)
    st.session_state.pop("inference_result_key", None)
    st.session_state.pop("persisted_analysis_id", None)


def persist_completed_analysis(result, *, video_name: str, analysis_key: tuple[object, ...]) -> str:
    """Persiste una inferencia ya completada sin volver a ejecutar YOLO."""
    exposure = None if result.mode is InferenceMode.TECHNICAL_TEST else calculate_exposure(result)
    deduplication_key = sha256(repr(analysis_key).encode("utf-8")).hexdigest()
    return SqliteAnalysisRepository().save_completed_analysis(
        result,
        exposure,
        video_name=video_name,
        deduplication_key=deduplication_key,
    )


def persist_analysis_evidences(analysis_id: str, result) -> None:
    """Guarda JPEGs anotados de evidencias ya producidas, sin ejecutar YOLO de nuevo."""
    repository = SqliteAnalysisRepository()
    file_store = EvidenceFileStore()
    for evidence in result.evidences:
        frame_detections = tuple(
            detection for detection in result.detections if detection.frame_index == evidence.frame_index
        )
        if not frame_detections:
            continue
        primary_detection = max(frame_detections, key=lambda detection: detection.confidence)
        annotated_jpeg = render_evidence_jpeg(
            evidence,
            frame_detections,
            show_labels=True,
            cv2=cv2,
        )
        file_path = file_store.write(analysis_id, evidence.frame_index, annotated_jpeg)
        repository.save_evidence(
            analysis_id,
            frame_index=evidence.frame_index,
            timestamp_seconds=evidence.timestamp_seconds,
            brand_name=primary_detection.brand_name,
            confidence=primary_detection.confidence,
            file_path=file_path,
            review_status=evidence.review_status,
        )


def render_inference_error(error: Exception) -> None:
    """Muestra un fallo de inferencia, distinto de un análisis vacío."""
    st.error(str(error))


def render_inference_result(result, *, exposure=None):
    """Presenta un resultado y devuelve la exposición ya agregada cuando aplica."""
    experimental_brand = experimental_brand_name(result.mode)
    st.subheader("Resumen del análisis")
    render_metric_cards(
        st,
        (
            ("Fotogramas analizados", result.analyzed_frame_count),
            ("Tiempo de ejecución", f"{result.elapsed_seconds:.2f} s"),
            ("Detecciones", len(result.detections)),
        ),
    )
    st.caption("PARÁMETROS DEL ANÁLISIS")
    st.caption(f"Modelo: {result.model_path} · Umbral: {result.confidence_threshold:.0%} · " f"Intervalo: {result.sample_interval_seconds:g} s")
    render_evidence_gallery(result)
    if result.mode is InferenceMode.TECHNICAL_TEST:
        st.info("Resultado de prueba técnica: las clases se conservan tal como las expone el modelo y no son marcas ESCENIQ.")
        return None
    if exposure is None:
        exposure = calculate_exposure(result)
    if not exposure.metrics:
        if experimental_brand is not None:
            st.info(
                f"El análisis terminó sin detecciones de {experimental_brand}. "
                "Esto no informa sobre otras marcas del vídeo."
            )
        else:
            st.info("El análisis terminó correctamente sin detecciones de marcas.")
        return exposure
    st.subheader("Exposición estimada por marca")
    if experimental_brand is not None:
        st.caption(
            f"Estimación experimental de {experimental_brand} basada en muestras; no representa presencia "
            "continua exacta ni evaluación comercial."
        )
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
    return exposure


def render_csv_download(result, exposure) -> None:
    """Ofrece el informe local solo cuando la agregación contiene filas reales."""
    csv_data = build_results_csv(
        result,
        exposure,
        video_name=st.session_state.get("analysis_video_name"),
    )
    if csv_data is None:
        return
    st.download_button(
        "Descargar CSV",
        data=csv_data,
        file_name="esceniq_resultados.csv",
        mime="text/csv",
        help="CSV UTF-8 para Excel, separado por punto y coma.",
    )


def render_stored_csv_download(analysis) -> None:
    """Ofrece el mismo CSV para un análisis real recuperado de SQLite."""
    csv_data = build_stored_results_csv(analysis)
    if csv_data is None:
        return
    st.download_button(
        "Descargar CSV",
        data=csv_data,
        file_name="esceniq_resultados_guardados.csv",
        mime="text/csv",
        help="CSV UTF-8 para Excel, separado por punto y coma.",
        key=f"library_csv_{analysis.analysis_id}",
    )


def navigate_to(page_name: str) -> None:
    """Cambia de sección sin perder el último resultado guardado en sesión."""
    st.session_state["navigation_page"] = page_name


def render_home_page() -> None:
    render_home_cinematic_hero(st, str(HERO_IMAGE_PATH))
    with st.container(key="home-real-cta"):
        st.button("Analizar vídeo", type="primary", on_click=navigate_to, args=("Analizar vídeo",))
    render_capability_showcase(st)

    st.subheader("Última señal de análisis")
    result = st.session_state.get("inference_result")
    if result is None:
        with st.container(border=True):
            st.caption("SIN ANÁLISIS EN ESTA SESIÓN")
            st.write("La sala de resultados se activará cuando completes una inferencia sobre un vídeo local.")
            st.caption("Las capacidades anteriores describen el flujo; no representan resultados ni métricas reales.")
        return
    with st.container(border=True):
        st.success("Hay un análisis real disponible para consultar en Resultados.")
        render_metric_cards(
            st,
            (
                ("Fotogramas analizados", result.analyzed_frame_count),
                ("Detecciones", len(result.detections)),
                ("Tiempo de ejecución", f"{result.elapsed_seconds:.2f} s"),
            ),
        )
        st.button("Ver resultados", key="home_results", on_click=navigate_to, args=("Resultados",))


def render_analysis_page() -> None:
    render_cinematic_header(
        st,
        "Sala de análisis audiovisual",
        "Carga un MP4 local, encuádralo en la consola y ejecuta una inferencia con parámetros explícitos.",
        str(HERO_IMAGE_PATH),
        eyebrow="ESCENIQ · ESCENA DE ANÁLISIS",
    )
    st.caption("SECUENCIA 01 · FUENTE LOCAL · PREPARADA PARA ANALIZAR")
    st.subheader("Carga la fuente")
    with st.container(border=True):
        upload_zone, upload_signal = st.columns((1.45, 0.55))
        with upload_zone:
            uploaded_video = st.file_uploader("Vídeo MP4", type=["mp4"], accept_multiple_files=False)
            st.caption("El archivo permanece local; ESCENIQ valida su decodificación antes de procesarlo.")
        with upload_signal:
            st.image(str(FAVICON_PATH), width=116)
            st.caption("ENCUADRE · MP4 · VISIÓN ARTIFICIAL")
    if uploaded_video is None:
        st.info("Selecciona un vídeo MP4 para comenzar. El archivo no se sube a ningún servicio externo.")
        return

    contents = uploaded_video.getvalue()
    if not contents:
        st.error("El archivo seleccionado está vacío.")
        return
    video_digest = sha256(contents).hexdigest()
    st.session_state["analysis_video_name"] = uploaded_video.name
    if st.session_state.get("analysis_video_digest") != video_digest:
        st.session_state["analysis_video_digest"] = video_digest
        st.session_state.pop("inference_result", None)
    try:
        with temporary_video_file(contents) as temporary_path:
            metadata = probe_video(temporary_path)
            st.subheader("Monitor de escena")
            with st.container(border=True):
                preview, metadata_panel = st.columns((1.45, 0.55))
                with preview:
                    st.video(
                        contents,
                        format="video/mp4",
                        width=player_width(metadata.width, metadata.height),
                    )
                with metadata_panel:
                    st.caption("FICHA DE LA ESCENA")
                    st.write(f"**{uploaded_video.name}**")
                    st.caption(f"{metadata.resolution} · {metadata.fps:.2f} FPS")
                    st.caption(f"{metadata.frame_count:,} fotogramas · {format_duration(metadata.duration_seconds)}")
                    st.image(str(FAVICON_PATH), width=78)
            render_metric_cards(
                st,
                (
                    ("Archivo", uploaded_video.name),
                    ("Resolución", metadata.resolution),
                    ("FPS", f"{metadata.fps:.2f}"),
                    ("Fotogramas", f"{metadata.frame_count:,}"),
                    ("Duración", format_duration(metadata.duration_seconds)),
                ),
            )
            st.subheader("Consola de detección")
            with st.container(border=True):
                mode_console, parameters_console = st.columns((1.1, 0.9))
                with mode_console:
                    st.caption("MODELO Y SEMÁNTICA")
                    mode_label = st.radio(
                        "Modo de inferencia",
                        tuple(MODE_LABELS),
                        help=(
                            "La prueba técnica conserva clases genéricas; los modos experimentales exigen su única "
                            "clase esperada; ESCENIQ exige el catálogo oficial completo."
                        ),
                    )
                    mode = inference_mode_from_label(mode_label)
                    experimental_brand = experimental_brand_name(mode)
                    if experimental_brand is not None:
                        st.warning(
                            f"Detector experimental monoclase de {experimental_brand}. Su rendimiento es limitado y sus "
                            "estimaciones de exposición no son fiables para uso comercial. Si no detecta la marca, no "
                            "significa que el vídeo no contenga otras marcas."
                        )
                    model_path = st.text_input(
                        "Ruta local de los pesos YOLO (.pt)",
                        value=suggested_model_path(mode),
                        key=f"model_path_{mode.value}",
                        help="Los pesos permanecen locales. ESCENIQ no descarga modelos automáticamente.",
                    )
                with parameters_console:
                    st.caption("MUESTREO Y CONFIANZA")
                    confidence_threshold = st.number_input(
                        "Umbral de confianza", min_value=0.0, max_value=1.0, value=0.25, step=0.05
                    )
                    sample_interval_seconds = st.number_input(
                        "Intervalo de muestreo (segundos)", min_value=0.1, value=1.0, step=0.1
                    )
            selected_analysis_key = (
                video_digest,
                mode.value,
                model_path,
                float(confidence_threshold),
                float(sample_interval_seconds),
            )
            if st.session_state.get("inference_result_key") != selected_analysis_key:
                clear_inference_result()
            st.subheader("Iniciar secuencia")
            with st.container(border=True):
                st.caption("ESTADO · CONSOLA LISTA")
                st.write("La inferencia usa los parámetros elegidos y procesa el vídeo únicamente en este equipo.")
                if st.button("Ejecutar inferencia", type="primary"):
                    clear_inference_result()
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
                        st.session_state["inference_result_key"] = selected_analysis_key
                        try:
                            st.session_state["persisted_analysis_id"] = persist_completed_analysis(
                                result,
                                video_name=uploaded_video.name,
                                analysis_key=selected_analysis_key,
                            )
                            persist_analysis_evidences(st.session_state["persisted_analysis_id"], result)
                        except (StorageError, EvidenceStorageError, ValueError, cv2.error) as error:
                            st.warning(
                                "El análisis terminó correctamente, pero no se pudieron conservar todos sus datos "
                                f"persistentes. El resultado actual sigue disponible en esta sesión. Detalle: {error}"
                            )
                    except (InferenceError, ExposureError) as error:
                        render_inference_error(error)
            result = (
                st.session_state.get("inference_result")
                if st.session_state.get("inference_result_key") == selected_analysis_key
                else None
            )
            if result is not None:
                with st.container(border=True):
                    st.caption("ÚLTIMO ANÁLISIS DE ESTE VÍDEO")
                    render_inference_result(result)
    except VideoValidationError as error:
        st.error(str(error))
    except OSError:
        st.error("No se pudo preparar el archivo temporal del vídeo. Revisa el espacio y los permisos locales.")


def render_results_page() -> None:
    render_cinematic_header(
        st,
        "Sala de resultados",
        "Evidencias reales, detecciones y exposición estimada del último análisis disponible.",
        str(FAVICON_PATH),
        eyebrow="ESCENIQ · ARCHIVO DE EVIDENCIAS",
        asset_width=142,
    )
    result = st.session_state.get("inference_result")
    if result is None:
        with st.container(border=True):
            symbol, copy = st.columns((0.28, 1.72))
            with symbol:
                st.image(str(FAVICON_PATH), width=118)
            with copy:
                st.caption("ARCHIVO VACÍO · SIN MÉTRICAS SIMULADAS")
                st.subheader("Aún no hay una escena analizada")
                st.write("Cuando completes un análisis, aquí aparecerán únicamente sus métricas, parámetros y evidencias reales.")
                st.button("Analizar vídeo", type="primary", key="results_analyze_video", on_click=navigate_to, args=("Analizar vídeo",))
                st.caption("Los análisis persistidos pueden consultarse desde Biblioteca.")
        st.info("Todavía no hay un análisis disponible. Carga un vídeo y ejecuta la inferencia desde Analizar vídeo.")
        return
    metadata = getattr(result, "video_metadata", None)
    with st.container(border=True):
        st.caption("FICHA DE LA ESCENA ANALIZADA")
        if metadata is None:
            st.write("Último análisis disponible en esta sesión.")
        else:
            render_metric_cards(
                st,
                (
                    ("Resolución", metadata.resolution),
                    ("Duración", format_duration(metadata.duration_seconds)),
                    ("Muestreo", f"Cada {result.sample_interval_seconds:g} s"),
                ),
            )
    exposure = render_inference_result(result)
    if exposure is not None and exposure.metrics:
        render_csv_download(result, exposure)


def _library_option_label(item) -> str:
    """Resume una entrada de historial sin exponer su ruta local completa."""
    created_at = item.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
    return f"{created_at} · {item.video_name} · {item.mode} · {item.detection_count} detecciones"


def render_library_analysis(analysis) -> None:
    """Presenta datos persistidos; las evidencias no se guardan en SQLite todavía."""
    st.subheader("Detalle del análisis guardado")
    st.caption(f"ID: {analysis.analysis_id} · Completado: {analysis.created_at.astimezone().strftime('%d/%m/%Y %H:%M')}")
    render_metric_cards(
        st,
        (
            ("Detecciones", len(analysis.detections)),
            ("Fotogramas analizados", analysis.analyzed_frame_count),
            ("Duración", format_duration(analysis.duration_seconds)),
            ("Marcas con exposición", len(analysis.exposures)),
        ),
    )
    st.caption(
        f"Vídeo: {analysis.video_name} · Modo: {analysis.mode} · Modelo: {analysis.model_path} · "
        f"Umbral: {analysis.confidence_threshold:.0%} · Intervalo: {analysis.sample_interval_seconds:g} s"
    )

    st.subheader("Exposición por marca")
    if analysis.exposures:
        st.dataframe(
            [
                {
                    "Marca": metric.brand_name,
                    "Muestras positivas": metric.positive_sample_count,
                    "Exposición estimada (s)": round(metric.estimated_seconds, 2),
                    "Vídeo (%)": round(metric.percentage_of_video, 2),
                    "Apariciones": metric.appearance_count,
                }
                for metric in analysis.exposures
            ],
            hide_index=True,
            use_container_width=True,
        )
        render_stored_csv_download(analysis)
    else:
        st.info("Este análisis no contiene métricas de exposición por marca.")

    st.subheader("Detecciones guardadas")
    if analysis.detections:
        st.dataframe(
            [
                {
                    "Tiempo": format_duration(detection.timestamp_seconds),
                    "Fotograma": detection.frame_index,
                    "Clase": detection.class_name,
                    "Marca": detection.brand_name or "—",
                    "Confianza": f"{detection.confidence:.0%}",
                }
                for detection in analysis.detections
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("El análisis se guardó correctamente sin detecciones.")
    render_stored_evidence_gallery(analysis)


def render_stored_evidence_gallery(analysis) -> None:
    """Muestra JPEGs anotados recuperados localmente, sin reconstruir ni inferir nada."""
    st.subheader("Evidencias visuales guardadas")
    if not analysis.evidences:
        st.info("Este análisis histórico no tiene evidencias visuales guardadas.")
        return
    file_store = EvidenceFileStore()
    st.caption(f"Hasta {MAX_EVIDENCE_FRAMES} fotogramas anotados conservados localmente para este análisis.")
    for start in range(0, len(analysis.evidences), 3):
        for column, evidence in zip(st.columns(3), analysis.evidences[start : start + 3], strict=False):
            with column.container(border=True):
                try:
                    image = file_store.read(evidence.file_path)
                except EvidenceStorageError as error:
                    column.warning(
                        f"Evidencia no disponible en {format_duration(evidence.timestamp_seconds)}. {error}"
                    )
                    continue
                column.image(image, use_container_width=True)
                label = evidence.brand_name or "Clase técnica"
                confidence = "" if evidence.confidence is None else f" · {evidence.confidence:.0%}"
                column.caption(
                    f"{format_duration(evidence.timestamp_seconds)} · {label}{confidence}\n\n"
                    f"{evidence.review_status}"
                )


def render_library_page() -> None:
    """Consulta el historial SQLite sin modificar el análisis activo de la sesión."""
    render_cinematic_header(
        st,
        "Biblioteca de análisis",
        "Recupera análisis completados localmente sin repetir la inferencia ni alterar sus métricas.",
        str(FAVICON_PATH),
        eyebrow="ESCENIQ · ARCHIVO LOCAL",
        asset_width=142,
    )
    try:
        repository = SqliteAnalysisRepository()
        analyses = repository.list_analyses()
    except StorageError as error:
        st.error(f"No se pudo leer la biblioteca local. El análisis actual de la sesión no se ha modificado. Detalle: {error}")
        return

    if not analyses:
        render_empty_state(
            st,
            "La biblioteca está vacía",
            "Los análisis completados aparecerán aquí automáticamente después de guardarse en SQLite.",
            detail="No hay resultados simulados ni se ejecutará una inferencia desde esta pantalla.",
        )
        return

    st.caption("HISTORIAL · ORDENADO DEL MÁS RECIENTE AL MÁS ANTIGUO")
    st.dataframe(
        [
            {
                "Fecha": item.created_at.astimezone().strftime("%d/%m/%Y %H:%M"),
                "Vídeo": item.video_name,
                "Estado": "Completado",
                "Modo": item.mode,
                "Modelo": Path(item.model_path).name,
                "Detecciones": item.detection_count,
            }
            for item in analyses
        ],
        hide_index=True,
        use_container_width=True,
    )
    selected_id = st.selectbox(
        "Abrir análisis guardado",
        options=tuple(item.analysis_id for item in analyses),
        format_func=lambda analysis_id: _library_option_label(
            next(item for item in analyses if item.analysis_id == analysis_id)
        ),
        key="library_analysis_id",
    )
    try:
        analysis = repository.get_analysis(selected_id)
    except StorageError as error:
        st.error(f"No se pudo abrir el análisis seleccionado. Detalle: {error}")
        return
    if analysis is None:
        st.warning("El análisis seleccionado ya no está disponible en la biblioteca. Actualiza la lista para continuar.")
        return
    render_library_analysis(analysis)


def render_unavailable_page(section_name: str, detail: str = "") -> None:
    render_page_intro(st, section_name, "Esta sección está preparada para incorporarse al flujo de trabajo.")
    message = "No disponible todavía."
    if detail:
        message = f"{message} {detail}"
    render_empty_state(
        st,
        f"{section_name} estará disponible próximamente",
        "No se muestran datos simulados ni controles inactivos mientras esta funcionalidad está pendiente.",
        detail=detail or "Podrás acceder a esta función desde el mismo menú lateral cuando esté implementada.",
    )
    st.info(message)


def render_models_methodology() -> None:
    """Explica metodología y límites reales sin presentar controles no disponibles."""
    st.subheader("Cómo se analiza una escena")
    with st.container(border=True):
        st.write(
            "YOLO examina los fotogramas muestreados y devuelve cajas delimitadoras, una clase y una confianza. "
            "ESCENIQ normaliza las clases aceptadas por el modo, agrupa las muestras positivas por marca y conserva "
            "las detecciones para su revisión visual."
        )
        st.caption("La detección es automática. La aplicación no verifica por sí sola si una caja corresponde realmente a una marca.")

    st.subheader("Cómo leer los resultados")
    metric_columns = st.columns(2)
    with metric_columns[0]:
        with st.container(border=True):
            st.caption("DETECCIÓN Y MUESTREO")
            st.write("**Detecciones**: cajas encontradas. **Muestras positivas**: instantes muestreados con al menos una detección de esa marca.")
            st.write("**Apariciones estimadas**: grupos de muestras positivas separados por huecos temporales.")
    with metric_columns[1]:
        with st.container(border=True):
            st.caption("EXPOSICIÓN ESTIMADA")
            st.write("**Exposición estimada**: segundos representados por las muestras positivas, sin duplicar cajas de una misma marca.")
            st.write("**Porcentaje de exposición**: exposición estimada dividida entre la duración del vídeo. Es una aproximación, no una medición continua.")

    st.subheader("Parámetros que cambian la lectura")
    parameter_columns = st.columns(2)
    with parameter_columns[0]:
        with st.container(border=True):
            st.caption("UMBRAL DE CONFIANZA")
            st.write("Un umbral más alto muestra menos cajas y puede reducir falsos positivos, pero también ocultar detecciones reales. No corrige por sí solo un modelo sesgado.")
    with parameter_columns[1]:
        with st.container(border=True):
            st.caption("INTERVALO DE MUESTREO")
            st.write("Un intervalo menor revisa más fotogramas y puede captar apariciones breves; uno mayor acelera el análisis, pero puede omitirlas o aproximar peor su duración.")

    st.subheader("Evaluación y límites")
    with st.container(border=True):
        st.write(
            "Una evaluación fiable debe separar vídeos, campañas o fuentes antes de entrenar, reservar un test independiente y no usarlo para ajustar el modelo. "
            "El piloto Eggo documentado se dividió por imagen y no garantiza independencia de fuente; su test ya se usó para diagnóstico y no debe emplearse para seleccionar otro modelo."
        )
        st.write(
            "La iluminación, el desenfoque, la escala, las oclusiones, el texto, los fondos y los encuadres cinematográficos pueden causar falsos positivos o falsos negativos. "
            "Los resultados requieren revisión humana, especialmente en los modos experimentales."
        )
        st.caption("No se muestran métricas de Coca-Cola: no hay una ejecución de evaluación independiente documentada en este repositorio.")


def render_models_page() -> None:
    render_cinematic_header(
        st,
        "Modelos e IA",
        "Conoce qué detector se ejecuta, qué puede medir y qué límites deben guiar la interpretación de cada escena.",
        str(FAVICON_PATH),
        eyebrow="ESCENIQ · METODOLOGÍA Y TRANSPARENCIA",
        asset_width=142,
    )
    st.caption("MODOS DE ANÁLISIS DISPONIBLES")
    render_information_cards(
        st,
        MODEL_INFORMATION_CARDS,
    )
    render_models_methodology()


def render_page(page_name: str) -> None:
    pages = {
        "Inicio": render_home_page,
        "Analizar vídeo": render_analysis_page,
        "Resultados": render_results_page,
        "Biblioteca": render_library_page,
        "Informes": lambda: render_unavailable_page("Informes"),
        "Modelos e IA": render_models_page,
        "Configuración": lambda: render_unavailable_page("Configuración"),
    }
    pages[page_name]()


def render_sidebar_navigation() -> str:
    """Renderiza una navegación estable, con nombres internos independientes de su iconografía."""
    st.sidebar.image(str(SIDEBAR_LOGO_PATH), use_container_width=True)
    st.sidebar.caption("Cada aparición cuenta")
    st.sidebar.divider()
    return st.sidebar.radio(
        "Navegación",
        NAVIGATION_PAGES,
        format_func=lambda page: NAVIGATION_LABELS[page],
        key="navigation_page",
    )


def main() -> None:
    st.set_page_config(page_title="ESCENIQ", page_icon=str(FAVICON_PATH), layout="wide")
    apply_brand_styles(st)
    page_name = render_sidebar_navigation()
    render_page(page_name)


if __name__ == "__main__":
    main()
