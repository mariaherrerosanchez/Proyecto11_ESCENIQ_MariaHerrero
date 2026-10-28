import unittest
from dataclasses import replace
from pathlib import Path

from esceniq.analytics import ExposureError, calculate_exposure
from esceniq.video import VideoMetadata
from esceniq.vision import Detection, InferenceMode, InferenceResult


class ExposureTests(unittest.TestCase):
    def result(self, detections=(), *, duration=4.0, interval=1.0, mode=InferenceMode.ESCENIQ):
        return InferenceResult(
            video_metadata=VideoMetadata(Path("video.mp4"), 10.0, int(duration * 10), 640, 480, duration),
            model_path=Path("model.pt"),
            mode=mode,
            model_class_names={0: "eggo", 1: "coca_cola", 2: "pepsi", 3: "fedex", 4: "wilson"},
            confidence_threshold=0.25,
            sample_interval_seconds=interval,
            analyzed_frame_count=0,
            elapsed_seconds=0.1,
            detections=tuple(detections),
        )

    def detection(self, class_id, timestamp, frame_index, *, brand_name=None):
        names = {0: "Eggo", 1: "Coca-Cola", 2: "Pepsi", 3: "FedEx", 4: "Wilson"}
        return Detection(
            class_id=class_id,
            class_name=names[class_id].casefold().replace("-", "_"),
            confidence=0.9,
            bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
            frame_index=frame_index,
            timestamp_seconds=timestamp,
            brand_name=brand_name if brand_name is not None else names[class_id],
        )

    def metric(self, result, brand_name):
        return next(metric for metric in calculate_exposure(result).metrics if metric.brand_name == brand_name)

    def test_consecutive_samples_form_one_appearance(self):
        result = self.result(
            [self.detection(0, 0.0, 0), self.detection(0, 1.0, 10), self.detection(0, 2.0, 20)],
            duration=3.0,
        )

        metric = self.metric(result, "Eggo")

        self.assertEqual(metric.positive_sample_count, 3)
        self.assertEqual(metric.estimated_seconds, 3.0)
        self.assertEqual(metric.percentage_of_video, 100.0)
        self.assertEqual(metric.first_detection_seconds, 0.0)
        self.assertEqual(metric.last_detection_seconds, 2.0)
        self.assertEqual(metric.appearance_count, 1)

    def test_multiple_boxes_in_one_frame_count_as_one_positive_sample(self):
        result = self.result([self.detection(0, 0.0, 0), self.detection(0, 0.0, 0)])

        metric = self.metric(result, "Eggo")

        self.assertEqual(metric.positive_sample_count, 1)
        self.assertEqual(metric.estimated_seconds, 1.0)

    def test_simultaneous_brands_are_counted_independently(self):
        result = self.result([self.detection(0, 0.0, 0), self.detection(1, 0.0, 0)])

        summary = calculate_exposure(result)

        self.assertEqual([(item.brand_name, item.estimated_seconds) for item in summary.metrics], [("Eggo", 1.0), ("Coca-Cola", 1.0)])

    def test_gap_between_intervals_creates_a_separate_appearance(self):
        result = self.result([self.detection(0, 0.0, 0), self.detection(0, 2.0, 20)])

        metric = self.metric(result, "Eggo")

        self.assertEqual(metric.appearance_count, 2)
        self.assertEqual(metric.estimated_seconds, 2.0)

    def test_video_without_detections_returns_no_brand_metrics(self):
        summary = calculate_exposure(self.result())

        self.assertEqual(summary.metrics, ())

    def test_last_sample_is_limited_to_real_video_duration(self):
        result = self.result([self.detection(0, 2.0, 20)], duration=2.4)

        metric = self.metric(result, "Eggo")

        self.assertAlmostEqual(metric.estimated_seconds, 0.4)
        self.assertAlmostEqual(metric.percentage_of_video, 100 * 0.4 / 2.4)

    def test_sample_interval_changes_estimated_duration(self):
        result = self.result([self.detection(0, 0.0, 0), self.detection(0, 1.0, 10)], interval=0.5)

        metric = self.metric(result, "Eggo")

        self.assertEqual(metric.estimated_seconds, 1.0)
        self.assertEqual(metric.appearance_count, 2)

    def test_irregular_timestamps_merge_overlapping_sample_intervals(self):
        result = self.result(
            [self.detection(0, 0.0, 0), self.detection(0, 0.5, 5), self.detection(0, 2.1, 21)],
            duration=3.0,
        )

        metric = self.metric(result, "Eggo")

        self.assertAlmostEqual(metric.estimated_seconds, 2.4)
        self.assertEqual(metric.appearance_count, 2)

    def test_technical_results_and_invalid_brand_detections_are_rejected(self):
        technical = self.result(mode=InferenceMode.TECHNICAL_TEST)
        with self.assertRaisesRegex(ExposureError, "prueba técnica"):
            calculate_exposure(technical)

        invalid_brand = self.result([replace(self.detection(0, 0.0, 0), brand_name=None)])
        with self.assertRaisesRegex(ExposureError, "marca ESCENIQ"):
            calculate_exposure(invalid_brand)


if __name__ == "__main__":
    unittest.main()
