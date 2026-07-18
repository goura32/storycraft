"""シリーズ生成工程の状態遷移とモデル協調。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .log import logger
from .series_contracts import ContractError, ContractValidator, LLMCallError, RunResult, StoryModel
from .series_output import OutputWriter


class SeriesWorkflow(ContractValidator):
    """状態を一工程ずつ前進させ、出力まで協調する。"""

    def _new_state(self, brief: dict[str, Any] | None = None, *, keywords: list[str] | None = None) -> dict[str, Any]:
        if (brief is None) == (keywords is None):
            raise ContractError("初回入力には企画またはkeywordsのどちらか一方が必要です")
        if brief is not None:
            self._validate_brief(brief)
        if keywords is not None and (not keywords or not all(isinstance(keyword, str) and keyword.strip() for keyword in keywords)):
            raise ContractError("keywords は空でない文字列を一つ以上指定してください")
        return {
            "version": 4,
            "brief": brief,
            "keywords": keywords,
            "volume_map": None,
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
        if state["brief"] is None:
            brief = self._improve("brief", {"keywords": state["keywords"]}, model, state, self._validate_brief)
            state["brief"] = brief
            state["last_completed_unit"] = {"stage": "brief", "unit": None}
            return None
        if state["characters"] is None:
            proposed = self._improve("characters", {"brief": state["brief"]}, model, state, self._validate_characters)
            state["characters"] = self._assign_ids(proposed["characters"], "char")
            return None
        if state["relationships"] is None:
            context = {"brief": state["brief"], "characters": state["characters"]}
            proposed = self._improve("relationships", context, model, state, lambda item: self._validate_relationships(item, state["characters"]))
            state["relationships"] = self._assign_ids(proposed["relationships"], "rel")
            return None
        if state["world"] is None:
            context = {"brief": state["brief"], "characters": state["characters"], "relationships": state["relationships"]}
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
            proposed = self._improve("threads", context, model, state, lambda item: self._validate_threads(item, self._known_ids(state)))
            state["threads"] = self._assign_ids(proposed["threads"], "thread")
            return None
        if not state["initial_ledgers_confirmed"]:
            self._validate_initial_ledgers(state)
            state["initial_ledgers_confirmed"] = True
            return None
        if state["volume_map"] is None:
            context = {"brief": state["brief"], "ledgers": self._ledger_context(state)}
            volume_map = self._improve("volume_map", context, model, state, lambda item: self._validate_volume_map(item, state["brief"], state["threads"]))
            self._validate_chapter_count_length(state["brief"], len(volume_map["volumes"]))
            state["volume_map"] = volume_map
            state["last_completed_unit"] = {"stage": "volume_map", "unit": None}
            return None

        for volume_number, planned_volume in enumerate(state["volume_map"]["volumes"], 1):
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
                self._validate_volume_thread_targets(state, volume)
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

    def _improve(
        self, stage: str, context: dict[str, Any], model: StoryModel, state: dict[str, Any],
        validator: Callable[[dict[str, Any]], None], *, review: bool = True,
    ) -> dict[str, Any]:
        state["_active"] = {"stage": stage, "unit": context.get("scene_id"), "phase": "generate"}
        self.store.save(state)
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
        state["_active"]["phase"] = "draft_accepted"
        self.store.save(state)
        if not review:
            state["_active"]["phase"] = "completed"
            self.store.save(state)
            return candidate

        # 批評→修正ループ（max_critique_passes 回まで）。
        # Workflow はテスト/外部実装の StoryModel も受け入れるため、OpenAIStoryModel 固有の
        # model.client.settings へは依存しない。
        settings = getattr(getattr(model, "client", None), "settings", None)
        quality = getattr(settings, "quality", {})
        max_passes = quality.get("max_critique_passes", 3) if isinstance(quality, dict) else 3
        current_candidate = candidate
        for pass_num in range(1, max_passes + 1):
            state["_active"]["phase"] = f"critique_pass_{pass_num}"
            self.store.save(state)
            try:
                critique = model.critique(stage, current_candidate, context)
                self._validate_critique(critique)
            except LLMCallError as exc:
                self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                raise ContractError(f"{stage} の批評に失敗したため停止しました: {exc}") from exc
            except Exception as exc:
                self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                return current_candidate
            self._record_attempt(state, stage, "critique", context, critique, "accepted")
            logger.info(
                "批評結果: stage=%s pass=%s/%s final=False issues=%s",
                stage, pass_num, max_passes, len(critique["issues"]),
            )
            if critique["issues"]:
                logger.info(f"批評指摘: stage={stage} pass={pass_num}/{max_passes} 件数={len(critique['issues'])} severities={[i['severity'] for i in critique['issues']]}")
                if logger.isEnabledFor(10):  # DEBUG
                    for i, issue in enumerate(critique["issues"]):
                        logger.debug(f"  issue[{i}]: field={issue.get('field')} severity={issue.get('severity')} desc={issue.get('description')[:80]}...")
            if not critique["issues"]:
                logger.info(f"批評合格: {stage} pass={pass_num}")
                state["_active"]["phase"] = "completed"
                self.store.save(state)
                return current_candidate
            logger.warning(f"批評指摘あり: {stage} pass={pass_num}/{max_passes} issues={len(critique['issues'])}")
            # 修正実行
            state["_active"]["phase"] = f"revision_pass_{pass_num}"
            self.store.save(state)
            revised: dict[str, Any] | None = None
            try:
                revised = model.revision(stage, current_candidate, critique, context)
                if not isinstance(revised, dict):
                    raise ContractError("修正版がオブジェクトではありません")
                validator(revised)
                self._validate_revision_preserves_contract(stage, current_candidate, revised)
            except LLMCallError as exc:
                self._record_attempt(state, stage, "revision_failed", context, revised, str(exc))
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                raise ContractError(f"{stage} の修正に失敗したため停止しました: {exc}") from exc
            except Exception as exc:
                self._record_attempt(state, stage, "revision_failed", context, revised, str(exc))
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                return current_candidate
            self._record_attempt(state, stage, "revision", context, revised, "accepted")
            current_candidate = revised
        # 最終revisionも必ず検査する。ここを省くと、最終revisionが全issueを解消しても
        # 未検査のまま「未解決」と扱われる。
        final_pass = max_passes + 1
        state["_active"]["phase"] = "critique_final"
        self.store.save(state)
        try:
            final_critique = model.critique(stage, current_candidate, context)
            self._validate_critique(final_critique)
        except LLMCallError as exc:
            self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
            state["_active"]["phase"] = "failed"
            self.store.save(state)
            raise ContractError(f"{stage} の最終批評に失敗したため停止しました: {exc}") from exc
        except Exception as exc:
            self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
            state["_active"]["phase"] = "failed"
            self.store.save(state)
            return current_candidate
        self._record_attempt(state, stage, "critique", context, final_critique, "accepted")
        logger.info(
            "批評結果: stage=%s pass=%s/%s final=True issues=%s",
            stage, final_pass, max_passes, len(final_critique["issues"]),
        )
        if not final_critique["issues"]:
            logger.info(f"批評合格: {stage} pass={final_pass} (final revision verified)")
            state["_active"]["phase"] = "completed"
            self.store.save(state)
            return current_candidate
        logger.warning(f"批評未解決: {stage} max_revisions={max_passes} final_issues={len(final_critique['issues'])}")
        state["_active"]["phase"] = "completed"
        self.store.save(state)
        return current_candidate

    @staticmethod
    def _record_attempt(state: dict[str, Any], stage: str, kind: str, input_value: dict[str, Any], response: Any, validation: str) -> None:
        state["attempts"].append({
            "stage": stage, "kind": kind, "unit": input_value.get("scene_id"), "input": input_value,
            "response": response, "validation": validation, "raw_reference": None,
        })

    def _validate_volume_thread_targets(self, state: dict[str, Any], volume: dict[str, Any]) -> None:
        required = {(target["thread_id"], target["required_action"]) for target in volume["thread_targets"]}
        actual = {
            (action["thread_id"], action["action"])
            for scene_id, card in state["cards"].items()
            if scene_id.startswith(f"v{volume['number']:02d}-")
            for action in card.get("thread_actions", [])
        }
        missing = required - actual
        if missing:
            raise ContractError("巻配分で必須の主要項目操作が場面カードにありません")

    def _validate_initial_ledgers(self, state: dict[str, Any]) -> None:
        if not all(state[key] is not None for key in ("characters", "relationships", "world", "timeline", "threads")):
            raise ContractError("初期台帳がそろっていません")
        for record in state["threads"]:
            for character_id in record["character_knowledge"]:
                if character_id not in self._known_ids(state):
                    raise ContractError("主要項目台帳の人物参照が不正です")

    def _ledger_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"brief": state["brief"], "characters": state["characters"] or [], "relationships": state["relationships"] or [], "world": state["world"] or [], "timeline": state["timeline"] or [], "threads": state["threads"] or []}

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
        return volume["number"] == len(state["volume_map"]["volumes"]) and chapter["number"] == state["chapters"][str(volume["number"])][-1]["number"] and scene_number == chapter["scene_count"]

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
        return RunResult(completed=bool(state["completed"]), volume_count=len(state["volume_map"]["volumes"]) if state["volume_map"] else 0, volume_paths=paths or self._volume_paths(), series_path=self.workspace / "output" / "series.md", closure=state["closure"])
