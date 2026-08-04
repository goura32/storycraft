from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any
import unittest
from unittest.mock import patch

from storycraft.artifact_ids import initial_counters
from storycraft.initial_design_stage import InitialDesignStageService
from storycraft.run_state import RunStateStore
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.series_contracts import ContractError
from storycraft.workspace import create_workspace, validate_workspace


TIMESTAMP = "2026-07-31T00:00:00Z"

RICH_INITIAL_DESIGN = {
    "schema_version": 1,
    "core": {
        "logline": "選択の代償",
        "premise": "主人公が選択の結果を引き受ける",
        "central_question": "何を守るのか",
        "themes": ["選択"],
        "dramatic_engine": "選択の結果が次の障害を生む",
        "tone": ["希望"],
        "reader_promise": "人物の選択が結末を変える",
        "ending_direction": "責任を引き受ける",
    },
    "cast": [{"name": "主人公", "role": "英雄", "description": "選択を迫られる", "relationships": []}],
    "world": {"settings": ["剣と魔法"], "constraints": ["契約を破れない"], "institutions": ["王国"]},
    "knowledge_model": {
        "author_knows": ["主人公の秘密"],
        "character_knows": {"主人公": ["自分の目的"]},
        "reader_knows": ["主人公の目的"],
    },
    "unresolved_threads": [{"name": "塔の試練", "type": "goal", "required_for_ending": True, "description": "塔を登頂する"}],
    "ending_conditions": [{"thread_name": "塔の試練", "condition": "塔を登頂する"}],
}


class FakeInitialDesignModel:
    __storycraft_test_double__ = True
    allow_test_synthetic_calls = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((stage, context))
        return {
            "schema_version": "candidate-response-v1",
            "artifact_kind": "initial-design",
            "payload": RICH_INITIAL_DESIGN,
        }

    def review(self, stage: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("review", {"stage": stage, "context": context, "candidate": candidate}))
        return {"schema_version": "review-response-v1", "decision": "pass", "issues": []}


class EnvelopeInitialDesignModel(FakeInitialDesignModel):
    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((stage, context))
        return {
            "schema_version": "candidate-response-v1",
            "artifact_kind": "initial-design",
            "payload": RICH_INITIAL_DESIGN,
        }


