import base64
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import server


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.PASSWORD = "test-password"
        cls.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, auth=True):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = "Basic " + base64.b64encode(b"admin:test-password").decode()
        connection = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port)
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_authentication_and_health(self):
        self.assertEqual(self.request("GET", "/health", auth=False)[0], 200)
        self.assertEqual(self.request("GET", "/", auth=False)[0], 401)
        self.assertEqual(self.request("GET", "/")[0], 200)

    def test_rejects_non_youtube_urls_before_launching_process(self):
        with patch.object(server.subprocess, "run") as run:
            for url in ("http://youtube.com/watch?v=x", "https://127.0.0.1/",
                        "https://youtube.com.evil.test/", "https://user:pass@youtube.com/",
                        "https://youtube.com:8080/"):
                self.assertEqual(self.request("POST", "/probe", json.dumps({"url": url}))[0], 400)
            run.assert_not_called()

    def test_reports_bot_failure(self):
        result = server.subprocess.CompletedProcess([], 1, "", "Sign in to confirm you are not a bot")
        with patch.object(server.subprocess, "run", return_value=result):
            status, body = self.request("POST", "/probe", json.dumps({"url": "https://youtu.be/jNQXAC9IVRw"}))
        self.assertEqual(status, 422)
        self.assertFalse(json.loads(body)["ok"])


if __name__ == "__main__":
    unittest.main()
