"""シリーズ生成工程の状態遷移とモデル協調。"""
from __future__ import annotations

from collections import Counter
import json
import re

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
            "version": 5,
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
            "quality_acceptances": [],
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
            logger.error(
                "工程終了: stage=%s %s result=failed error=%s",
                active["stage"], self._progress_label(state, {"scene_id": active.get("unit")}).replace(" ", ","), exc,
            )
            state["stopped_at"] = active
            state["stop_reason"] = str(exc)
            self.store.save(state)
            raise

    @staticmethod
    def _progress_label(state: dict[str, Any], context: dict[str, Any]) -> str:
        """現在の対象を、運用ログで比較可能な巻・章・場面座標に整形する。"""
        scene_id = context.get("scene_id")
        volume = context.get("volume") if isinstance(context.get("volume"), dict) else {}
        volume_number = volume.get("number")
        chapter_number = None
        scene_number = None
        if isinstance(scene_id, str):
            try:
                volume_number = int(scene_id[1:3])
                chapter_number = int(scene_id[5:7])
                scene_number = int(scene_id[9:11])
            except (TypeError, ValueError):
                pass
        volume_map = state.get("volume_map")
        volumes = volume_map.get("volumes", []) if isinstance(volume_map, dict) else []
        if not isinstance(volume_number, int) or not volumes:
            return "v:-/-"
        label = f"v:{volume_number}/{len(volumes)}"
        chapters = state.get("chapters", {}).get(str(volume_number), [])
        if not isinstance(chapter_number, int) or not chapters:
            return label
        chapter = next((item for item in chapters if item.get("number") == chapter_number), None)
        if not isinstance(chapter, dict):
            return label
        label += f" c:{chapter_number}/{len(chapters)}"
        if not isinstance(scene_number, int):
            return label
        return f"{label} s:{scene_number}/{chapter['scene_count']}"

    def _finish_stage(self, state: dict[str, Any], stage: str, context: dict[str, Any], candidate: dict[str, Any], result: str) -> dict[str, Any]:
        logger.info("工程完了: stage=%s %s result=%s", stage, self._progress_label(state, context).replace(" ", ","), result)
        return candidate

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
                    card = self._improve(
                        "scene_card", card_context, model, state,
                        lambda item: self._validate_card(
                            item, scene_id, state, volume, card_context["required_thread_actions"],
                        ),
                    )
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
        progress = self._progress_label(state, context)
        set_log_ref = getattr(model, "set_log_ref", None)
        if callable(set_log_ref):
            set_log_ref(progress)
        set_log_quality_pass = getattr(model, "set_log_quality_pass", None)
        if callable(set_log_quality_pass):
            set_log_quality_pass()
        logger.info("工程開始: stage=%s %s", stage, progress.replace(" ", ","))
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
            return self._finish_stage(state, stage, context, candidate, "accepted")

        # 批評→修正ループ（max_critique_passes 回まで、既定は最小の1回）。
        # Workflow はテスト/外部実装の StoryModel も受け入れるため、OpenAIStoryModel 固有の
        # model.client.settings へは依存しない。
        settings = getattr(getattr(model, "client", None), "settings", None)
        quality = getattr(settings, "quality", {})
        max_passes = quality.get("max_critique_passes", 1) if isinstance(quality, dict) else 1
        current_candidate = candidate
        for pass_num in range(1, max_passes + 1):
            critique = self._review_candidate(
                stage, current_candidate, context, model, state,
                pass_num=pass_num, max_passes=max_passes, final=False,
            )
            if critique is None:
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                raise ContractError(f"{stage} の批評を検証できないため停止しました")
            if critique["issues"]:
                if logger.isEnabledFor(10):  # DEBUG
                    for i, issue in enumerate(critique["issues"]):
                        logger.debug(f"  issue[{i}]: field={issue.get('field')} severity={issue.get('severity')} desc={issue.get('description')[:80]}...")
            if not critique["issues"]:
                state["_active"]["phase"] = "completed"
                self.store.save(state)
                return self._finish_stage(state, stage, context, current_candidate, "accepted")
            # 修正実行
            state["_active"]["phase"] = f"revision_pass_{pass_num}"
            self.store.save(state)
            revised: dict[str, Any] | None = None
            set_log_quality_pass = getattr(model, "set_log_quality_pass", None)
            if callable(set_log_quality_pass):
                set_log_quality_pass(f"{pass_num}/{max_passes + 1}")
            try:
                revised = model.revision(stage, current_candidate, critique, context)
                if not isinstance(revised, dict):
                    raise ContractError("修正版がオブジェクトではありません")
                validator(revised)
                self._validate_revision_scope(current_candidate, revised, critique)
            except LLMCallError as exc:
                self._record_attempt(state, stage, "revision_failed", context, revised, str(exc))
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                raise ContractError(f"{stage} の修正に失敗したため停止しました: {exc}") from exc
            except ContractError as exc:
                self._record_attempt(state, stage, "revision_rejected", context, revised, str(exc))
                state["_active"]["phase"] = f"revision_pass_{pass_num}_rejected"
                self.store.save(state)
                logger.warning("修正版を構造契約違反として不採用: stage=%s pass=%s error=%s", stage, pass_num, exc)
                continue
            except Exception as exc:
                self._record_attempt(state, stage, "revision_failed", context, revised, str(exc))
                state["_active"]["phase"] = "failed"
                self.store.save(state)
                raise ContractError(f"{stage} の修正版処理に失敗したため停止しました: {exc}") from exc
            self._record_attempt(state, stage, "revision", context, revised, "accepted")
            current_candidate = revised
        # 最終revisionも必ず検査する。ここを省くと、最終revisionが全issueを解消しても
        # 未検査のまま「未解決」と扱われる。
        final_pass = max_passes + 1
        final_critique = self._review_candidate(
            stage, current_candidate, context, model, state,
            pass_num=final_pass, max_passes=max_passes, final=True,
        )
        if final_critique is None:
            state["_active"]["phase"] = "failed"
            self.store.save(state)
            raise ContractError(f"{stage} の最終批評を検証できないため停止しました")
        if not final_critique["issues"]:
            state["_active"]["phase"] = "completed"
            self.store.save(state)
            return self._finish_stage(state, stage, context, current_candidate, "accepted")
        acceptance = {
            "stage": stage,
            "unit": context.get("scene_id"),
            "reason": "max_critique_passes_exhausted",
            "max_critique_passes": max_passes,
            "final_review_pass": final_pass,
            "issues": final_critique["issues"],
        }
        state["quality_acceptances"].append(acceptance)
        self._record_attempt(state, stage, "quality_accepted_with_known_issues", context, acceptance, "accepted_with_known_issues")
        logger.warning(
            "既知の品質課題を受容して採用: stage=%s max_revisions=%s final_issues=%s severities=%s",
            stage, max_passes, len(final_critique["issues"]),
            [issue["severity"] for issue in final_critique["issues"]],
        )
        state["_active"]["phase"] = "completed_with_known_issues"
        # 親工程がcandidateをstateへ反映した直後にまとめて永続化する。
        # ここで保存すると、受容記録だけが残ってcandidateが未採用の状態になり得る。
        return self._finish_stage(state, stage, context, current_candidate, "accepted_with_known_issues")

    def _review_candidate(
        self, stage: str, candidate: dict[str, Any], context: dict[str, Any], model: StoryModel,
        state: dict[str, Any], *, pass_num: int, max_passes: int, final: bool,
    ) -> dict[str, Any] | None:
        """批評の記録・失敗正規化・件数ログを通常／最終工程で共有する。"""
        active = state.get("_active") or {"stage": stage, "unit": context.get("scene_id")}
        state["_active"] = active
        active["phase"] = "critique_final" if final else f"critique_pass_{pass_num}"
        self.store.save(state)
        critique: Any = None
        set_log_quality_pass = getattr(model, "set_log_quality_pass", None)
        if callable(set_log_quality_pass):
            set_log_quality_pass(f"{pass_num}/{max_passes + 1}")
        try:
            critique = model.critique(stage, candidate, context)
            self._validate_critique(critique)
            self._validate_critique_fields(critique, candidate)
        except LLMCallError as exc:
            self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
            active["phase"] = "failed"
            self.store.save(state)
            label = "最終批評" if final else "批評"
            raise ContractError(f"{stage} の{label}に失敗したため停止しました: {exc}") from exc
        except Exception as exc:
            self._record_attempt(state, stage, "critique_failed", context, critique, str(exc))
            active["phase"] = "failed"
            self.store.save(state)
            return None
        self._record_attempt(state, stage, "critique", context, critique, "accepted")
        if critique["issues"]:
            logger.warning(
                "批評指摘: stage=%s %s quality_pass=%s/%s severities=%s",
                stage,
                self._progress_label(state, context).replace(" ", ","),
                pass_num,
                max_passes + 1,
                [issue["severity"] for issue in critique["issues"]],
            )
        return critique

    @staticmethod
    def _field_tokens(field: str) -> tuple[str | int, ...]:
        """Convert the review schema's dotted/indexed field path into a candidate path."""
        if field.startswith("$."):
            field = field[2:]
        elif field == "$":
            return ()
        tokens: list[str | int] = []
        position = 0
        while position < len(field):
            if field[position] == "[":
                match = re.match(r"\[(\d+)\]", field[position:])
                if match is not None:
                    tokens.append(int(match.group(1)))
                    position += match.end()
                else:
                    match = re.match(r'\[("(?:[^"\\]|\\.)*")\]', field[position:])
                    if match is None:
                        raise ContractError("批評 issue の field パスが不正です")
                    try:
                        tokens.append(json.loads(match.group(1)))
                    except json.JSONDecodeError as exc:
                        raise ContractError("批評 issue の field パスが不正です") from exc
                    position += match.end()
            else:
                match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", field[position:])
                if match is None:
                    raise ContractError("批評 issue の field パスが不正です")
                tokens.append(match.group(0))
                position += match.end()
            if position < len(field) and field[position] == ".":
                position += 1
            elif position < len(field) and field[position] != "[":
                raise ContractError("批評 issue の field パスが不正です")
        return tuple(tokens)

    @classmethod
    def _validate_critique_fields(cls, critique: dict[str, Any], candidate: dict[str, Any]) -> None:
        for issue in critique["issues"]:
            value: Any = candidate
            for token in cls._field_tokens(issue["field"]):
                if isinstance(value, dict) and isinstance(token, str) and token in value:
                    value = value[token]
                elif isinstance(value, list) and isinstance(token, int) and 0 <= token < len(value):
                    value = value[token]
                else:
                    raise ContractError("批評 issue の field が候補を指しません")

    @classmethod
    def _validate_revision_scope(cls, candidate: dict[str, Any], revised: dict[str, Any], critique: dict[str, Any]) -> None:
        """A revision may alter only a field explicitly cited by the accepted critique."""
        allowed = [cls._field_tokens(issue["field"]) for issue in critique["issues"]]

        def changed_paths(before: Any, after: Any, prefix: tuple[str | int, ...] = ()) -> set[tuple[str | int, ...]]:
            if type(before) is not type(after):
                return {prefix}
            if isinstance(before, dict):
                paths: set[tuple[str | int, ...]] = set()
                for key in set(before) | set(after):
                    if key not in before or key not in after:
                        paths.add(prefix + (key,))
                    else:
                        paths |= changed_paths(before[key], after[key], prefix + (key,))
                return paths
            if isinstance(before, list):
                if len(before) != len(after):
                    return {prefix}
                paths = set()
                for index, (old, new) in enumerate(zip(before, after)):
                    paths |= changed_paths(old, new, prefix + (index,))
                return paths
            return {prefix} if before != after else set()

        for path in changed_paths(candidate, revised):
            if not any(path[:len(cited)] == cited for cited in allowed):
                raise ContractError("修正版が批評で引用されていないfieldを変更しています")

    @staticmethod
    def _record_attempt(state: dict[str, Any], stage: str, kind: str, input_value: dict[str, Any], response: Any, validation: str) -> None:
        state["attempts"].append({
            "stage": stage, "kind": kind, "unit": input_value.get("scene_id"), "input": input_value,
            "response": response, "validation": validation, "raw_reference": None,
        })

    def _validate_volume_thread_targets(self, state: dict[str, Any], volume: dict[str, Any]) -> None:
        actual = Counter(
            (action["thread_id"], action["action"])
            for scene_id, card in state["cards"].items()
            if scene_id.startswith(f"v{volume['number']:02d}-")
            for action in card.get("thread_actions", [])
        )
        required = Counter((target["thread_id"], target["required_action"]) for target in volume["thread_targets"])
        if actual != required:
            if actual - required:
                raise ContractError("場面カードに巻配分の対象外または重複した主要項目操作があります")
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
        time_by_id = {record["id"]: record for record in state["timeline"]}
        volume_prefix = scene_id.split("-c", 1)[0] + "-"
        prior_end_ids = [
            card["end_time_id"] for prior_scene_id, card in state["cards"].items()
            if prior_scene_id.startswith(volume_prefix)
        ]
        floor = max((time_by_id[time_id] for time_id in prior_end_ids), key=lambda record: record["sequence"], default=None)
        allowed_start_time_ids = [
            record["id"] for record in state["timeline"]
            if floor is None or record["sequence"] >= floor["sequence"]
        ]
        return {
            "scene_id": scene_id, "volume": volume, "chapter": chapter, "scene_number": scene_number,
            "ledgers": self._ledger_context(state),
            "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "",
            "previous_scene_content": state["scenes"][-1]["content"] if state["scenes"] else "",
            "is_final_scene": is_final_scene,
            "same_volume_time_floor": {"sequence": floor["sequence"], "time_id": floor["id"]} if floor else None,
            "allowed_start_time_ids": allowed_start_time_ids,
            "required_thread_actions": self._required_thread_actions(state, volume, scene_id),
        }

    def _required_thread_actions(self, state: dict[str, Any], volume: dict[str, Any], scene_id: str) -> list[dict[str, str]]:
        """巻配分の各主要項目操作を、意味に沿う一つの場面へ決定的に割り当てる。"""
        chapters = state["chapters"].get(str(volume["number"]), [])
        if not chapters or not volume.get("thread_targets"):
            return []
        slots = [
            self._scene_id(volume["number"], chapter["number"], number)
            for chapter in chapters
            for number in range(1, chapter["scene_count"] + 1)
        ]
        if not slots:
            return []
        grouped = {action: [] for action in ("introduce", "advance", "resolve")}
        for target in volume["thread_targets"]:
            grouped[target["required_action"]].append(target)
        targets_by_slot: dict[str, list[dict[str, str]]] = {}
        anchors = {"introduce": 0, "advance": (len(slots) - 1) // 2, "resolve": len(slots) - 1}
        for action, targets in grouped.items():
            for offset, target in enumerate(targets):
                slot = slots[min(anchors[action] + offset, len(slots) - 1)]
                targets_by_slot.setdefault(slot, []).append({"thread_id": target["thread_id"], "action": action})
        return targets_by_slot.get(scene_id, [])

    def _writer_context(self, state: dict[str, Any], card: dict[str, Any], scene_id: str, is_final_scene: bool) -> dict[str, Any]:
        visible = {record["id"]: record for key in ("characters", "relationships", "world", "timeline", "threads") for record in state[key] or [] if record["id"] in card["visible_ids"]}
        return {"scene_id": scene_id, "card": card, "writer_view": visible, "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "", "is_final_scene": is_final_scene, "ending": state["brief"]["ending_preference"] if is_final_scene else ""}

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
