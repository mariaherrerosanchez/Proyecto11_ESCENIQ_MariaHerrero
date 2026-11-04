import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esceniq.ui import build_brand_styles, normalize_theme


class ThemeStyleTests(unittest.TestCase):
    def test_dark_and_light_styles_define_contrasting_palette_without_scripts(self):
        dark_styles = build_brand_styles("dark")
        light_styles = build_brand_styles("light")

        self.assertIn("--esceniq-background: #09131c", dark_styles)
        self.assertIn("--esceniq-background: #edf5f5", light_styles)
        self.assertIn("--esceniq-text: #102a33", light_styles)
        self.assertIn("--esceniq-selected-text: #087f83", light_styles)
        self.assertIn("--esceniq-sidebar-text: #102a33", light_styles)
        self.assertIn("--esceniq-sidebar-disabled: #4d6268", light_styles)
        self.assertIn("--esceniq-turquoise", dark_styles)
        self.assertIn("--esceniq-lime", light_styles)
        self.assertIn(
            '[data-testid="stSidebar"] [data-testid="stSidebarContent"] label * { color: var(--esceniq-sidebar-text) !important; }',
            light_styles,
        )
        self.assertIn(
            '[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background: var(--esceniq-active); }',
            light_styles,
        )
        self.assertIn("label[aria-disabled=", light_styles)
        self.assertIn("@media (max-width: 760px)", light_styles)
        self.assertNotIn("st-key-theme-toggle", light_styles)
        self.assertNotIn("theme-toggle-symbol", light_styles)
        self.assertNotIn("color: transparent", light_styles)
        self.assertIn(".st-key-theme_toggle_button button", light_styles)
        self.assertIn(".st-key-theme_toggle_button button * { color: #ffffff !important; }", light_styles)
        self.assertNotIn(".st-key-theme_toggle_button button", dark_styles)
        self.assertIn('[data-testid="stHeader"] { background: var(--esceniq-background) !important; }', light_styles)
        self.assertIn('[data-testid="stHeader"] button *', light_styles)
        self.assertIn("prefers-reduced-motion", dark_styles)
        self.assertIn(".esceniq-timeline", light_styles)
        self.assertIn(".esceniq-timeline__tone-0", dark_styles)
        self.assertNotIn("<script", light_styles.lower())

    def test_invalid_theme_falls_back_to_dark(self):
        self.assertEqual(normalize_theme("light"), "light")
        self.assertEqual(normalize_theme("unexpected"), "dark")


if __name__ == "__main__":
    unittest.main()
