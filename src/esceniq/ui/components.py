"""Primitivas visuales seguras para la interfaz Streamlit de ESCENIQ."""
from __future__ import annotations

from base64 import b64encode
from collections.abc import Sequence
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any

from esceniq.analytics.timeline import AppearanceInterval


THEME_DARK = "dark"
THEME_LIGHT = "light"
THEMES = (THEME_DARK, THEME_LIGHT)

_THEME_VARIABLES = {
    THEME_DARK: """
:root {
  --esceniq-background: #09131c;
  --esceniq-surface: #101a24;
  --esceniq-surface-strong: #132230;
  --esceniq-sidebar: #0d1b26;
  --esceniq-border: #284052;
  --esceniq-hover: #183041;
  --esceniq-active: #1a4850;
  --esceniq-text: #edf7f8;
  --esceniq-muted: #a9c1c8;
  --esceniq-input: #0d1b26;
  --esceniq-hero-base: #07141d;
  --esceniq-hero-veil: #09202c;
  --esceniq-card-start: rgba(16, 37, 49, .98);
  --esceniq-card-end: rgba(8, 22, 31, .98);
  --esceniq-card-hover-start: rgba(21, 60, 70, .98);
  --esceniq-card-hover-end: rgba(10, 29, 38, .98);
  --esceniq-turquoise: #42d8d2;
  --esceniq-lime: #bef264;
  --esceniq-coral: #ff8967;
  --esceniq-selected-text: #bef264;
  --esceniq-sidebar-text: #edf7f8;
  --esceniq-sidebar-caption: #a9c1c8;
  --esceniq-sidebar-disabled: #a9c1c8;
}
""",
    THEME_LIGHT: """
:root {
  --esceniq-background: #edf5f5;
  --esceniq-surface: #ffffff;
  --esceniq-surface-strong: #e2eff0;
  --esceniq-sidebar: #e5f1f2;
  --esceniq-border: #91b4ba;
  --esceniq-hover: #d3e8e8;
  --esceniq-active: #b9dddd;
  --esceniq-text: #102a33;
  --esceniq-muted: #46636c;
  --esceniq-input: #ffffff;
  --esceniq-hero-base: #07141d;
  --esceniq-hero-veil: #09202c;
  --esceniq-card-start: rgba(255, 255, 255, .98);
  --esceniq-card-end: rgba(230, 242, 242, .98);
  --esceniq-card-hover-start: rgba(246, 255, 255, .98);
  --esceniq-card-hover-end: rgba(211, 238, 237, .98);
  --esceniq-turquoise: #087f83;
  --esceniq-lime: #597b00;
  --esceniq-coral: #c24d35;
  --esceniq-selected-text: #087f83;
  --esceniq-sidebar-text: #102a33;
  --esceniq-sidebar-caption: #294850;
  --esceniq-sidebar-disabled: #4d6268;
}
.st-key-theme_toggle_button button,
.st-key-theme_toggle_button button * { color: #ffffff !important; }
""",
}


