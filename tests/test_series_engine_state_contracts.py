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

    def test_stage_logs_include_start_completion_and_scene_progress(self) -> None:
        service = SeriesService(self.workspace)
        with self.assertLogs("storycraft", level="INFO") as captured:
            service.run(BRIEF, FlowModel())
        logs = "\n".join(captured.output)
        progress = "v:1/4 c:1/1 s:1/1"
        self.assertIn("工程開始: stage=scene_card v:1/4,c:1/1,s:1/1", logs)
        self.assertIn("工程完了: stage=scene_card v:1/4,c:1/1,s:1/1", logs)
        self.assertIn("工程開始: stage=scene v:1/4,c:1/1,s:1/1", logs)
        self.assertIn("工程完了: stage=continuity v:1/4,c:1/1,s:1/1", logs)

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
        self.assertEqual(service.store.load()["version"], 5)

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

    def test_output_publishes_quality_acceptance_manifest(self) -> None:
        import json

        service = SeriesService(self.workspace)
        service.run(BRIEF, FlowModel())
        state = service.store.load()
        acceptance = {
            "stage": "brief", "unit": None, "reason": "max_critique_passes_exhausted",
            "max_critique_passes": 1, "final_review_pass": 2,
            "issues": [{"severity": "major", "field": "protagonist", "description": "改善点", "suggestion": "修正"}],
        }
        state["quality_acceptances"] = [acceptance]
        service._write_output(state)
        manifest = json.loads((self.workspace / "output" / "quality-acceptances.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest, [acceptance])

    def test_step_on_completed_series_does_not_rewrite_output(self) -> None:
        service = SeriesService(self.workspace)
        service.run(BRIEF, FlowModel())
        service._write_output = lambda state: self.fail("completed series must not write output")  # type: ignore[method-assign]
        result = service.step(FlowModel())
        self.assertTrue(result.completed)

    def test_unresolved_major_brief_review_is_adopted_with_audit_and_allows_characters_stage(self) -> None:
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
        self.assertEqual(
            [attempt["kind"] for attempt in state["attempts"]],
            ["draft", "critique", "revision", "critique", "quality_accepted_with_known_issues"],
        )
        self.assertEqual(state["quality_acceptances"], [{
            "stage": "brief", "unit": None, "reason": "max_critique_passes_exhausted",
            "max_critique_passes": 1, "final_review_pass": 2,
            "issues": [{"severity": "major", "field": "protagonist", "description": "改善点", "suggestion": "修正"}],
        }])
        service._run_one(state, model)
        self.assertEqual(model.generated_stages, ["brief", "characters"])
        self.assertIsNotNone(state["characters"])

    def test_review_candidate_records_final_attempt_and_logs_final_metadata(self) -> None:
        class CleanCritiqueModel:
            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": []}

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        with self.assertNoLogs("storycraft", level="INFO"):
            critique = service._review_candidate(
                "quality_probe", {"value": 0}, {}, CleanCritiqueModel(), state,
                pass_num=1, max_passes=0, final=True,
            )
        self.assertEqual(critique, {"issues": []})
        self.assertEqual(state["_active"]["phase"], "critique_final")
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["critique"])

    def test_every_critique_logs_issue_count_including_final_critique(self) -> None:
        class AlwaysIssuesModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 2}))

            def __init__(self) -> None:
                self.quality_pass = ""
                self.revision_quality_passes: list[str] = []

            def set_log_quality_pass(self, quality_pass: str = "") -> None:
                self.quality_pass = quality_pass

            def generate(self, stage: str, context: dict) -> dict:
                return {"value": 0}

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": [{"severity": "minor", "field": "value", "description": "改善点", "suggestion": "修正"}]}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                self.revision_quality_passes.append(self.quality_pass)
                return {"value": candidate["value"] + 1}

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["ログ検証"])
        model = AlwaysIssuesModel()
        with self.assertLogs("storycraft", level="INFO") as captured:
            service._improve("quality_probe", {}, model, state, lambda value: None)
        output = "\n".join(captured.output)
        self.assertIn("工程開始: stage=quality_probe v:-/-", output)
        self.assertEqual(model.revision_quality_passes, ["1/3", "2/3"])
        self.assertIn("批評指摘: stage=quality_probe v:-/- quality_pass=1/3 severities=['minor']", output)
        self.assertIn("批評指摘: stage=quality_probe v:-/- quality_pass=2/3 severities=['minor']", output)
        self.assertIn("批評指摘: stage=quality_probe v:-/- quality_pass=3/3 severities=['minor']", output)
        self.assertNotIn("批評結果:", output)
        self.assertNotIn("批評指摘あり:", output)

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

    def test_malformed_critique_is_retried_before_valid_critique_is_adopted(self) -> None:
        class TransientMalformedCritiqueModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def __init__(self) -> None:
                self.critique_calls = 0

            def generate(self, stage: str, context: dict) -> dict:
                return dict(BRIEF)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                self.critique_calls += 1
                if self.critique_calls == 1:
                    return {"issues": [{"severity": "major", "field": "protagonist", "description": "改善点"}]}
                return {"issues": []}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                raise AssertionError("issuesが空ならrevisionしてはならない")

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["女性向けロマンスファンタジー"])
        model = TransientMalformedCritiqueModel()
        service._run_one(state, model)
        self.assertEqual(model.critique_calls, 2)
        self.assertEqual(state["brief"], BRIEF)
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique_rejected", "critique"])

    def test_malformed_critique_stops_without_adoption_or_quality_acceptance(self) -> None:
        class MalformedCritiqueModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def generate(self, stage: str, context: dict) -> dict:
                return dict(BRIEF)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": "not-an-array"}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                raise AssertionError("critique契約違反時にrevisionしてはならない")

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["女性向けロマンスファンタジー"])
        with self.assertRaisesRegex(ContractError, "批評を検証できない"):
            service._run_one(state, MalformedCritiqueModel())
        self.assertIsNone(state["brief"])
        self.assertEqual(state["quality_acceptances"], [])
        self.assertEqual(
            [attempt["kind"] for attempt in state["attempts"]],
            ["draft", "critique_rejected", "critique_rejected", "critique_rejected", "critique_failed"],
        )
        self.assertEqual(state["attempts"][-1]["response"], {"issues": "not-an-array"})

    def test_invalid_revision_is_rejected_but_last_valid_candidate_is_accepted_with_known_issues(self) -> None:
        class InvalidRevisionModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def __init__(self) -> None:
                self.generated_stages: list[str] = []

            def generate(self, stage: str, context: dict) -> dict:
                self.generated_stages.append(stage)
                return dict(BRIEF)

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": [{"severity": "major", "field": "protagonist", "description": "改善点", "suggestion": "修正"}]}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return {}

        service = SeriesService(self.workspace)
        state = service._new_state(keywords=["女性向けロマンスファンタジー"])
        model = InvalidRevisionModel()
        service._run_one(state, model)
        self.assertEqual(state["brief"], BRIEF)
        self.assertEqual(state["_active"]["phase"], "completed_with_known_issues")
        self.assertEqual(model.generated_stages, ["brief"])
        self.assertEqual(
            [attempt["kind"] for attempt in state["attempts"]],
            ["draft", "critique", "revision_rejected", "critique", "quality_accepted_with_known_issues"],
        )

    def test_revision_can_repair_a_critique_repairable_scene_card_field(self) -> None:
        class RepairingModel:
            client = SimpleNamespace(settings=SimpleNamespace(quality={"max_critique_passes": 1}))

            def generate(self, stage: str, context: dict) -> dict:
                return {"scene_id": context["scene_id"], "required_events": ["曖昧な出来事"]}

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                if candidate["required_events"] == ["曖昧な出来事"]:
                    return {"issues": [{"severity": "major", "field": "required_events", "description": "具体性不足", "suggestion": "入力事実で書き直し"}]}
                return {"issues": []}

            def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
                return {"scene_id": context["scene_id"], "required_events": ["灯台の灯りを見つける"]}

        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        candidate = service._improve(
            "scene_card", {"scene_id": "v01-c01-s01"}, RepairingModel(), state,
            lambda value: self.assertEqual(value["scene_id"], "v01-c01-s01"),
        )
        self.assertEqual(candidate["required_events"], ["灯台の灯りを見つける"])
        self.assertEqual([attempt["kind"] for attempt in state["attempts"]], ["draft", "critique", "revision", "critique"])

    def test_card_context_exposes_same_volume_time_floor_and_allowed_time_ids(self) -> None:
        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        state["timeline"] = [
            {"id": "time-0001", "sequence": 0},
            {"id": "time-0002", "sequence": 1},
            {"id": "time-0003", "sequence": 2},
        ]
        state["cards"] = {"v01-c01-s01": {"end_time_id": "time-0002"}}
        context = service._card_context(state, {"number": 1}, {"number": 2}, 1, False)
        self.assertEqual(context["same_volume_time_floor"], {"sequence": 1, "time_id": "time-0002"})
        self.assertEqual(context["allowed_start_time_ids"], ["time-0002", "time-0003"])

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
    def test_continuity_rejects_relationship_updates_even_when_the_field_exists(self) -> None:
        service = SeriesService(self.workspace)
        state = service._new_state(BRIEF)
        state["threads"] = []
        state["relationships"] = [{"id": "rel-0001", "current_state": {"emotion": "緊張"}}]
        card = {"scene_id": "v01-c01-s01", "allowed_update_ids": ["rel-0001"], "thread_actions": []}
        update = {"source_scene_id": "v01-c01-s01", "id": "rel-0001", "field": "emotion", "value": "信頼", "evidence": "根拠"}
        with self.assertRaisesRegex(ContractError, "更新できない台帳種別"):
            service._validate_continuity({"handoff_summary": "次へ", "state_updates": [update]}, "根拠", card, state, False)

    def test_volume_summary_requires_every_unresolved_major_thread_exactly_once(self) -> None:
        state = SeriesService(self.workspace)._new_state(BRIEF)
        state["threads"] = [
            {"id": "thread-0001", "importance": "major", "current_state": {"status": "open"}},
            {"id": "thread-0002", "importance": "supporting", "current_state": {"status": "open"}},
        ]
        with self.assertRaisesRegex(ContractError, "未回収主要項目"):
            SeriesService._validate_volume_summary({"volume_summary": "要約", "unresolved_thread_ids": []}, state)


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
