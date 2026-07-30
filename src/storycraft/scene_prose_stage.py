"""Storycraft Version 1 scene_prose Stage実行。"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .initial_generation import validate_initial_generation
from .reviewed_candidate_stage import (
    fsync_directory,
    read_json,
    utc_now,
)
from .reviewed_prose_stage import (
    ReviewedProseSpec,
    ReviewedProseStageRunner,
)
from .series_contracts import (
    ContractError,
    ContractValidator,
    ProseStoryModel,
)
from .workspace import validate_workspace_layout


_SPEC = ReviewedProseSpec(
    stage="scene_prose",
    artifact_type="scene_prose",
    review_category="scene_prose_quality",
    next_stage="scene_continuity",
    model_stage="scene_prose",
)


class SceneProseStageService:
    """採用済みScene Cardから日本語Scene本文を確定する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.runner = ReviewedProseStageRunner(
            self.workspace_root,
            _SPEC,
        )

    def run(
        self,
        model: ProseStoryModel,
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace_layout(
                self.workspace_root
            )
        state = self.runner.state_store.load()
        target = state["current_target"]

        volume_number = target.get("volume_number")
        chapter_number = target.get("chapter_number")
        scene_number = target.get("scene_number")
        for number, label in (
            (volume_number, "Volume"),
            (chapter_number, "Chapter"),
            (scene_number, "Scene"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"scene_proseには対象{label}番号が必要です"
                )

        generation_id = state["current_generation_id"]
        if generation_id is None:
            raise ContractError(
                "scene_proseにはcurrent Generationが必要です"
            )
        if target.get("basis_generation_id") != generation_id:
            raise ContractError(
                "scene_prose targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "scene_prose targetのseriesがworkspaceと"
                "一致しません"
            )

        scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        if target.get("scene_id") != scene_id:
            raise ContractError(
                "scene_prose targetのscene_idが対象座標と"
                "一致しません"
            )
        if state["active_scene_id"] != scene_id:
            raise ContractError(
                "scene_proseのactive_scene_idが実行対象と"
                "一致しません"
            )

        brief = read_json(
            self.workspace_root / "input/brief.json"
        )
        initial_design = read_json(
            self.workspace_root
            / "design/initial/v0001/initial-design.json"
        )
        series_plan = read_json(
            self.workspace_root
            / "design/series-plans"
            / "series-plan-v0001"
            / "series-plan.json"
        )
        volume_plan = read_json(
            self.workspace_root
            / "design/volume-plans"
            / f"v{volume_number:02d}-v0001"
            / "volume-plan.json"
        )
        chapter_plan = read_json(
            self.workspace_root
            / "design/chapter-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}-v0001"
            )
            / "chapter-plan.json"
        )
        scene_plan = read_json(
            self.workspace_root
            / "design/scene-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}"
                f"-s{scene_number:03d}-v0001"
            )
            / "scene-plan.json"
        )

        staging_root = (
            self.workspace_root
            / "runtime/staging"
            / f"scene-{scene_id}"
        )
        scene_card = read_json(staging_root / "scene-card.json")

        expected_targets = {
            "series_plan_id": series_plan["series_plan_id"],
            "volume_plan_id": volume_plan["volume_plan_id"],
            "chapter_plan_id": chapter_plan["chapter_plan_id"],
            "scene_plan_id": scene_plan["scene_plan_id"],
            "scene_card_version": scene_card["version"],
        }
        for field, expected in expected_targets.items():
            if target.get(field) != expected:
                raise ContractError(
                    f"scene_prose targetの{field}が"
                    "採用済み成果物と一致しません"
                )

        if scene_card.get("scene_id") != scene_id:
            raise ContractError(
                "Scene Cardのscene_idが実行対象と一致しません"
            )
        if scene_card.get("basis_generation_id") != generation_id:
            raise ContractError(
                "Scene Cardのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if (
            scene_card.get("scene_plan_id")
            != scene_plan["scene_plan_id"]
        ):
            raise ContractError(
                "Scene Cardのscene_plan_idが"
                "採用済みScene Planと一致しません"
            )

        current_generation = self._read_generation(generation_id)
        self._validate_current_generation(
            current_generation,
            generation_id,
            initial_design,
        )
        ContractValidator._validate_scene_card_v1(
            scene_card,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            generation_id,
            adopted=True,
        )

        writer_context = self._build_writer_context(
            brief,
            initial_design,
            scene_card,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
        )
        review_context = self._build_review_context(
            writer_context,
            initial_design,
            scene_card,
        )
        timestamp = updated_at or utc_now()

        return self.runner.run(
            model,
            context=writer_context,
            review_context=review_context,
            validator=self._validate_prose_text,
            adopter=lambda prose: self._adopt(
                prose,
                staging_root,
            ),
            next_target={
                "series": state["workspace_id"],
                "series_plan_id": series_plan["series_plan_id"],
                "volume_plan_id": volume_plan["volume_plan_id"],
                "chapter_plan_id": chapter_plan["chapter_plan_id"],
                "scene_plan_id": scene_plan["scene_plan_id"],
                "scene_id": scene_id,
                "scene_card_version": scene_card["version"],
                "prose_version": 1,
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": scene_number,
                "basis_generation_id": generation_id,
            },
            updated_at=timestamp,
            workspace_already_validated=True,
        )

    def _read_generation(
        self,
        generation_id: str,
    ) -> dict[str, Any]:
        root = self.workspace_root / "generations" / generation_id
        if not root.is_dir():
            raise ContractError(
                "current Generation directoryが存在しません"
            )

        return {
            name: read_json(root / name)
            for name in (
                "canon.json",
                "state.json",
                "evidence.json",
                "commit.json",
            )
        }

    @staticmethod
    def _validate_current_generation(
        generation: dict[str, Any],
        generation_id: str,
        initial_design: dict[str, Any],
    ) -> None:
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            value = generation.get(name)
            if not isinstance(value, dict):
                raise ContractError(
                    f"current Generation fileが不正です: {name}"
                )
            if value.get("generation_id") != generation_id:
                raise ContractError(
                    "current Generationのgeneration_idが"
                    f"一致しません: {name}"
                )

        if (
            generation["commit.json"].get("commit_type")
            == "initial_design"
        ):
            validate_initial_generation(
                generation,
                initial_design,
            )

    def _build_writer_context(
        self,
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        scene_card: dict[str, Any],
        generation: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
    ) -> dict[str, Any]:
        pov_id = scene_card["pov_character_id"]
        participant_ids = set(scene_card["participant_ids"])
        location_id = scene_card["location_id"]
        state = generation["state.json"]

        characters_by_id = {
            record["character_id"]: record
            for record in initial_design["characters"]
        }
        locations_by_id = {
            record["location_id"]: record
            for record in initial_design["locations"]
        }
        relationships_by_id = {
            record["relationship_id"]: record
            for record in initial_design["relationships"]
        }
        knowledge_by_id = {
            record["knowledge_id"]: record
            for record in initial_design["knowledge_facts"]
        }
        threads_by_id = {
            record["thread_id"]: record
            for record in initial_design["threads"]
        }

        forbidden = set(scene_card["forbidden_revelations"])
        allowed = (
            set(scene_card["allowed_revelations"]) - forbidden
        )
        required = (
            set(scene_card["required_revelations"]) - forbidden
        )
        pov_knowledge = state["characters"][pov_id][
            "knowledge_states"
        ]

        permitted_information = []
        for identifier, fact in knowledge_by_id.items():
            if identifier in forbidden:
                continue
            pov_state = pov_knowledge.get(identifier, "unknown")
            if (
                identifier not in allowed
                and fact["reader_visibility"] != "revealed"
                and pov_state == "unknown"
            ):
                continue
            permitted_information.append({
                "statement": fact["statement"],
                "pov_state": pov_state,
                "already_reader_visible": (
                    fact["reader_visibility"] == "revealed"
                ),
                "required_in_scene": identifier in required,
            })

        permitted_threads = []
        for identifier, thread in threads_by_id.items():
            if (
                identifier in forbidden
                or identifier not in allowed
            ):
                continue
            current = state["threads"][identifier]
            permitted_threads.append({
                "title": thread["title"],
                "question": thread["question"],
                "importance": thread["importance"],
                "current_status": current["status"],
                "progress_summary": current["progress_summary"],
                "open_questions": deepcopy(
                    current["open_questions"]
                ),
                "required_in_scene": identifier in required,
            })

        writer_characters = []
        for identifier in scene_card["participant_ids"]:
            design = characters_by_id[identifier]
            current = state["characters"][identifier]
            record = {
                "name": design["name"],
                "aliases": deepcopy(design["aliases"]),
                "role": design["role"],
                "public_profile": design["public_profile"],
                "observable_state": {
                    "current_location": locations_by_id[
                        current["current_location_id"]
                    ]["name"],
                    "physical_condition": current[
                        "physical_condition"
                    ],
                    "availability": current["availability"],
                    "alive_status": current["alive_status"],
                },
                "is_pov": identifier == pov_id,
            }
            if identifier == pov_id:
                record["pov_inner_context"] = {
                    "desires": deepcopy(design["desires"]),
                    "fears": deepcopy(design["fears"]),
                    "misbeliefs": deepcopy(design["misbeliefs"]),
                    "strengths": deepcopy(design["strengths"]),
                    "weaknesses": deepcopy(design["weaknesses"]),
                    "emotional_condition": current[
                        "emotional_condition"
                    ],
                    "goals": deepcopy(current["goals"]),
                    "active_constraints": deepcopy(
                        current["active_constraints"]
                    ),
                }
            writer_characters.append(record)

        writer_relationships = []
        for identifier, design in relationships_by_id.items():
            if not set(design["participant_ids"]).issubset(
                participant_ids
            ):
                continue
            current = state["relationships"][identifier]
            writer_relationships.append({
                "participants": [
                    characters_by_id[character_id]["name"]
                    for character_id in design["participant_ids"]
                ],
                "relationship_type": design[
                    "relationship_type"
                ],
                "public_description": design[
                    "public_description"
                ],
                "constraints": deepcopy(design["constraints"]),
                "current_state": {
                    "status": current["status"],
                    "trust": current["trust"],
                    "affection": current["affection"],
                    "fear": current["fear"],
                    "hostility": current["hostility"],
                    "obligations": deepcopy(
                        current["obligations"]
                    ),
                    "public_status": current["public_status"],
                },
            })

        location = locations_by_id[location_id]
        writer_location = {
            "name": location["name"],
            "description": location["description"],
            "access_constraints": deepcopy(
                location["access_constraints"]
            ),
            "public_facts": deepcopy(location["public_facts"]),
        }

        world_rules = [
            {
                "name": rule["name"],
                "description": rule["description"],
                "scope": rule["scope"],
                "exceptions": deepcopy(rule["exceptions"]),
            }
            for rule in initial_design["world_rules"]
            if rule["reader_visibility"] == "reader_visible"
        ]

        continuity_boundaries = []
        for update in scene_card["allowed_updates"]:
            target_type = update["target_type"]
            target_id = update["target_id"]
            if target_type == "character_state":
                target = characters_by_id[target_id]["name"]
            elif target_type == "relationship_state":
                target = relationships_by_id[target_id][
                    "public_description"
                ]
            elif target_type == "thread_state":
                target = threads_by_id[target_id]["title"]
            elif target_type == "timeline_state":
                target = "物語時間"
            else:
                target = target_type
            continuity_boundaries.append({
                "target_type": target_type,
                "target": target,
                "allowed_fields": deepcopy(
                    update["allowed_fields"]
                ),
            })

        safe_scene_card = {
            "pov_character": characters_by_id[pov_id]["name"],
            "participants": [
                characters_by_id[identifier]["name"]
                for identifier in scene_card["participant_ids"]
            ],
            "location": location["name"],
            "story_time": scene_card["story_time"],
            "purpose": scene_card["purpose"],
            "opening_state": scene_card["opening_state"],
            "required_beats": [
                {
                    "description": beat["description"],
                    "order_hint": beat["order_hint"],
                }
                for beat in scene_card["required_beats"]
            ],
            "conflict": scene_card["conflict"],
            "permitted_information": deepcopy(
                permitted_information
            ),
            "permitted_threads": deepcopy(permitted_threads),
            "continuity_boundaries": continuity_boundaries,
            "ending_state_targets": deepcopy(
                scene_card["ending_state_targets"]
            ),
            "style_constraints": deepcopy(
                scene_card["style_constraints"]
            ),
        }

        return {
            "brief_style": {
                field: deepcopy(brief[field])
                for field in ("genre", "tone", "audience")
                if field in brief
            },
            "scene_card": safe_scene_card,
            "characters": writer_characters,
            "relationships": writer_relationships,
            "location": writer_location,
            "world_rules": world_rules,
            "current_time": {
                "scene_time": scene_card["story_time"],
                "current_story_time": state["timeline"][
                    "current_story_time"
                ],
                "elapsed_time": state["timeline"]["elapsed_time"],
                "time_constraints": deepcopy(
                    state["timeline"]["time_constraints"]
                ),
            },
            "previous_scene_excerpt": self._previous_scene_excerpt(
                volume_number,
                chapter_number,
                scene_number,
            ),
        }

    @staticmethod
    def _build_review_context(
        writer_context: dict[str, Any],
        initial_design: dict[str, Any],
        scene_card: dict[str, Any],
    ) -> dict[str, Any]:
        knowledge_by_id = {
            record["knowledge_id"]: record
            for record in initial_design["knowledge_facts"]
        }
        threads_by_id = {
            record["thread_id"]: record
            for record in initial_design["threads"]
        }

        forbidden_disclosures = []
        for identifier in scene_card["forbidden_revelations"]:
            if identifier in knowledge_by_id:
                forbidden_disclosures.append({
                    "kind": "knowledge",
                    "statement": knowledge_by_id[identifier][
                        "statement"
                    ],
                })
            elif identifier in threads_by_id:
                forbidden_disclosures.append({
                    "kind": "thread",
                    "title": threads_by_id[identifier]["title"],
                    "question": threads_by_id[identifier][
                        "question"
                    ],
                })

        participant_ids = set(scene_card["participant_ids"])

        return {
            **deepcopy(writer_context),
            "review_only_constraints": {
                "forbidden_disclosures": forbidden_disclosures,
                "non_pov_private_profiles": [
                    record["private_profile"]
                    for record in initial_design["characters"]
                    if (
                        record["character_id"] in participant_ids
                        and record["character_id"]
                        != scene_card["pov_character_id"]
                        and record["private_profile"]
                    )
                ],
                "relationship_private_truths": [
                    record["private_truth"]
                    for record in initial_design["relationships"]
                    if (
                        set(record["participant_ids"]).issubset(
                            participant_ids
                        )
                        and record["private_truth"]
                    )
                ],
            },
        }

    def _previous_scene_excerpt(
        self,
        volume_number: int,
        chapter_number: int,
        scene_number: int,
    ) -> str | None:
        current_key = (
            volume_number,
            chapter_number,
            scene_number,
        )
        candidates: list[tuple[tuple[int, int, int], Path]] = []
        pattern = re.compile(
            r"scene-v(\d{2})-c(\d{3})-s(\d{3})"
        )

        for entry in (self.workspace_root / "scenes").iterdir():
            if not entry.is_dir():
                continue
            match = pattern.fullmatch(entry.name)
            if match is None:
                continue
            key = tuple(int(value) for value in match.groups())
            prose = entry / "prose.md"
            if key < current_key and prose.is_file():
                candidates.append((key, prose))

        if not candidates:
            return None

        _, path = max(candidates, key=lambda item: item[0])
        text = path.read_text(encoding="utf-8").strip()
        return text[-4000:] if text else None

    @staticmethod
    def _validate_prose_text(value: object) -> None:
        """Scene本文の決定的な最低形式契約を検証する。"""
        if not isinstance(value, str):
            raise ContractError(
                "Scene本文は文字列でなければなりません"
            )

        text = value.strip()
        if not text:
            raise ContractError("Scene本文が空です")
        if "\x00" in text:
            raise ContractError("Scene本文にNULを含められません")
        if not re.search(
            r"[\u3040-\u30ff\u3400-\u9fff]",
            text,
        ):
            raise ContractError(
                "Scene本文には日本語の散文が必要です"
            )
        if "```" in text:
            raise ContractError(
                "Scene本文にMarkdown code fenceを含められません"
            )
        if re.match(r"^---(?:\r?\n|$)", text):
            raise ContractError(
                "Scene本文にfront matterを含められません"
            )
        if re.search(
            r"(?m)^\s*(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)",
            text,
        ):
            raise ContractError(
                "Scene本文に見出しまたは箇条書きを"
                "含められません"
            )
        if re.search(
            r"(?im)^\s*(?:review|批評|修正内容|執筆指示|"
            r"metadata|メタデータ)\s*[:：]",
            text,
        ):
            raise ContractError(
                "Scene本文にReviewまたは実装説明を"
                "含められません"
            )
        if re.search(
            r"\b(?:char|rel|loc|know|thread|rule|scene|gen|"
            r"candidate|review|revision)-[A-Za-z0-9_-]+\b",
            text,
        ):
            raise ContractError(
                "Scene本文に内部識別子を含められません"
            )

        if text[0] in '{["':
            try:
                json.loads(text)
            except json.JSONDecodeError:
                pass
            else:
                raise ContractError(
                    "Scene本文をJSONとして返せません"
                )

    @classmethod
    def _adopt(
        cls,
        prose: str,
        staging_root: Path,
    ) -> None:
        """Review済み本文をactive Scene stagingへ保存する。"""
        cls._validate_prose_text(prose)
        staging_root.mkdir(parents=True, exist_ok=True)
        path = staging_root / "prose.md"
        normalized = prose.strip() + "\n"

        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing != normalized:
                raise ContractError(
                    "採用済みScene本文を上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".prose-",
            suffix=".md.tmp",
            dir=staging_root,
        )
        temporary = Path(temporary_name)

        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(normalized)
                handle.flush()
                os.fsync(handle.fileno())

            written = temporary.read_text(encoding="utf-8")
            cls._validate_prose_text(written)
            os.replace(temporary, path)
            fsync_directory(staging_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
