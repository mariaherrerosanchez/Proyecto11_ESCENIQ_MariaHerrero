import csv
from io import StringIO
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esceniq.analytics import ExposureMetric, ExposureSummary
from esceniq.reports import CSV_HEADERS, build_results_csv


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


if __name__ == "__main__":
    unittest.main()