_BRAND_STYLES = """
<style>
/* ESCENIQ_THEME_VARIABLES */
.stApp, [data-testid="stAppViewContainer"] { background: var(--esceniq-background); color: var(--esceniq-text); }
[data-testid="stHeader"] { background: var(--esceniq-background) !important; }
[data-testid="stHeader"] button,
[data-testid="stHeader"] button * { background: transparent; color: var(--esceniq-text) !important; }
[data-testid="stHeader"] button:hover { background: var(--esceniq-hover) !important; }
[data-testid="stSidebar"] { background: var(--esceniq-sidebar); border-right: 1px solid var(--esceniq-border); }
[data-testid="stSidebar"] [data-testid="stImage"] { margin: .25rem .2rem .7rem; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] label,
[data-testid="stSidebar"] [data-testid="stSidebarContent"] label * { color: var(--esceniq-sidebar-text) !important; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stSidebarContent"] [data-testid="stCaptionContainer"] * { color: var(--esceniq-sidebar-caption) !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 9px; padding: .38rem .45rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:disabled),
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:disabled) *,
[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-disabled="true"],
[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-disabled="true"] * { color: var(--esceniq-sidebar-disabled) !important; opacity: 1; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: var(--esceniq-hover); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background: var(--esceniq-active); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p,
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span,
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * { color: var(--esceniq-selected-text) !important; }
.esceniq-home-hero { position: relative; min-height: 495px; overflow: hidden; border: 1px solid rgba(66, 216, 210, .42); border-radius: 18px; background: var(--esceniq-hero-base); box-shadow: 0 26px 64px rgba(0, 0, 0, .34), inset 0 1px 0 rgba(255, 255, 255, .05); animation: esceniq-reveal .48s ease both; }
.esceniq-home-hero__photo { position: absolute; inset: 0 0 0 37%; display: grid; place-items: center; background: radial-gradient(circle at 45% 45%, rgba(66, 216, 210, .19), transparent 48%); }
.esceniq-home-hero__photo img { display: block; width: 100%; height: 100%; object-fit: contain; object-position: center; filter: saturate(1.1) contrast(1.05); }
.esceniq-home-hero__veil { position: absolute; inset: 0; background: linear-gradient(90deg, var(--esceniq-hero-base) 0%, var(--esceniq-hero-veil) 34%, rgba(7, 20, 29, .82) 46%, rgba(7, 20, 29, .08) 70%, rgba(7, 20, 29, .12) 100%), linear-gradient(0deg, rgba(7, 20, 29, .55), transparent 35%); pointer-events: none; }
.esceniq-home-hero__content { position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: center; width: min(54%, 620px); min-height: 420px; padding: 2.6rem clamp(1.5rem, 4vw, 4.5rem); }
.esceniq-home-hero__eyebrow { margin: 0 0 .9rem; color: #69f5f0; font-size: .73rem; font-weight: 800; letter-spacing: .16em; }
.esceniq-home-hero h1 { max-width: 560px; margin: 0; color: #f5ffff; font-size: clamp(2.4rem, 4.45vw, 4.8rem); line-height: .96; letter-spacing: -.06em; text-wrap: balance; text-shadow: 0 8px 28px rgba(0, 0, 0, .38); }
.esceniq-home-hero h1 em { color: var(--esceniq-lime); font-style: normal; }
.esceniq-home-hero__copy { max-width: 500px; margin: 1.15rem 0 0; color: #c8d9dd; font-size: 1.05rem; line-height: 1.55; }
.esceniq-home-hero__tagline { display: flex; align-items: center; gap: .55rem; margin: 1.2rem 0 0; color: #78e9e6; font-size: .75rem; font-weight: 700; letter-spacing: .12em; }
.esceniq-home-hero__tagline::before { content: ""; width: 58px; height: 3px; background: linear-gradient(90deg, var(--esceniq-turquoise), var(--esceniq-lime), transparent); box-shadow: 0 0 12px var(--esceniq-turquoise); }
.esceniq-home-hero__frame { position: absolute; z-index: 3; pointer-events: none; border-color: rgba(66, 216, 210, .75); border-style: solid; filter: drop-shadow(0 0 8px rgba(66, 216, 210, .48)); }
.esceniq-home-hero__frame--top { top: 27px; right: 27px; width: 98px; height: 98px; border-width: 2px 2px 0 0; }
.esceniq-home-hero__frame--bottom { right: 27px; bottom: 27px; width: 98px; height: 98px; border-width: 0 2px 2px 0; }
.esceniq-home-hero__scan { position: absolute; z-index: 2; top: 12%; right: 4%; width: 56%; height: 1px; pointer-events: none; background: linear-gradient(90deg, transparent, var(--esceniq-turquoise), var(--esceniq-lime), transparent); box-shadow: 0 0 18px var(--esceniq-turquoise); animation: esceniq-home-scan 5.5s ease-in-out infinite; }
.st-key-home-real-cta { position: relative; z-index: 3; width: fit-content; margin-top: -6.8rem; margin-left: clamp(1.5rem, 4vw, 4.5rem); }
.st-key-home-real-cta button { min-height: 48px; padding-inline: 1.55rem; box-shadow: 0 12px 30px rgba(66, 216, 210, .27); }
.esceniq-capabilities { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; margin: 1.2rem 0; overflow: hidden; border: 1px solid rgba(66, 216, 210, .25); border-radius: 15px; background: rgba(66, 216, 210, .18); box-shadow: 0 16px 38px rgba(0, 0, 0, .16); }
.esceniq-capability { min-height: 154px; padding: 1.2rem 1.1rem; background: linear-gradient(145deg, var(--esceniq-card-start), var(--esceniq-card-end)); transition: transform .22s ease, background .22s ease; }
.esceniq-capability:hover { transform: translateY(-3px); background: linear-gradient(145deg, var(--esceniq-card-hover-start), var(--esceniq-card-hover-end)); }
.esceniq-capability__icon { display: grid; width: 39px; height: 39px; place-items: center; margin-bottom: .7rem; border: 1px solid currentColor; border-radius: 11px; color: var(--esceniq-turquoise); font-size: 1.35rem; box-shadow: inset 0 0 18px rgba(66, 216, 210, .13), 0 0 16px rgba(66, 216, 210, .12); }
.esceniq-capability:nth-child(2) .esceniq-capability__icon { color: var(--esceniq-lime); }
.esceniq-capability:nth-child(3) .esceniq-capability__icon { color: var(--esceniq-coral); }
.esceniq-capability h3 { margin: 0; color: var(--esceniq-text); font-size: 1rem; }
.esceniq-capability p { margin: .32rem 0 0; color: var(--esceniq-muted); font-size: .82rem; line-height: 1.35; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--esceniq-border); box-shadow: 0 14px 35px rgba(0, 0, 0, .16); transition: border-color .22s ease, box-shadow .22s ease, transform .22s ease; animation: esceniq-reveal .42s ease both; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: #3b8490; box-shadow: 0 16px 40px rgba(66, 216, 210, .10); transform: translateY(-2px); }
[data-testid="stMetric"] { background: var(--esceniq-surface); border: 1px solid var(--esceniq-border); border-radius: 12px; padding: .8rem; }
[data-testid="stMetricLabel"] { color: var(--esceniq-muted); }
[data-testid="stMetricValue"] { color: var(--esceniq-turquoise); }
[data-testid="stFileUploader"] { border: 1px dashed var(--esceniq-border); border-radius: 12px; padding: .6rem; background: linear-gradient(105deg, var(--esceniq-input) 35%, var(--esceniq-surface-strong) 50%, var(--esceniq-input) 65%); background-size: 220% 100%; animation: esceniq-scan 4.5s ease-in-out infinite; }
[data-testid="stVideo"] { border: 1px solid #3b8490; border-radius: 12px; overflow: hidden; box-shadow: 0 0 0 1px rgba(190, 242, 100, .12), 0 16px 35px rgba(0, 0, 0, .25); }
[data-testid="stDataFrame"] { border: 1px solid var(--esceniq-border); border-radius: 12px; overflow: hidden; }
[data-testid="stAlert"] { border-left: 3px solid var(--esceniq-coral); }
button[kind="primary"] { background: var(--esceniq-turquoise); color: #06232a; border: 0; font-weight: 700; }
button { transition: transform .18s ease, box-shadow .18s ease, background-color .18s ease; }
button:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(66, 216, 210, .16); }
button[kind="primary"]:hover { background: var(--esceniq-lime); color: #152400; }
.stCaption { color: var(--esceniq-muted); }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-baseweb="select"] > div, [data-testid="stTextArea"] textarea { background: var(--esceniq-input) !important; color: var(--esceniq-text) !important; border-color: var(--esceniq-border) !important; }
[data-testid="stDataFrame"], [data-testid="stTable"], [data-testid="stDataEditor"] { background: var(--esceniq-surface); color: var(--esceniq-text); }
[data-testid="stDataFrame"] * { color: var(--esceniq-text); }
[data-testid="stAlert"] { background: var(--esceniq-surface-strong); color: var(--esceniq-text); }
.esceniq-timeline { margin: .75rem 0 1.35rem; padding: 1.1rem; border: 1px solid var(--esceniq-border); border-radius: 14px; background: linear-gradient(135deg, var(--esceniq-surface), var(--esceniq-surface-strong)); box-shadow: inset 0 1px 0 rgba(255, 255, 255, .08); }
.esceniq-timeline__legend { display: flex; flex-wrap: wrap; gap: .4rem .8rem; margin: 0 0 1rem; color: var(--esceniq-muted); font-size: .78rem; }
.esceniq-timeline__legend span { display: inline-flex; align-items: center; gap: .35rem; }
.esceniq-timeline__dot { width: .58rem; height: .58rem; border-radius: 50%; background: currentColor; box-shadow: 0 0 10px currentColor; }
.esceniq-timeline__row { display: grid; grid-template-columns: minmax(92px, 150px) 1fr; gap: .7rem; align-items: start; padding: .6rem 0; border-top: 1px solid var(--esceniq-border); }
.esceniq-timeline__row:first-of-type { border-top: 0; }
.esceniq-timeline__brand { padding-top: .18rem; color: var(--esceniq-text); font-size: .82rem; font-weight: 750; }
.esceniq-timeline__track { position: relative; min-height: 2.2rem; overflow: hidden; border: 1px solid var(--esceniq-border); border-radius: 9px; background: repeating-linear-gradient(90deg, transparent 0, transparent calc(25% - 1px), var(--esceniq-border) calc(25% - 1px), var(--esceniq-border) 25%); }
.esceniq-timeline__appearance { position: absolute; top: .48rem; min-width: 4px; height: 1.16rem; border-radius: 5px; background: currentColor; box-shadow: 0 0 12px currentColor; opacity: .88; }
.esceniq-timeline__times { display: flex; flex-wrap: wrap; gap: .28rem .5rem; margin-top: .35rem; color: var(--esceniq-muted); font-size: .73rem; }
.esceniq-timeline__times code { padding: .14rem .32rem; border-radius: 4px; background: var(--esceniq-background); color: inherit; }
.esceniq-timeline__tone-0 { color: var(--esceniq-turquoise); }
.esceniq-timeline__tone-1 { color: var(--esceniq-lime); }
.esceniq-timeline__tone-2 { color: var(--esceniq-coral); }
.esceniq-timeline__tone-3 { color: #8faeff; }
.esceniq-timeline__tone-4 { color: #c5a7ff; }
@keyframes esceniq-reveal {
  from { opacity: 0; transform: translateY(7px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes esceniq-scan {
  0%, 100% { background-position: 100% 0; }
  50% { background-position: 0 0; }
}
@keyframes esceniq-home-scan {
  0%, 100% { transform: translateY(0); opacity: .35; }
  50% { transform: translateY(270px); opacity: .9; }
}
@keyframes esceniq-home-scan {
  0%, 100% { transform: translateY(0); opacity: .35; }
  50% { transform: translateY(270px); opacity: .9; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: .01ms !important; }
}
@media (max-width: 760px) {
  .esceniq-home-hero { min-height: 650px; }
  .esceniq-home-hero__photo { inset: 38% 0 0; }
  .esceniq-home-hero__veil { background: linear-gradient(180deg, #07141d 0%, rgba(7, 20, 29, .9) 43%, rgba(7, 20, 29, .18) 78%), linear-gradient(0deg, rgba(7, 20, 29, .52), transparent 30%); }
  .esceniq-home-hero__content { width: auto; min-height: 0; padding: 2rem 1.4rem; }
  .st-key-home-real-cta { margin-top: -5.35rem; margin-left: 1.4rem; }
  .esceniq-home-hero__frame { display: none; }
  .esceniq-capabilities { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .esceniq-timeline__row { grid-template-columns: 1fr; gap: .25rem; }
}
</style>
"""


