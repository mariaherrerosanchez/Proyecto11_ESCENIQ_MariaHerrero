import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_eggo_pilot_dataset.py"
SPEC = importlib.util.spec_from_file_location("prepare_eggo_pilot_dataset", SCRIPT)
preparer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = preparer
SPEC.loader.exec_module(preparer)


class PrepareEggoPilotDatasetTests(unittest.TestCase):
    def reviewed_payload(self, names: list[str]) -> dict:
        return {
            "schema_version": 1,
            "dataset": "Eggo",
            "class_id": 0,
            "annotations": [
                {
                    "filename": name,
                    "decision": "approved",
                    "notes": "",
                    "boxes_yolo": [[0, 0.5, 0.5, 0.4, 0.4]]
                    + ([[0, 0.2, 0.2, 0.1, 0.1]] if index < 39 else []),
                }
                for index, name in enumerate(names)
            ],
        }

    def test_split_is_deterministic_and_has_requested_counts(self):
        images = [
            preparer.ReviewedImage(f"image-{index:02}.png", ((0, 0.5, 0.5, 0.4, 0.4),))
            for index in range(44)
        ]
        first = preparer.split_reviewed_images(images)
        second = preparer.split_reviewed_images(images)

        self.assertEqual(first, second)
        self.assertEqual({split: len(items) for split, items in first.items()}, {"train": 31, "val": 7, "test": 6})
        self.assertEqual(len({item.filename for items in first.values() for item in items}), 44)

    def test_rejects_boxes_outside_image(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            review_path = Path(temporary) / "review.json"
            payload = self.reviewed_payload([f"image-{index:02}.png" for index in range(44)])
            payload["annotations"][0]["boxes_yolo"] = [[0, 0.95, 0.5, 0.2, 0.2]]
            review_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(preparer.PilotDatasetError, "límites horizontales"):
                preparer.load_approved_review(review_path)

    def test_prepares_copies_from_final_review_without_touching_sources(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            originals = root / "originales"
            originals.mkdir()
            names = [f"image-{index:02}.png" for index in range(44)]
            for index, name in enumerate(names):
                (originals / name).write_bytes(f"source-{index}".encode())
            review_path = root / "review.json"
            review_path.write_text(json.dumps(self.reviewed_payload(names)), encoding="utf-8")
            output = root / "pilot"

            result = preparer.prepare_dataset(originals, review_path, output)

            self.assertEqual(result, {"images": 44, "boxes": 83, "train": 31, "val": 7, "test": 6})
            self.assertEqual((originals / names[0]).read_bytes(), b"source-0")
            self.assertEqual(sum(1 for _ in (output / "images").glob("*/*.png")), 44)
            self.assertEqual(sum(1 for _ in (output / "labels").glob("*/*.txt")), 44)
            data_yaml = (output / "data.yaml").read_text(encoding="utf-8")
            self.assertEqual(data_yaml, preparer.render_data_yaml(output))
            self.assertIn(f"path: {output.resolve().as_posix()}", data_yaml)
            self.assertIn("0: eggo", data_yaml)
            report = json.loads((output / "manifests" / "preparation_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["counts"]["splits"], {"train": 31, "val": 7, "test": 6})

    def test_rejects_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            output = Path(temporary) / "pilot"
            output.mkdir()
            (output / "existing.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(preparer.PilotDatasetError, "ya existe"):
                preparer.ensure_empty_output_directory(output)

    def test_yolo_serialization_keeps_edge_boxes_inside_after_rounding(self):
        content = preparer.yolo_text(((0, 0.50033201, 0.5, 0.99933599, 0.4),))
        _, center_x, _, width, _ = content.split()

        self.assertLessEqual(float(center_x) + float(width) / 2, 1.0)


if __name__ == "__main__":
    unittest.main()
