import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

import app


class FakeSidebar:
    def __init__(self, selected_page):
        self.selected_page = selected_page
        self.calls = []

    def title(self, *_args, **_kwargs):
        pass

    def image(self, *_args, **_kwargs):
        pass

    def caption(self, *_args, **_kwargs):
        pass

    def divider(self):
        pass

    def radio(self, label, options, *, format_func, key):
        self.calls.append((label, options, format_func, key))
        return self.selected_page


class FakeColumn:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def image(self, *_args, **_kwargs):
        pass

    def caption(self, *_args, **_kwargs):
        pass

    def subheader(self, *_args, **_kwargs):
        pass

    def title(self, *_args, **_kwargs):
        pass

    def write(self, *_args, **_kwargs):
        pass

    def button(self, *_args, **_kwargs):
        return False


class FakeStreamlit:
    def __init__(self, selected_page="Inicio"):
        self.session_state = {}
        self.sidebar = FakeSidebar(selected_page)
        self.infos = []
        self.html_fragments = []
        self.page_config = None
        self.container_calls = []

    def set_page_config(self, **kwargs):
        self.page_config = kwargs

    def html(self, value, *_args, **_kwargs):
        self.html_fragments.append(value)

    def title(self, *_args, **_kwargs):
        pass

    def caption(self, *_args, **_kwargs):
        pass

    def header(self, *_args, **_kwargs):
        pass

    def subheader(self, *_args, **_kwargs):
        pass

    def write(self, *_args, **_kwargs):
        pass

    def markdown(self, *_args, **_kwargs):
        pass

    def image(self, *_args, **_kwargs):
        pass

    def button(self, *_args, **_kwargs):
        return False

    def divider(self):
        pass

    def container(self, *_args, **_kwargs):
        self.container_calls.append(_kwargs)
        return nullcontext()

    def columns(self, count_or_widths, **_kwargs):
        count = count_or_widths if isinstance(count_or_widths, int) else len(count_or_widths)
        return [FakeColumn() for _ in range(count)]

    def info(self, value, *_args, **_kwargs):
        self.infos.append(value)

    def success(self, *_args, **_kwargs):
        pass


class NavigationTests(unittest.TestCase):
    def test_navigation_exposes_the_seven_expected_sections(self):
        self.assertEqual(
            app.NAVIGATION_PAGES,
            (
                "Inicio",
                "Analizar vídeo",
                "Resultados",
                "Biblioteca",
                "Informes",
                "Modelos e IA",
                "Configuración",
            ),
        )

    def test_main_uses_sidebar_navigation_and_renders_the_selected_page(self):
        fake_streamlit = FakeStreamlit(selected_page="Resultados")

        with patch.object(app, "st", fake_streamlit), patch.object(app, "render_page") as render_page:
            app.main()

        self.assertEqual(len(fake_streamlit.sidebar.calls), 1)
        label, options, format_func, key = fake_streamlit.sidebar.calls[0]
        self.assertEqual((label, options, key), ("Navegación", app.NAVIGATION_PAGES, "navigation_page"))
        self.assertEqual(format_func("Biblioteca"), "▣  Biblioteca")
        self.assertTrue(fake_streamlit.html_fragments)
        self.assertIn("<style>", fake_streamlit.html_fragments[0])
        self.assertNotIn("<script", fake_streamlit.html_fragments[0].lower())
        self.assertIn("prefers-reduced-motion", fake_streamlit.html_fragments[0])
        self.assertEqual(fake_streamlit.page_config["page_icon"], str(app.FAVICON_PATH))
        render_page.assert_called_once_with("Resultados")

    def test_visual_resources_exist_and_are_used_by_the_navigation(self):
        self.assertTrue(app.SIDEBAR_LOGO_PATH.is_file())
        self.assertTrue(app.FAVICON_PATH.is_file())
        self.assertTrue(app.HERO_IMAGE_PATH.is_file())

    def test_home_empty_state_does_not_render_metrics(self):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit), patch.object(app, "render_metric_cards") as metric_cards:
            app.render_home_page()

        metric_cards.assert_not_called()
        self.assertIn({"key": "home-real-cta"}, fake_streamlit.container_calls)
        self.assertTrue(any("esceniq-home-hero" in fragment for fragment in fake_streamlit.html_fragments))
        self.assertTrue(any("esceniq-capabilities" in fragment for fragment in fake_streamlit.html_fragments))

    def test_navigation_labels_include_icons_and_identify_only_pending_sections(self):
        self.assertEqual(set(app.NAVIGATION_LABELS), set(app.NAVIGATION_PAGES))
        self.assertNotIn("Próximamente", app.NAVIGATION_LABELS["Biblioteca"])
        self.assertIn("Próximamente", app.NAVIGATION_LABELS["Informes"])
        self.assertIn("Próximamente", app.NAVIGATION_LABELS["Configuración"])

    def test_results_page_explains_when_no_analysis_exists(self):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit), patch.object(app, "render_inference_result") as render_result:
            app.render_results_page()

        render_result.assert_not_called()
        self.assertEqual(
            fake_streamlit.infos,
            ["Todavía no hay un análisis disponible. Carga un vídeo y ejecuta la inferencia desde Analizar vídeo."],
        )

    def test_results_page_reuses_the_analysis_in_session_state(self):
        fake_streamlit = FakeStreamlit()
        previous_result = object()
        fake_streamlit.session_state["inference_result"] = previous_result

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "render_inference_result", return_value=None) as render_result,
            patch.object(app, "render_csv_download") as render_csv_download,
        ):
            app.render_results_page()

        render_result.assert_called_once_with(previous_result)
        render_csv_download.assert_not_called()
        self.assertIs(fake_streamlit.session_state["inference_result"], previous_result)

    def test_results_page_hides_csv_download_when_exposure_has_no_rows(self):
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state["inference_result"] = object()

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "render_inference_result", return_value=SimpleNamespace(metrics=())),
            patch.object(app, "render_csv_download") as render_csv_download,
        ):
            app.render_results_page()

        render_csv_download.assert_not_called()

    def test_unavailable_pages_identify_their_pending_status(self):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            app.render_unavailable_page("Biblioteca", "Requiere implementar US-010.")

        self.assertEqual(fake_streamlit.infos, ["No disponible todavía. Requiere implementar US-010."])

    def test_models_page_describes_the_four_modes_without_claiming_metrics(self):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit), patch.object(app, "render_information_cards") as cards:
            app.render_models_page()

        displayed_cards = cards.call_args.args[1]
        self.assertEqual([card[1] for card in displayed_cards], [
            "ESCENIQ oficial",
            "Eggo experimental",
            "Coca-Cola experimental",
            "Prueba técnica",
        ])
        self.assertIn("no afirma", displayed_cards[0][3])

    def test_router_maps_every_page_to_a_working_renderer(self):
        with (
            patch.object(app, "render_home_page") as home,
            patch.object(app, "render_analysis_page") as analysis,
            patch.object(app, "render_results_page") as results,
            patch.object(app, "render_library_page") as library,
            patch.object(app, "render_unavailable_page") as unavailable,
            patch.object(app, "render_models_page") as models,
        ):
            for page_name in app.NAVIGATION_PAGES:
                with self.subTest(page_name=page_name):
                    app.render_page(page_name)

        home.assert_called_once()
        analysis.assert_called_once()
        results.assert_called_once()
        library.assert_called_once()
        self.assertEqual(unavailable.call_count, 2)
        models.assert_called_once()


if __name__ == "__main__":
    unittest.main()
