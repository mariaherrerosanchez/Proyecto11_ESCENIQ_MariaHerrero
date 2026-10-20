import tempfile
import unittest
from pathlib import Path

from esceniq.dataset.preparation import (
    DatasetRecord,
    DatasetValidationError,
    SplitConfig,
    read_manifest,
    render_data_yaml,
    split_records_by_group,
    validate_data_yaml_text,
    validate_dataset_files,
    validate_manifest,
    validate_manifest_paths,
    validate_yolo_label,
    write_manifest,
)


def record(index: int, group: str, class_id: int = 0) -> DatasetRecord:
    return DatasetRecord(
        image_path=f"images/source_{index}.jpg",
        label_path=f"labels/source_{index}.txt",
        class_ids=(class_id,),
        source="synthetic-source",
        group_id=group,
        license="test-license",
    )


class DatasetPreparationTests(unittest.TestCase):
    def test_split_is_reproducible_and_keeps_groups_together(self):
        records = [record(index, f"clip-{index // 2}", index % 5) for index in range(12)]
        first, warnings = split_records_by_group(records, SplitConfig(seed=9))
        second, _ = split_records_by_group(records, SplitConfig(seed=9))
        self.assertEqual(first, second)
        self.assertTrue(warnings)
        by_group = {}
        for item in first:
            by_group.setdefault(item.group_id, set()).add(item.split)
        self.assertTrue(all(len(splits) == 1 for splits in by_group.values()))

    def test_demo_groups_and_leaked_groups_are_rejected(self):
        records = [record(0, "demo-clip"), record(1, "other")]
        with self.assertRaises(DatasetValidationError):
            split_records_by_group(records, demo_groups={"demo-clip"})
        leaked = [DatasetRecord(**{**records[0].__dict__, "split": "train"}), DatasetRecord(**{**records[0].__dict__, "image_path": "images/other.jpg", "label_path": "labels/other.txt", "split": "test"})]
        with self.assertRaises(DatasetValidationError):
            validate_manifest(leaked)

    def test_invalid_class_and_duplicate_destinations_are_rejected(self):
        with self.assertRaises(DatasetValidationError):
            validate_manifest([record(0, "clip", 5)])
        duplicated = [record(0, "clip-a"), DatasetRecord(**{**record(1, "clip-b").__dict__, "image_path": "images/source_0.jpg"})]
        with self.assertRaises(DatasetValidationError):
            validate_manifest(duplicated)

    def test_yolo_labels_accept_negatives_and_reject_invalid_values(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            empty = root / "negative.txt"
            empty.write_text("", encoding="utf-8")
            self.assertEqual(validate_yolo_label(empty), ())
            invalid = root / "invalid.txt"
            invalid.write_text("5 0.5 0.5 0.2 0.2\n", encoding="utf-8")
            with self.assertRaises(DatasetValidationError):
                validate_yolo_label(invalid)
            invalid.write_text("0 1.2 0.5 0.2 0.2\n", encoding="utf-8")
            with self.assertRaises(DatasetValidationError):
                validate_yolo_label(invalid)

    def test_dataset_files_detect_missing_pairs_and_allow_negative_image(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            for split in ("train", "val", "test"):
                (root / "images" / split).mkdir(parents=True)
                (root / "labels" / split).mkdir(parents=True)
            (root / "images" / "train" / "negative.jpg").touch()
            (root / "labels" / "train" / "negative.txt").write_text("", encoding="utf-8")
            validate_dataset_files(root)
            (root / "images" / "val" / "missing.jpg").touch()
            with self.assertRaises(DatasetValidationError):
                validate_dataset_files(root)

    def test_manifest_csv_paths_and_data_yaml_are_validated(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            item = record(0, "clip-a")
            (root / "images").mkdir()
            (root / "labels").mkdir()
            (root / item.image_path).touch()
            (root / item.label_path).write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
            manifest = root / "manifest.csv"
            write_manifest([item], manifest)
            loaded = read_manifest(manifest)
            self.assertEqual(loaded, [item])
            validate_manifest_paths(loaded, root)
            (root / item.label_path).unlink()
            with self.assertRaises(DatasetValidationError):
                validate_manifest_paths(loaded, root)
        yaml_text = render_data_yaml(Path("datasets/esceniq"))
        validate_data_yaml_text(yaml_text)
        with self.assertRaises(DatasetValidationError):
            validate_data_yaml_text(yaml_text.replace("fedex", "unknown"))


if __name__ == "__main__":
    unittest.main()