def normalize_theme(value: object) -> str:
    """Normaliza una preferencia externa sin aceptar valores arbitrarios en CSS."""
    return str(value).casefold() if str(value).casefold() in THEMES else THEME_DARK


def resolve_theme(streamlit: Any) -> str:
    """Recupera el tema de sesión o de la URL para conservarlo tras una recarga."""
    session_state = streamlit.session_state
    query_params = getattr(streamlit, "query_params", None)
    requested_theme = None
    if query_params is not None:
        try:
            requested_theme = query_params.get("theme")
        except (AttributeError, TypeError):
            requested_theme = None
    if isinstance(requested_theme, (tuple, list)):
        requested_theme = requested_theme[-1] if requested_theme else None
    if "esceniq_theme" not in session_state:
        session_state["esceniq_theme"] = normalize_theme(requested_theme)
    theme = normalize_theme(session_state["esceniq_theme"])
    session_state["esceniq_theme"] = theme
    return theme


def build_brand_styles(theme: str) -> str:
    """Compone una única hoja CSS con variables de color para el tema solicitado."""
    return _BRAND_STYLES.replace("/* ESCENIQ_THEME_VARIABLES */", _THEME_VARIABLES[normalize_theme(theme)])


def apply_brand_styles(streamlit: Any, theme: str = THEME_DARK) -> None:
    """Aplica CSS estático tematizado, sin scripts ni contenido de usuario."""
    render_html = getattr(streamlit, "html", None)
    if render_html is not None:
        render_html(build_brand_styles(theme))


