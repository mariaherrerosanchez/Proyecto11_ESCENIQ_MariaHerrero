import unittest

from esceniq.vision.brand_classes import (
    BRAND_CLASSES,
    BrandClass,
    BrandClassValidationError,
    UnknownBrandClassError,
    brand_name_for_yolo_id,
    render_yolo_names_yaml,
    validate_brand_catalog,
    validate_yolo_names,
    yolo_id_for_brand_name,
    yolo_names,
)


class BrandClassesTests(unittest.TestCase):
    def test_catalog_has_exactly_five_consecutive_classes_in_official_order(self):
        self.assertEqual(len(BRAND_CLASSES), 5)
        self.assertEqual([item.yolo_id for item in BRAND_CLASSES], [0, 1, 2, 3, 4])
        self.assertEqual([item.class_name for item in BRAND_CLASSES], ["eggo", "coca_cola", "pepsi", "fedex", "wilson"])

    def test_identifiers_resolve_to_official_brand_names(self):
        self.assertEqual([brand_name_for_yolo_id(index) for index in range(5)], ["Eggo", "Coca-Cola", "Pepsi", "FedEx", "Wilson"])
        self.assertEqual(yolo_id_for_brand_name("Coca-Cola"), 1)

    def test_unknown_identifiers_and_names_are_explicit(self):
        with self.assertRaises(UnknownBrandClassError):
            brand_name_for_yolo_id(5)
        with self.assertRaises(UnknownBrandClassError):
            brand_name_for_yolo_id(-1)
        with self.assertRaises(UnknownBrandClassError):
            yolo_id_for_brand_name("Coke")

    def test_duplicate_and_inconsistent_catalogs_are_rejected(self):
        duplicated = (*BRAND_CLASSES[:-1], BrandClass(3, "wilson", "Wilson", ("W",)))
        with self.assertRaises(BrandClassValidationError):
            validate_brand_catalog(duplicated)
        unknown_class = (*BRAND_CLASSES[:-1], BrandClass(4, "unknown", "Unknown", ("example",)))
        with self.assertRaises(BrandClassValidationError):
            validate_brand_catalog(unknown_class)
        with self.assertRaises(BrandClassValidationError):
            validate_yolo_names({0: "eggo", 1: "coca_cola"})

    def test_yolo_representation_is_stable_and_validated(self):
        self.assertEqual(yolo_names(), {0: "eggo", 1: "coca_cola", 2: "pepsi", 3: "fedex", 4: "wilson"})
        validate_yolo_names(yolo_names())
        self.assertEqual(
            render_yolo_names_yaml(),
            "names:\n  0: eggo\n  1: coca_cola\n  2: pepsi\n  3: fedex\n  4: wilson\n",
        )


if __name__ == "__main__":
    unittest.main()
