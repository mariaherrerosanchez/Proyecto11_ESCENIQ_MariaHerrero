import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app

from esceniq.vision import InferenceMode


class FakeColumn:
    def metric(self, *_args, **_kwargs):
        pass


class FakeStreamlit:
    def __init__(self):
        self.captions = []
        self.infos = []
        self.errors = []
        self.dataframes = []
        self.downloads = []
        self.session_state = {}

    def columns(self, count):
        return [FakeColumn() for _ in range(count)]

    def subheader(self, *_args, **_kwargs):
        pass

    def caption(self, value, *_args, **_kwargs):
        self.captions.append(value)

    def dataframe(self, data, *_args, **_kwargs):
        self.dataframes.append(data)

    def info(self, value, *_args, **_kwargs):
        self.infos.append(value)

    def error(self, value, *_args, **_kwargs):
        self.errors.append(value)

    def download_button(self, label, **kwargs):
        self.downloads.append((label, kwargs))


class InferenceResultRenderingTests(unittest.TestCase):
    def result(self, mode):
        return SimpleNamespace(
            mode=mode,
            analyzed_frame_count=4,
            elapsed_seconds=0.1,
            detections=(object(),),
            model_path="model.pt",
            confidence_threshold=0.25,
            sample_interval_seconds=1.0,
        )

    @patch.object(app, "render_evidence_gallery")
    @patch.object(app, "calculate_exposure")
    def test_renders_experimental_and_official_exposure_without_missing_brand_context(
        self, calculate_exposure, _render_evidence_gallery
    ):
        calculate_exposure.return_value = SimpleNamespace(
            metrics=(
                SimpleNamespace(
                    brand_name="Coca-Cola",
                    positive_sample_count=1,
                    estimated_seconds=1.0,
                    percentage_of_video=10.0,
                    appearance_count=1,
                ),
            )
        )
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            for mode, expected_caption in (
                (InferenceMode.EGGO_EXPERIMENTAL, "Estimación experimental de Eggo"),
                (InferenceMode.COCACOLA_EXPERIMENTAL, "Estimación experimental de Coca-Cola"),
                (InferenceMode.ESCENIQ, "Estimación basada en muestras"),
            ):
                with self.subTest(mode=mode):
                    app.render_inference_result(self.result(mode))
                    self.assertIn(expected_caption, fake_streamlit.captions[-1])

    @patch.object(app, "render_evidence_gallery")
    @patch.object(app, "calculate_exposure")
    def test_renders_table_values_and_analysis_parameters(self, calculate_exposure, _render_evidence_gallery):
        metric = SimpleNamespace(
            brand_name="Coca-Cola",
            positive_sample_count=2,
            estimated_seconds=1.25,
            percentage_of_video=12.5,
            appearance_count=1,
        )
        calculate_exposure.return_value = SimpleNamespace(metrics=(metric,))
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            app.render_inference_result(self.result(InferenceMode.ESCENIQ))

        self.assertEqual(fake_streamlit.dataframes, [[{
            "Marca": "Coca-Cola",
            "Muestras positivas": 2,
            "Exposición estimada (s)": 1.25,
            "Vídeo (%)": 12.5,
            "Apariciones": 1,
        }]])
        self.assertIn("Modelo: model.pt · Umbral: 25% · Intervalo: 1 s", fake_streamlit.captions)

    @patch.object(app, "render_evidence_gallery")
    @patch.object(app, "calculate_exposure")
    def test_empty_result_shows_an_info_message_without_table(self, calculate_exposure, _render_evidence_gallery):
        calculate_exposure.return_value = SimpleNamespace(metrics=())
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            app.render_inference_result(self.result(InferenceMode.ESCENIQ))

        self.assertEqual(fake_streamlit.dataframes, [])
        self.assertEqual(fake_streamlit.infos, ["El análisis terminó correctamente sin detecciones de marcas."])
        self.assertEqual(fake_streamlit.errors, [])

    @patch.object(app, "render_evidence_gallery")
    @patch.object(app, "calculate_exposure")
    def test_technical_mode_does_not_calculate_brand_exposure(self, calculate_exposure, _render_evidence_gallery):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            app.render_inference_result(self.result(InferenceMode.TECHNICAL_TEST))

        calculate_exposure.assert_not_called()
        self.assertEqual(fake_streamlit.dataframes, [])
        self.assertIn("prueba técnica", fake_streamlit.infos[0])

    def test_inference_error_clears_previous_result_and_is_not_an_empty_state(self):
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state.update(
            {"inference_result": object(), "inference_result_key": ("previous",)}
        )

        with patch.object(app, "st", fake_streamlit):
            app.clear_inference_result()
            app.render_inference_error(RuntimeError("fallo de inferencia"))

        self.assertNotIn("inference_result", fake_streamlit.session_state)
        self.assertNotIn("inference_result_key", fake_streamlit.session_state)
        self.assertEqual(fake_streamlit.errors, ["fallo de inferencia"])
        self.assertEqual(fake_streamlit.infos, [])

    @patch.object(app, "build_results_csv")
    def test_csv_download_uses_real_result_and_current_video_name(self, build_results_csv):
        build_results_csv.return_value = b"csv-real"
        fake_streamlit = FakeStreamlit()
        fake_streamlit.session_state["analysis_video_name"] = "escena.mp4"
        result = self.result(InferenceMode.ESCENIQ)
        exposure = object()

        with patch.object(app, "st", fake_streamlit):
            app.render_csv_download(result, exposure)

        build_results_csv.assert_called_once_with(
            result, exposure, video_name="escena.mp4"
        )
        self.assertEqual(fake_streamlit.downloads[0][0], "Descargar CSV")
        self.assertEqual(fake_streamlit.downloads[0][1]["data"], b"csv-real")

    @patch.object(app, "build_results_csv", return_value=None)
    def test_csv_download_is_not_offered_when_there_are_no_exportable_rows(self, _build_results_csv):
        fake_streamlit = FakeStreamlit()

        with patch.object(app, "st", fake_streamlit):
            app.render_csv_download(self.result(InferenceMode.ESCENIQ), object())

        self.assertEqual(fake_streamlit.downloads, [])


if __name__ == "__main__":
    unittest.main()
