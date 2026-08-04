from __future__ import annotations

from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from storycraft.series_contracts import ContractError


NOW = "2026-07-31T00:00:00Z"


def running(stage: str, *, pending_commit: object = None) -> dict[str, object]:
    target: dict[str, int] = {}
    if stage == "scene_commit":
        target = {"volume_number": 1, "chapter_number": 1, "scene_number": 1}
    elif stage == "volume_publication":
        target = {"volume_number": 1}
    return {
        "schema_version": 3,
        "workspace_id": "ws-000001",
        "status": "running",
        "last_error": None,
        "current_stage": stage,
        "current_target": target,
        "current_selection_id": "selection-000001",
        "pending_commit": pending_commit,
        "published_volumes": [],
        "created_at": NOW,
        "updated_at": NOW,
    }


class FakeStore:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = deepcopy(state)
        self.saved: list[dict[str, object]] = []

    def load(self) -> dict[str, object]:
        return deepcopy(self.state)

    def save(self, state: dict[str, object]) -> None:
        self.state = deepcopy(state)
        self.saved.append(deepcopy(state))


class WorkflowDispatcherTests(unittest.TestCase):
    def _run(self, state: dict[str, object], **kwargs: object) -> tuple[dict[str, object], FakeStore]:
        from storycraft import workflow

        validate = kwargs.pop("_validate", lambda root: None)
        store = FakeStore(state)
        self.last_store = store
        with patch.object(workflow, "RunStateStore", return_value=store), patch.object(
            workflow, "workspace_lock", return_value=nullcontext()
        ), patch.object(workflow, "validate_workspace", side_effect=validate):
            return workflow.run(Path("/workspace"), **kwargs), store

    def test_completed_run_revalidates_workspace_before_returning(self) -> None:
        from storycraft.workflow import RunUnavailable

        state = dict(
            running("volume_publication"),
            status="completed", current_stage=None, current_target=None,
            pending_commit=None, last_error=None,
            published_volumes=[{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        )
        with self.assertRaisesRegex(RunUnavailable, "authority_inconsistency"):
            self._run(state, _validate=lambda root: (_ for _ in ()).throw(ContractError("tampered workspace")))
        self.assertEqual(self.last_store.saved, [])
        self.assertEqual(self.last_store.state, state)

    def test_validates_then_recovers_pending_commit_before_constructing_a_model(self) -> None:
        from storycraft import workflow

        state = running("initial_design", pending_commit={"kind": "candidate_adoption"})
        calls: list[str] = []
        completed = dict(state, status="completed", current_stage=None, current_target=None,
                         pending_commit=None, last_error=None,
                         published_volumes=[{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}])
        provider = Mock(side_effect=AssertionError("provider must not be constructed"))
        with patch.object(
            workflow, "recover_pending_commit", side_effect=lambda root: calls.append("recover") or completed
        ):
            result, _ = self._run(
                state, model_factory=provider, _validate=lambda root: calls.append("validate")
            )

        self.assertEqual(result, completed)
        self.assertEqual(calls, ["validate", "recover"])
        provider.assert_not_called()

    def test_loops_through_injected_handlers_until_completed_and_only_supplies_model_to_llm_stage(self) -> None:
        initial = running("initial_design")
        scene = running("scene_commit")
        completed = dict(scene, status="completed", current_stage=None, current_target=None,
                         pending_commit=None, last_error=None,
                         published_volumes=[{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}])
        model = object()
        calls: list[tuple[str, object]] = []

        def initial_handler(root: Path, state: dict[str, object], injected_model: object | None) -> dict[str, object]:
            calls.append(("initial_design", injected_model))
            return scene

        def scene_handler(root: Path, state: dict[str, object], injected_model: object | None) -> dict[str, object]:
            calls.append(("scene_commit", injected_model))
            return completed

        result, _ = self._run(
            initial,
            handlers={"initial_design": (True, initial_handler), "scene_commit": (False, scene_handler)},
            model_factory=lambda root, state: model,
        )

        self.assertEqual(result, completed)
        self.assertEqual(calls, [("initial_design", model), ("scene_commit", None)])

    def test_default_registry_contains_only_implemented_v2_handlers(self) -> None:
        from storycraft import workflow

        handlers = workflow._default_handlers()
        self.assertEqual(set(handlers), {
            "request_intake", "initial_design", "series_plan", "volume_plan", "chapter_plan",
            "scene_plan", "scene_card", "scene_prose", "scene_continuity", "scene_commit", "volume_publication",
        })
        self.assertEqual(
            {stage for stage, (needs_model, _) in handlers.items() if needs_model},
            {"request_intake", "initial_design", "series_plan", "volume_plan", "chapter_plan", "scene_plan", "scene_card", "scene_prose", "scene_continuity"},
        )
        self.assertNotIn("unknown_stage", handlers)

    def test_default_request_intake_is_reachable_with_an_injected_fake_model(self) -> None:
        state = running("request_intake")
        state["current_selection_id"] = None
        model = object()
        next_state = dict(
            running("initial_design"), status="completed", current_stage=None, current_target=None,
            pending_commit=None, last_error=None,
            published_volumes=[{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        )
        calls: list[object] = []

        def request_handler(root: Path, current: dict[str, object], injected_model: object | None) -> dict[str, object]:
            calls.append(injected_model)
            return next_state

        result, _ = self._run(
            state, handlers={"request_intake": (True, request_handler)},
            model_factory=lambda root, current: model,
        )
        # The injected request handler advances to an intentionally unregistered stage;
        # reachability has already proved the provider is created only after preflight.
        self.assertIs(result, next_state)
        self.assertEqual(calls, [model])

    def test_deterministic_publication_contract_error_blocks_as_publication_invalid_without_model(self) -> None:
        from storycraft.workflow import RunUnavailable

        state = running("volume_publication")
        provider = Mock(side_effect=AssertionError("provider must not be constructed"))

        def broken_publication(root: Path, state: dict[str, object], model: object | None) -> dict[str, object]:
            self.assertIsNone(model)
            raise ContractError("bad publication")

        with self.assertRaisesRegex(RunUnavailable, "publication_invalid"):
            _, store = self._run(
                state, handlers={"volume_publication": (False, broken_publication)}, model_factory=provider
            )
        provider.assert_not_called()
        self.assertEqual(self.last_store.state["status"], "blocked")
        self.assertEqual(self.last_store.state["last_error"]["code"], "publication_invalid")

    def test_recovery_contract_error_uses_pending_publication_kind_for_diagnostic(self) -> None:
        from storycraft.workflow import RunUnavailable

        state = running("volume_publication", pending_commit={"kind": "volume_publication"})
        with patch("storycraft.workflow.recover_pending_commit", side_effect=ContractError("bad publication manifest")):
            with self.assertRaisesRegex(RunUnavailable, "publication_invalid"):
                self._run(state)
        self.assertEqual(self.last_store.state["last_error"]["code"], "publication_invalid")

        from storycraft.workflow import RunUnavailable

        state = running("scene_commit")
        with self.assertRaisesRegex(RunUnavailable, "internal_error"):
            _, store = self._run(
                state,
                handlers={"scene_commit": (False, lambda root, state, model: (_ for _ in ()).throw(RuntimeError("boom")))},
            )
        self.assertEqual(self.last_store.state["status"], "blocked")
        self.assertEqual(self.last_store.state["last_error"]["code"], "internal_error")

    def test_provider_format_error_blocks_as_invalid_response_not_technical_retry(self) -> None:
        from storycraft.ollama import OllamaResponseFormatError
        from storycraft.workflow import RunUnavailable

        state = running("initial_design")
        with self.assertRaisesRegex(RunUnavailable, "invalid_response_limit"):
            self._run(
                state,
                handlers={"initial_design": (True, lambda root, state, model: (_ for _ in ()).throw(OllamaResponseFormatError("bad response")))},
                model_factory=lambda root, state: object(),
            )
        self.assertEqual(self.last_store.state["last_error"]["code"], "invalid_response_limit")


if __name__ == "__main__":
    unittest.main()
