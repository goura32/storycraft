from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest

from storycraft.candidate_stage import CandidateStageRunner, CandidateStageSpec
from storycraft.run_state import RunStateStore
from storycraft.series_model import OpenAIStoryModel
from storycraft.workspace import create_workspace, validate_workspace


NOW = "2026-07-31T00:00:00Z"


class _OpenAICompatibleHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, dict[str, object] | None]] = []
    completion_responses: list[dict[str, object]] = []

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _send(self, value: dict[str, object]) -> None:
        encoded = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        self.__class__.requests.append((self.path, None))
        if self.path == "/v1/models/fake-model":
            self._send({"id": "fake-model", "context_length": 4096})
        elif self.path in {"/models", "/v1/models"}:
            self._send({"object": "list", "data": [{"id": "fake-model"}]})
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        self.__class__.requests.append((self.path, request))
        response = self.__class__.completion_responses.pop(0)
        self._send({"choices": [{"message": {"content": json.dumps(response, ensure_ascii=False)}}]})


class OpenAIStoryModelV2IntegrationTests(unittest.TestCase):
    def test_candidate_runner_uses_exact_v2_wrappers_and_persists_bound_physical_calls(self) -> None:
        handler = _OpenAICompatibleHandler
        handler.requests = []
        handler.completion_responses = [
            {"schema_version": "candidate-response-v1", "artifact_kind": "request", "payload": {"title": "候補", "genre": "fantasy", "premise": "試験", "required_elements": ["塔"], "forbidden_elements": ["宇宙"], "ending_preference": "希望", "volume_count": 4, "language": "ja"}},
            {"schema_version": "review-response-v1", "decision": "issues", "issues": [{"severity": "critical", "evidence_locations": ["$.title"], "explanation": "改稿"}]},
            {"schema_version": "candidate-response-v1", "artifact_kind": "request", "payload": {"title": "改稿", "genre": "fantasy", "premise": "試験", "required_elements": ["塔"], "forbidden_elements": ["宇宙"], "ending_preference": "希望", "volume_count": 4, "language": "ja"}},
            {"schema_version": "review-response-v1", "decision": "pass", "issues": []},
        ]
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "workspace"
                endpoint = f"http://127.0.0.1:{server.server_port}"
                create_workspace(root, workspace_id="ws-000001", request={"title": "依頼", "genre": "fantasy", "premise": "試験", "required_elements": ["塔"], "forbidden_elements": ["宇宙"], "ending_preference": "希望", "volume_count": 4, "language": "ja"}, settings={"provider": "ollama", "endpoint": endpoint, "model": "fake-model", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 2], "chapter_scene_range": [1, 2], "scene_text_char_range": [100, 200]}, created_at=NOW)
                state = RunStateStore(root).load()
                state.update({"current_stage": "request_intake", "current_target": {}})
                RunStateStore(root).save(state)
                counters_path = root / "runtime/counters.json"
                counters = json.loads(counters_path.read_text(encoding="utf-8"))
                counters["next_selection"] = 2
                counters_path.write_text(json.dumps(counters) + "\n", encoding="utf-8")
                model = OpenAIStoryModel(SimpleNamespace(llm={"v2_openai_ollama": True, "provider": "ollama", "base_url": endpoint, "model": "fake-model", "api_key_env": None, "headers_env": {}, "thinking": True, "stream": False, "first_event_timeout_seconds": 5, "idle_timeout_seconds": 5, "stream_progress_log_interval_seconds": 5, "request_options": {}}, retry={"max_attempts": 1}), root / "runtime/raw_logs")
                runner = CandidateStageRunner(root, CandidateStageSpec(stage="request_intake", artifact_kind="request", next_stage="initial_design", next_target={}, content_id_factory=lambda _root, _target: "request-000002"))

                result = runner.run(model, context={"request": "current"}, updated_at=NOW)

                self.assertEqual(result["current_stage"], "initial_design")
                validate_workspace(root)
                posts = [body for path, body in handler.requests if path == "/v1/chat/completions"]
                self.assertEqual(len(posts), 4)
                self.assertEqual(posts[0]["response_format"]["json_schema"]["schema"]["properties"]["schema_version"]["const"], "candidate-response-v1")
                self.assertEqual(posts[1]["response_format"]["json_schema"]["schema"]["properties"]["schema_version"]["const"], "review-response-v1")
                self.assertEqual(posts[2]["response_format"]["json_schema"]["schema"]["properties"]["schema_version"]["const"], "candidate-response-v1")
                calls = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "runtime/calls").glob("*/record.json"))]
                self.assertEqual(len(calls), 8)
                self.assertEqual([call["seed"] for call in calls], [1, 1, 3, 3, 5, 5, 7, 7])
                generated = next(call for call in calls if call["operation"] == "generate")
                reviewed = next(call for call in calls if call["operation"] == "review")
                self.assertEqual(generated["settings_id"], "settings-000001")
                self.assertEqual(generated["input_refs"], ["selection-000001"])
                self.assertIsNone(generated["target_candidate_id"])
                self.assertEqual(reviewed["input_refs"], ["selection-000001", "candidate-000001"])
                self.assertEqual(reviewed["target_candidate_id"], "candidate-000001")
                revised = next(call for call in calls if call["operation"] == "revise")
                self.assertEqual(revised["input_refs"], ["selection-000001", "candidate-000001", "review-000001"])
                self.assertEqual(revised["target_candidate_id"], "candidate-000001")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()