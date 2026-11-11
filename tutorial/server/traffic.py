"""Generate one minute of traffic for the workshop dashboards."""

import argparse
import http.client
import json
import os
import socket
import threading
import time
from urllib.parse import urlsplit


PROMPT = "Explain how Kubernetes schedules a Pod onto a GPU node. Give a detailed example."


def run_traffic(base_url, model, concurrency, duration=60, request_timeout=30):
    endpoint = urlsplit(base_url)
    if endpoint.scheme not in ("http", "https") or not endpoint.hostname or endpoint.query or endpoint.fragment:
        raise ValueError("VLLM_BASE_URL must be an HTTP or HTTPS base URL.")
    connection_type = http.client.HTTPSConnection if endpoint.scheme == "https" else http.client.HTTPConnection
    port = endpoint.port
    target = endpoint.path.rstrip("/") + "/v1/chat/completions"
    body = json.dumps({
        "model": model, "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 256, "temperature": 0,
    }).encode()
    stop, lock = threading.Event(), threading.Lock()
    active = set()
    completed = failed = output_tokens = 0
    started = time.monotonic()
    deadline = started + duration

    def worker():
        nonlocal completed, failed, output_tokens
        while not stop.is_set() and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            connection = connection_type(endpoint.hostname, port, timeout=min(request_timeout, remaining))
            transport = None
            try:
                connection.connect()
                transport = connection.sock
                with lock:
                    if stop.is_set() or time.monotonic() >= deadline:
                        return
                    active.add(transport)
                connection.request("POST", target, body, {"Content-Type": "application/json"})
                with connection.getresponse() as response:
                    if response.status != 200:
                        raise ValueError(f"Upstream returned HTTP {response.status}")
                    result = json.loads(response.read(1_048_576))
                tokens = result["usage"]["completion_tokens"]
                if type(tokens) is not int or tokens < 0:
                    raise ValueError("Missing valid completion token usage.")
                with lock:
                    if not stop.is_set() and time.monotonic() < deadline:
                        completed += 1
                        output_tokens += tokens
            except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError):
                with lock:
                    if not stop.is_set() and time.monotonic() < deadline:
                        failed += 1
                stop.wait(0.1)
            finally:
                with lock:
                    active.discard(transport)
                connection.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(concurrency)]
    interrupted = False
    try:
        for thread in threads:
            thread.start()
        stop.wait(max(0, deadline - time.monotonic()))
    except KeyboardInterrupt:
        interrupted = True
    finally:
        stop.set()
        with lock:
            transports = list(active)
        for transport in transports:
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        join_deadline = time.monotonic() + 1
        for thread in threads:
            if thread.ident is not None:
                thread.join(max(0, join_deadline - time.monotonic()))
    elapsed = max(time.monotonic() - started, 0.001)
    return {"completed": completed, "failed": failed,
            "output_tokens_per_second": output_tokens / elapsed, "interrupted": interrupted}


def main():
    parser = argparse.ArgumentParser(description="Run traffic for 60 seconds, with a 256-token output limit per request.")
    parser.add_argument("--concurrency", type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    base_url, model = os.environ.get("VLLM_BASE_URL"), os.environ.get("VLLM_MODEL")
    if not base_url or not model:
        parser.error("Set VLLM_BASE_URL and VLLM_MODEL before starting traffic.")
    try:
        result = run_traffic(base_url, model, args.concurrency)
    except ValueError as exc:
        parser.error(str(exc))
    print(f'completed={result["completed"]} failed={result["failed"]} '
          f'output_tokens_per_second={result["output_tokens_per_second"]:.2f}', flush=True)
    return 130 if result["interrupted"] else int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
