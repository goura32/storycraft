"""Selection-based scene continuity adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import CandidateStageRunner, CandidateStageSpec
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


class SceneContinuityStageService:
    """Propose and adopt continuity only against the selected adopted prose."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("scene_continuityの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["status"] != "running" or state["current_stage"] != "scene_continuity":
            raise ContractError("現在のrun-stateは実行可能なscene_continuityではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("scene_continuityには入力selectionが必要です")
        target = self._coordinate(state["current_target"])
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        coordinate = self._slot_coordinate(target)
        required = {"settings", "current_state", f"scene_plan.{coordinate}", f"scene_card.{coordinate}", f"scene_prose.{coordinate}"}
        if not required.issubset(snapshot["slots"]):
            raise ContractError("scene_continuity入力selectionに必須slotがありません")
        bundle = dict(snapshot)
        bundle["slots"] = {slot: snapshot["slots"][slot] for slot in required}
        inputs = resolve_selection(self.workspace_root, bundle)
        self._require_inputs(inputs, target)
        spec = CandidateStageSpec(
            stage="scene_continuity", artifact_kind="continuity-update", next_stage="scene_commit",
            next_target=dict(target), content_id_factory=self._content_id,
            content_validator=lambda content: self._validate_content(content, target, inputs),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(
            model, context=self._context(inputs, target), updated_at=updated_at,
        )

    @staticmethod
    def _coordinate(value: object) -> dict[str, int]:
        if not isinstance(value, dict) or set(value) != {"volume_number", "chapter_number", "scene_number"}:
            raise ContractError("scene_continuityのcurrent_targetが不正です")
        if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value.values()):
            raise ContractError("scene_continuityには有効な場面座標が必要です")
        return dict(value)

    @staticmethod
    def _slot_coordinate(target: dict[str, int]) -> str:
        return f"v{target['volume_number']:02d}.c{target['chapter_number']:02d}.s{target['scene_number']:02d}"

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"scene_continuity入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, int]) -> None:
        coordinate = self._slot_coordinate(target)
        required = {"settings", "current_state", f"scene_plan.{coordinate}", f"scene_card.{coordinate}", f"scene_prose.{coordinate}"}
        if not required.issubset(inputs):
            raise ContractError("scene_continuity入力selectionが不正です")
        for slot in (f"scene_plan.{coordinate}", f"scene_card.{coordinate}", f"scene_prose.{coordinate}"):
            if not isinstance(self._payload(inputs[slot], slot), dict):
                raise ContractError("scene_continuity入力成果物が不正です")

    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, int]) -> dict[str, Any]:
        coordinate = self._slot_coordinate(target)
        return {
            "settings": self._payload(inputs["settings"], "settings"),
            "current_state": self._payload(inputs["current_state"], "current_state"),
            "scene_plan": self._payload(inputs[f"scene_plan.{coordinate}"], "scene_plan"),
            "scene_card": self._payload(inputs[f"scene_card.{coordinate}"], "scene_card"),
            "scene_prose": self._payload(inputs[f"scene_prose.{coordinate}"], "scene_prose"),
            **target,
        }

    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"continuity-v{target['volume_number']:02d}-c{target['chapter_number']:02d}-s{target['scene_number']:02d}-{reserve_counter(self.workspace_root, 'next_continuity'):06d}"

    @staticmethod
    def _path_binding(target: str, path: str) -> tuple[str, str]:
        prefix = f"$.{target}."
        if not path.startswith(prefix):
            raise ContractError("continuity_update pathが不正です")
        parts = path[len(prefix):].split(".")
        if not parts or any(not part for part in parts):
            raise ContractError("continuity_update pathが不正です")
        return parts[0], parts[1] if len(parts) > 1 else "value"

    @staticmethod
    def _evidence_is_in_prose(location: object, text: str) -> bool:
        if not isinstance(location, str):
            return False
        if location.startswith("prose:"):
            try:
                offset = int(location.split(":", 1)[1])
            except ValueError:
                return False
            encoded = text.encode("utf-8")
            if not 0 <= offset < len(encoded):
                return False
            try:
                encoded[:offset].decode("utf-8")
            except UnicodeDecodeError:
                return False
            return True
        if location.startswith("paragraph:"):
            try:
                paragraph = int(location.split(":", 1)[1])
            except ValueError:
                return False
            return 0 <= paragraph < len(text.split("\n\n"))
        return False

    @staticmethod
    def _validate_content(
        content: object,
        target: dict[str, int],
        inputs: dict[str, dict[str, Any]],
    ) -> None:
        if not isinstance(content, dict) or set(content) != {"coordinate", "changes"} or content.get("coordinate") != target or not isinstance(content.get("changes"), list):
            raise ContractError("continuity_update contentが不正です")
        current_state = SceneContinuityStageService._payload(inputs.get("current_state", {}), "current_state")
        card = SceneContinuityStageService._payload(
            SceneContinuityStageService._record_for_coordinate(inputs, "scene_card", target),
            "scene_card",
        )
        prose = SceneContinuityStageService._payload(
            SceneContinuityStageService._record_for_coordinate(inputs, "scene_prose", target),
            "scene_prose",
        )
        timeline = current_state.get("timeline_position")
        if not isinstance(timeline, int) or isinstance(timeline, bool) or timeline < 0:
            raise ContractError("current_state timeline_positionが不正です")
        thread_states = current_state.get("unresolved_thread_states")
        if not isinstance(thread_states, dict):
            raise ContractError("current_state unresolved_thread_statesが不正です")
        text = prose.get("text")
        if not isinstance(text, str) or not text:
            raise ContractError("scene_prose本文が不正です")
        allowed_updates = card.get("allowed_updates")
        if not isinstance(allowed_updates, list):
            raise ContractError("scene-card allowed_updatesが不正です")
        for change in content["changes"]:
            if not isinstance(change, dict) or set(change) != {"op", "target", "path", "value", "evidence_locations"}:
                raise ContractError("continuity_update changeが不正です")
            if change["op"] not in {"set", "add", "remove"} or change["target"] not in {"story_facts", "character_knowledge", "reader_disclosures", "unresolved_thread_states", "timeline_position"}:
                raise ContractError("continuity_update changeが不正です")
            if not isinstance(change["path"], str):
                raise ContractError("continuity_update pathが不正です")
            if change["target"] == "timeline_position":
                if change["path"] != "$.timeline_position" or not isinstance(change["value"], int) or isinstance(change["value"], bool) or change["value"] < timeline:
                    raise ContractError("timeline_positionは非負整数のsetによる単調増加だけを許可します")
                target_id, field = "timeline_position", "value"
            else:
                target_id, field = SceneContinuityStageService._path_binding(change["target"], change["path"])
                if change["target"] == "unresolved_thread_states":
                    if (
                        target_id not in thread_states
                        or change["op"] != "set"
                        or field != "status"
                        or change["value"] not in {"open", "progressed", "resolved"}
                    ):
                        raise ContractError("continuity_updateのthread targetがcanonical state外です")
            matching_updates = [
                update for update in allowed_updates
                if isinstance(update, dict)
                and update.get("target_type") == change["target"]
                and update.get("target_id") == target_id
                and isinstance(update.get("allowed_fields"), list)
                and field in update["allowed_fields"]
            ]
            if not matching_updates:
                raise ContractError("continuity_updateがscene-cardのallowed_updates外です")
            if not isinstance(change["evidence_locations"], list) or not change["evidence_locations"] or any(not isinstance(item, str) or not item for item in change["evidence_locations"]):
                raise ContractError("continuity_update evidence_locationsが不正です")
            if any(not SceneContinuityStageService._evidence_is_in_prose(item, text) for item in change["evidence_locations"]):
                raise ContractError("continuity_update evidence_locationsが本文を指していません")

        # Reuse the commit applicator at the candidate boundary so invalid
        # paths/values cannot survive until scene_commit.
        from .scene_commit_stage import SceneCommitStageService
        SceneCommitStageService._apply_continuity(current_state, content)

    @staticmethod
    def _record_for_coordinate(
        inputs: dict[str, dict[str, Any]],
        stem: str,
        target: dict[str, int],
    ) -> dict[str, Any]:
        coordinate = SceneContinuityStageService._slot_coordinate(target)
        record = inputs.get(f"{stem}.{coordinate}")
        if not isinstance(record, dict):
            raise ContractError(f"scene_continuity入力{stem}がありません")
        return record


def create_scene_continuity_stage_service(workspace_root: Path) -> SceneContinuityStageService:
    return SceneContinuityStageService(workspace_root)