@lru_cache(maxsize=4)
def _image_data_url(image_path: str) -> str:
    image = Path(image_path)
    encoded = b64encode(image.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_home_cinematic_hero(streamlit: Any, image_path: str) -> None:
    """Renderiza una escena de portada estática; el CTA continúa siendo un widget nativo."""
    data_url = _image_data_url(image_path)
    streamlit.html(
        f'''<section class="esceniq-home-hero" aria-label="ESCENIQ, análisis audiovisual con inteligencia artificial">
  <div class="esceniq-home-hero__photo"><img src="{data_url}" alt="Escena cinematográfica de análisis audiovisual" /></div>
  <div class="esceniq-home-hero__veil"></div>
  <div class="esceniq-home-hero__frame esceniq-home-hero__frame--top"></div>
  <div class="esceniq-home-hero__frame esceniq-home-hero__frame--bottom"></div>
  <div class="esceniq-home-hero__scan"></div>
  <div class="esceniq-home-hero__content">
    <p class="esceniq-home-hero__eyebrow">ESCENIQ · COMPUTER VISION</p>
    <h1>Convierte cada escena en <em>datos de valor</em></h1>
    <p class="esceniq-home-hero__copy">Analiza apariciones visuales de marca en vídeo y conserva evidencias revisables para interpretar cada resultado.</p>
    <p class="esceniq-home-hero__tagline">CADA APARICIÓN CUENTA</p>
  </div>
</section>'''
    )


def render_capability_showcase(streamlit: Any) -> None:
    """Presenta capacidades del producto sin declarar resultados ni métricas."""
    streamlit.html(
        '''<section class="esceniq-capabilities" aria-label="Capacidades de ESCENIQ">
  <article class="esceniq-capability"><div class="esceniq-capability__icon">▣</div><h3>Carga local</h3><p>Valida el vídeo y preserva su contexto.</p></article>
  <article class="esceniq-capability"><div class="esceniq-capability__icon">◎</div><h3>Detecta marcas</h3><p>Procesa fotogramas con el modo elegido.</p></article>
  <article class="esceniq-capability"><div class="esceniq-capability__icon">↗</div><h3>Analiza presencia</h3><p>Agrupa muestras sin duplicar cajas.</p></article>
  <article class="esceniq-capability"><div class="esceniq-capability__icon">◈</div><h3>Revisa escenas</h3><p>Contrasta detecciones reales visualmente.</p></article>
</section>'''
    )


def render_page_intro(streamlit: Any, title: str, description: str, *, eyebrow: str = "ESCENIQ") -> None:
    """Muestra una cabecera de página consistente y de jerarquía breve."""
    streamlit.caption(eyebrow.upper())
    streamlit.title(title)
    streamlit.write(description)


def render_cinematic_header(
    streamlit: Any,
    title: str,
    description: str,
    asset_path: str,
    *,
    eyebrow: str,
    asset_width: int | None = None,
) -> None:
    """Compone una cabecera editorial con un recurso local y texto de contexto real."""
    with streamlit.container(border=True):
        copy, visual = streamlit.columns((1.2, 0.8))
        with copy:
            streamlit.caption(eyebrow.upper())
            streamlit.title(title)
            streamlit.write(description)
        with visual:
            image_options = {"use_container_width": asset_width is None}
            if asset_width is not None:
                image_options["width"] = asset_width
            streamlit.image(asset_path, **image_options)


def render_metric_cards(streamlit: Any, metrics: Sequence[tuple[str, str | int | float]]) -> None:
    """Presenta métricas reales en una cuadrícula responsive de Streamlit."""
    for column, (label, value) in zip(streamlit.columns(len(metrics)), metrics, strict=True):
        column.metric(label, value)


def _format_timeline_seconds(seconds: float) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remaining_seconds:05.2f}"


