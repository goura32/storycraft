"""次世代実行状態の製品契約。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.nextgen import ContractError, SeriesService
from test_nextgen_flow import BRIEF, FlowModel


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

    def test_step_on_completed_series_does_not_rewrite_output(self) -> None:
        service = SeriesService(self.workspace)
        service.run(BRIEF, FlowModel())
        service._write_output = lambda state: self.fail("completed series must not write output")  # type: ignore[method-assign]
        result = service.step(FlowModel())
        self.assertTrue(result.completed)

    def test_revision_contract_loss_keeps_validated_draft_and_records_normalized_attempt(self) -> None:
        class RevisionLossModel:
            def generate(self, stage: str, context: dict) -> dict:
                return {"scene_id": context["scene_id"], "required_events": ["発見"]}

            def critique(self, stage: str, candidate: dict, context: dict) -> dict:
                return {"issues": [{"severity": "minor", "field": "required_events", "description": "表現", "suggestion": "修正"}]}

            def revise(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
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
