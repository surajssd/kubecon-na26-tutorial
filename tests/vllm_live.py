import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import runpy
import select
import subprocess
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LESSONS = {"01": "01-vllm", "02": "02-tensor-parallel", "03": "03-pipeline-parallel"}
IMAGE = re.compile(r"vllm/vllm-openai:v(\d+\.\d+\.\d+)@sha256:[a-f0-9]{64}")


def manifest(lesson, image=None):
    text = (ROOT / "tutorial" / LESSONS[lesson] / "vllm.yaml").read_text()
    images = re.findall(r"^\s+image:\s+(\S+)\s*$", text, re.MULTILINE)
    if len(set(images)) != 1 or not all(IMAGE.fullmatch(value) for value in images):
        raise ValueError("Each lesson must use one pinned vLLM image.")
    if image is not None:
        if not IMAGE.fullmatch(image):
            raise ValueError("Use vllm/vllm-openai:vX.Y.Z@sha256:<64 lowercase hex digits>.")
        text = IMAGE.sub(image, text)
    return text, IMAGE.search(text).group(1)


def check_idle(document):
    if document["items"]:
        raise RuntimeError("Use an idle workload namespace without Pods, workloads, or Services.")


def check_stream(response):
    content, finish, usage, done = "", None, None, False
    for line in response:
        if not line.startswith(b"data: "):
            continue
        if line.strip() == b"data: [DONE]":
            done = True
            break
        chunk = json.loads(line[6:])
        if chunk.get("usage"):
            usage = chunk["usage"]
        for choice in chunk.get("choices", []):
            content += choice.get("delta", {}).get("content") or ""
            finish = choice.get("finish_reason") or finish
    assert done, "Stream ended without [DONE]."
    assert finish == "stop", f"Incomplete stream: {finish!r}."
    assert usage and usage.get("completion_tokens", 0) > 0, "Missing output usage."
    assert re.search(r"\b4\b", content), f"Expected an arithmetic answer containing 4: {content!r}."
    assert not any(token in content for token in ("<|", "<think>", "</think>")), content


