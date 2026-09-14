from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from cough_analysis.service import analyze_audio_path


class AnalyzeServiceTests(SimpleTestCase):
    @patch("cough_analysis.service.predict_scores", return_value=[.2, .8])
    @patch("cough_analysis.service.extract_features", return_value={})
    @patch("cough_analysis.service.load_segmentation_model")
    @patch("cough_analysis.service.detect_segments", return_value=[(0, 1600), (3200, 4800)])
    @patch("cough_analysis.service.load_audio", return_value=np.ones(4800, dtype=np.float32))
    def test_scores_each_cough_and_returns_mean(self, *_mocks):
        result = analyze_audio_path("sample.wav")
        self.assertEqual(result["cough_count"], 2)
        self.assertEqual(result["average_positive_score"], .5)
        self.assertEqual([item["positive_score"] for item in result["coughs"]], [.2, .8])

    @patch("cough_analysis.service.load_segmentation_model")
    @patch("cough_analysis.service.detect_segments", return_value=[])
    @patch("cough_analysis.service.load_audio", return_value=np.ones(1600, dtype=np.float32))
    def test_no_cough_has_no_average(self, *_mocks):
        result = analyze_audio_path("sample.wav")
        self.assertEqual(result, {"cough_count": 0, "average_positive_score": None, "coughs": []})
