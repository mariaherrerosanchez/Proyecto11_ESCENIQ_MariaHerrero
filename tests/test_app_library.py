from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import app

from esceniq.storage import AnalysisListItem, StorageError


class FakeStreamlit:
    def __init__(self, selected_id: str | None = None):
        self.selected_id = selected_id
        self.session_state = {"inference_result": object()}
        self.dataframes = []
        self.errors = []
        self.warnings = []
        self.infos = []
        self.downloads = []

    def dataframe(self, data, *_args, **_kwargs):
        self.dataframes.append(data)

    def selectbox(self, _label, options, **_kwargs):
        return self.selected_id or options[0]

    def error(self, value, *_args, **_kwargs):
        self.errors.append(value)

    def warning(self, value, *_args, **_kwargs):
        self.warnings.append(value)

    def info(self, value, *_args, **_kwargs):
        self.infos.append(value)

    def download_button(self, label, **kwargs):
        self.downloads.append((label, kwargs))

    def caption(self, *_args, **_kwargs):
        pass

    def subheader(self, *_args, **_kwargs):
        pass


class FakeRepository:
    def __init__(self, analyses=(), analysis=None, error=None):
        self.analyses = analyses
        self.analysis = analysis
        self.error = error
        self.selected_id = None

    def list_analyses(self):
        if self.error:
            raise self.error
        return self.analyses

    def get_analysis(self, analysis_id):
        self.selected_id = analysis_id
        if self.error:
            raise self.error
        return self.analysis


class LibraryPageTests(unittest.TestCase):
    def item(self, analysis_id="analysis-1"):
        return AnalysisListItem(
            analysis_id=analysis_id,
            created_at=datetime(2026, 11, 4, 10, 30, tzinfo=timezone.utc),
            video_name="escena.mp4",
            mode="esceniq",
            model_path=r"models\esceniq.pt",
            detection_count=3,
        )

    def test_lists_analysis_and_opens_selected_detail_without_changing_session_result(self):
        item = self.item()
        stored = SimpleNamespace(analysis_id=item.analysis_id)
        repository = FakeRepository((item,), stored)
        fake_streamlit = FakeStreamlit(item.analysis_id)

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "SqliteAnalysisRepository", return_value=repository),
            patch.object(app, "render_cinematic_header"),
            patch.object(app, "render_library_analysis") as render_detail,
        ):
            app.render_library_page()

        self.assertEqual(repository.selected_id, item.analysis_id)
        self.assertEqual(fake_streamlit.dataframes[0][0]["Vídeo"], "escena.mp4")
        self.assertEqual(fake_streamlit.dataframes[0][0]["Estado"], "Completado")
        render_detail.assert_called_once_with(stored)
        self.assertIn("inference_result", fake_streamlit.session_state)

    def test_empty_library_uses_an_explicit_empty_state(self):
        fake_streamlit = FakeStreamlit()

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "SqliteAnalysisRepository", return_value=FakeRepository()),
            patch.object(app, "render_cinematic_header"),
            patch.object(app, "render_empty_state") as render_empty,
        ):
            app.render_library_page()

        self.assertEqual(render_empty.call_args.args[1], "La biblioteca está vacía")

    def test_read_error_is_clear_and_does_not_block_the_session_result(self):
        fake_streamlit = FakeStreamlit()

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "SqliteAnalysisRepository", return_value=FakeRepository(error=StorageError("sin acceso"))),
            patch.object(app, "render_cinematic_header"),
        ):
            app.render_library_page()

        self.assertIn("No se pudo leer la biblioteca local", fake_streamlit.errors[0])
        self.assertIn("inference_result", fake_streamlit.session_state)

    def test_missing_selected_analysis_is_reported_without_inference(self):
        item = self.item()
        fake_streamlit = FakeStreamlit(item.analysis_id)

        with (
            patch.object(app, "st", fake_streamlit),
            patch.object(app, "SqliteAnalysisRepository", return_value=FakeRepository((item,), None)),
            patch.object(app, "render_cinematic_header"),
        ):
            app.render_library_page()

        self.assertIn("ya no está disponible", fake_streamlit.warnings[0])

    def test_historical_analysis_without_evidences_has_a_clear_state(self):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            app.render_stored_evidence_gallery(SimpleNamespace(evidences=()))

        self.assertEqual(
            fake_streamlit.infos,
            ["Este análisis histórico no tiene evidencias visuales guardadas."],
        )

    def test_comparison_requires_two_saved_analyses_without_running_yolo(self):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit), patch.object(app, "analyze_video") as analyze_video:
            app.render_library_comparison(FakeRepository(), (self.item(),))

        self.assertEqual(fake_streamlit.infos, ["Necesitas al menos dos análisis guardados para compararlos."])
        analyze_video.assert_not_called()

    def test_comparison_renders_two_saved_analyses_and_keeps_yolo_unused(self):
        first, second = self.item("analysis-1"), self.item("analysis-2")
        exposure = SimpleNamespace(
            brand_name="Coca-Cola",
            positive_sample_count=2,
            estimated_seconds=2.0,
            percentage_of_video=20.0,
            appearance_count=1,
        )
        stored = {
            first.analysis_id: SimpleNamespace(
                video_name="primero.mp4", mode="esceniq", model_path="models/esceniq.pt",
                confidence_threshold=0.25, sample_interval_seconds=1.0, duration_seconds=10.0,
                exposures=(exposure,),
            ),
            second.analysis_id: SimpleNamespace(
                video_name="segundo.mp4", mode="esceniq", model_path="models/esceniq.pt",
                confidence_threshold=0.25, sample_interval_seconds=1.0, duration_seconds=10.0,
                exposures=(exposure,),
            ),
        }

        class ComparisonRepository(FakeRepository):
            def get_analysis(self, analysis_id):
                return stored[analysis_id]

        fake_streamlit = FakeStreamlit()
        with patch.object(app, "st", fake_streamlit), patch.object(app, "analyze_video") as analyze_video:
            app.render_library_comparison(ComparisonRepository(), (first, second))

        self.assertEqual(len(fake_streamlit.dataframes), 2)
        self.assertEqual(fake_streamlit.dataframes[1][0]["Marca"], "Coca-Cola")
        self.assertEqual(fake_streamlit.dataframes[1][0]["Métrica"], "Apariciones")
        self.assertEqual(fake_streamlit.dataframes[1][0]["Análisis A"], 1)
        self.assertEqual(fake_streamlit.dataframes[1][2]["Métrica"], "Vídeo (%)")
        self.assertEqual(fake_streamlit.dataframes[1][1]["Mayor exposición estimada"], "Igual exposición estimada")
        analyze_video.assert_not_called()

    @patch.object(app, "build_stored_results_csv", return_value=b"csv-guardado")
    def test_saved_analysis_csv_reuses_the_persisted_data(self, build_csv):
        fake_streamlit = FakeStreamlit()
        analysis = SimpleNamespace(analysis_id="analysis-1")

        with patch.object(app, "st", fake_streamlit):
            app.render_stored_csv_download(analysis)

        build_csv.assert_called_once_with(analysis)
        self.assertEqual(fake_streamlit.downloads[0][0], "Descargar CSV")
        self.assertEqual(fake_streamlit.downloads[0][1]["data"], b"csv-guardado")


if __name__ == "__main__":
    unittest.main()
