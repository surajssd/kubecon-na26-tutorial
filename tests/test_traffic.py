from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


SCRIPT = Path(__file__).resolve().parents[1] / "tutorial/server/traffic.py"
RUN = runpy.run_path(str(SCRIPT))["run_traffic"]


class TrafficTest(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.release, self.received = threading.Event(), threading.Event()
        self.lock = threading.Lock()
        self.mode = "success"
        self.active = self.peak = 0
        owner = self

        class Upstream(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with owner.lock:
                    owner.requests.append((self.path, payload))
                    owner.active += 1
                    owner.peak = max(owner.peak, owner.active)
                owner.received.set()
                try:
                    if owner.mode == "timeout":
                        owner.release.wait(3)
                    if owner.mode == "error":
                        self.send_error(503)
                        return
                    data = json.dumps({"usage": {"completion_tokens": 32}}).encode()
                    if owner.mode == "bad-usage":
                        data = b'{"usage":{}}'
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    if owner.mode == "trickle":
                        for byte in data:
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                            time.sleep(.02)
                    else:
                        time.sleep(.03)
                        self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with owner.lock:
                        owner.active -= 1

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/"
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.release.set)

    def test_success_uses_the_selected_model_and_actual_output_usage(self):
        result = RUN(self.url, "workshop-model", 1, duration=.2)
        self.assertGreater(result["completed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertGreater(result["output_tokens_per_second"], 0)
        self.assertLess(result["output_tokens_per_second"], result["completed"] * 256 / .2)
        for path, payload in self.requests:
            self.assertEqual(path, "/v1/chat/completions")
            self.assertEqual(payload["model"], "workshop-model")
            self.assertEqual(payload["max_tokens"], 256)
            self.assertEqual(payload["temperature"], 0)
            self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(len({p["messages"][0]["content"] for _, p in self.requests}), 1)

    def test_upstream_errors_and_missing_usage_are_counted(self):
        for mode in ("error", "bad-usage"):
            with self.subTest(mode=mode):
                self.mode = mode
                result = RUN(self.url, "model", 1, duration=.2)
                self.assertEqual(result["completed"], 0)
                self.assertGreater(result["failed"], 0)
                self.assertEqual(result["output_tokens_per_second"], 0)

    def test_request_timeout_is_counted(self):
        self.mode = "timeout"
        result = RUN(self.url, "model", 1, duration=.2, request_timeout=.03)
        self.assertEqual(result["completed"], 0)
        self.assertGreater(result["failed"], 0)

    def test_deadline_cancels_a_response_that_keeps_sending_bytes(self):
        self.mode = "trickle"
        started = time.monotonic()
        result = RUN(self.url, "model", 1, duration=.12, request_timeout=.1)
        self.assertLess(time.monotonic() - started, .8)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["failed"], 0)

    def test_concurrency_is_bounded_and_launches_stop_at_the_deadline(self):
        for concurrency in (1, 4):
            with self.subTest(concurrency=concurrency):
                self.peak = 0
                RUN(self.url, "model", concurrency, duration=.2)
                self.assertEqual(self.peak, concurrency)
                count = len(self.requests)
                time.sleep(.05)
                self.assertEqual(len(self.requests), count)

    def test_ctrl_c_prints_one_summary_and_exits_without_a_traceback(self):
        self.mode = "timeout"
        process = subprocess.Popen(
            [sys.executable, "-B", str(SCRIPT), "--concurrency", "4"],
            env={**os.environ, "VLLM_BASE_URL": self.url, "VLLM_MODEL": "model"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        self.assertTrue(self.received.wait(5), "Traffic did not reach the upstream")
        process.send_signal(signal.SIGINT)
        output, error = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 130)
        self.assertEqual(error, "")
        self.assertEqual(len(output.splitlines()), 1)
        self.assertRegex(output, r"^completed=\d+ failed=\d+ output_tokens_per_second=\d+\.\d{2}\n$")

    def test_cli_rejects_missing_configuration_and_unsupported_concurrency(self):
        for environment, arguments in (({}, []), ({"VLLM_BASE_URL": "not-a-url", "VLLM_MODEL": "model"}, []),
                                       ({"VLLM_BASE_URL": self.url, "VLLM_MODEL": "model"}, ["--concurrency", "2"])):
            with self.subTest(arguments=arguments, environment=environment):
                process = subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments], env=environment,
                                         capture_output=True, text=True, timeout=3)
                self.assertEqual(process.returncode, 2)
                self.assertIn("error:", process.stderr)
                self.assertNotIn("Traceback", process.stderr)
        self.assertEqual(self.requests, [])