def render_brand_timeline(
    streamlit: Any,
    intervals: Sequence[AppearanceInterval],
    *,
    duration_seconds: float,
    sample_interval_seconds: float,
) -> None:
    """Renderiza tramos reales de exposición estimada sin JavaScript ni datos ficticios."""
    if not intervals:
        streamlit.info("No hay detecciones de marca con información temporal para mostrar en la línea temporal.")
        return
    grouped: dict[str, list[AppearanceInterval]] = {}
    for interval in intervals:
        grouped.setdefault(interval.brand_name, []).append(interval)
    rows: list[str] = []
    legend: list[str] = []
    for index, (brand_name, brand_intervals) in enumerate(grouped.items()):
        tone = index % 5
        safe_brand = escape(brand_name)
        legend.append(
            f'<span class="esceniq-timeline__tone-{tone}"><i class="esceniq-timeline__dot"></i>{safe_brand}</span>'
        )
        markers: list[str] = []
        labels: list[str] = []
        for interval in brand_intervals:
            left = max(0.0, min(100.0, 100 * interval.start_seconds / duration_seconds))
            width = max(0.15, min(100.0 - left, 100 * interval.estimated_seconds / duration_seconds))
            start = _format_timeline_seconds(interval.start_seconds)
            end = _format_timeline_seconds(interval.end_seconds)
            description = f"{safe_brand}: {start} a {end}; {interval.positive_sample_count} muestra(s) positiva(s)"
            markers.append(
                f'<span class="esceniq-timeline__appearance esceniq-timeline__tone-{tone}" '
                f'style="left:{left:.4f}%;width:{width:.4f}%" title="{description}"></span>'
            )
            labels.append(
                f"<code>{start} → {end} · {interval.estimated_seconds:.2f} s estimados</code>"
            )
        rows.append(
            f'<div class="esceniq-timeline__row"><div class="esceniq-timeline__brand esceniq-timeline__tone-{tone}">{safe_brand}</div>'
            f'<div><div class="esceniq-timeline__track" aria-label="Tramos estimados de {safe_brand}">{"".join(markers)}</div>'
            f'<div class="esceniq-timeline__times">{"".join(labels)}</div></div></div>'
        )
    streamlit.subheader("Línea temporal de apariciones")
    streamlit.caption(
        f"Tramos estimados a partir de muestras cada {sample_interval_seconds:g} s. "
        "No confirman presencia continua entre muestras ni modifican la exposición calculada."
    )
    streamlit.html(
        '<section class="esceniq-timeline" aria-label="Línea temporal estimada de marcas">'
        f'<div class="esceniq-timeline__legend">{"".join(legend)}</div>{"".join(rows)}</section>'
    )


