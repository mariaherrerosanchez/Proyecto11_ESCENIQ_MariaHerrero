from types import SimpleNamespace
from unittest.mock import patch
import unittest

import app

from esceniq.vision import InferenceMode


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


if __name__ == "__main__":
    unittest.main()
