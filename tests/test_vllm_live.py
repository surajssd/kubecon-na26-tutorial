import io
import json
from pathlib import Path
import runpy
import unittest


LIVE = runpy.run_path(str(Path(__file__).with_name("vllm_live.py")))


class LiveStreamTest(unittest.TestCase):
    def stream(self, content="4", reasoning="", finish="stop", usage=True, done=True):
        chunks = [{"choices": [{"delta": {"content": content, "reasoning": reasoning},
                                "finish_reason": finish}]}]
        if usage:
            chunks.append({"choices": [], "usage": {"completion_tokens": 3}})
        body = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
        return io.BytesIO((body + ("data: [DONE]\n\n" if done else "")).encode())

    def test_reasoning_and_trailing_usage_preserve_the_answer(self):
        LIVE["check_stream"](self.stream(reasoning="Two plus two is four."))

    def test_incomplete_or_invalid_inference_fails(self):
        for fields in ({"done": False}, {"usage": False}, {"finish": "length"},
                       {"content": "", "reasoning": "The answer is 4"}, {"content": "5"}):
            with self.subTest(fields=fields), self.assertRaises(AssertionError):
                LIVE["check_stream"](self.stream(**fields))


class LiveTargetTest(unittest.TestCase):
    def test_lesson_images_use_the_same_digest(self):
        images = set()
        for lesson in LIVE["LESSONS"]:
            text, version = LIVE["manifest"](lesson)
            images.update(match.group(0) for match in LIVE["IMAGE"].finditer(text))
            readme = LIVE["ROOT"] / "tutorial" / LIVE["LESSONS"][lesson] / "README.md"
            self.assertIn(version, readme.read_text())
        self.assertEqual(len(images), 1)

    def test_existing_resources_prevent_deployment(self):
        for kind in ("Pod", "Deployment", "StatefulSet", "Service"):
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                LIVE["check_idle"]({"items": [{"kind": kind, "metadata": {"name": "vllm"}}]})
        LIVE["check_idle"]({"items": []})

    def test_candidate_image_replaces_both_pipeline_stages(self):
        image = "vllm/vllm-openai:v9.8.7@sha256:" + "a" * 64
        text, version = LIVE["manifest"]("03", image)
        self.assertEqual(text.count(image), 2)
        self.assertEqual(version, "9.8.7")
        self.assertIn("--headless", text)
        self.assertIn('"$(LWS_GROUP_SIZE)"', text)

    def test_unpinned_candidate_is_rejected(self):
        with self.assertRaises(ValueError):
            LIVE["manifest"]("01", "vllm/vllm-openai:v9.8.7")


if __name__ == "__main__":
    unittest.main()