def render_information_cards(
    streamlit: Any, cards: Sequence[tuple[str, str, str, str]], *, columns: int = 2
) -> None:
    """Presenta información de producto en tarjetas, sin atribuir datos no verificables."""
    for index in range(0, len(cards), columns):
        for column, (eyebrow, title, description, limitation) in zip(
            streamlit.columns(columns), cards[index : index + columns], strict=False
        ):
            with column.container(border=True):
                streamlit.caption(eyebrow.upper())
                streamlit.subheader(title)
                streamlit.write(description)
                streamlit.caption(f"Límite: {limitation}")


def render_empty_state(streamlit: Any, title: str, description: str, *, detail: str | None = None) -> None:
    """Muestra un estado vacío o pendiente con jerarquía visual y mensaje accionable."""
    with streamlit.container(border=True):
        streamlit.caption("ESCENIQ · ESTADO")
        streamlit.subheader(title)
        streamlit.write(description)
        if detail:
            streamlit.caption(detail)


def render_workflow(streamlit: Any) -> None:
    """Explica el flujo real del producto sin introducir datos simulados."""
    steps = (
        ("01", "Carga el vídeo", "Valida un MP4 local y consulta sus metadatos."),
        ("02", "Detecta marcas", "YOLO analiza muestras con el modelo y umbral elegidos."),
        ("03", "Analiza exposición", "Revisa métricas y evidencias de las detecciones reales."),
    )
    for column, (number, title, description) in zip(streamlit.columns(3), steps, strict=True):
        with column.container(border=True):
            streamlit.caption(number)
            streamlit.subheader(title)
            streamlit.write(description)
