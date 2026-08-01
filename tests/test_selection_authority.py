from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.selection_authority import DEFAULT_CONTENT_VALIDATORS, resolve_selection
from storycraft.series_contracts import ContractError


NOW = "2026-07-29T00:00:00Z"
REQUEST = {"title": "t", "genre": "g", "premise": "p", "required_elements": [], "forbidden_elements": [], "ending_preference": "e", "volume_count": 4, "language": "ja"}


def write_record(root: Path, directory: str, artifact_id: str, record: dict) -> None:
    path = root / directory / artifact_id / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def snapshot(selection_id: str, slots: dict[str, str], parent: str | None = None) -> dict:
    return {"schema_version": 1, "selection_id": selection_id, "input_selection_id": parent, "slots": slots, "created_at": NOW}


class SelectionAuthorityTests(unittest.TestCase):
    def test_resolves_bootstrap_enveloped_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            value = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            self.assertEqual(set(resolve_selection(root, value)), {"request", "settings"})

    def test_rejects_missing_authority_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = snapshot("selection-000001", {"request": "request-000001"})
            with self.assertRaises(ContractError):
                resolve_selection(root, value)

    def test_rejects_a_symlinked_selected_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            external = root / "external-request"
            write_record(root, "external", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            external.mkdir(exist_ok=True)
            (root / "inputs").mkdir()
            (root / "inputs/request-000001").symlink_to(root / "external/request-000001", target_is_directory=True)
            value = snapshot("selection-000001", {"request": "request-000001"})

            with self.assertRaisesRegex(ContractError, "directory"):
                resolve_selection(root, value)

    def test_reapplies_the_request_content_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": {"title": "t"}})
            value = snapshot("selection-000001", {"request": "request-000001"})
            with self.assertRaisesRegex(ContractError, "request content"):
                resolve_selection(root, value)

    def test_default_resolver_rejects_an_empty_selected_initial_design(self) -> None:
        """Envelope validity alone must not make a selected stage artifact usable."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            parent = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            write_record(root, "runtime/selections", "selection-000001", parent)
            write_record(root, "design/initial", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "created_at": NOW, "content": {}})
            child = snapshot("selection-000002", {"initial_design": "initial-design-000001"}, "selection-000001")

            with self.assertRaisesRegex(ContractError, "initial-design content"):
                resolve_selection(root, child)

    def test_rejects_planning_count_and_coordinate_gaps(self) -> None:
        series = {"volume_count": 4, "series_objectives": ["完結"], "volume_summaries": [{"volume_number": n, "purpose": "p", "ending_change": "c"} for n in (1, 2, 3, 5)], "character_arc_map": {"c": [1]}, "relationship_arc_map": {"r": [1]}, "thread_progression": {"t": [1]}, "revelation_schedule": [{"volume_number": 1, "knowledge_id": "k"}], "ending_path": "完結", "global_constraints": []}
        volume = {"title": "巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立", "character_changes": {"c": "変化"}, "relationship_changes": {"r": "変化"}, "thread_goals": {"t": "進展"}, "revelations": [], "chapter_summaries": [{"chapter_number": 1, "purpose": "章"}, {"chapter_number": 3, "purpose": "章"}], "required_end_state": "終了", "handoff_expectations": []}
        chapter = {"title": "章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"], "scene_summaries": [{"scene_number": 1, "purpose": "場面"}, {"scene_number": 3, "purpose": "場面"}], "required_revelations": [], "constraints": []}
        with self.assertRaises(ContractError):
            DEFAULT_CONTENT_VALIDATORS["series-plan"](series, {})
        with self.assertRaises(ContractError):
            DEFAULT_CONTENT_VALIDATORS["volume-plan"](volume, {})
        with self.assertRaises(ContractError):
            DEFAULT_CONTENT_VALIDATORS["chapter-plan"](chapter, {})

    def test_default_resolver_registers_every_selected_content_kind(self) -> None:
        self.assertEqual(
            set(DEFAULT_CONTENT_VALIDATORS),
            {"request", "initial-design", "series-plan", "volume-plan", "chapter-plan", "scene-plan", "scene-card", "scene-prose", "continuity-update", "generation", "scene"},
        )

    def test_reapplies_kind_content_validator_using_the_artifact_input_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            parent = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            write_record(root, "runtime/selections", "selection-000001", parent)
            write_record(root, "design/initial", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "created_at": NOW, "content": {"valid": False}})
            child = snapshot("selection-000002", {"initial_design": "initial-design-000001"}, "selection-000001")
            seen: list[tuple[dict, dict]] = []
            def validator(content: dict, inputs: dict) -> None:
                seen.append((content, inputs))
                if content["valid"] is not True:
                    raise ContractError("content rejected")
            with self.assertRaisesRegex(ContractError, "content rejected"):
                resolve_selection(root, child, content_validators={"initial-design": validator})
            self.assertEqual(seen[0][1]["request"]["content"], REQUEST)
