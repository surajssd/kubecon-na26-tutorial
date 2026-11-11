import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEMO = Path(__file__).resolve().parents[1] / "tutorial/server/demo.py"


class StreamingDemoTest(unittest.TestCase):
    def setUp(self):
        self.release = threading.Event()
        self.requests = []
        self.failure = False
        self.first_chunk = b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        self.last_chunk = b'data: {"choices":[],"usage":{"completion_tokens":1}}\n\ndata: [DONE]\n\n'
        fixture = self

        class Model(BaseHTTPRequestHandler):
            def do_POST(self):
                fixture.requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                if fixture.failure:
                    self.send_error(503, "Model unavailable")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(fixture.first_chunk)
                self.wfile.flush()
                fixture.release.wait(3)
                self.wfile.write(fixture.last_chunk)

            def log_message(self, *args):
                pass

        model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
        with patch.dict("os.environ", {"VLLM_BASE_URL": f"http://127.0.0.1:{model.server_port}/"}, clear=True):
            handler = runpy.run_path(str(DEMO))["DemoHandler"]
        self.handler = handler
        demo = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        for server in (model, demo):
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
        self.addCleanup(self.release.set)
        self.url = f"http://127.0.0.1:{demo.server_port}"

    def chat(self, **fields):
        return urlopen(Request(self.url + "/chat", data=json.dumps(fields).encode(),
                               headers={"Content-Type": "application/json"}), timeout=2)

    def test_page_does_not_contact_model_when_opened(self):
        with urlopen(self.url + "/?browser=embedded", timeout=2) as response:
            page = response.read()
            self.assertIn(b">Generate</button>", page)
            self.assertIn(b'max="512" value="128"', page)
        self.assertEqual(self.requests, [])

    def test_default_output_limit_is_enforced(self):
        self.release.set()
        with self.chat(prompt="Hello", max_tokens=512) as response:
            self.assertIn(b"data: [DONE]", response.read())
        self.assertEqual(self.requests[0]["max_tokens"], 512)
        for maximum in (513, 0, -1, True, 1.5):
            with self.subTest(max_tokens=maximum):
                with self.assertRaises(HTTPError) as caught:
                    self.chat(prompt="Hello", max_tokens=maximum)
                with caught.exception as response:
                    self.assertEqual(response.code, 400)
                    self.assertEqual(json.load(response)["error"],
                                     "Max output tokens must be between 1 and 512.")
        self.assertEqual(len(self.requests), 1)

    def test_configured_output_limit_is_shown_and_enforced(self):
        self.release.set()
        for limit in (64, 1024):
            with self.subTest(limit=limit):
                self.requests.clear()
                with patch.dict("os.environ", {"VLLM_BASE_URL": self.handler.api_url,
                                               "VLLM_MAX_OUTPUT_TOKENS": str(limit)}, clear=True):
                    configured = runpy.run_path(str(DEMO))["DemoHandler"]
                self.handler.max_output_tokens = configured.max_output_tokens
                with urlopen(self.url + "/", timeout=2) as response:
                    self.assertIn(f'max="{limit}" value="{min(128, limit)}"'.encode(), response.read())
                self.assertEqual(self.requests, [])
                with self.chat(prompt="Hello") as response:
                    self.assertIn(b"data: [DONE]", response.read())
                self.assertEqual(self.requests[0]["max_tokens"], min(128, limit))
                with self.chat(prompt="Hello", max_tokens=limit) as response:
                    self.assertIn(b"data: [DONE]", response.read())
                self.assertEqual(self.requests[1]["max_tokens"], limit)
                with self.assertRaises(HTTPError) as caught:
                    self.chat(prompt="Hello", max_tokens=limit + 1)
                with caught.exception as response:
                    self.assertEqual(response.code, 400)
                    self.assertEqual(json.load(response)["error"],
                                     f"Max output tokens must be between 1 and {limit}.")
                self.assertEqual(len(self.requests), 2)

    def test_invalid_output_limit_configuration_is_rejected(self):
        for limit in ("0", "-1", "abc", "1.5", ""):
            with self.subTest(limit=limit):
                with patch.dict("os.environ", {"VLLM_BASE_URL": self.handler.api_url,
                                               "VLLM_MAX_OUTPUT_TOKENS": limit}, clear=True):
                    with self.assertRaisesRegex(ValueError, "VLLM_MAX_OUTPUT_TOKENS must be a positive integer"):
                        runpy.run_path(str(DEMO))
        self.assertEqual(self.requests, [])

    def test_stream_arrives_before_model_finishes_and_includes_usage(self):
        with self.chat(prompt="Hello", max_tokens=64, temperature=0) as response:
            self.assertEqual(response.headers["Content-Type"], "text/event-stream")
            self.assertIn("no-transform", response.headers["Cache-Control"])
            self.assertIn(b'"content":"Hello"', response.readline())
            self.assertFalse(self.release.is_set())
            self.release.set()
            remaining = response.read()
            self.assertIn(b'"completion_tokens":1', remaining)
            self.assertIn(b"data: [DONE]", remaining)
        self.assertTrue(self.requests[0]["stream"])
        self.assertEqual(self.requests[0]["stream_options"], {"include_usage": True})
        self.assertEqual(self.requests[0]["model"], "Qwen/Qwen3.5-0.8B")

    def test_configured_model_is_shown_and_used_for_streaming(self):
        model = "google/gemma-4-31B-it"
        with patch.dict("os.environ", {"VLLM_MODEL": model, "VLLM_BASE_URL": self.handler.api_url}):
            configured = runpy.run_path(str(DEMO))["DemoHandler"]
        self.handler.model_name = configured.model_name
        with urlopen(self.url + "/", timeout=2) as response:
            self.assertIn(model.encode(), response.read())
        self.assertEqual(self.requests, [])
        self.release.set()
        with self.chat(prompt="Hello") as response:
            self.assertIn(b"data: [DONE]", response.read())
        self.assertEqual(self.requests[0]["model"], model)

    def test_reasoning_streams_before_the_answer(self):
        for field in ("reasoning", "reasoning_content"):
            with self.subTest(field=field):
                self.release.clear()
                self.first_chunk = ("data: " + json.dumps({
                    "choices": [{"delta": {field: "Let me think. <script>alert(1)</script>"}}],
                }) + "\n\n").encode()
                self.last_chunk = (
                    b'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":"stop"}]}\n\n'
                    b'data: {"choices":[],"usage":{"completion_tokens":8}}\n\ndata: [DONE]\n\n'
                )
                with self.chat(prompt="Hello") as response:
                    self.assertEqual(response.headers["X-Accel-Buffering"], "no")
                    self.assertEqual(response.readline(), self.first_chunk.splitlines(keepends=True)[0])
                    self.assertFalse(self.release.is_set())
                    self.release.set()
                    remaining = response.read()
                    self.assertIn(b'"content":"Hello"', remaining)
                    self.assertIn(b'"finish_reason":"stop"', remaining)
                    self.assertIn(b'"completion_tokens":8', remaining)
                self.assertNotIn("chat_template_kwargs", self.requests[-1])

    def test_reasoning_only_stream_preserves_the_output_limit_finish_reason(self):
        self.first_chunk = b'data: {"choices":[{"delta":{"reasoning":"Still thinking."}}]}\n\n'
        self.last_chunk = (
            b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\n'
            b'data: {"choices":[],"usage":{"completion_tokens":128}}\n\ndata: [DONE]\n\n'
        )
        self.release.set()
        with self.chat(prompt="Hello", max_tokens=128) as response:
            body = response.read()
        self.assertIn(self.first_chunk, body)
        self.assertIn(self.last_chunk, body)
        self.assertNotIn(b'"content"', body)

    def test_model_name_is_escaped_in_the_page(self):
        self.handler.model_name = '<script>alert("model")</script>'
        with urlopen(self.url + "/", timeout=2) as response:
            page = response.read()
        self.assertIn(b"&lt;script&gt;alert(&quot;model&quot;)&lt;/script&gt;", page)
        self.assertNotIn(self.handler.model_name.encode(), page)
        self.assertEqual(self.requests, [])

    def test_invalid_input_does_not_contact_model(self):
        with self.assertRaises(HTTPError) as caught:
            self.chat(prompt=" ")
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        self.assertEqual(self.requests, [])

    def test_model_errors_are_reported_before_streaming(self):
        self.failure = True
        with self.assertRaises(HTTPError) as caught:
            self.chat(prompt="Hello")
        with caught.exception as response:
            self.assertEqual(response.code, 502)
            self.assertIn("vLLM returned HTTP 503", json.load(response)["error"])

    def test_unreachable_model_reports_configured_url(self):
        self.handler.api_url = "http://127.0.0.1:0"
        with self.assertRaises(HTTPError) as caught:
            self.chat(prompt="Hello")
        with caught.exception as response:
            self.assertEqual(response.code, 503)
            message = json.load(response)["error"]
            self.assertIn(self.handler.api_url, message)
            self.assertIn("Check model readiness and VLLM_BASE_URL.", message)


class DemoServerTest(unittest.TestCase):
    def test_ctrl_c_exits_cleanly(self):
        with subprocess.Popen(
            [sys.executable, str(DEMO)],
            env={**os.environ, "VLLM_BASE_URL": "http://127.0.0.1:0",
                 "VLLM_MAX_OUTPUT_TOKENS": "512"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) as process:
            try:
                deadline = time.monotonic() + 5
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        with urlopen("http://127.0.0.1:8080/", timeout=0.1) as response:
                            self.assertEqual(response.status, 200)
                        break
                    except URLError:
                        time.sleep(0.02)
                else:
                    self.fail("Demo server did not start within five seconds.")
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=5)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("KeyboardInterrupt", stderr)
        self.assertEqual(process.returncode, 0, stdout + stderr)


if __name__ == "__main__":
    unittest.main()
