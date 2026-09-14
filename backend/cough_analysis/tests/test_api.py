from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase


class AnalyzeCoughApiTests(SimpleTestCase):
    def test_audio_is_required(self):
        self.assertEqual(self.client.post("/api/cough-check/analyze/").status_code, 400)

    @patch("cough_analysis.views.analyze_uploaded_audio")
    def test_returns_analysis(self, analyze):
        analyze.return_value = {"cough_count": 2, "average_positive_score": .5, "coughs": []}
        audio = SimpleUploadedFile("sample.wav", b"RIFFtest", content_type="audio/wav")
        response = self.client.post("/api/cough-check/analyze/", {"audio": audio})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["average_positive_score"], .5)

    def test_rejects_unsupported_extension(self):
        upload = SimpleUploadedFile("sample.txt", b"text", content_type="text/plain")
        self.assertEqual(self.client.post("/api/cough-check/analyze/", {"audio": upload}).status_code, 415)
