import tempfile
import unittest
from pathlib import Path

from esceniq.video import VideoMetadata
from esceniq.vision import InferenceConfig, InferenceError, InferenceMode, analyze_video


class FakeCapture:
    def __init__(self, frames, *, opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        self.released = True


class FakeOpenCV:
    def __init__(self, capture):
        self.capture = capture

    def VideoCapture(self, _path):
        return self.capture


class FakeBoxes:
    def __init__(self, class_ids, confidences, coordinates):
        self.cls = class_ids
        self.conf = confidences
        self.xyxy = coordinates


class FakeResult:
    def __init__(self, boxes):
        self.boxes = boxes


class FakeModel:
    def __init__(self, names, results_by_frame):
        self.names = names
        self.results_by_frame = results_by_frame
        self.calls = []

    def predict(self, frame, *, conf, verbose):
        self.calls.append((frame, conf, verbose))
        return self.results_by_frame.get(frame, [])


class YOLOInferenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.NamedTemporaryFile(suffix=".pt", delete=False)
        temporary.close()
        self.model_path = Path(temporary.name)
        self.addCleanup(self.model_path.unlink, missing_ok=True)
        self.metadata = VideoMetadata(Path("video.mp4"), 10.0, 10, 640, 480, 1.0)

    def config(self, **changes):
        values = {"model_path": self.model_path}
        values.update(changes)
        return InferenceConfig(**values)

    def analyze(self, model, capture, config=None):
        return analyze_video(
            Path("video.mp4"),
            config or self.config(),
            model_loader=lambda _path: model,
            video_probe=lambda _path: self.metadata,
            cv2_loader=lambda: FakeOpenCV(capture),
            clock=iter((10.0, 10.5)).__next__,
        )

    def test_samples_frames_and_keeps_traceable_detection_fields(self):
        boxes = FakeBoxes([0, 1], [0.9, 0.2], [[1, 2, 30, 40], [5, 6, 7, 8]])
        model = FakeModel({0: "person", 1: "bicycle"}, {"frame-0": [FakeResult(boxes)]})
        capture = FakeCapture([f"frame-{index}" for index in range(10)])

        result = self.analyze(model, capture, self.config(sample_interval_seconds=0.5))

        self.assertEqual(result.analyzed_frame_count, 2)
        self.assertEqual([call[0] for call in model.calls], ["frame-0", "frame-5"])
        self.assertEqual(len(result.detections), 1)
        detection = result.detections[0]
        self.assertEqual(detection.class_id, 0)
        self.assertEqual(detection.class_name, "person")
        self.assertEqual(detection.confidence, 0.9)
        self.assertEqual(detection.bbox_xyxy, (1.0, 2.0, 30.0, 40.0))
        self.assertEqual(detection.frame_index, 0)
        self.assertEqual(detection.timestamp_seconds, 0.0)
        self.assertIsNone(detection.brand_name)
        self.assertTrue(capture.released)

    def test_reports_progress_for_each_analyzed_sample(self):
        model = FakeModel({0: "person"}, {})
        capture = FakeCapture([f"frame-{index}" for index in range(10)])
        progress_updates = []

        analyze_video(
            Path("video.mp4"),
            self.config(sample_interval_seconds=0.5),
            model_loader=lambda _path: model,
            video_probe=lambda _path: self.metadata,
            cv2_loader=lambda: FakeOpenCV(capture),
            clock=iter((10.0, 10.5)).__next__,
            progress_callback=lambda completed, total: progress_updates.append((completed, total)),
        )

        self.assertEqual(progress_updates, [(1, 2), (2, 2)])

    def test_esceniq_mode_validates_catalog_and_maps_brands(self):
        boxes = FakeBoxes([0], [0.8], [[1, 2, 30, 40]])
        model = FakeModel(
            {0: "eggo", 1: "coca_cola", 2: "pepsi", 3: "fedex", 4: "wilson"},
            {"frame-0": [FakeResult(boxes)]},
        )
        capture = FakeCapture([f"frame-{index}" for index in range(10)])

        result = self.analyze(model, capture, self.config(mode=InferenceMode.ESCENIQ))

        self.assertEqual(result.detections[0].brand_name, "Eggo")

    def test_esceniq_mode_rejects_a_generic_model_before_reading_frames(self):
        model = FakeModel({0: "person"}, {})
        capture = FakeCapture(["frame-0"])

        with self.assertRaisesRegex(InferenceError, "cinco clases oficiales"):
            self.analyze(model, capture, self.config(mode=InferenceMode.ESCENIQ))
        self.assertEqual(capture.frames, ["frame-0"])

    def test_handles_video_without_detections(self):
        model = FakeModel({0: "person"}, {})
        capture = FakeCapture([f"frame-{index}" for index in range(10)])

        result = self.analyze(model, capture)

        self.assertEqual(result.analyzed_frame_count, 1)
        self.assertEqual(result.detections, ())

    def test_rejects_missing_model_and_invalid_parameters(self):
        model = FakeModel({0: "person"}, {})
        capture = FakeCapture([])
        with self.assertRaisesRegex(InferenceError, "pesos"):
            self.analyze(model, capture, InferenceConfig(Path("missing.pt")))
        with self.assertRaisesRegex(InferenceError, "confianza"):
            self.analyze(model, capture, self.config(confidence_threshold=1.1))
        with self.assertRaisesRegex(InferenceError, "intervalo"):
            self.analyze(model, capture, self.config(sample_interval_seconds=0))

    def test_reports_a_read_error_before_the_expected_frame_count(self):
        model = FakeModel({0: "person"}, {})
        capture = FakeCapture(["frame-0"])

        with self.assertRaisesRegex(InferenceError, "interrumpió"):
            self.analyze(model, capture)
        self.assertTrue(capture.released)

    def test_reports_inconsistent_boxes(self):
        model = FakeModel({0: "person"}, {"frame-0": [FakeResult(FakeBoxes([0], [], []))]})
        capture = FakeCapture([f"frame-{index}" for index in range(10)])

        with self.assertRaisesRegex(InferenceError, "inconsistentes"):
            self.analyze(model, capture)


if __name__ == "__main__":
    unittest.main()