class RevisingInitialDesignModel(EnvelopeInitialDesignModel):
    def __init__(self) -> None:
        super().__init__()
        self.review_count = 0

    def review(self, stage: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        self.review_count += 1
        if self.review_count == 1:
            return {"schema_version": "review-response-v1", "decision": "issues", "issues": [{"severity": "critical", "evidence_locations": ["$.core.logline"], "explanation": "改善"}]}
        return {"schema_version": "review-response-v1", "decision": "pass", "issues": []}

    def revise(self, stage: str, context: dict[str, Any], candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
        return {"schema_version": "candidate-response-v1", "artifact_kind": "initial-design", "payload": RICH_INITIAL_DESIGN}


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _workspace(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    for relative in (
        "inputs", "quality", "candidates", "reviews", "runtime/settings", "runtime/selections",
        "runtime/staging", "runtime/calls", "runtime/adoptions",
        "design/initial", "design/series-plans", "design/volume-plans", "design/chapter-plans",
        "design/scene-plans", "design/scene-cards", "generations", "scenes", "publications",
    ):
        (root / relative).mkdir(parents=True)
    _write_json(root / "runtime/counters.json", initial_counters())
    request = {
        "title": "現在の依頼", "genre": ["fantasy"], "premise": "選択の物語",
        "required_elements": ["灯台"], "avoid": ["宇宙"],
        "ending_preference": "希望", "volume_count": 4, "language": "ja",
    }
    settings = {
        "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "fake-model",
        "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5,
        "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100],
    }
    _write_json(root / "inputs/request-000001/record.json", {
        "schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request",
        "input_selection_id": None, "created_at": TIMESTAMP, "content": request,
    })
    _write_json(root / "runtime/settings/settings-000001/record.json", {
        "schema_version": 1, "settings_id": "settings-000001", "payload": settings,
        "created_at": TIMESTAMP,
    })
    # NOTE: initial-design and generation records are created by the stage, not pre-written
    selection = SelectionSnapshotStore(root).create(
        input_selection_id=None, created_at=TIMESTAMP,
        slots={"request": "request-000001", "settings": "settings-000001"},
    )
    assert selection["selection_id"] == "selection-000001"
    RunStateStore(root).save({
        "schema_version": 3, "workspace_id": "ws-000001", "status": "running",
        "last_error": None, "current_stage": "initial_design", "current_target": {},
        "current_selection_id": "selection-000001", "pending_commit": None,
        "published_volumes": [], "created_at": TIMESTAMP, "updated_at": TIMESTAMP,
    })
    return request, settings


class InitialDesignStageTests(unittest.TestCase):
    def test_revalidates_persisted_settings_when_workspace_validation_is_skipped(self) -> None:
        for mutation in ("injected_endpoint", "missing_model"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _workspace(root)
                settings_path = root / "runtime/settings/settings-000001/record.json"
                persisted = json.loads(settings_path.read_text(encoding="utf-8"))
                if mutation == "injected_endpoint":
                    persisted["payload"]["endpoint"] = "injected"
                else:
                    del persisted["payload"]["model"]
                settings_path.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                model = FakeInitialDesignModel()
                before = RunStateStore(root).load()
                with self.assertRaises(ContractError):
                    InitialDesignStageService(root).run(model, workspace_already_validated=True, updated_at=TIMESTAMP)
                self.assertEqual(model.calls, [])
                self.assertEqual(RunStateStore(root).load(), before)

    def test_initial_design_unwraps_the_live_candidate_response_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _workspace(root)
            result = InitialDesignStageService(root).run(EnvelopeInitialDesignModel(), updated_at=TIMESTAMP)

            self.assertEqual(result["current_stage"], "series_plan")
            candidate = json.loads((root / "candidates/candidate-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(candidate["payload"], RICH_INITIAL_DESIGN)

    def test_initial_design_uses_only_current_selection_inputs_and_finalizes_via_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request, settings = _workspace(root)
            # These unsupported paths must neither supply input nor be read by the adapter.
            _write_json(root / "input/unselected_request.json", {"title": "UNSUPPORTED REQUEST"})
            _write_json(root / "runtime/config.json", {"model": "UNSUPPORTED MODEL"})
            model = FakeInitialDesignModel()
            unsupported_paths = {root / "input/unselected_request.json", root / "runtime/config.json"}
            original_read_text = Path.read_text

            def reject_unsupported_reads(path: Path, *args: Any, **kwargs: Any) -> str:
                if path in unsupported_paths:
                    raise AssertionError(f"adapter read retired path: {path}")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", new=reject_unsupported_reads):
                result = InitialDesignStageService(root).run(model, updated_at=TIMESTAMP)

            self.assertEqual(model.calls, [
                ("initial_design", {"request": request, "settings": settings}),
                ("review", {
                    "stage": "initial_design",
                    "context": {"request": request, "settings": settings},
                    "candidate": RICH_INITIAL_DESIGN,
                }),
            ])
            self.assertIsNone(result["pending_commit"])
            self.assertEqual(result["current_stage"], "series_plan")
            self.assertEqual(result["current_target"], {})
            self.assertEqual(result["current_selection_id"], "selection-000002")

            initial_record = json.loads((root / "design/initial/initial-design-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(initial_record, {
                "schema_version": 1,
                "artifact_id": "initial-design-000001",
                "artifact_kind": "initial-design",
                "input_selection_id": "selection-000001",
                "created_at": TIMESTAMP,
                "content": RICH_INITIAL_DESIGN,
            })
            next_selection = json.loads((root / "runtime/selections/selection-000002/record.json").read_text(encoding="utf-8"))
            self.assertEqual(next_selection["input_selection_id"], "selection-000001")
            self.assertEqual(next_selection["slots"], {
                "request": "request-000001", "settings": "settings-000001",
                "initial_design": "initial-design-000001", "initial_design_adoption": "adoption-000001",
                "current_state": "gen-000001",
            })
            generation = json.loads((root / "generations/gen-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(generation["input_selection_id"], "selection-000001")
            self.assertEqual(generation["content"], InitialDesignStageService._build_initial_state(RICH_INITIAL_DESIGN))
            candidate = json.loads((root / "candidates/candidate-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(candidate["artifact_kind"], "initial-design")
            self.assertEqual(candidate["payload"], RICH_INITIAL_DESIGN)
            review = json.loads((root / "reviews/review-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(review["candidate_id"], "candidate-000001")
            self.assertEqual(review["response"], {"schema_version": "review-response-v1", "decision": "pass", "issues": []})
            quality = json.loads((root / "quality/quality-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(quality, {
                "schema_version": 1, "quality_id": "quality-000001", "candidate_id": "candidate-000001",
                "review_record_ids": ["review-000001"], "revision_count": 0, "result": "accepted",
                "remaining_major_issues": [], "created_at": TIMESTAMP,
            })
            self.assertTrue((root / "input/unselected_request.json").read_text(encoding="utf-8"))
            self.assertTrue((root / "runtime/config.json").read_text(encoding="utf-8"))

    def test_initial_design_quality_reviews_only_the_final_revision_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _workspace(root)
            InitialDesignStageService(root).run(RevisingInitialDesignModel(), updated_at=TIMESTAMP)
            validate_workspace(root)
            quality = json.loads((root / "quality/quality-000001/record.json").read_text(encoding="utf-8"))
            review = json.loads((root / "reviews/review-000002/record.json").read_text(encoding="utf-8"))
            self.assertEqual(quality["candidate_id"], "candidate-000002")
            self.assertEqual(quality["review_record_ids"], ["review-000002"])
            self.assertEqual(review["candidate_id"], "candidate-000002")

    def test_fresh_direct_request_workspace_initial_design_allocates_a_new_output_selection(self) -> None:
        """The initializer must retain its reserved input selection counter."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fresh-workspace"
            request = {
                "title": "現在の依頼", "genre": ["fantasy"], "premise": "選択の物語",
                "required_elements": ["灯台"], "avoid": ["宇宙"],
                "ending_preference": "希望", "volume_count": 4, "language": "ja",
            }
            settings = {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "fake-model",
                "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 1,
                "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1],
                "scene_text_char_range": [1000, 1000],
            }
            create_workspace(root, workspace_id="ws-000001", request=request, settings=settings, created_at=TIMESTAMP)
            input_selection_id = RunStateStore(root).load()["current_selection_id"]
            direct_adoption = root / "runtime/adoptions/adoption-000001/record.json"
            self.assertTrue(direct_adoption.is_file())
            self.assertEqual(json.loads(direct_adoption.read_text(encoding="utf-8"))["source_kind"], "direct_request")

            # DO NOT pre-write initial-design or generation records - they will be created by the stage
            # and placed in staging. Pre-writing them causes staging/final conflict.

            result = InitialDesignStageService(root).run(FakeInitialDesignModel(), updated_at=TIMESTAMP)

            self.assertNotEqual(result["current_selection_id"], input_selection_id)
            self.assertEqual(result["current_selection_id"], "selection-000002")
            self.assertEqual(json.loads((root / "runtime/counters.json").read_text(encoding="utf-8"))["next_selection"], 3)
            validate_workspace(root)
