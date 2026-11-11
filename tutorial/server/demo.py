"""Serve the workshop's streaming chat page on localhost:8080."""

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class DemoHandler(BaseHTTPRequestHandler):
    api_url = os.environ["VLLM_BASE_URL"].rstrip("/")
    model_name = os.environ.get("VLLM_MODEL", "Qwen/Qwen3.5-0.8B")
    try:
        max_output_tokens = int(os.environ.get("VLLM_MAX_OUTPUT_TOKENS", "512"))
        if max_output_tokens < 1:
            raise ValueError
    except ValueError:
        raise ValueError("VLLM_MAX_OUTPUT_TOKENS must be a positive integer.") from None

    def error(self, status, message):
        body = json.dumps({"error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path != "/":
            self.error(404, "Page not found.")
            return
        page = Path(__file__).with_name("demo.html").read_text()
        page = page.replace("{{MAX_OUTPUT_TOKENS}}", str(self.max_output_tokens))
        page = page.replace("{{DEFAULT_OUTPUT_TOKENS}}", str(min(128, self.max_output_tokens)))
        body = page.replace("{{MODEL_NAME}}", html.escape(self.model_name)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlsplit(self.path).path != "/chat":
            self.error(404, "Endpoint not found.")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("Enter a prompt of at most 8,000 characters.")
            fields = json.loads(self.rfile.read(length))
            prompt = fields.get("prompt", "")
            maximum = fields.get("max_tokens", min(128, self.max_output_tokens))
            temperature = fields.get("temperature", 0.7)
            if not isinstance(prompt, str) or not 0 < len(prompt.strip()) <= 8000:
                raise ValueError("Enter a prompt of at most 8,000 characters.")
            if type(maximum) is not int or not 1 <= maximum <= self.max_output_tokens:
                raise ValueError(f"Max output tokens must be between 1 and {self.max_output_tokens}.")
            if type(temperature) not in (int, float) or not 0 <= temperature <= 2:
                raise ValueError("Temperature must be between 0 and 2.")
        except (ValueError, AttributeError) as exc:
            self.error(400, str(exc))
            return
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": maximum, "temperature": temperature,
            "stream": True, "stream_options": {"include_usage": True},
        }
        request = Request(self.api_url + "/v1/chat/completions",
                          data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            upstream = urlopen(request, timeout=60)
        except HTTPError as exc:
            with exc:
                self.error(502, f"vLLM returned HTTP {exc.code}: " + exc.read(2048).decode(errors="replace"))
            return
        except (URLError, TimeoutError) as exc:
            self.error(503, f"Cannot reach vLLM at {self.api_url}. Check model readiness and VLLM_BASE_URL. {exc}")
            return
        with upstream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store, no-transform")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                for line in upstream:
                    self.wfile.write(line)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except OSError as exc:
                self.log_error("Stream stopped: %s", exc)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8080), DemoHandler) as server:
        print("Streaming demo: http://127.0.0.1:8080/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nDemo server stopped.")
