from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esceniq.analytics import TimelineError, build_appearance_intervals


def detection(brand_name: str | None, frame_index: int, timestamp_seconds: float):
    return SimpleNamespace(
        brand_name=brand_name,
        frame_index=frame_index,
        timestamp_seconds=timestamp_seconds,
    )


class AppearanceTimelineTests(unittest.TestCase):
    def test_merges_consecutive_samples_and_keeps_separate_appearances(self):
        intervals = build_appearance_intervals(
            (
                detection("Eggo", 0, 0.0),
                detection("Eggo", 0, 0.0),
                detection("Eggo", 10, 1.0),
                detection("Eggo", 30, 3.0),
                detection("Coca-Cola", 10, 1.0),
            ),
            duration_seconds=4.0,
            sample_interval_seconds=1.0,
        )

        self.assertEqual(
            intervals,
            (
                intervals[0].__class__("Coca-Cola", 1.0, 2.0, 1),
                intervals[0].__class__("Eggo", 0.0, 2.0, 2),
                intervals[0].__class__("Eggo", 3.0, 4.0, 1),
            ),
        )

    def test_limits_the_last_interval_to_the_real_video_duration(self):
        interval = build_appearance_intervals(
            (detection("Eggo", 24, 2.4),),
            duration_seconds=2.5,
            sample_interval_seconds=1.0,
        )[0]

        self.assertEqual((interval.start_seconds, interval.end_seconds), (2.4, 2.5))
        self.assertAlmostEqual(interval.estimated_seconds, 0.1)

    def test_returns_no_intervals_without_brand_detections(self):
        intervals = build_appearance_intervals(
            (detection(None, 0, 0.0),), duration_seconds=3.0, sample_interval_seconds=1.0
        )

        self.assertEqual(intervals, ())

    def test_accepts_sqlite_compatible_detection_objects(self):
        stored_detection = SimpleNamespace(brand_name="Coca-Cola", frame_index=5, timestamp_seconds=0.5)

        intervals = build_appearance_intervals(
            (stored_detection,), duration_seconds=2.0, sample_interval_seconds=1.0
        )

        self.assertEqual(intervals[0].brand_name, "Coca-Cola")
        self.assertEqual((intervals[0].start_seconds, intervals[0].end_seconds), (0.5, 1.5))

    def test_rejects_incomplete_temporal_context(self):
        with self.assertRaisesRegex(TimelineError, "duración"):
            build_appearance_intervals((), duration_seconds=0.0, sample_interval_seconds=1.0)


if __name__ == "__main__":
    unittest.main()
