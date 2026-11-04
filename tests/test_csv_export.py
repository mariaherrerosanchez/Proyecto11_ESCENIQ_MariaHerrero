import csv
from io import StringIO
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esceniq.analytics import ExposureMetric, ExposureSummary
from esceniq.reports import CSV_HEADERS, build_results_csv, build_stored_results_csv


class CsvExportTests(unittest.TestCase):
    def result(self):
        return SimpleNamespace(
            model_path=Path("models/esceniq.pt"),
            confidence_threshold=0.25,
            sample_interval_seconds=1.0,
            detections=(
                SimpleNamespace(brand_name="Coca-Cola"),
                SimpleNamespace(brand_name="Coca-Cola"),
                SimpleNamespace(brand_name="Eggo"),
            ),
        )

    def exposure(self, *metrics):
        return ExposureSummary(60.0, 1.0, metrics)

    def test_builds_excel_ready_csv_from_the_existing_summary(self):
        metric = ExposureMetric("Coca-Cola", 1, 1.25, 2.0833333333, 2.0, 2.0, 1)

        content = build_results_csv(
            self.result(), self.exposure(metric), video_name="escena.mp4"
        )

        self.assertIsNotNone(content)
        self.assertTrue(content.startswith(b"\xef\xbb\xbf"))
        decoded = content.decode("utf-8-sig")
        self.assertIn(";", decoded.splitlines()[0])
        rows = list(csv.DictReader(StringIO(decoded), delimiter=";"))
        self.assertEqual(CSV_HEADERS, tuple(rows[0]))
        self.assertEqual(rows, [{
            "Vídeo": "escena.mp4",
            "Marca": "Coca-Cola",
            "Número de detecciones": "2",
            "Muestras positivas": "1",
            "Exposición estimada (s)": "1,25",
            "Exposición (%)": "2,08",
            "Apariciones": "1",
            "Modelo": "models\\esceniq.pt",
            "Umbral de confianza": "0,25",
            "Intervalo de muestreo (s)": "1,00",
        }])

    def test_does_not_create_a_csv_when_the_summary_has_no_real_rows(self):
        self.assertIsNone(build_results_csv(self.result(), self.exposure(), video_name="escena.mp4"))

    def test_builds_the_same_excel_ready_format_from_a_saved_analysis(self):
        stored_analysis = SimpleNamespace(
            video_name="guardada.mp4",
            model_path=r"models\esceniq.pt",
            confidence_threshold=0.25,
            sample_interval_seconds=1.0,
            detections=(
                SimpleNamespace(brand_name="Coca-Cola"),
                SimpleNamespace(brand_name="Coca-Cola"),
            ),
            exposures=(ExposureMetric("Coca-Cola", 1, 1.25, 2.08, 2.0, 2.0, 1),),
        )

        content = build_stored_results_csv(stored_analysis)

        rows = list(csv.DictReader(StringIO(content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(rows[0]["Vídeo"], "guardada.mp4")
        self.assertEqual(rows[0]["Número de detecciones"], "2")
        self.assertEqual(rows[0]["Exposición estimada (s)"], "1,25")

    def test_does_not_offer_a_csv_for_a_saved_analysis_without_exposure(self):
        stored_analysis = SimpleNamespace(
            video_name="sin_marcas.mp4",
            model_path="model.pt",
            confidence_threshold=0.25,
            sample_interval_seconds=1.0,
            detections=(),
            exposures=(),
        )

        self.assertIsNone(build_stored_results_csv(stored_analysis))


if __name__ == "__main__":
    unittest.main()
