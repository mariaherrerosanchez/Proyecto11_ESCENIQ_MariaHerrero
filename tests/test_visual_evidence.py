import unittest

from esceniq.vision import Detection
from esceniq.vision.evidence import (
    AUTOMATIC_REVIEW_STATUS,
    EvidenceCollector,
    evidence_slot,
    render_evidence_jpeg,
    visible_detections,
)


class FakeFrame:
    shape = (1080, 1920, 3)


class FakeOpenCV:
    FONT_HERSHEY_SIMPLEX = 0
    LINE_AA = 0
    IMWRITE_JPEG_QUALITY = 1
    IMREAD_COLOR = 1

    def __init__(self):
        self.rectangles = []
        self.labels = []
        self.resize_sizes = []

    def resize(self, frame, size):
        self.resize_sizes.append(size)
        return frame

    def imdecode(self, _source, _mode):
        return FakeFrame()

    def rectangle(self, _image, start, end, *_args):
        self.rectangles.append((start, end))

    def putText(self, _image, label, *_args):
        self.labels.append(label)

    def imencode(self, _extension, _image, _options):
        return True, bytearray(b"jpeg")


def detection(frame_index, timestamp, confidence, *, brand_name="Eggo", class_name="eggo"):
    return Detection(0, class_name, confidence, (10.0, 20.0, 100.0, 120.0), frame_index, timestamp, brand_name)


class VisualEvidenceTests(unittest.TestCase):
    def test_slots_are_distributed_over_the_full_video(self):
        self.assertEqual(evidence_slot(0, 240), 0)
        self.assertEqual(evidence_slot(120, 240), 12)
        self.assertEqual(evidence_slot(239, 240), 23)

    def test_collector_limits_frames_without_drawing_or_duplicating_detections(self):
        cv2 = FakeOpenCV()
        collector = EvidenceCollector(240, cv2)
        for index in range(0, 240, 10):
            collector.add(FakeFrame(), (detection(index, index / 10, 0.60),))

        evidences = collector.build()

        self.assertLessEqual(len(evidences), 24)
        self.assertEqual(cv2.rectangles, [])
        self.assertEqual(cv2.labels, [])
        self.assertTrue(all(item.source_jpeg == b"jpeg" for item in evidences))
        self.assertTrue(all(width <= 960 and height <= 540 for width, height in cv2.resize_sizes))
        self.assertEqual(evidences[0].review_status, AUTOMATIC_REVIEW_STATUS)

    def test_visual_filter_and_label_toggle_do_not_change_original_detections(self):
        cv2 = FakeOpenCV()
        collector = EvidenceCollector(10, cv2)
        original = (detection(0, 0.0, 0.40), detection(0, 0.0, 0.90, brand_name="Coca-Cola", class_name="coca_cola"))
        collector.add(FakeFrame(), original)
        evidence = collector.build()[0]

        visible = visible_detections(original, 0.80)
        rendered = render_evidence_jpeg(evidence, visible, show_labels=False, cv2=cv2)

        self.assertEqual(rendered, b"jpeg")
        self.assertEqual(len(visible), 1)
        self.assertEqual(len(cv2.rectangles), 1)
        self.assertEqual(cv2.labels, [])
        self.assertEqual(original[0].confidence, 0.40)
        self.assertEqual(len(original), 2)

        render_evidence_jpeg(evidence, visible, show_labels=True, cv2=cv2)
        self.assertEqual(len(cv2.labels), 1)
        self.assertIn("90%", cv2.labels[0])

    def test_higher_confidence_replaces_evidence_in_the_same_temporal_slot(self):
        collector = EvidenceCollector(100, FakeOpenCV())
        collector.add(FakeFrame(), (detection(1, 0.1, 0.40),))
        collector.add(FakeFrame(), (detection(2, 0.2, 0.80),))

        evidences = collector.build()

        self.assertEqual(len(evidences), 1)
        self.assertEqual(evidences[0].frame_index, 2)


if __name__ == "__main__":
    unittest.main()
