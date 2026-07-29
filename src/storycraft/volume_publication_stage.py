"""selection snapshot に基づき一巻だけを確定する公開工程。"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .publication_builder import (
    build_volume_publication_files,
    validate_volume_publication_files,
)
from .run_state import RunStateStore, validate_run_state
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError


class VolumePublicationStageService:
    """LLMを呼ばず、現在selectionの対象巻を一度だけ公開する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)
        self.selection_store = SelectionSnapshotStore(self.workspace_root)

    def run(self, *, updated_at: str) -> dict[str, Any]:
        state = self.state_store.load()
        if state["status"] != "running" or state["current_stage"] != "volume_publication":
            raise ContractError("現在のrun-stateは実行可能なvolume_publicationではありません")
        if state["active_candidate"] is not None or state["active_scene_id"] is not None:
            raise ContractError("volume_publication開始時にactive成果物を残せません")
        if state["pending_commit"] is not None:
            raise ContractError("pending_commitは復旧処理で先に収束する必要があります")
        target = state["current_target"]
        volume_number = target.get("volume_number") if isinstance(target, dict) else None
        if not isinstance(volume_number, int) or isinstance(volume_number, bool) or volume_number < 1:
            raise ContractError("volume_publication.current_target.volume_numberが不正です")
        selection_id = state["current_selection_id"]
        assert isinstance(selection_id, str)
        snapshot = self.selection_store.load(selection_id)
        inputs = self._resolve_inputs(snapshot["slots"], volume_number)
        publication_id = self._reserve_identifier(volume_number)
        files = build_volume_publication_files(
            publication_id=publication_id,
            volume_number=volume_number,
            input_selection_id=selection_id,
            settings_id=inputs["settings_id"],
            series_plan_id=inputs["series_plan_id"],
            volume_plan_id=inputs["volume_plan_id"],
            current_state_id=inputs["current_state_id"],
            chapter_plan_ids=inputs["chapter_plan_ids"],
            scene_ids=inputs["scene_ids"],
            quality_disposition_refs=inputs["quality_ids"],
            scenes=inputs["scenes"],
            remaining_major_issues=inputs["remaining_major_issues"],
            created_at=updated_at,
        )
        validate_volume_publication_files(files)
        staging = self.workspace_root / "runtime/staging" / f"volume-publication-{publication_id}"
        final = self.workspace_root / "publications" / publication_id
        if staging.exists() or final.exists() or staging.is_symlink() or final.is_symlink():
            raise ContractError("巻公開の不変配置を上書きできません")
        staging.mkdir(parents=True)
        self._write_files(staging, files)
        digest = self._digest(files)
        prepared = deepcopy(state)
        prepared["pending_commit"] = {
            "kind": "volume_publication",
            "staging_path": str(staging.relative_to(self.workspace_root)),
            "input_selection_id": selection_id,
            "output_selection_id": None,
            "state_update": {"volume_number": volume_number, "publication_id": publication_id},
            "targets": [{
                "artifact_id": publication_id,
                "artifact_kind": "volume_publication",
                "staging_path": str(staging.relative_to(self.workspace_root)),
                "final_path": str(final.relative_to(self.workspace_root)),
                "sha256": digest,
                "status": "pending",
            }],
        }
        prepared["updated_at"] = updated_at
        self.state_store.save(prepared)
        try:
            final.parent.mkdir(parents=True, exist_ok=True)
            os.rename(staging, final)
        except OSError as exc:
            raise ContractError("巻公開directoryを確定できません") from exc
        self._validate_final(final, files, digest)
        result = deepcopy(prepared)
        result["pending_commit"] = None
        result["published_volumes"] = [*state["published_volumes"], {"volume_number": volume_number, "publication_id": publication_id}]
        volume_count = inputs["volume_count"]
        if volume_number == volume_count:
            result.update({"status": "completed", "stop_reason": None, "last_error": None, "current_stage": None, "current_target": None, "active_candidate": None, "active_scene_id": None})
        else:
            result.update({"current_stage": "volume_plan", "current_target": {"volume_number": volume_number + 1}, "status": "running", "stop_reason": None, "last_error": None})
        result["updated_at"] = updated_at
        validate_run_state(result)
        self.state_store.save(result)
        return result

    def recover_pending(self, *, updated_at: str) -> dict[str, Any]:
        """manifest と staging/final の配置を照合し、providerなしで公開を収束する。"""
        state = self.state_store.load()
        pending = state["pending_commit"]
        if not isinstance(pending, dict) or pending.get("kind") != "volume_publication":
            raise ContractError("volume_publicationのpending_commitがありません")
        targets = pending.get("targets")
        update = pending.get("state_update")
        if not isinstance(targets, list) or len(targets) != 1 or not isinstance(update, dict):
            raise ContractError("volume_publication manifestが不正です")
        target = targets[0]
        if not isinstance(target, dict):
            raise ContractError("volume_publication manifest targetが不正です")
        publication_id = target.get("artifact_id")
        volume_number = update.get("volume_number")
        if (
            target.get("artifact_kind") != "volume_publication"
            or target.get("status") not in {"pending", "finalized"}
            or update.get("publication_id") != publication_id
            or not isinstance(publication_id, str)
            or not isinstance(volume_number, int)
            or isinstance(volume_number, bool)
        ):
            raise ContractError("volume_publication manifest参照が不正です")
        staging_rel = target.get("staging_path")
        final_rel = target.get("final_path")
        if not isinstance(staging_rel, str) or not isinstance(final_rel, str):
            raise ContractError("volume_publication manifest pathが不正です")
        staging = self.workspace_root / staging_rel
        final = self.workspace_root / final_rel
        if staging.is_symlink() or final.is_symlink() or (staging.exists() and final.exists()):
            raise ContractError("publication_invalid: staging/final配置が不整合です")
        if staging.exists():
            try:
                final.parent.mkdir(parents=True, exist_ok=True)
                os.rename(staging, final)
            except OSError as exc:
                raise ContractError("巻公開recoveryでfinalizeできません") from exc
        if not final.is_dir():
            raise ContractError("publication_invalid: 公開targetが存在しません")
        try:
            actual = {
                "record.json": json.loads((final / "record.json").read_text(encoding="utf-8")),
                "manuscript.md": (final / "manuscript.md").read_text(encoding="utf-8"),
            }
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("publication_invalid: 公開targetを読めません") from exc
        validate_volume_publication_files(actual)
        if actual["record.json"].get("volume_publication_id") != publication_id or self._digest(actual) != target.get("sha256"):
            raise ContractError("publication_invalid: 公開targetがmanifestと一致しません")
        selection_id = state["current_selection_id"]
        assert isinstance(selection_id, str)
        inputs = self._resolve_inputs(self.selection_store.load(selection_id)["slots"], volume_number)
        result = deepcopy(state)
        result["pending_commit"] = None
        result["published_volumes"] = [*state["published_volumes"], {"volume_number": volume_number, "publication_id": publication_id}]
        if volume_number == inputs["volume_count"]:
            result.update({"status": "completed", "stop_reason": None, "last_error": None, "current_stage": None, "current_target": None, "active_candidate": None, "active_scene_id": None})
        else:
            result.update({"status": "running", "stop_reason": None, "last_error": None, "current_stage": "volume_plan", "current_target": {"volume_number": volume_number + 1}})
        result["updated_at"] = updated_at
        validate_run_state(result)
        self.state_store.save(result)
        return result

    def _resolve_inputs(self, slots: object, volume_number: int) -> dict[str, Any]:
        if not isinstance(slots, dict):
            raise ContractError("selection slotsが不正です")
        required = ("settings", "series_plan", f"volume_plan.v{volume_number:02d}", "current_state")
        if any(key not in slots for key in required):
            raise ContractError("巻公開に必要なselection slotがありません")
        settings_id = slots["settings"]
        series_plan_id = slots["series_plan"]
        volume_plan_id = slots[f"volume_plan.v{volume_number:02d}"]
        current_state_id = slots["current_state"]
        settings = self._read("runtime/settings", settings_id)
        series = self._read("design/series-plans", series_plan_id)
        volume = self._read("design/volume-plans", volume_plan_id)
        self._read("generations", current_state_id)
        if settings.get("settings_id") != settings_id or series.get("series_plan_id") != series_plan_id or volume.get("volume_plan_id") != volume_plan_id or volume.get("volume_number") != volume_number:
            raise ContractError("巻公開入力のselection参照が成果物と一致しません")
        volume_count = series.get("volume_count")
        if not isinstance(volume_count, int) or isinstance(volume_count, bool) or volume_count < volume_number:
            raise ContractError("series-planのvolume_countが不正です")
        prefix = f".v{volume_number:02d}"
        chapter_slots = sorted((key, value) for key, value in slots.items() if key.startswith("chapter_plan" + prefix))
        scene_slots = sorted((key, value) for key, value in slots.items() if key.startswith("scene" + prefix) and not key.startswith("scene_prose"))
        quality_slots = sorted((key, value) for key, value in slots.items() if key.startswith("scene_prose_disposition" + prefix))
        if not chapter_slots or not scene_slots or len(quality_slots) != len(scene_slots):
            raise ContractError("巻公開の章・場面・品質判定slotが不完全です")
        chapter_ids = [value for _, value in chapter_slots]
        scenes: list[dict[str, str]] = []
        for _, scene_id in scene_slots:
            record = self._read("scenes", scene_id)
            prose = record.get("prose")
            if record.get("scene_id") != scene_id or not isinstance(prose, str):
                raise ContractError("scene成果物が不正です")
            scenes.append({"scene_id": scene_id, "prose": prose})
        quality_ids = [value for _, value in quality_slots]
        remaining = False
        for quality_id in quality_ids:
            quality = self._read("quality", quality_id)
            if quality.get("quality_id") != quality_id or quality.get("result") == "blocked_manual_review":
                raise ContractError("publication_invalid: quality dispositionが公開不能です")
            issues = quality.get("remaining_major_issues")
            if not isinstance(issues, list):
                raise ContractError("quality dispositionが不正です")
            remaining = remaining or bool(issues)
        return {"settings_id": settings_id, "series_plan_id": series_plan_id, "volume_plan_id": volume_plan_id, "current_state_id": current_state_id, "chapter_plan_ids": chapter_ids, "scene_ids": [item["scene_id"] for item in scenes], "quality_ids": quality_ids, "scenes": scenes, "remaining_major_issues": remaining, "volume_count": volume_count}

    def _read(self, directory: str, artifact_id: object) -> dict[str, Any]:
        if not isinstance(artifact_id, str):
            raise ContractError("artifact IDが不正です")
        path = self.workspace_root / directory / artifact_id / "record.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"公開入力成果物を読めません: {artifact_id}") from exc
        if not isinstance(value, dict):
            raise ContractError("公開入力成果物がobjectではありません")
        return value

    def _reserve_identifier(self, volume_number: int) -> str:
        path = self.workspace_root / "runtime/counters.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            counters = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("counters.jsonを読めません") from exc
        number = counters.get("next_volume_publication", 1)
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ContractError("next_volume_publicationが不正です")
        counters["next_volume_publication"] = number + 1
        temporary = path.with_suffix(".json.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                json.dump(counters, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise ContractError("next_volume_publicationを原子的に予約できません") from exc
        return f"volume-pub-v{volume_number:02d}-{number:06d}"

    @staticmethod
    def _write_files(directory: Path, files: dict[str, dict[str, Any] | str]) -> None:
        for name, value in files.items():
            path = directory / name
            text = json.dumps(value, ensure_ascii=False, indent=2) + "\n" if isinstance(value, dict) else value
            path.write_text(text, encoding="utf-8")

    @staticmethod
    def _digest(files: dict[str, dict[str, Any] | str]) -> str:
        record = json.dumps(files["record.json"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256((record + "\n" + str(files["manuscript.md"])).encode()).hexdigest()

    def _validate_final(self, directory: Path, expected: dict[str, dict[str, Any] | str], digest: str) -> None:
        try:
            actual = {"record.json": json.loads((directory / "record.json").read_text(encoding="utf-8")), "manuscript.md": (directory / "manuscript.md").read_text(encoding="utf-8")}
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("確定済み巻公開を検証できません") from exc
        validate_volume_publication_files(actual)
        if actual != expected or self._digest(actual) != digest:
            raise ContractError("確定済み巻公開の内容がmanifestと一致しません")
