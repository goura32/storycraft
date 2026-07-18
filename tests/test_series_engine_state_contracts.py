"""次世代実行状態の製品契約。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from storycraft.series_contracts import ContractError, LLMCallError
from storycraft.series_engine import SeriesService
from test_series_engine_flow import BRIEF, FlowModel


class StateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-state-contract-"))

    def test_failed_scene_persists_stop_reason_and_target_unit(self) -> None:
        service = SeriesService(self.workspace)
        with self.assertRaisesRegex(ContractError, "本文根拠"):
            service.run(BRIEF, FlowModel(invalid_evidence=True))

        state = service.store.load()
        self.assertEqual(state["stopped_at"]["stage"], "continuity")
        self.assertEqual(state["stopped_at"]["unit"], "v01-c01-s01")
        self.assertIn("本文根拠", state["stop_reason"])
        self.assertEqual(state["last_completed_unit"]["stage"], "scene_card")

    def test_plan_rejects_chapter_counts_when_volume_count_is_selected_later(self) -> None:
        brief = {**BRIEF, "volumes": None, "chapters_per_volume": [1, 1]}
        with self.assertRaisesRegex(ContractError, "chapters_per_volume"):
            SeriesService(self.workspace).run(brief, FlowModel())

    def test_loading_state_without_required_contract_keys_fails_cleanly(self) -> None:
        (self.workspace / "state.json").write_text('{"version": 3}', encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "保存状態"):
            SeriesService(self.workspace).resume(FlowModel())

    def test_active_workspace_lock_rejects_second_public_operation_without_state_change(self) -> None:
        import threading

        started = threading.Event()
        release = threading.Event()

        class BlockingPlanModel:
            def __init__(self) -> None:
                self._blocked = False
                self._model = FlowModel()

            def generate(self, stage: str, context: dict) -> dict:
                if not self._blocked:
                    case.assertEqual(stage, "characters")
                    self._blocked = True
                    started.set()
                    case.assertTrue(release.wait(timeout=5))
                return self._model.generate(stage, context)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return self._model.critique(stage, candidate, context)

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return self._model.revision(stage, candidate, critique, context)

        errors: list[Exception] = []
        case = self

        def run_first() -> None:
            try:
                SeriesService(self.workspace).run(BRIEF, BlockingPlanModel())
            except Exception as exc:  # assertion failures must reach the test thread
                errors.append(exc)

        worker = threading.Thread(target=run_first)
        worker.start()
        self.assertTrue(started.wait(timeout=5))
        state_before = (self.workspace / "state.json").read_bytes()
        second_operations = {
            "run": lambda: SeriesService(self.workspace).run(BRIEF, FlowModel()),
            "resume": lambda: SeriesService(self.workspace).resume(FlowModel()),
            "step": lambda: SeriesService(self.workspace).step(FlowModel()),
        }
        for name, operation in second_operations.items():
            with self.subTest(operation=name), self.assertRaisesRegex(ContractError, "使用中"):
                operation()
            self.assertEqual((self.workspace / "state.json").read_bytes(), state_before)
        release.set()
        worker.join(timeout=10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])

    def test_save_fsyncs_state_file_before_replace_and_workspace_after_replace(self) -> None:
        from unittest.mock import patch

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        with patch("storycraft.series_store.os.fsync") as fsync:
            service.store.save(state)
        self.assertGreaterEqual(fsync.call_count, 2)
        self.assertEqual(service.store.load()["version"], 4)

    def test_output_rejects_missing_planned_scene_before_creating_files(self) -> None:
        service = SeriesService(self.workspace)
        service.run(BRIEF, FlowModel())
        state = service.store.load()
        state["scenes"] = state["scenes"][1:]
        output = self.workspace / "blocked-output"
        service.workspace = output.parent
        for path in (service.workspace / "output").glob("*"):
            path.unlink()
        with self.assertRaisesRegex(ContractError, "必要な場面"):
            service._write_output(state)
        self.assertFalse((service.workspace / "output" / "series.md").exists())

    def test_output_replacement_is_atomic_when_validation_fails(self) -> None:
        service = SeriesService(self.workspace)
        service.run(BRIEF, FlowModel())
        previous = (self.workspace / "output" / "series.md").read_text(encoding="utf-8")
        state = service.store.load()
        state["scenes"][0]["content"] = "変更済み本文"
        service._validate_output = lambda paths, series: (_ for _ in ()).throw(ContractError("出力検証失敗"))  # type: ignore[method-assign]
        with self.assertRaisesRegex(ContractError, "出力検証失敗"):
            service._write_output(state)
        self.assertEqual((self.workspace / "output" / "series.md").read_text(encoding="utf-8"), previous)

    def test_step_on_completed_series_does_not_rewrite_output(self) -> None:
        service = SeriesService(self.workspace)
        service.run(BRIEF, FlowModel())
        service._write_output = lambda state: self.fail("completed series must not write output")  # type: ignore[method-assign]
        result = service.step(FlowModel())
        self.assertTrue(result.completed)

    def test_unresolved_brief_review_is_adopted_and_allows_characters_stage(self) -> None:
        class UnresolvedBriefModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def __init__(self) -> None:
                self._flow = FlowModel()
                self.generated_stages: list[str] = []

            def generate(self, stage: str, context: dict) -> dict:
                self.generated_stages.append(stage)
                return dict(BRIEF) if stage == "brief" else self._flow.generate(stage, context)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                if stage == "brief":
                    return {"issues": [{"severity": "major", "field": "protagonist", "description": "改善点", "suggestion": "修正"}]}
                return {"issues": []}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return dict(candidate)

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["女性向けロマンスファンタジー"])
        model = UnresolvedBriefModel()
        service._run_one(state, model)
        self.assertEqual(state["brief"], BRIEF)
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique", "revision", "critique"])

        service._run_one(state, model)
        self.assertEqual(model.generated_stages, ["brief", "characters"])
        self.assertIsNotNone(state["characters"])

    def test_every_critique_logs_issue_count_including_final_critique(self) -> None:
        class AlwaysIssuesModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 2}))

            def generate(self, stage: str, context: dict) -> dict:
                return {"value": 0}

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": [{"severity": "minor", "field": "value", "description": "改善点", "suggestion": "修正"}]}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return {"value": candidate["value"] + 1}

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["ログ検証"])
        with self.assertLogs("storycraft", level="INFO") as captured:
            service._improve("quality_probe", {}, AlwaysIssuesModel(), state, lambda value: None)
        output = "\n".join(captured.output)
        self.assertIn("批評結果: stage=quality_probe pass=1/2 final=False issues=1", output)
        self.assertIn("批評結果: stage=quality_probe pass=2/2 final=False issues=1", output)
        self.assertIn("批評結果: stage=quality_probe pass=3/2 final=True issues=1", output)

    def test_critique_call_failure_blocks_characters_stage_after_model_retries(self) -> None:
        class FailingCritiqueModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def generate(self, stage: str, context: dict) -> dict:
                self_stage.assertEqual(stage, "characters")
                return FlowModel().generate(stage, context)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                raise LLMCallError("LLM通信の再試行上限に達しました")

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                raise AssertionError("critique failure must not revision")

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        self_stage = self
        with self.assertRaisesRegex(ContractError, "characters の批評に失敗"):
            service._run_one(state, FailingCritiqueModel())
        self.assertIsNone(state["characters"])
        self.assertEqual(state["_active"]["phase"], "failed")
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique_failed"])

    def test_revision_call_failure_blocks_characters_stage_after_model_retries(self) -> None:
        class FailingRevisionModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def generate(self, stage: str, context: dict) -> dict:
                return FlowModel().generate(stage, context)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": [{"severity": "minor", "field": "characters", "description": "改善点", "suggestion": "修正"}]}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                raise LLMCallError("LLM通信の再試行上限に達しました")

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        with self.assertRaisesRegex(ContractError, "characters の修正に失敗"):
            service._run_one(state, FailingRevisionModel())
        self.assertIsNone(state["characters"])
        self.assertEqual(state["_active"]["phase"], "failed")
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique", "revision_failed"])

    def test_final_critique_call_failure_blocks_characters_stage_after_model_retries(self) -> None:
        class FailingFinalCritiqueModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def __init__(self) -> None:
                self.critique_calls = 0

            def generate(self, stage: str, context: dict) -> dict:
                return FlowModel().generate(stage, context)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                self.critique_calls += 1
                if self.critique_calls == 1:
                    return {"issues": [{"severity": "minor", "field": "characters", "description": "改善点", "suggestion": "修正"}]}
                raise LLMCallError("LLM通信の再試行上限に達しました")

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return dict(candidate)

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        with self.assertRaisesRegex(ContractError, "characters の最終批評に失敗"):
            service._run_one(state, FailingFinalCritiqueModel())
        self.assertIsNone(state["characters"])
        self.assertEqual(state["_active"]["phase"], "failed")
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique", "revision", "critique_failed"])

    def test_final_revision_is_reviewed_and_adopted_when_clean(self) -> None:
        class ResolvingBriefModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def __init__(self) -> None:
                self.critique_calls = 0

            def generate(self, stage: str, context: dict) -> dict:
                return dict(BRIEF)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                self.critique_calls += 1
                if self.critique_calls == 1:
                    return {"issues": [{"severity": "minor", "field": "protagonist", "description": "修正対象", "suggestion": "削除"}]}
                return {"issues": []}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return dict(candidate)

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["女性向けロマンスファンタジー"])
        model = ResolvingBriefModel()
        service._run_one(state, model)
        self.assertEqual(model.critique_calls, 2)
        self.assertEqual(state["brief"], BRIEF)
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique", "revision", "critique"])

    def test_revision_contract_loss_keeps_validated_draft_and_records_normalized_attempt(self) -> None:
        class RevisionLossModel:
            def generate(self, stage: str, context: dict) -> dict:
                return {"scene_id": context["scene_id"], "required_events": ["発見"]}

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": [{"severity": "minor", "field": "required_events", "description": "表現", "suggestion": "修正"}]}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return {"required_events": []}

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        candidate = service._improve(
            "scene_card", {"scene_id": "v01-c01-s01"}, RevisionLossModel(), state,
            lambda value: None,
        )
        self.assertEqual(candidate["scene_id"], "v01-c01-s01")
        self.assertEqual(state["attempts"][-1]["kind"], "revision_failed")
        for attempt in state["attempts"]:
            self.assertTrue({"stage", "kind", "unit", "input", "response", "validation"}.issubset(attempt))

    def test_continuity_update_requires_matching_source_scene_and_existing_state_field(self) -> None:
        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        state["threads"] = [{
            "id": "thread-0001", "importance": "major", "current_state": {"status": "open"},
        }]
        card = {"scene_id": "v01-c01-s01", "allowed_update_ids": ["thread-0001"]}
        update = {
            "source_scene_id": "v01-c01-s99", "id": "thread-0001", "field": "current_state",
            "value": "resolved", "evidence": "根拠",
        }
        with self.assertRaisesRegex(ContractError, "場面ID|更新できないフィールド"):
            service._validate_continuity({"handoff_summary": "次へ", "state_updates": [update]}, "根拠", card, state, False)


class SceneCardContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-card-contract-"))

    def test_scene_card_without_required_temporal_and_disclosure_contract_is_rejected(self) -> None:
        class MissingFieldsModel(FlowModel):
            def generate(self, stage: str, context: dict) -> dict:
                value = super().generate(stage, context)
                if stage == "scene_card":
                    for key in ("start_time_id", "end_time_id", "character_ids", "thread_actions", "withheld_information", "end_change"):
                        value.pop(key, None)
                return value

        with self.assertRaisesRegex(ContractError, "必須項目"):
            SeriesService(self.workspace).run(BRIEF, MissingFieldsModel())


if __name__ == "__main__":
    unittest.main()
