from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.run_state import RunStateStore
from storycraft.workspace import create_workspace


NOW = "2026-07-31T00:00:00Z"
SETTINGS = {
    "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test",
    "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1,
    "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1],
    "scene_text_char_range": [1000, 1000],
}
REQUEST = {
    "title": "霧の街", "genre": "幻想", "premise": "霧の街で真実を探す。",
    "required_elements": ["霧"], "forbidden_elements": ["銃"],
    "ending_preference": "希望", "volume_count": 4, "language": "ja",
}


class FakeRequestModel:
    allow_test_synthetic_calls = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def generate(self, stage: str, context: dict[str, object]) -> dict[str, object]:
        self.calls.append(("generate", context))
        return {"schema_version": "candidate-response-v1", "artifact_kind": "request", "payload": REQUEST}

    def review(self, stage: str, context: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
        self.calls.append(("review", candidate))
        return {"schema_version": "review-response-v1", "decision": "pass", "issues": []}

    def revise(self, stage: str, context: dict[str, object], candidate: dict[str, object], review: dict[str, object]) -> dict[str, object]:
        raise AssertionError("a passing review must not revise")


class RequestIntakeStageTests(unittest.TestCase):
    def test_keywords_bootstrap_adopts_request_and_recovers_before_returning(self) -> None:
        from storycraft.request_intake_stage import create_request_intake_stage_service

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ws"
            create_workspace(root, workspace_id="ws-000001", request=None,
                             keywords={"keywords": ["霧"], "language": "ja"},
                             settings=SETTINGS, created_at=NOW)
            model = FakeRequestModel()

            state = create_request_intake_stage_service(root).run(
                model, workspace_already_validated=True, updated_at=NOW,
            )

            self.assertEqual(state["current_stage"], "initial_design")
            self.assertEqual(state["current_selection_id"], "selection-000001")
            self.assertIsNone(state["pending_commit"])
            self.assertEqual(model.calls[0], ("generate", {
                "keywords": {"keywords": ["霧"], "language": "ja"}, "settings": SETTINGS,
            }))
            self.assertTrue((root / "inputs/request-000001/record.json").is_file())
            self.assertTrue((root / "runtime/adoptions/adoption-000001/record.json").is_file())
            self.assertEqual(
                RunStateStore(root).load()["current_selection_id"], "selection-000001",
            )


if __name__ == "__main__":
    unittest.main()
