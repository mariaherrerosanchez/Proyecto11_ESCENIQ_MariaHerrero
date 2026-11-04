import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from esceniq.video.tempfiles import temporary_video_file
from esceniq.video.validation import VideoValidationError, probe_video


class FakeCapture:
    def __init__(self, *, opened=True, values=None, decoded=True):
        self.opened = opened
        self.values = values or {1: 25.0, 2: 100.0, 3: 1920.0, 4: 1080.0}
        self.decoded = decoded
        self.released = False

    def isOpened(self):
        return self.opened

    def get(self, property_id):
        return self.values[property_id]

    def read(self):
        return (True, object()) if self.decoded else (False, None)

    def release(self):
        self.released = True


class FakeOpenCV:
    CAP_PROP_FPS = 1
    CAP_PROP_FRAME_COUNT = 2
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4

    def __init__(self, capture):
        self.capture = capture

    def VideoCapture(self, _path):
        return self.capture


class VideoValidationTests(unittest.TestCase):
    def temporary_file(self, suffix=".mp4", contents=b"video"):
        temporary = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temporary.write(contents)
        temporary.close()
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_returns_metadata_after_opening_and_decoding_a_frame(self):
        capture = FakeCapture()
        with patch("esceniq.video.validation._load_opencv", return_value=FakeOpenCV(capture)):
            metadata = probe_video(self.temporary_file())
        self.assertEqual(metadata.resolution, "1920 × 1080")
        self.assertEqual(metadata.frame_count, 100)
        self.assertEqual(metadata.duration_seconds, 4.0)
        self.assertTrue(capture.released)

    def test_rejects_missing_empty_and_non_mp4_files(self):
        with self.assertRaisesRegex(VideoValidationError, "extensión"):
            probe_video(self.temporary_file(".avi"))
        with self.assertRaisesRegex(VideoValidationError, "vacío"):
            probe_video(self.temporary_file(contents=b""))
        with self.assertRaisesRegex(VideoValidationError, "No se encontró"):
            probe_video(Path("missing.mp4"))

    def test_rejects_invalid_metadata_and_failed_decoding(self):
        path = self.temporary_file()
        for values, decoded, message in [
            ({1: 0.0, 2: 100.0, 3: 1920.0, 4: 1080.0}, True, "FPS"),
            ({1: 25.0, 2: 0.0, 3: 1920.0, 4: 1080.0}, True, "fotogramas"),
            ({1: 25.0, 2: 100.0, 3: 0.0, 4: 1080.0}, True, "ancho"),
            ({1: 25.0, 2: 100.0, 3: 1920.0, 4: 1080.0}, False, "decodificar"),
        ]:
            with self.subTest(message=message), patch(
                "esceniq.video.validation._load_opencv", return_value=FakeOpenCV(FakeCapture(values=values, decoded=decoded))
            ):
                with self.assertRaisesRegex(VideoValidationError, message):
                    probe_video(path)

    def test_rejects_a_video_that_opencv_cannot_open(self):
        capture = FakeCapture(opened=False)
        with patch("esceniq.video.validation._load_opencv", return_value=FakeOpenCV(capture)):
            with self.assertRaisesRegex(VideoValidationError, "No se pudo abrir"):
                probe_video(self.temporary_file())
        self.assertTrue(capture.released)

    def test_temporary_video_file_is_removed_after_use(self):
        with temporary_video_file(b"video") as path:
            self.assertTrue(path.is_file())
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
