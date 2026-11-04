from types import SimpleNamespace
from unittest.mock import patch
import unittest

import app

from esceniq.vision import InferenceMode
from esceniq.vision.evidence import VisualEvidence


class AppPersistenceTests(unittest.TestCase):
    @patch.object(app, "SqliteAnalysisRepository")
    @patch.object(app, "calculate_exposure")
    def test_persists_completed_brand_analysis_with_existing_exposure(self, calculate_exposure, repository_type):
        result = SimpleNamespace(mode=InferenceMode.ESCENIQ)
        exposure = object()
        calculate_exposure.return_value = exposure
        repository_type.return_value.save_completed_analysis.return_value = "analysis-id"

        analysis_id = app.persist_completed_analysis(
            result, video_name="escena.mp4", analysis_key=("digest", "esceniq", 0.25, 1.0)
        )

        self.assertEqual(analysis_id, "analysis-id")
        calculate_exposure.assert_called_once_with(result)
        repository_type.return_value.save_completed_analysis.assert_called_once()
        arguments = repository_type.return_value.save_completed_analysis.call_args
        self.assertIs(arguments.args[0], result)
        self.assertIs(arguments.args[1], exposure)
        self.assertEqual(arguments.kwargs["video_name"], "escena.mp4")
        self.assertTrue(arguments.kwargs["deduplication_key"])

    @patch.object(app, "SqliteAnalysisRepository")
    @patch.object(app, "calculate_exposure")
    def test_persists_technical_result_without_brand_exposure(self, calculate_exposure, repository_type):
        result = SimpleNamespace(mode=InferenceMode.TECHNICAL_TEST)
        repository_type.return_value.save_completed_analysis.return_value = "analysis-id"

        app.persist_completed_analysis(result, video_name="escena.mp4", analysis_key=("digest", "technical"))

        calculate_exposure.assert_not_called()
        self.assertIsNone(repository_type.return_value.save_completed_analysis.call_args.args[1])

    @patch.object(app, "render_evidence_jpeg", return_value=b"annotated-jpeg")
    @patch.object(app, "EvidenceFileStore")
    @patch.object(app, "SqliteAnalysisRepository")
    def test_persists_existing_evidences_with_annotations_without_running_inference(
        self, repository_type, file_store_type, render_evidence
    ):
        evidence = VisualEvidence(10, 1.0, b"base-jpeg", 640, 480)
        detection = SimpleNamespace(frame_index=10, confidence=0.9, brand_name="Coca-Cola")
        result = SimpleNamespace(evidences=(evidence,), detections=(detection,))
        file_store_type.return_value.write.return_value = "analysis-id/frame_00000010.jpg"

        app.persist_analysis_evidences("analysis-id", result)

        render_evidence.assert_called_once_with(
            evidence,
            (detection,),
            show_labels=True,
            cv2=app.cv2,
        )
        file_store_type.return_value.write.assert_called_once_with("analysis-id", 10, b"annotated-jpeg")
        repository_type.return_value.save_evidence.assert_called_once_with(
            "analysis-id",
            frame_index=10,
            timestamp_seconds=1.0,
            brand_name="Coca-Cola",
            confidence=0.9,
            file_path="analysis-id/frame_00000010.jpg",
            review_status=evidence.review_status,
        )


if __name__ == "__main__":
    unittest.main()
