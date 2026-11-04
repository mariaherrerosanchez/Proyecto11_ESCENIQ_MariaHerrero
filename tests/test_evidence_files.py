import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esceniq.storage import EvidenceFileStore, EvidenceStorageError, default_evidence_directory


TEST_WORKSPACE = Path(__file__).resolve().parents[1]


class EvidenceFileStoreTests(unittest.TestCase):
    def test_directory_can_be_configured(self):
        previous_directory = os.environ.get("ESCENIQ_EVIDENCE_DIRECTORY")
        try:
            os.environ["ESCENIQ_EVIDENCE_DIRECTORY"] = r"C:\ESCENIQ_Datasets\evidences"
            self.assertEqual(default_evidence_directory(), Path(r"C:\ESCENIQ_Datasets\evidences"))
        finally:
            if previous_directory is None:
                os.environ.pop("ESCENIQ_EVIDENCE_DIRECTORY", None)
            else:
                os.environ["ESCENIQ_EVIDENCE_DIRECTORY"] = previous_directory

    def test_writes_and_recovers_evidence_across_store_instances_without_overwriting(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            analysis_id = str(uuid4())
            first_store = EvidenceFileStore(temporary_directory)
            stored_path = first_store.write(analysis_id, 12, b"first-jpeg")
            repeated_path = first_store.write(analysis_id, 12, b"second-jpeg")
            with patch("esceniq.storage.evidence_files._is_valid_jpeg", return_value=True):
                recovered = EvidenceFileStore(temporary_directory).read(stored_path)

        self.assertEqual(stored_path, repeated_path)
        self.assertEqual(recovered, b"first-jpeg")

    def test_reports_missing_corrupt_and_unsafe_evidence_paths(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            store = EvidenceFileStore(temporary_directory)
            analysis_id = str(uuid4())
            stored_path = store.write(analysis_id, 1, b"corrupt")

            with self.assertRaisesRegex(EvidenceStorageError, "no está disponible"):
                store.read(f"{analysis_id}/missing.jpg")
            with patch("esceniq.storage.evidence_files._is_valid_jpeg", return_value=False):
                with self.assertRaisesRegex(EvidenceStorageError, "corrupta"):
                    store.read(stored_path)
            with self.assertRaisesRegex(EvidenceStorageError, "ruta"):
                store.read("../outside.jpg")

    def test_write_error_is_explicit(self):
        with TemporaryDirectory(dir=TEST_WORKSPACE) as temporary_directory:
            blocked_root = Path(temporary_directory) / "blocked"
            blocked_root.write_text("not a directory", encoding="utf-8")
            store = EvidenceFileStore(blocked_root)

            with self.assertRaises(EvidenceStorageError):
                store.write(str(uuid4()), 1, b"jpeg")


if __name__ == "__main__":
    unittest.main()
