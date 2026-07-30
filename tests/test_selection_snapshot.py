"""成果物と保存の設計に基づく不変 selection snapshot。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.artifact_ids import initial_counters
from storycraft.selection_snapshot import (
    SelectionSnapshotStore,
    validate_selection_snapshot,
)
from storycraft.series_contracts import ContractError


class SelectionSnapshotTests(unittest.TestCase):
    @staticmethod
    def _store(root: Path) -> SelectionSnapshotStore:
        runtime = root / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "counters.json").write_text(json.dumps(initial_counters()), encoding="utf-8")
        return SelectionSnapshotStore(root)

    def test_accepts_canonical_coordinate_and_prose_disposition_slots(self) -> None:
        snapshot = {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"request": "request-000001", "scene_prose.v01.c02.s03": "scene-v01-c02-s03-000001", "scene_prose_disposition.v01.c02.s03": "quality-000001"}, "created_at": "2026-07-29T00:00:00Z"}
        self.assertIs(validate_selection_snapshot(snapshot), snapshot)

    def test_rejects_legacy_quality_slot_name(self) -> None:
        snapshot = {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"quality_disposition.quality-000001": "quality-000001"}, "created_at": "2026-07-29T00:00:00Z"}
        with self.assertRaises(ContractError):
            validate_selection_snapshot(snapshot)

    def test_rejects_invalid_slot_name(self) -> None:
        snapshot = {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"bad slot": "request-000001"}, "created_at": "2026-07-29T00:00:00Z"}
        with self.assertRaises(ContractError):
            validate_selection_snapshot(snapshot)

    def test_creates_immutable_snapshot_with_parent_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            first = store.create(
                slots={"request": "request-000001", "settings": "settings-000001"},
                created_at="2026-07-28T00:00:00Z",
            )
            second = store.create(
                input_selection_id=first["selection_id"],
                slots={**first["slots"], "series_plan": "series-plan-000001"},
                created_at="2026-07-28T00:00:01Z",
            )
            self.assertEqual(first["selection_id"], "selection-000001")
            self.assertEqual(second["selection_id"], "selection-000002")
            self.assertEqual(second["input_selection_id"], first["selection_id"])
            self.assertEqual(store.load(first["selection_id"]), first)

    def test_rejects_overwriting_existing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            store.create(
                slots={"request": "request-000001"},
                created_at="2026-07-28T00:00:00Z",
            )
            path = store.root / "selection-000001" / "record.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "不変"):
                store.create(
                    slots={"request": "request-000002"},
                    created_at="2026-07-28T00:00:01Z",
                    selection_id="selection-000001",
                )

    def test_rejects_selection_id_as_slot_value(self) -> None:
        with self.assertRaisesRegex(ContractError, "slots"):
            validate_selection_snapshot(
                {
                    "schema_version": 1,
                    "selection_id": "selection-000001",
                    "input_selection_id": None,
                    "slots": {"request": "selection-000001"},
                    "created_at": "2026-07-28T00:00:00Z",
                }
            )
