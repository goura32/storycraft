"""シリーズ生成工程の状態遷移とモデル協調。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .series_contracts import ContractError, ContractValidator, RunResult, StoryModel
from .series_output import OutputWriter


class SeriesWorkflow(ContractValidator):
    """状態を一工程ずつ前進させ、出力まで協調する。"""

    def _new_state(self, brief: dict[str, Any]) -> dict[str, Any]:
        self._validate_brief(brief)
        return {
            "version": 3,
            "brief": brief,
            "plan": None,
            "characters": None,
            "relationships": None,
            "world": None,
            "timeline": None,
            "threads": None,
            "chapters": {},
            "cards": {},
            "scenes": [],
            "volume_summaries": {},
            "initial_ledgers_confirmed": False,
            "attempts": [],
            "closure": {},
            "completed": False,
            "last_completed_unit": None,
            "stopped_at": None,
            "stop_reason": None,
            "_active": None,
        }

    def _advance(self, state: dict[str, Any], model: StoryModel, *, stop_after_scene: str | None = None) -> RunResult:
        try:
            while not state["completed"]:
                scene_id = self._run_one(state, model)
                self.store.save(state)
                if scene_id is not None and scene_id == stop_after_scene:
                    return self._result(state)
            return self._result(state, self._volume_paths())
        except ContractError as exc:
            active = state.get("_active") or {"stage": "unknown", "unit": None}
            state["stopped_at"] = active
            state["stop_reason"] = str(exc)
            self.store.save(state)
            raise

    def _run_one(self, state: dict[str, Any], model: StoryModel) -> str | None:
        if state["plan"] is None:
            plan = self._improve("plan", {"brief": state["brief"]}, model, state, lambda item: self._validate_plan(item, state["brief"]))
            self._validate_chapter_count_length(state["brief"], len(plan["volumes"]))
            state["plan"] = plan
            state["last_completed_unit"] = {"stage": "plan", "unit": None}
            return None
        if state["characters"] is None:
            proposed = self._improve("characters", {"brief": state["brief"], "plan": state["plan"]}, model, state, self._validate_characters)
            state["characters"] = self._assign_ids(proposed["characters"], "char")
            return None
        if state["relationships"] is None:
            context = {"brief": state["brief"], "plan": state["plan"], "characters": state["characters"]}
            proposed = self._improve("relationships", context, model, state, lambda item: self._validate_relationships(item, state["characters"]))
            state["relationships"] = self._assign_ids(proposed["relationships"], "rel")
            return None
        if state["world"] is None:
            context = {"brief": state["brief"], "plan": state["plan"], "characters": state["characters"], "relationships": state["relationships"]}
            proposed = self._improve("world", context, model, state, self._validate_world)
            state["world"] = self._assign_ids(proposed["entities"], "entity")
            return None
        if state["timeline"] is None:
            context = self._ledger_context(state)
            proposed = self._improve("timeline", context, model, state, lambda item: self._validate_timeline(item, self._known_ids(state)))
            state["timeline"] = self._assign_ids(proposed["timelines"], "time")
            return None
        if state["threads"] is None:
            context = self._ledger_context(state)
            proposed = self._improve("threads", context, model, state, lambda item: self._validate_threads(item, self._known_ids(state), state["brief"], state["plan"]))
            state["threads"] = self._assign_ids(proposed["threads"], "thread")
            return None
        if not state["initial_ledgers_confirmed"]:
            self._validate_initial_ledgers(state)
            state["initial_ledgers_confirmed"] = True
            return None

        for volume_number, planned_volume in enumerate(state["plan"]["volumes"], 1):
            volume = {**planned_volume, "number": volume_number}
            volume_key = str(volume_number)
            if volume_key not in state["chapters"]:
                context = {"brief": state["brief"], "volume": volume, "ledgers": self._ledger_context(state), "prior_summaries": self._prior_summaries(state, volume["number"])}
                state["chapters"][volume_key] = self._improve("volume_chapters", context, model, state, lambda item: self._validate_chapters(item, volume, state["brief"]))["chapters"]
                return None
            for chapter in state["chapters"][volume_key]:
                for scene_number in range(1, chapter["scene_count"] + 1):
                    scene_id = self._scene_id(volume["number"], chapter["number"], scene_number)
                    if any(scene["scene_id"] == scene_id for scene in state["scenes"]):
                        continue
                    is_final_scene = self._is_final_scene(state, volume, chapter, scene_number)
                    card_context = self._card_context(state, volume, chapter, scene_number, is_final_scene)
                    card = self._improve("scene_card", card_context, model, state, lambda item: self._validate_card(item, scene_id, state))
                    state["cards"][scene_id] = card
                    state["last_completed_unit"] = {"stage": "scene_card", "unit": scene_id}
                    prose_context = self._writer_context(state, card, scene_id, is_final_scene)
                    prose = self._improve("scene", prose_context, model, state, self._validate_scene)
                    continuity_context = {"scene_id": scene_id, "content": prose["content"], "card": card, "is_final_scene": is_final_scene}
                    continuity = self._improve("continuity", continuity_context, model, state, lambda item: self._validate_continuity(item, prose["content"], card, state, is_final_scene))
                    self._apply_updates(state, continuity["state_updates"], scene_id)
                    state["scenes"].append({"scene_id": scene_id, "volume": volume["number"], "chapter": chapter["number"], "content": prose["content"], "handoff_summary": continuity["handoff_summary"], "state_updates": continuity["state_updates"]})
                    return scene_id
            if volume_key not in state["volume_summaries"]:
                scenes = [scene for scene in state["scenes"] if scene["volume"] == volume["number"]]
                context = {"volume": volume, "scenes": scenes, "threads": state["threads"]}
                summary = self._improve("volume_summary", context, model, state, lambda item: self._validate_volume_summary(item, state))
                state["volume_summaries"][volume_key] = summary
                return None

        if not state["closure"]:
            context = {"brief": state["brief"], "threads": state["threads"], "scenes": state["scenes"], "volume_summaries": state["volume_summaries"]}
            state["closure"] = self._improve("closure", context, model, state, lambda item: self._validate_closure(item, state))
            return None
        self._write_output(state)
        state["completed"] = True
        return None

    def _improve(self, stage: str, context: dict[str, Any], model: StoryModel, state: dict[str, Any], validator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        state["_active"] = {"stage": stage, "unit": context.get("scene_id")}
        candidate: dict[str, Any] | None = None
        error = ""
        for _ in range(4):
            proposed = model.generate(stage, context)
            try:
                if not isinstance(proposed, dict):
                    raise ContractError("草稿がオブジェクトではありません")
                validator(proposed)
            except ContractError as exc:
                error = str(exc)
                self._record_attempt(state, stage, "draft_rejected", context, proposed, error)
                self.store.save(state)
                continue
            candidate = proposed
            break
        if candidate is None:
            raise ContractError(f"{stage} の草稿を検証できませんでした: {error}")
        self._record_attempt(state, stage, "draft", context, candidate, "accepted")
        try:
            critique = model.critique(stage, candidate, context)
            self._validate_critique(critique)
        except Exception as exc:
            self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
            return candidate
        self._record_attempt(state, stage, "critique", context, critique, "accepted")
        if not critique["issues"]:
            return candidate
        revised: dict[str, Any] | None = None
        try:
            revised = model.revision(stage, candidate, critique, context)
            if not isinstance(revised, dict):
                raise ContractError("修正版がオブジェクトではありません")
            validator(revised)
            self._validate_revision_preserves_contract(stage, candidate, revised)
        except Exception as exc:
            self._record_attempt(state, stage, "revision_failed", context, revised, str(exc))
            return candidate
        self._record_attempt(state, stage, "revision", context, revised, "accepted")
        return revised

    @staticmethod
    def _record_attempt(state: dict[str, Any], stage: str, kind: str, input_value: dict[str, Any], response: Any, validation: str) -> None:
        state["attempts"].append({
            "stage": stage, "kind": kind, "unit": input_value.get("scene_id"), "input": input_value,
            "response": response, "validation": validation, "raw_reference": None,
        })

    def _validate_initial_ledgers(self, state: dict[str, Any]) -> None:
        if not all(state[key] is not None for key in ("characters", "relationships", "world", "timeline", "threads")):
            raise ContractError("初期台帳がそろっていません")
        for record in state["threads"]:
            for character_id in record["character_knowledge"]:
                if character_id not in self._known_ids(state):
                    raise ContractError("主要項目台帳の人物参照が不正です")

    def _ledger_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"brief": state["brief"], "plan": state["plan"], "characters": state["characters"] or [], "relationships": state["relationships"] or [], "world": state["world"] or [], "timeline": state["timeline"] or [], "threads": state["threads"] or []}

    def _known_ids(self, state: dict[str, Any]) -> set[str]:
        return {record["id"] for key in ("characters", "relationships", "world", "timeline", "threads") for record in (state[key] or [])}

    def _record_for_id(self, state: dict[str, Any], identifier: str) -> dict[str, Any] | None:
        for key in ("characters", "relationships", "world", "timeline", "threads"):
            for record in state[key] or []:
                if record["id"] == identifier:
                    return record
        return None

    def _apply_updates(self, state: dict[str, Any], updates: list[dict[str, Any]], scene_id: str) -> None:
        for update in updates:
            target = self._record_for_id(state, update["id"])
            assert target is not None
            target["current_state"][update["field"]] = update["value"]
            target["last_scene_id"] = scene_id

    def _card_context(self, state: dict[str, Any], volume: dict[str, Any], chapter: dict[str, Any], scene_number: int, is_final_scene: bool) -> dict[str, Any]:
        scene_id = self._scene_id(volume["number"], chapter["number"], scene_number)
        return {"scene_id": scene_id, "volume": volume, "chapter": chapter, "scene_number": scene_number, "ledgers": self._ledger_context(state), "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "", "is_final_scene": is_final_scene}

    def _writer_context(self, state: dict[str, Any], card: dict[str, Any], scene_id: str, is_final_scene: bool) -> dict[str, Any]:
        visible = {record["id"]: record for key in ("characters", "relationships", "world", "timeline", "threads") for record in state[key] or [] if record["id"] in card["visible_ids"]}
        return {"scene_id": scene_id, "card": card, "writer_view": visible, "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "", "is_final_scene": is_final_scene, "ending": state["brief"]["ending"] if is_final_scene else ""}

    @staticmethod
    def _scene_id(volume: int, chapter: int, scene: int) -> str:
        return f"v{volume:02d}-c{chapter:02d}-s{scene:02d}"

    def _is_final_scene(self, state: dict[str, Any], volume: dict[str, Any], chapter: dict[str, Any], scene_number: int) -> bool:
        return volume["number"] == len(state["plan"]["volumes"]) and chapter["number"] == state["chapters"][str(volume["number"])][-1]["number"] and scene_number == chapter["scene_count"]

    @staticmethod
    def _prior_summaries(state: dict[str, Any], volume_number: int) -> list[dict[str, Any]]:
        return [state["volume_summaries"][str(number)] for number in range(1, volume_number) if str(number) in state["volume_summaries"]]

    def _validate_manuscript_state(self, state: dict[str, Any]) -> None:
        OutputWriter(self.workspace).validate_manuscript_state(state)

    def _write_output(self, state: dict[str, Any]) -> list[Path]:
        writer = OutputWriter(self.workspace)
        writer.validate_output = self._validate_output
        return writer.write(state)

    @staticmethod
    def _validate_output(paths: list[Path], series: Path) -> None:
        OutputWriter.validate_output(paths, series)

    def _volume_paths(self) -> list[Path]:
        return sorted((self.workspace / "output").glob("volume-*.md"))

    def _result(self, state: dict[str, Any], paths: list[Path] | None = None) -> RunResult:
        return RunResult(completed=bool(state["completed"]), volume_count=len(state["plan"]["volumes"]) if state["plan"] else 0, volume_paths=paths or self._volume_paths(), series_path=self.workspace / "output" / "series.md", closure=state["closure"])