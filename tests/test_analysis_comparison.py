from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esceniq.analytics import build_analysis_comparison


def metric(brand_name: str, seconds: float, *, appearances: int = 1, percentage: float = 10.0):
    return SimpleNamespace(
        brand_name=brand_name,
        positive_sample_count=appearances,
        estimated_seconds=seconds,
        percentage_of_video=percentage,
        appearance_count=appearances,
    )


def analysis(*, video_name: str, exposures=(), **overrides):
    values = {
        "video_name": video_name,
        "mode": "esceniq",
        "model_path": r"models\esceniq.pt",
        "confidence_threshold": 0.25,
        "sample_interval_seconds": 1.0,
        "duration_seconds": 10.0,
        "exposures": tuple(exposures),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class AnalysisComparisonTests(unittest.TestCase):
    def test_compares_valid_saved_metrics_without_recalculating_them(self):
        left = analysis(video_name="primero.mp4", exposures=(metric("Eggo", 3.0, appearances=2),))
        right = analysis(video_name="segundo.mp4", exposures=(metric("Eggo", 1.0),))

        comparison = build_analysis_comparison(left, right)

        self.assertTrue(comparison.is_directly_comparable)
        self.assertEqual(comparison.metrics[0].higher_exposure, "left")
        self.assertIs(comparison.metrics[0].left, left.exposures[0])
        self.assertEqual(comparison.metrics[0].left.appearance_count, 2)

    def test_distinguishes_a_missing_brand_from_unavailable_metrics(self):
        left = analysis(video_name="sin-eggo.mp4", exposures=())
        right = analysis(video_name="con-eggo.mp4", exposures=(metric("Eggo", 1.0),))

        comparison = build_analysis_comparison(left, right)

        metric_comparison = comparison.metrics[0]
        self.assertTrue(metric_comparison.left_available)
        self.assertIsNone(metric_comparison.left)
        self.assertTrue(metric_comparison.right_available)
        self.assertEqual(metric_comparison.higher_exposure, "right")

        unavailable = build_analysis_comparison(
            analysis(video_name="tecnico.mp4", mode="technical_test"), right
        ).metrics[0]
        self.assertFalse(unavailable.left_available)
        self.assertIsNone(unavailable.higher_exposure)

    def test_configuration_differences_block_a_direct_exposure_conclusion(self):
        left = analysis(video_name="uno.mp4", exposures=(metric("Eggo", 3.0),))
        right = analysis(
            video_name="dos.mp4",
            exposures=(metric("Eggo", 1.0),),
            confidence_threshold=0.5,
            sample_interval_seconds=2.0,
        )

        comparison = build_analysis_comparison(left, right)

        self.assertFalse(comparison.is_directly_comparable)
        self.assertEqual(comparison.configuration_differences, ("umbral de confianza", "intervalo de muestreo"))
        self.assertIsNone(comparison.metrics[0].higher_exposure)

    def test_incomplete_persisted_metrics_are_not_reported_as_absent(self):
        malformed = SimpleNamespace(
            brand_name="Eggo",
            positive_sample_count=1,
            estimated_seconds=float("nan"),
            percentage_of_video=10.0,
            appearance_count=1,
        )
        comparison = build_analysis_comparison(
            analysis(video_name="incompleto.mp4", exposures=(malformed,)),
            analysis(video_name="real.mp4", exposures=(metric("Eggo", 1.0),)),
        )

        self.assertFalse(comparison.metrics[0].left_available)
        self.assertIsNone(comparison.metrics[0].higher_exposure)


if __name__ == "__main__":
    unittest.main()
