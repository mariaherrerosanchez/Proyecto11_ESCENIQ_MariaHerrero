from pathlib import Path
import os
import sqlite3
import sys
from tempfile import TemporaryDirectory
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esceniq.analytics import calculate_exposure
from esceniq.storage import SqliteAnalysisRepository, StorageError
from esceniq.storage import default_database_path
from esceniq.video import VideoMetadata
from esceniq.vision import Detection, InferenceMode, InferenceResult

TEST_WORKSPACE = Path(__file__).resolve().parents[1]


class SqliteAnalysisRepositoryTests(unittest.TestCase):
    def test_database_path_can_be_configured(self):
        previous_path = os.environ.get("ESCENIQ_DATABASE_PATH")
        try:
            os.environ["ESCENIQ_DATABASE_PATH"] = r"C:\ESCENIQ_Datasets\analyses.sqlite3"
            self.assertEqual(default_database_path(), Path(r"C:\ESCENIQ_Datasets\analyses.sqlite3"))
        finally:
            if previous_path is None:
                os.environ.pop("ESCENIQ_DATABASE_PATH", None)
            else:
                os.environ["ESCENIQ_DATABASE_PATH"] = previous_path

    def result(self, *, timestamp: float = 1.0) -> InferenceResult:
        return InferenceResult(
            video_metadata=VideoMetadata(Path("temporal.mp4"), 10.0, 100, 640, 480, 10.0),
            model_path=Path("models/esceniq.pt"),
            mode=InferenceMode.ESCENIQ,
            model_class_names={0: "eggo", 1: "coca_cola", 2: "pepsi", 3: "fedex", 4: "wilson"},
            confidence_threshold=0.25,
            sample_interval_seconds=1.0,
            analyzed_frame_count=10,
            elapsed_seconds=0.4,
            detections=(
                Detection(1, "coca_cola", 0.9, (10.0, 20.0, 30.0, 40.0), 10, timestamp, "Coca-Cola"),
                Detection(1, "coca_cola", 0.8, (11.0, 21.0, 31.0, 41.0), 10, timestamp, "Coca-Cola"),
            ),
        )

    def save(self, repository: SqliteAnalysisRepository, *, key: str, video_name: str = "escena.mp4") -> str:
        result = self.result()
        return repository.save_completed_analysis(
            result,
            calculate_exposure(result),
            video_name=video_name,
            deduplication_key=key,
        )

    def test_saves_and_recovers_complete_analysis(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            repository = SqliteAnalysisRepository(Path(temporary_directory) / "analyses.sqlite3")
            analysis_id = self.save(repository, key="analysis-1")

            stored = repository.get_analysis(analysis_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.video_name, "escena.mp4")
        self.assertEqual(stored.mode, InferenceMode.ESCENIQ.value)
        self.assertEqual(stored.model_path, "models\\esceniq.pt")
        self.assertEqual(stored.analyzed_frame_count, 10)
        self.assertEqual(len(stored.detections), 2)
        self.assertEqual(stored.detections[0].bbox_xyxy, (10.0, 20.0, 30.0, 40.0))
        self.assertEqual(stored.exposures[0].brand_name, "Coca-Cola")
        self.assertEqual(stored.exposures[0].positive_sample_count, 1)

    def test_lists_newest_analysis_first_and_persists_between_connections(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            database_path = Path(temporary_directory) / "analyses.sqlite3"
            first_repository = SqliteAnalysisRepository(database_path)
            first_id = self.save(first_repository, key="analysis-1", video_name="primero.mp4")
            time.sleep(0.001)
            second_repository = SqliteAnalysisRepository(database_path)
            second_id = self.save(second_repository, key="analysis-2", video_name="segundo.mp4")

            listed = SqliteAnalysisRepository(database_path).list_analyses()

        self.assertEqual([item.analysis_id for item in listed], [second_id, first_id])
        self.assertEqual([item.video_name for item in listed], ["segundo.mp4", "primero.mp4"])

    def test_repeated_rerun_uses_existing_analysis_instead_of_duplicate(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            repository = SqliteAnalysisRepository(Path(temporary_directory) / "analyses.sqlite3")
            first_id = self.save(repository, key="same-analysis")
            repeated_id = self.save(repository, key="same-analysis")

            listed = repository.list_analyses()

        self.assertEqual(first_id, repeated_id)
        self.assertEqual(len(listed), 1)

    def test_rejects_incomplete_metadata_and_rolls_back(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            repository = SqliteAnalysisRepository(Path(temporary_directory) / "analyses.sqlite3")
            result = self.result()

            with self.assertRaisesRegex(StorageError, "vídeo"):
                repository.save_completed_analysis(
                    result, calculate_exposure(result), video_name="", deduplication_key="missing-video"
                )

            self.assertEqual(repository.list_analyses(), ())

    def test_foreign_key_and_database_errors_are_explicit(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            database_path = Path(temporary_directory) / "analyses.sqlite3"
            repository = SqliteAnalysisRepository(database_path)
            repository.initialize()
            connection = sqlite3.connect(database_path)
            try:
                connection.execute("PRAGMA foreign_keys = ON")
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO brand_exposures VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ("missing", "Coca-Cola", 1, 1.0, 10.0, 0.0, 0.0, 1),
                    )
            finally:
                connection.close()

            blocked_path = Path(temporary_directory) / "blocked"
            blocked_path.write_text("not a directory", encoding="utf-8")
            failing_repository = SqliteAnalysisRepository(blocked_path / "analyses.sqlite3")
            with self.assertRaises(StorageError):
                self.save(failing_repository, key="unavailable")


if __name__ == "__main__":
    unittest.main()
