"""Regression checks for provider selection and artifact validation."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import download


class DownloadTests(unittest.TestCase):
    def test_bare_youtube_domain_uses_bgutils_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"YTDLP_BGUTIL_HOME": "/provider/server",
                                         "YTDLP_BROWSER_PATH": "", "YT_DLP_PROXY": ""}):
                with patch.object(sys, "argv", ["download.py", "https://youtube.com/watch?v=example",
                                                "--output-dir", directory]):
                    with patch.object(download.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
                        self.assertEqual(download.main(), 1)
                        self.assertEqual(run.call_count, 2)
                        self.assertIn("youtubepot-bgutilscript:server_home=/provider/server", run.call_args.args[0])

    def test_success_without_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, "argv", ["download.py", "https://example.com/video",
                                            "--output-dir", directory]):
                with patch.object(download.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
                    self.assertEqual(download.main(), 1)

    def test_file_without_video_stream_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "audio.mp4").write_bytes(b"audio")
            with patch.object(sys, "argv", ["download.py", "https://example.com/video",
                                            "--output-dir", directory]):
                with patch.object(download.subprocess, "run", side_effect=[
                    subprocess.CompletedProcess([], 0),
                    subprocess.CompletedProcess([], 0, '{"format":{"duration":"10"},"streams":[{"codec_type":"audio"}]}'),
                ]):
                    self.assertEqual(download.main(), 1)

    def test_probed_resolution_controls_acceptance(self):
        for height, expected in ((720, 0), (2160, 1)):
            with self.subTest(height=height), tempfile.TemporaryDirectory() as directory:
                Path(directory, "video.mp4").write_bytes(b"video")
                with patch.object(sys, "argv", ["download.py", "https://example.com/video",
                                                "--output-dir", directory]):
                    with patch.object(download.subprocess, "run", side_effect=[
                        subprocess.CompletedProcess([], 0),
                        subprocess.CompletedProcess([], 0,
                            '{"format":{"duration":"10"},"streams":[{"codec_type":"video","height":%d}]}' % height),
                    ]):
                        self.assertEqual(download.main(), expected)


if __name__ == "__main__":
    unittest.main()
