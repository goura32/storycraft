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


if __name__ == "__main__":
    unittest.main()
