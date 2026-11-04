import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "review_eggo_gallery.py"
SPEC = importlib.util.spec_from_file_location("review_eggo_gallery", SCRIPT)
gallery = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = gallery
SPEC.loader.exec_module(gallery)


class EggoGalleryTests(unittest.TestCase):
    def build_dataset(self, root: Path) -> Path:
        originals = root / "originales"
        labels = root / "revision_corregida" / "labels"
        pilots = root / "piloto" / "labels"
        originals.mkdir(parents=True)
        labels.mkdir(parents=True)
        pilots.mkdir(parents=True)
        rows = []
        statuses = ["corrected_pending_human_review"] * 30
        statuses += ["retained_provisional_pending_human_review"] * 8
        statuses += ["policy_review"]
        for index, status in enumerate(statuses):
            filename = f"active-{index:02}.png"
            (originals / filename).write_bytes(b"PNG")
            (labels / f"active-{index:02}.txt").write_text("0 0.5 0.5 0.4 0.4\n", encoding="utf-8")
            rows.append({"filename": filename, "status": status, "box_count_after": "1", "observations": "Pendiente."})
        excluded = []
        for index in range(6):
            filename = f"excluded-{index:02}.png"
            (originals / filename).write_bytes(b"PNG")
            rows.append({"filename": filename, "status": "excluded_from_main_training", "box_count_after": "0", "observations": "Cartón."})
            excluded.append({"filename": filename, "status": "excluded_from_main_training"})
        for index in range(5):
            filename = f"pilot-{index:02}.png"
            (originals / filename).write_bytes(b"PNG")
            (pilots / f"pilot-{index:02}.txt").write_text("0 0.5 0.5 0.4 0.4\n", encoding="utf-8")
        with (root / "revision_corregida" / "revision_manifest.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=("filename", "status", "box_count_after", "observations"))
            writer.writeheader()
            writer.writerows(rows)
        with (root / "revision_corregida" / "excluded_from_main_training.csv").open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=("filename", "status"))
            writer.writeheader()
            writer.writerows(excluded)
        return root

    def test_generates_gallery_for_44_candidates_and_six_exclusions(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = self.build_dataset(Path(temporary) / "Eggo")
            output = root / "revision_visual_html"

            candidates, boxes = gallery.generate_gallery(root, output)

            self.assertEqual((candidates, boxes), (44, 44))
            html = (output / "eggo_review_gallery.html").read_text(encoding="utf-8")
            self.assertIn("44 candidatas", html)
            self.assertIn("6 excluidas fuera del entrenamiento", html)
            self.assertIn("Corregida pendiente de revisión", html)
            self.assertIn("Pendiente de decisión de política", html)
            self.assertIn('stroke="#c8ff00" stroke-width="3"', html)
            self.assertIn('fill="#071c20"', html)
            self.assertIn("Exportar JSON de revisión", html)
            self.assertIn("Importar JSON", html)
            self.assertIn("boxes_yolo", html)
            self.assertIn("resize-handle", html)
            self.assertEqual(len((output / "eggo_review_template.csv").read_text(encoding="utf-8").splitlines()), 45)

    def test_rejects_boxes_outside_image(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = self.build_dataset(Path(temporary) / "Eggo")
            (root / "revision_corregida" / "labels" / "active-00.txt").write_text(
                "0 0.95 0.5 0.2 0.2\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(gallery.GalleryValidationError, "fuera de la imagen"):
                gallery.load_gallery_items(root)

    def test_visual_pixel_and_yolo_coordinates_round_trip_at_different_resolutions(self):
        for width, height in ((275, 274), (1649, 1238)):
            with self.subTest(width=width, height=height):
                original_pixels = (width * 0.12, height * 0.23, width * 0.54, height * 0.41)
                yolo = gallery.pixels_to_yolo(original_pixels, width, height)

                restored_pixels = gallery.yolo_to_pixels(yolo, width, height)

                self.assertEqual(yolo[0], 0)
                for expected, actual in zip(original_pixels, restored_pixels, strict=True):
                    self.assertAlmostEqual(expected, actual)

    def test_rejects_invalid_yolo_conversion(self):
        with self.assertRaisesRegex(gallery.GalleryValidationError, "fuera de la imagen"):
            gallery.yolo_to_xywh(0, 0.95, 0.5, 0.2, 0.2)
        with self.assertRaisesRegex(gallery.GalleryValidationError, "clase 0"):
            gallery.yolo_to_xywh(1, 0.5, 0.5, 0.2, 0.2)

    def test_output_must_stay_inside_dataset_root(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = self.build_dataset(Path(temporary) / "Eggo")
            with self.assertRaisesRegex(gallery.GalleryValidationError, "dentro de la raíz"):
                gallery.validate_output_directory(root, Path(temporary) / "outside")


if __name__ == "__main__":
    unittest.main()
