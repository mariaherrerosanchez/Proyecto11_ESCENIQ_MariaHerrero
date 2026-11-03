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

    def columns(self, count):
        return [FakeColumn() for _ in range(count)]

    def subheader(self, *_args, **_kwargs):
        pass

    def caption(self, value, *_args, **_kwargs):
        self.captions.append(value)

    def dataframe(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass


class InferenceResultRenderingTests(unittest.TestCase):
    def result(self, mode):
        return SimpleNamespace(
            mode=mode,
            analyzed_frame_count=4,
            elapsed_seconds=0.1,
            detections=(object(),),
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


if __name__ == "__main__":
    unittest.main()
