"""Componentes de presentación reutilizables de ESCENIQ."""

from .components import (
    THEME_DARK,
    THEME_LIGHT,
    apply_brand_styles,
    build_brand_styles,
    normalize_theme,
    render_capability_showcase,
    render_cinematic_header,
    render_empty_state,
    render_home_cinematic_hero,
    render_information_cards,
    render_metric_cards,
    render_page_intro,
    render_workflow,
    resolve_theme,
)

__all__ = [
    "apply_brand_styles",
    "build_brand_styles",
    "normalize_theme",
    "render_capability_showcase",
    "render_cinematic_header",
    "render_empty_state",
    "render_home_cinematic_hero",
    "render_information_cards",
    "render_metric_cards",
    "render_page_intro",
    "render_workflow",
    "resolve_theme",
    "THEME_DARK",
    "THEME_LIGHT",
]