class LiveLesson(unittest.TestCase):
    def __init__(self, lesson, kube, image, timeout):
        super().__init__("runTest")
        self.lesson, self.kube, self.timeout = lesson, kube, timeout
        self.text, self.version = manifest(lesson, image)

    def shortDescription(self):
        return f"Live lesson {self.lesson}, vLLM {self.version}"

    def command(self, *arguments, stdin=None, timeout=60):
        result = subprocess.run([*self.kube, *arguments], input=stdin, text=True,
                                capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError(f"kubectl {' '.join(arguments)}: {result.stderr}{result.stdout}")
        return result.stdout

    def get(self, *arguments):
        return json.loads(self.command("get", *arguments, "-o", "json"))

    def wait_idle(self):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            pods = self.get("pods")["items"]
            quotas = self.get("resourcequota")["items"]
            if not pods and all(q["status"].get("used", {}).get("requests.nvidia.com/gpu", "0") == "0"
                                for q in quotas):
                return
            time.sleep(2)
        raise TimeoutError("Cleanup did not release Pods and GPU quota within 180 seconds.")

    def cleanup(self):
        self.command("delete", "-f", "-", "--ignore-not-found", "--timeout=180s",
                     stdin=self.text, timeout=210)
        self.wait_idle()
        print(f"\nLesson {self.lesson}: cleanup passed", flush=True)

    def forward(self, service):
        process = subprocess.Popen([*self.kube, "port-forward", f"service/{service}", ":8000",
                                    "--address=127.0.0.1"], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)

        def stop():
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()

        self.addCleanup(stop)
        deadline, output = time.monotonic() + 30, ""
        while time.monotonic() < deadline and process.poll() is None:
            if select.select([process.stdout], [], [], 1)[0]:
                output += process.stdout.readline()
                match = re.search(r"Forwarding from 127\.0\.0\.1:(\d+)", output)
                if match:
                    return f"http://127.0.0.1:{match[1]}"
        raise RuntimeError(f"Port forwarding failed: {output}")

    def runTest(self):
        check_idle(self.get("deployments,statefulsets,services,pods"))
        self.assertEqual(self.get("pvc", "workshop-models")["status"]["phase"], "Bound")
        self.wait_idle()
        if self.lesson == "03":
            check_idle(self.get("leaderworkersets"))
        self.addCleanup(self.cleanup)
        try:
            print(f"\nApplying lesson {self.lesson}, vLLM {self.version}", flush=True)
            self.command("apply", "--dry-run=server", "-f", "-", stdin=self.text)
            self.command("apply", "-f", "-", stdin=self.text)
            expected = 2 if self.lesson == "03" else 1
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                pods = self.get("pods", "-l", "app.kubernetes.io/name=vllm")["items"]
                self.assertFalse(any(p["status"]["phase"] == "Failed" for p in pods), "A Pod failed.")
                self.assertFalse(any(s["restartCount"] > 0 for p in pods
                                     for s in p["status"].get("containerStatuses", [])), "A container restarted.")
                if len(pods) == expected and all(
                    any(c["type"] == "Ready" and c["status"] == "True"
                        for c in p["status"].get("conditions", [])) for p in pods
                ):
                    break
                print(f"Lesson {self.lesson}: waiting for {expected} Ready Pod(s)", flush=True)
                time.sleep(10)
            else:
                raise TimeoutError(f"Lesson {self.lesson} did not become Ready in {self.timeout}s.")
            for pod in pods:
                self.assertIsNone(pod["metadata"].get("deletionTimestamp"))
                for container in pod["spec"]["containers"]:
                    self.assertIn(container["image"], self.text)
                    self.assertEqual(container["resources"]["limits"]["nvidia.com/gpu"],
                                     "2" if self.lesson == "02" else "1")
                self.assertTrue(all(s["restartCount"] == 0 for s in pod["status"]["containerStatuses"]))
                print(f"Lesson {self.lesson}: {pod['metadata']['name']} on {pod['spec']['nodeName']}", flush=True)
            if self.lesson == "03":
                self.assertEqual(len({p["spec"]["nodeName"] for p in pods}), 2)
            base = self.forward("vllm-leader" if self.lesson == "03" else "vllm")
            for path in ("/health", "/version", "/v1/models", "/metrics"):
                with urlopen(base + path, timeout=30) as response:
                    body = response.read()
                    if path == "/version":
                        self.assertEqual(json.loads(body)["version"], self.version)
                    elif path == "/v1/models":
                        model = "Qwen/Qwen3.5-0.8B" if self.lesson == "01" else "meta-models/Muse-Glimmer-30B"
                        self.assertIn(model, [m["id"] for m in json.loads(body)["data"]])
                    elif path == "/metrics":
                        self.assertIn(b"vllm:", body)
            payload = {"model": model, "messages": [{"role": "user", "content": "What is 2 + 2? Reply with only the answer."}],
                       "max_tokens": 512, "temperature": 0}
            request = Request(base + "/v1/chat/completions", data=json.dumps(payload).encode(),
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=120) as response:
                result = json.load(response)
                self.assertEqual(result["choices"][0]["finish_reason"], "stop")
                self.assertRegex(result["choices"][0]["message"]["content"] or "", r"\b4\b")
                self.assertGreater(result["usage"]["completion_tokens"], 0)
            with patch.dict(os.environ, {"VLLM_BASE_URL": base, "VLLM_MODEL": model,
                                         "VLLM_MAX_OUTPUT_TOKENS": "512"}):
                handler = runpy.run_path(str(ROOT / "tutorial/server/demo.py"))["DemoHandler"]
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            self.addCleanup(server.server_close)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.shutdown)
            demo = f"http://127.0.0.1:{server.server_port}"
            with urlopen(demo, timeout=30) as response:
                self.assertIn(model.encode(), response.read())
            request = Request(demo + "/chat", data=json.dumps({"prompt": payload["messages"][0]["content"],
                              "max_tokens": 512, "temperature": 0}).encode(), headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=120) as response:
                self.assertIn("text/event-stream", response.headers["Content-Type"])
                self.assertEqual(response.headers["Cache-Control"], "no-store, no-transform")
                self.assertEqual(response.headers["X-Accel-Buffering"], "no")
                check_stream(response)
            for pod in self.get("pods")["items"]:
                self.assertTrue(all(s["restartCount"] == 0 for s in pod["status"]["containerStatuses"]))
        except Exception:
            for arguments in (("describe", "pods"), ("get", "events", "--sort-by=.lastTimestamp"),
                              ("logs", "-l", "app.kubernetes.io/name=vllm", "--all-containers", "--tail=80")):
                try:
                    print(self.command(*arguments), flush=True)
                except Exception as error:
                    print(f"Diagnostics failed: {error}", flush=True)
            raise
        finally:
            self.doCleanups()


def main():
    parser = argparse.ArgumentParser(description="Deploy and test vLLM lessons in an idle workload namespace. Cleanup deletes the lesson resources.")
    parser.add_argument("--kubeconfig", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--lessons", nargs="+", choices=LESSONS, default=list(LESSONS))
    parser.add_argument("--image", help="Override the pinned image in memory for a candidate version.")
    parser.add_argument("--timeout", type=int, default=1800, help="Startup timeout per lesson in seconds.")
    args = parser.parse_args()
    if args.timeout < 1 or args.namespace in ("default", "kube-system"):
        parser.error("Use a positive timeout and a dedicated workload namespace.")
    kube = ["kubectl", "--kubeconfig", args.kubeconfig, "--context", args.context,
            "--namespace", args.namespace, "--request-timeout=30s"]
    suite = unittest.TestSuite(LiveLesson(lesson, kube, args.image, args.timeout) for lesson in args.lessons)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
