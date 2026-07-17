"""次世代Storycraftの互換なし実行系。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol


class ContractError(ValueError):
    """利用者入力または生成結果が製品契約を満たさない。"""


class StoryModel(Protocol):
    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]: ...

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...

    def revise(
        self,
        stage: str,
        candidate: dict[str, Any],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RunResult:
    completed: bool
    volume_count: int
    volume_paths: list[Path]
    series_path: Path
    closure: dict[str, Any]


class _Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "state.json"

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict[str, Any]:
        if not self.exists():
            raise ContractError("保存済みシリーズがありません")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContractError("保存状態が壊れています") from exc
        if data.get("version") != 2:
            raise ContractError("この保存状態は次世代形式ではありません")
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)


class SeriesService:
    """一つのシリーズを生成、再開、出力する公開境界。"""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.store = _Store(workspace)

    def run(
        self,
        brief: dict[str, Any],
        model: StoryModel,
        *,
        stop_after_scene: str | None = None,
    ) -> RunResult:
        if self.store.exists():
            raise ContractError("この作業場所には保存済みシリーズがあります。resume を使ってください")
        state = self._new_state(brief)
        self.store.save(state)
        return self._advance(state, model, stop_after_scene=stop_after_scene)

    def resume(self, model: StoryModel) -> RunResult:
        state = self.store.load()
        return self._advance(state, model)

    def step(self, model: StoryModel, brief: dict[str, Any] | None = None) -> RunResult:
        """未完了の最初の単位だけを実行する。初回だけ企画が必要。"""
        if not self.store.exists():
            if brief is None:
                raise ContractError("初回の step には企画が必要です")
            state = self._new_state(brief)
            self.store.save(state)
        else:
            state = self.store.load()
        if state["plan"] is None:
            plan = self._improve(
                "plan", {"brief": state["brief"]}, model, state,
                lambda value: self._validate_plan(value, state["brief"]),
            )
            self._validate_plan(plan, state["brief"])
            state["plan"] = plan
            self.store.save(state)
            return self._result(state)
        specs = self._scene_specs(state["plan"])
        if state["next_scene_index"] < len(specs):
            scene_id = specs[state["next_scene_index"]]["scene_id"]
            return self._advance(state, model, stop_after_scene=str(scene_id))
        return self._advance(state, model)

    def _new_state(self, brief: dict[str, Any]) -> dict[str, Any]:
        self._validate_brief(brief)
        return {
            "version": 2,
            "brief": brief,
            "plan": None,
            "threads": self._initial_threads(brief),
            "scenes": [],
            "next_scene_index": 0,
            "attempts": [],
            "closure": {},
            "completed": False,
        }

    def _advance(
        self,
        state: dict[str, Any],
        model: StoryModel,
        *,
        stop_after_scene: str | None = None,
    ) -> RunResult:
        if state["plan"] is None:
            plan = self._improve(
                "plan", {"brief": state["brief"]}, model, state,
                lambda value: self._validate_plan(value, state["brief"]),
            )
            self._validate_plan(plan, state["brief"])
            state["plan"] = plan
            self.store.save(state)

        scene_specs = self._scene_specs(state["plan"])
        index = state["next_scene_index"]
        while index < len(scene_specs):
            spec = scene_specs[index]
            is_final_scene = index == len(scene_specs) - 1
            unresolved_thread_ids = [
                thread_id for thread_id, thread in state["threads"].items() if thread["status"] != "resolved"
            ]
            required_final_resolved_ids = unresolved_thread_ids if is_final_scene else []
            card_context = self._card_context(state, spec, is_final_scene, unresolved_thread_ids)
            card = self._improve(
                "scene_card", card_context, model, state,
                lambda value: self._validate_card(value, spec, state["threads"], required_final_resolved_ids),
            )
            self._validate_card(card, spec, state["threads"], required_final_resolved_ids)

            scene_context = {
                "brief": state["brief"],
                "plan": state["plan"],
                "card": card,
                "threads": {
                    thread_id: dict(state["threads"][thread_id])
                    for thread_id in card["visible_thread_ids"]
                },
                "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "",
                "is_final_scene": is_final_scene,
                "required_ending": state["brief"]["ending"] if is_final_scene else "",
                "required_resolved_ids": unresolved_thread_ids if is_final_scene else [],
            }
            scene = self._improve(
                "scene", scene_context, model, state,
                lambda value: self._validate_scene(value, card, state["threads"], required_final_resolved_ids),
            )
            self._validate_scene(scene, card, state["threads"], required_final_resolved_ids)
            self._apply_updates(state["threads"], scene["state_updates"], card["scene_id"])
            state["scenes"].append(
                {
                    "scene_id": card["scene_id"],
                    "volume": spec["volume"],
                    "chapter": spec["chapter"],
                    "content": scene["content"],
                    "handoff_summary": scene["handoff_summary"],
                    "state_updates": scene["state_updates"],
                }
            )
            index += 1
            state["next_scene_index"] = index
            self.store.save(state)
            if stop_after_scene == card["scene_id"]:
                return self._result(state)

        if not state["closure"]:
            closure_context = {"brief": state["brief"], "threads": state["threads"], "scenes": state["scenes"]}
            closure = self._improve(
                "closure", closure_context, model, state,
                lambda value: self._validate_closure(value, state["threads"]),
            )
            self._validate_closure(closure, state["threads"])
            state["closure"] = closure
            self.store.save(state)

        paths = self._write_output(state)
        state["completed"] = True
        self.store.save(state)
        return self._result(state, paths)

    def _improve(
        self,
        stage: str,
        context: dict[str, Any],
        model: StoryModel,
        state: dict[str, Any],
        validator: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        candidate: dict[str, Any] | None = None
        validation_error = ""
        for _ in range(4):
            proposed = model.generate(stage, context)
            if not isinstance(proposed, dict):
                validation_error = "草稿がオブジェクトではありません"
                state["attempts"].append({"stage": stage, "kind": "draft_rejected", "reason": validation_error})
                self.store.save(state)
                continue
            try:
                validator(proposed)
            except ContractError as exc:
                validation_error = str(exc)
                state["attempts"].append(
                    {"stage": stage, "kind": "draft_rejected", "candidate": proposed, "reason": validation_error}
                )
                self.store.save(state)
                continue
            candidate = proposed
            break
        if candidate is None:
            raise ContractError(f"{stage} の草稿を検証できませんでした: {validation_error}")
        state["attempts"].append(
            {"stage": stage, "kind": "draft", "input": context, "candidate": candidate}
        )
        self.store.save(state)
        try:
            critique = model.critique(stage, candidate, context)
        except Exception as exc:
            state["attempts"].append({"stage": stage, "kind": "critique_failed", "reason": str(exc)})
            self.store.save(state)
            return candidate
        try:
            self._validate_critique(critique)
        except ContractError as exc:
            state["attempts"].append({"stage": stage, "kind": "critique_failed", "reason": str(exc)})
            self.store.save(state)
            return candidate
        state["attempts"].append({"stage": stage, "kind": "critique", "critique": critique})
        try:
            revised = model.revise(stage, candidate, critique, context)
            if not isinstance(revised, dict):
                raise ContractError("修正版がオブジェクトではありません")
            validator(revised)
        except Exception as exc:  # 批評・修正失敗では草稿を失わせない
            state["attempts"].append({"stage": stage, "kind": "revision_failed", "reason": str(exc)})
            self.store.save(state)
            return candidate
        state["attempts"].append({"stage": stage, "kind": "revision", "candidate": revised})
        self.store.save(state)
        return revised

    @staticmethod
    def _validate_brief(brief: dict[str, Any]) -> None:
        if not isinstance(brief, dict):
            raise ContractError("企画はオブジェクトでなければなりません")
        for key in ("title", "premise", "ending"):
            if not isinstance(brief.get(key), str) or not brief[key].strip():
                raise ContractError(f"企画の必須項目がありません: {key}")
        volumes = brief.get("volumes")
        if volumes is not None and (not isinstance(volumes, int) or not 4 <= volumes <= 10):
            raise ContractError("volumes は 4〜10 の整数でなければなりません")
        chapter_counts = brief.get("chapters_per_volume")
        if chapter_counts is not None:
            if (
                not isinstance(chapter_counts, list)
                or not all(isinstance(count, int) and 1 <= count <= 12 for count in chapter_counts)
                or (volumes is not None and len(chapter_counts) != volumes)
            ):
                raise ContractError("chapters_per_volume は巻数と一致する1〜12の整数配列でなければなりません")
        questions = brief.get("major_questions", [])
        if not isinstance(questions, list) or not all(isinstance(question, str) and question.strip() for question in questions):
            raise ContractError("major_questions は空でない文字列の配列でなければなりません")

    @staticmethod
    def _initial_threads(brief: dict[str, Any]) -> dict[str, dict[str, Any]]:
        questions = brief.get("major_questions") or [brief["ending"]]
        return {
            f"question-{index:02d}": {
                "id": f"question-{index:02d}",
                "question": question,
                "status": "open",
                "last_scene_id": None,
            }
            for index, question in enumerate(questions, start=1)
        }

    @staticmethod
    def _validate_plan(plan: dict[str, Any], brief: dict[str, Any]) -> None:
        volumes = plan.get("volumes")
        if not isinstance(volumes, list) or not 4 <= len(volumes) <= 10:
            raise ContractError("全巻計画は4〜10巻でなければなりません")
        requested = brief.get("volumes")
        if requested is not None and len(volumes) != requested:
            raise ContractError("指定巻数と全巻計画の巻数が一致しません")
        requested_chapters = brief.get("chapters_per_volume")
        for expected, volume in enumerate(volumes, start=1):
            if not isinstance(volume, dict) or volume.get("number") != expected:
                raise ContractError("全巻計画の巻番号が連番ではありません")
            if not isinstance(volume.get("title"), str) or not volume["title"].strip():
                raise ContractError("巻題がありません")
            chapters = volume.get("chapters")
            if not isinstance(chapters, list) or not chapters:
                raise ContractError("各巻には少なくとも一章が必要です")
            if requested_chapters is not None and len(chapters) != requested_chapters[expected - 1]:
                raise ContractError("指定章数と全巻計画の章数が一致しません")
            for chapter_number, chapter in enumerate(chapters, start=1):
                if not isinstance(chapter, dict) or chapter.get("number") != chapter_number:
                    raise ContractError("章番号が連番ではありません")
                if not isinstance(chapter.get("title"), str) or not chapter["title"].strip():
                    raise ContractError("章題がありません")
            if not isinstance(volume.get("change"), str) or not volume["change"].strip():
                raise ContractError("各巻には成立する変化または区切りが必要です")
            if expected < len(volumes) and (
                not isinstance(volume.get("leaves_question"), str)
                or not volume["leaves_question"].strip()
            ):
                raise ContractError("最終巻以外には次巻へ続く問いが必要です")

    @staticmethod
    def _scene_specs(plan: dict[str, Any]) -> list[dict[str, int | str]]:
        specs: list[dict[str, int | str]] = []
        for volume in plan["volumes"]:
            for chapter in volume["chapters"]:
                volume_number = volume["number"]
                chapter_number = chapter["number"]
                for scene_number in (1, 2):
                    specs.append(
                        {
                            "volume": volume_number,
                            "chapter": chapter_number,
                            "scene": scene_number,
                            "scene_id": f"v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}",
                        }
                    )
        return specs

    @staticmethod
    def _card_context(
        state: dict[str, Any],
        spec: dict[str, int | str],
        is_final_scene: bool,
        unresolved_thread_ids: list[str],
    ) -> dict[str, Any]:
        return {
            "brief": state["brief"],
            "plan": state["plan"],
            "scene_id": spec["scene_id"],
            "volume": spec["volume"],
            "chapter": spec["chapter"],
            "scene": spec["scene"],
            "available_thread_ids": sorted(state["threads"]),
            "is_final_scene": is_final_scene,
            "unresolved_thread_ids": unresolved_thread_ids,
        }

    @staticmethod
    def _validate_card(
        card: dict[str, Any],
        spec: dict[str, int | str],
        threads: dict[str, Any],
        required_update_ids: list[str] | None = None,
    ) -> None:
        if card.get("scene_id") != spec["scene_id"]:
            raise ContractError("場面カードのIDが実行対象と一致しません")
        for field in ("visible_thread_ids", "allowed_update_ids"):
            values = card.get(field)
            if not isinstance(values, list) or not all(value in threads for value in values):
                raise ContractError(f"場面カードに未知の台帳IDがあります: {field}")
            if len(values) != len(set(values)):
                raise ContractError(f"場面カードのIDが重複しています: {field}")
        if not set(card["allowed_update_ids"]).issubset(card["visible_thread_ids"]):
            raise ContractError("状態更新の許可IDは可視IDの部分集合でなければなりません")
        if required_update_ids and not set(required_update_ids).issubset(card["allowed_update_ids"]):
            raise ContractError("最終場面は未回収の主要な問いをすべて更新許可しなければなりません")

    @staticmethod
    def _validate_scene(
        scene: dict[str, Any],
        card: dict[str, Any],
        threads: dict[str, Any],
        required_resolved_ids: list[str] | None = None,
    ) -> None:
        if not isinstance(scene.get("content"), str) or not scene["content"].strip():
            raise ContractError("場面本文が空です")
        if not isinstance(scene.get("handoff_summary"), str) or not scene["handoff_summary"].strip():
            raise ContractError("引継ぎ要約が空です")
        updates = scene.get("state_updates")
        if not isinstance(updates, list):
            raise ContractError("状態更新が配列ではありません")
        allowed = set(card["allowed_update_ids"])
        updated_ids: set[str] = set()
        for update in updates:
            if not isinstance(update, dict) or update.get("id") not in threads:
                raise ContractError("未知IDの状態更新です")
            if update["id"] not in allowed:
                raise ContractError("場面カードで許可されていない状態更新です")
            if update["id"] in updated_ids:
                raise ContractError("同じ問いを一場面で複数回更新できません")
            updated_ids.add(update["id"])
            if update.get("status") not in {"open", "in_progress", "resolved"}:
                raise ContractError("状態更新のstatusが不正です")
        if required_resolved_ids:
            unresolved = set(required_resolved_ids) - {
                update["id"] for update in updates if update.get("status") == "resolved"
            }
            if unresolved:
                raise ContractError("最終場面で回収されていない主要な問いがあります")

    @staticmethod
    def _apply_updates(threads: dict[str, Any], updates: list[dict[str, Any]], scene_id: str) -> None:
        for update in updates:
            thread = threads[update["id"]]
            thread["status"] = update["status"]
            thread["last_scene_id"] = scene_id

    @staticmethod
    def _validate_closure(closure: dict[str, Any], threads: dict[str, Any]) -> None:
        resolved_ids = closure.get("resolved_ids")
        if (
            not isinstance(resolved_ids, list)
            or len(resolved_ids) != len(set(resolved_ids))
            or set(resolved_ids) != set(threads)
        ):
            raise ContractError("主要な問いの回収結果が台帳と一致しません")
        if closure.get("ending_reached") is not True:
            raise ContractError("結末が確認できません")
        unresolved = [thread_id for thread_id, thread in threads.items() if thread["status"] != "resolved"]
        if unresolved:
            raise ContractError(f"未回収の主要な問いがあります: {', '.join(unresolved)}")

    @staticmethod
    def _validate_critique(critique: Any) -> None:
        if not isinstance(critique, dict) or not isinstance(critique.get("issues"), list):
            raise ContractError("批評の issues が配列ではありません")
        for issue in critique["issues"]:
            if not isinstance(issue, dict):
                raise ContractError("批評 issue がオブジェクトではありません")
            if issue.get("severity") not in {"critical", "major", "minor"}:
                raise ContractError("批評 issue の severity が不正です")
            for field in ("field", "description", "suggestion"):
                if not isinstance(issue.get(field), str) or not issue[field].strip():
                    raise ContractError(f"批評 issue の {field} がありません")

    def _write_output(self, state: dict[str, Any]) -> list[Path]:
        output_dir = self.workspace / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        scenes_by_volume: dict[int, list[dict[str, Any]]] = {}
        for scene in state["scenes"]:
            scenes_by_volume.setdefault(scene["volume"], []).append(scene)
        paths: list[Path] = []
        for volume in state["plan"]["volumes"]:
            number = volume["number"]
            chapter_titles = {chapter["number"]: chapter["title"] for chapter in volume["chapters"]}
            label = "無料導入巻" if number == 1 else "販売対象巻"
            lines = [f"# 第{number}巻 {volume['title']}", f"<!-- {label} -->", ""]
            current_chapter: int | None = None
            for scene in scenes_by_volume.get(number, []):
                if current_chapter != scene["chapter"]:
                    current_chapter = scene["chapter"]
                    lines.extend([f"## 第{current_chapter}章 {chapter_titles[current_chapter]}", ""])
                lines.extend([scene["content"], ""])
            path = output_dir / f"volume-{number:02d}.md"
            path.write_text("\n".join(lines), encoding="utf-8")
            paths.append(path)
        series_path = output_dir / "series.md"
        series_path.write_text(
            "\n\n".join(path.read_text(encoding="utf-8") for path in paths),
            encoding="utf-8",
        )
        self._validate_output(paths, series_path)
        return paths

    @staticmethod
    def _validate_output(paths: list[Path], series_path: Path) -> None:
        bodies = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if "## 第" not in text or not text.strip():
                raise ContractError(f"必要な章がない出力です: {path.name}")
            body = "\n".join(line for line in text.splitlines() if not line.startswith("#") and not line.startswith("<!--")).strip()
            if not body:
                raise ContractError(f"空本文の出力です: {path.name}")
            bodies.append(body)
        if len(bodies) != len(set(bodies)):
            raise ContractError("巻本文が重複しています")
        if not series_path.exists() or not series_path.read_text(encoding="utf-8").strip():
            raise ContractError("全巻Markdownがありません")

    def _result(self, state: dict[str, Any], paths: list[Path] | None = None) -> RunResult:
        if paths is None:
            output_dir = self.workspace / "output"
            paths = sorted(output_dir.glob("volume-*.md"))
        return RunResult(
            completed=bool(state["completed"]),
            volume_count=len(state["plan"]["volumes"]) if state["plan"] else 0,
            volume_paths=paths,
            series_path=self.workspace / "output" / "series.md",
            closure=state["closure"],
        )
