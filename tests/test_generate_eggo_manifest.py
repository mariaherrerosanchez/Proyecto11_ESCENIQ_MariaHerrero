import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_eggo_manifest.py"
SPEC = importlib.util.spec_from_file_location("generate_eggo_manifest", SCRIPT)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


def png(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big")


class EggoManifestGeneratorTests(unittest.TestCase):
    def test_build_rows_uses_relative_paths_and_pending_split(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            source = Path(temporary)
            filename = "2026-10-23_10h38_08.png"
            (source / filename).write_bytes(png(275, 274))
            rows = generator.build_rows(source)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source_path"], f"originales/{filename}")
        self.assertEqual(row["class_id"], 0)
        self.assertEqual(row["split"], "")
        self.assertEqual(row["license"], "unverified")
        self.assertEqual(row["review_status"], "needs_review")
        self.assertIn("lado mínimo", str(row["notes"]))

    def test_dataset_record_projection_preserves_existing_contract(self):
        rows = [{
            "filename": "sample.png", "source_path": "originales/sample.png",
            "group_id": generator.GROUP_ID,
        }]
        record = generator.dataset_records(rows)[0]
        self.assertEqual(record.image_path, "originales/sample.png")
        self.assertEqual(record.label_path, "labels/sample.txt")
        self.assertEqual(record.class_ids, (0,))
        self.assertEqual(record.split, "")
        self.assertEqual(record.license, "unverified")


if __name__ == "__main__":
    unittest.main()
