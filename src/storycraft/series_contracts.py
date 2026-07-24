"""シリーズ工程の契約型と決定的検証。"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Protocol

from jsonschema import Draft202012Validator

from .prompt_template import get_template_loader


class ContractError(ValueError):
    """利用者入力または生成結果が製品契約を満たさない。"""


class LLMCallError(ContractError):
    """設定済みretry後もLLM呼び出しまたはJSON parseに成功しなかった。"""


class StoryModel(Protocol):
    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]: ...

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...

    def revision(self, stage: str, candidate: dict[str, Any], critique: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...


class ProseStoryModel(Protocol):
    """Scene本文用のraw text生成・JSON Review interface。"""

    def generate_prose(
        self,
        stage: str,
        context: dict[str, Any],
    ) -> str: ...

    def critique_prose(
        self,
        stage: str,
        candidate: str,
        context: dict[str, Any],
    ) -> dict[str, Any]: ...

    def revision_prose(
        self,
        stage: str,
        candidate: str,
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> str: ...


@dataclass(frozen=True)
class RunResult:
    completed: bool
    volume_count: int
    volume_paths: list[Path]
    series_path: Path
    closure: dict[str, Any]


class ContractValidator:
    """モデル入出力と状態の決定的な製品契約を検証する。"""

    @staticmethod
    def _validate_revision_preserves_contract(stage: str, candidate: dict[str, Any], revised: dict[str, Any]) -> None:
        critical = {
            "scene_card": ("scene_id", "required_events", "thread_actions", "character_ids", "visible_ids", "allowed_update_ids"),
            "continuity": ("state_updates",),
            "volume_chapters": ("chapters",),
            "closure": ("resolved_ids",),
        }
        for field in critical.get(stage, ()):
            if field in candidate and revised.get(field) != candidate[field]:
                raise ContractError(f"修正版が契約上重要な {field} を変更または欠落しました")

    @staticmethod
    def _validate_brief(brief: dict[str, Any]) -> None:
        """Briefをproduction JSON Schemaで構造検証する。"""
        if not isinstance(brief, dict):
            raise ContractError(
                "BriefはJSON objectでなければなりません"
            )

        schema = get_template_loader().load_schema_object(
            "generate",
            "brief",
        )
        validator = Draft202012Validator(schema)

        errors = sorted(
            validator.iter_errors(brief),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )

        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                f"Brief契約違反: {target}: {error.message}"
            )

    @staticmethod
    def _validate_initial_concept(
        concept: dict[str, Any],
        brief: dict[str, Any] | None = None,
    ) -> None:
        """Initial Conceptをproduction JSON Schemaで検証する。"""
        if not isinstance(concept, dict):
            raise ContractError(
                "Initial ConceptはJSON objectでなければなりません"
            )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_concept",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(concept),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Concept契約違反: "
                f"{target}: {error.message}"
            )

        if brief is None:
            return

        ContractValidator._validate_brief(brief)

        serialized = json.dumps(
            concept,
            ensure_ascii=False,
            sort_keys=True,
        )
        violated = [
            item
            for item in brief["avoid"]
            if item and item in serialized
        ]
        if violated:
            raise ContractError(
                "Initial ConceptがBriefのavoidを含みます: "
                + ", ".join(violated)
            )

    @staticmethod
    def _validate_initial_characters(
        value: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Initial Characters Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial CharactersはJSON objectでなければなりません"
            )

        ContractValidator._validate_brief(brief)
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )

        candidate = deepcopy(value)
        records = candidate.get("characters")
        if not isinstance(records, list):
            raise ContractError(
                "Initial Characters.charactersは配列でなければなりません"
            )

        identifiers: list[str] = []
        for record in records:
            if not isinstance(record, dict):
                raise ContractError(
                    "Character recordはobjectでなければなりません"
                )

            if adopted:
                identifier = record.get("character_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("char-")
                ):
                    raise ContractError(
                        "採用済みCharacterにはcharacter_idが必要です"
                    )
                identifiers.append(identifier)
                record.pop("character_id")
            elif "character_id" in record:
                raise ContractError(
                    "Character Candidateへcharacter_idを含められません"
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_characters",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Characters契約違反: "
                f"{target}: {error.message}"
            )

        if adopted and len(identifiers) != len(set(identifiers)):
            raise ContractError(
                "採用済みCharacterのcharacter_idが重複しています"
            )

        names = [
            record["name"]
            for record in candidate["characters"]
        ]
        if len(names) != len(set(names)):
            raise ContractError(
                "Characterのnameが重複しています"
            )

        protagonist_count = sum(
            record["role"] == "protagonist"
            for record in candidate["characters"]
        )
        if protagonist_count < 1:
            raise ContractError(
                "Initial Charactersにはprotagonistが必要です"
            )

        serialized = json.dumps(
            candidate,
            ensure_ascii=False,
            sort_keys=True,
        )
        violated = [
            item
            for item in brief["avoid"]
            if item and item in serialized
        ]
        if violated:
            raise ContractError(
                "Initial CharactersがBriefのavoidを含みます: "
                + ", ".join(violated)
            )

    @staticmethod
    def _validate_initial_relationships(
        value: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Relationship Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial RelationshipsはJSON objectでなければなりません"
            )

        character_records = characters.get("characters")
        if not isinstance(character_records, list):
            raise ContractError(
                "採用済みCharactersが不正です"
            )

        character_ids = {
            record.get("character_id")
            for record in character_records
            if isinstance(record, dict)
        }
        if (
            not character_ids
            or None in character_ids
            or len(character_ids) != len(character_records)
        ):
            raise ContractError(
                "採用済みCharactersのIDが不正です"
            )

        if not isinstance(concept, dict):
            raise ContractError(
                "採用済みConceptが不正です"
            )
        ContractValidator._validate_initial_concept(concept)

        candidate = deepcopy(value)
        records = candidate.get("relationships")
        if not isinstance(records, list):
            raise ContractError(
                "Initial Relationships.relationshipsは"
                "配列でなければなりません"
            )

        identifiers: list[str] = []
        for record in records:
            if not isinstance(record, dict):
                raise ContractError(
                    "Relationship recordはobjectでなければなりません"
                )

            if adopted:
                identifier = record.get("relationship_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("rel-")
                ):
                    raise ContractError(
                        "採用済みRelationshipには"
                        "relationship_idが必要です"
                    )
                identifiers.append(identifier)
                record.pop("relationship_id")
            elif "relationship_id" in record:
                raise ContractError(
                    "Relationship Candidateへ"
                    "relationship_idを含められません"
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_relationships",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Relationships契約違反: "
                f"{target}: {error.message}"
            )

        if adopted and len(identifiers) != len(set(identifiers)):
            raise ContractError(
                "採用済みRelationshipのIDが重複しています"
            )

        seen: set[tuple[tuple[str, ...], str]] = set()
        for record in candidate["relationships"]:
            participants = record["participant_ids"]
            unknown = set(participants) - character_ids
            if unknown:
                raise ContractError(
                    "Relationshipが未知のCharacterを参照しています: "
                    + ", ".join(sorted(unknown))
                )

            key = (
                tuple(sorted(participants)),
                record["relationship_type"],
            )
            if key in seen:
                raise ContractError(
                    "同じ参加人物と種別のRelationshipが重複しています"
                )
            seen.add(key)

    @staticmethod
    def _validate_initial_world_prerequisites(
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
    ) -> None:
        """Initial Worldの採用済み入力を検証する。"""
        ContractValidator._validate_brief(brief)
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )
        ContractValidator._validate_initial_characters(
            characters,
            brief,
            concept,
            adopted=True,
        )
        ContractValidator._validate_initial_relationships(
            relationships,
            concept,
            characters,
            adopted=True,
        )

    @staticmethod
    def _validate_initial_world(
        value: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        *,
        adopted: bool = False,
    ) -> None:
        """V1 World Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial WorldはJSON objectでなければなりません"
            )

        ContractValidator._validate_initial_world_prerequisites(
            brief,
            concept,
            characters,
            relationships,
        )

        candidate = deepcopy(value)
        locations = candidate.get("locations")
        rules = candidate.get("world_rules")
        if not isinstance(locations, list):
            raise ContractError(
                "Initial World.locationsは配列でなければなりません"
            )
        if not isinstance(rules, list):
            raise ContractError(
                "Initial World.world_rulesは配列でなければなりません"
            )

        location_ids: list[str] = []
        rule_ids: list[str] = []

        if adopted:
            id_to_index: dict[str, int] = {}
            for index, location in enumerate(locations):
                if not isinstance(location, dict):
                    raise ContractError(
                        "Location recordはobjectでなければなりません"
                    )
                if "parent_location_index" in location:
                    raise ContractError(
                        "採用済みLocationへ"
                        "parent_location_indexを含められません"
                    )
                if "parent_location_id" not in location:
                    raise ContractError(
                        "採用済みLocationには"
                        "parent_location_idが必要です"
                    )
                identifier = location.get("location_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("loc-")
                ):
                    raise ContractError(
                        "採用済みLocationにはlocation_idが必要です"
                    )
                location_ids.append(identifier)
                id_to_index[identifier] = index

            if len(id_to_index) != len(locations):
                raise ContractError(
                    "採用済みLocationのIDが重複しています"
                )

            for location in locations:
                parent_id = location.pop(
                    "parent_location_id",
                    None,
                )
                location.pop("location_id")
                if parent_id is None:
                    location["parent_location_index"] = None
                elif parent_id in id_to_index:
                    location["parent_location_index"] = (
                        id_to_index[parent_id]
                    )
                else:
                    raise ContractError(
                        "Locationが未知の親Locationを参照しています"
                    )

            for rule in rules:
                if not isinstance(rule, dict):
                    raise ContractError(
                        "World Rule recordはobjectでなければなりません"
                    )
                identifier = rule.get("rule_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("rule-")
                ):
                    raise ContractError(
                        "採用済みWorld Ruleにはrule_idが必要です"
                    )
                rule_ids.append(identifier)
                rule.pop("rule_id")
        else:
            for location in locations:
                if not isinstance(location, dict):
                    raise ContractError(
                        "Location recordはobjectでなければなりません"
                    )
                if (
                    "location_id" in location
                    or "parent_location_id" in location
                ):
                    raise ContractError(
                        "World CandidateへLocation IDを含められません"
                    )
            for rule in rules:
                if not isinstance(rule, dict):
                    raise ContractError(
                        "World Rule recordはobjectでなければなりません"
                    )
                if "rule_id" in rule:
                    raise ContractError(
                        "World Candidateへrule_idを含められません"
                    )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_world",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial World契約違反: "
                f"{target}: {error.message}"
            )

        if len(rule_ids) != len(set(rule_ids)):
            raise ContractError(
                "採用済みWorld RuleのIDが重複しています"
            )

        location_names = [
            location["name"]
            for location in candidate["locations"]
        ]
        if len(location_names) != len(set(location_names)):
            raise ContractError(
                "Locationのnameが重複しています"
            )

        rule_names = [
            rule["name"]
            for rule in candidate["world_rules"]
        ]
        if len(rule_names) != len(set(rule_names)):
            raise ContractError(
                "World Ruleのnameが重複しています"
            )

        roots = 0
        for index, location in enumerate(
            candidate["locations"]
        ):
            parent_index = location["parent_location_index"]
            if parent_index is None:
                roots += 1
                continue
            if (
                isinstance(parent_index, bool)
                or not isinstance(parent_index, int)
                or parent_index < 0
                or parent_index >= index
            ):
                raise ContractError(
                    "parent_location_indexは"
                    "先行する親Locationを参照しなければなりません"
                )

        if roots < 1:
            raise ContractError(
                "Location階層には最上位Locationが必要です"
            )

        serialized = json.dumps(
            candidate,
            ensure_ascii=False,
            sort_keys=True,
        )
        violated = [
            item
            for item in brief["avoid"]
            if item and item in serialized
        ]
        if violated:
            raise ContractError(
                "Initial WorldがBriefのavoidを含みます: "
                + ", ".join(violated)
            )

    @staticmethod
    def _validate_initial_knowledge_prerequisites(
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
    ) -> None:
        """Initial Knowledgeの採用済み入力を検証する。"""
        ContractValidator._validate_initial_world_prerequisites(
            brief,
            concept,
            characters,
            relationships,
        )
        ContractValidator._validate_initial_world(
            world,
            brief,
            concept,
            characters,
            relationships,
            adopted=True,
        )

    @staticmethod
    def _validate_initial_knowledge(
        value: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Knowledge Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial KnowledgeはJSON objectでなければなりません"
            )

        ContractValidator._validate_initial_knowledge_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
        )

        candidate = deepcopy(value)
        facts = candidate.get("knowledge_facts")
        states = candidate.get("character_knowledge")
        if not isinstance(facts, list):
            raise ContractError(
                "knowledge_factsは配列でなければなりません"
            )
        if not isinstance(states, list):
            raise ContractError(
                "character_knowledgeは配列でなければなりません"
            )

        knowledge_ids: list[str] = []
        if adopted:
            id_to_index: dict[str, int] = {}

            for index, fact in enumerate(facts):
                if not isinstance(fact, dict):
                    raise ContractError(
                        "Knowledge Fact recordはobjectでなければなりません"
                    )

                identifier = fact.get("knowledge_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("know-")
                ):
                    raise ContractError(
                        "採用済みKnowledge Factには"
                        "knowledge_idが必要です"
                    )

                knowledge_ids.append(identifier)
                id_to_index[identifier] = index
                fact.pop("knowledge_id")

            if len(id_to_index) != len(facts):
                raise ContractError(
                    "採用済みKnowledge IDが重複しています"
                )

            for state in states:
                if not isinstance(state, dict):
                    raise ContractError(
                        "Character Knowledge recordは"
                        "objectでなければなりません"
                    )
                if "knowledge_index" in state:
                    raise ContractError(
                        "採用済みCharacter Knowledgeへ"
                        "knowledge_indexを含められません"
                    )

                identifier = state.pop("knowledge_id", None)
                if identifier not in id_to_index:
                    raise ContractError(
                        "Character Knowledgeが未知の"
                        "Knowledgeを参照しています"
                    )
                state["knowledge_index"] = id_to_index[identifier]
        else:
            for fact in facts:
                if not isinstance(fact, dict):
                    raise ContractError(
                        "Knowledge Fact recordはobjectでなければなりません"
                    )
                if "knowledge_id" in fact:
                    raise ContractError(
                        "Knowledge Candidateへ"
                        "knowledge_idを含められません"
                    )

            for state in states:
                if not isinstance(state, dict):
                    raise ContractError(
                        "Character Knowledge recordは"
                        "objectでなければなりません"
                    )
                if "knowledge_id" in state:
                    raise ContractError(
                        "Knowledge Candidateへ"
                        "knowledge_idを含められません"
                    )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_knowledge",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Knowledge契約違反: "
                f"{target}: {error.message}"
            )

        statements = [
            fact["statement"]
            for fact in candidate["knowledge_facts"]
        ]
        if len(statements) != len(set(statements)):
            raise ContractError(
                "Knowledge Factのstatementが重複しています"
            )

        character_ids = [
            record["character_id"]
            for record in characters["characters"]
        ]
        known_character_ids = set(character_ids)
        fact_count = len(candidate["knowledge_facts"])
        seen_pairs: set[tuple[str, int]] = set()

        for record in candidate["character_knowledge"]:
            character_id = record["character_id"]
            knowledge_index = record["knowledge_index"]

            if character_id not in known_character_ids:
                raise ContractError(
                    "Character Knowledgeが未知の人物を参照しています"
                )
            if (
                isinstance(knowledge_index, bool)
                or knowledge_index < 0
                or knowledge_index >= fact_count
            ):
                raise ContractError(
                    "Character Knowledgeの"
                    "knowledge_indexが範囲外です"
                )

            pair = (character_id, knowledge_index)
            if pair in seen_pairs:
                raise ContractError(
                    "Character Knowledgeの組合せが重複しています"
                )
            seen_pairs.add(pair)

            fact = candidate["knowledge_facts"][
                knowledge_index
            ]
            if (
                record["state"] == "knows"
                and fact["truth_status"] != "true"
            ):
                raise ContractError(
                    "真実でないKnowledge Factを"
                    "knowsとして設定できません"
                )

        expected_pairs = {
            (character_id, knowledge_index)
            for character_id in character_ids
            for knowledge_index in range(fact_count)
        }
        if seen_pairs != expected_pairs:
            raise ContractError(
                "全Characterと全Knowledge Factの"
                "状態を明示しなければなりません"
            )

        for index, fact in enumerate(
            candidate["knowledge_facts"]
        ):
            if fact["truth_status"] != "belief_only":
                continue

            relevant_states = [
                record["state"]
                for record in candidate["character_knowledge"]
                if record["knowledge_index"] == index
            ]
            if all(
                state == "unknown"
                for state in relevant_states
            ):
                raise ContractError(
                    "belief_onlyのFactには"
                    "人物の認識状態が必要です"
                )

        if adopted and len(knowledge_ids) != len(
            set(knowledge_ids)
        ):
            raise ContractError(
                "採用済みKnowledge IDが重複しています"
            )

    @staticmethod
    def _validate_initial_threads_prerequisites(
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
        knowledge: dict[str, Any],
    ) -> None:
        """Initial Threadsの採用済み入力を検証する。"""
        ContractValidator._validate_initial_knowledge_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
        )
        ContractValidator._validate_initial_knowledge(
            knowledge,
            brief,
            concept,
            characters,
            relationships,
            world,
            adopted=True,
        )

    @staticmethod
    def _validate_initial_threads(
        value: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
        knowledge: dict[str, Any],
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Thread Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial ThreadsはJSON objectでなければなりません"
            )

        ContractValidator._validate_initial_threads_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
        )

        candidate = deepcopy(value)
        records = candidate.get("threads")
        if not isinstance(records, list):
            raise ContractError(
                "Initial Threads.threadsは"
                "配列でなければなりません"
            )

        identifiers: list[str] = []
        for record in records:
            if not isinstance(record, dict):
                raise ContractError(
                    "Thread recordはobjectでなければなりません"
                )

            if adopted:
                identifier = record.get("thread_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("thread-")
                ):
                    raise ContractError(
                        "採用済みThreadにはthread_idが必要です"
                    )
                identifiers.append(identifier)
                record.pop("thread_id")
            elif "thread_id" in record:
                raise ContractError(
                    "Thread Candidateへ"
                    "thread_idを含められません"
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_threads",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Threads契約違反: "
                f"{target}: {error.message}"
            )

        if adopted and len(identifiers) != len(
            set(identifiers)
        ):
            raise ContractError(
                "採用済みThreadのIDが重複しています"
            )

        titles = [record["title"] for record in records]
        if len(titles) != len(set(titles)):
            raise ContractError(
                "Threadのtitleが重複しています"
            )

        questions = [record["question"] for record in records]
        if len(questions) != len(set(questions)):
            raise ContractError(
                "Threadのquestionが重複しています"
            )

        major_count = 0
        required_count = 0

        for record in records:
            if record["required_for_completion"]:
                required_count += 1

            if record["importance"] == "major":
                major_count += 1
                if not record["required_for_completion"]:
                    raise ContractError(
                        "major Threadは"
                        "完結必須でなければなりません"
                    )
                if record["initial_status"] != "open":
                    raise ContractError(
                        "major Threadはopenから"
                        "開始しなければなりません"
                    )

            if (
                record["initial_status"] == "planned"
                and record["reader_visibility"] != "hidden"
            ):
                raise ContractError(
                    "planned Threadは"
                    "reader_visibleにできません"
                )

        if major_count == 0:
            raise ContractError(
                "Initial Threadsにはmajorが必要です"
            )
        if required_count == 0:
            raise ContractError(
                "Initial Threadsには"
                "完結必須Threadが必要です"
            )

    @staticmethod
    def _validate_initial_ending_prerequisites(
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        threads: dict[str, Any],
    ) -> None:
        """Initial Endingの採用済み入力を検証する。"""
        ContractValidator._validate_brief(brief)
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )
        ContractValidator._validate_initial_characters(
            characters,
            brief,
            concept,
            adopted=True,
        )
        ContractValidator._validate_initial_relationships(
            relationships,
            concept,
            characters,
            adopted=True,
        )

        version_root_placeholder_world = {
            "world": {
                "setting_summary": "Ending前提検証用の世界。",
                "historical_background": "Ending前提検証用の歴史。",
                "social_structure": "Ending前提検証用の社会。",
                "technology_or_magic": "Ending前提検証用の技術。",
                "cultural_norms": [
                    "Ending前提検証用の文化。",
                ],
                "major_conflicts": [
                    "Ending前提検証用の対立。",
                ],
                "public_knowledge": [],
                "private_truths": [],
            },
            "locations": [{
                "location_id": "loc-ending-validation",
                "name": "Ending前提検証用",
                "parent_location_id": None,
                "description": "Ending前提検証用の場所。",
                "access_constraints": [],
                "public_facts": [],
                "private_facts": [],
            }],
            "world_rules": [{
                "rule_id": "rule-ending-validation",
                "name": "Ending前提検証用",
                "description": "Ending前提検証用の規則。",
                "scope": "series",
                "exceptions": [],
                "reader_visibility": "hidden",
                "change_policy": "immutable",
            }],
        }
        version_root_placeholder_knowledge = {
            "knowledge_facts": [{
                "knowledge_id": "know-ending-validation",
                "statement": "Ending前提検証用",
                "truth_status": "true",
                "reader_visibility": "hidden",
                "source_type": "validation",
                "private_notes": None,
            }],
            "character_knowledge": [
                {
                    "character_id": character["character_id"],
                    "knowledge_id": "know-ending-validation",
                    "state": "unknown",
                }
                for character in characters["characters"]
            ],
        }
        ContractValidator._validate_initial_threads(
            threads,
            brief,
            concept,
            characters,
            relationships,
            version_root_placeholder_world,
            version_root_placeholder_knowledge,
            adopted=True,
        )

    @staticmethod
    def _validate_initial_ending(
        value: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        threads: dict[str, Any],
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Ending Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial EndingはJSON objectでなければなりません"
            )

        ContractValidator._validate_initial_ending_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            threads,
        )

        candidate = deepcopy(value)
        ending = candidate.get("ending")
        arcs = candidate.get("long_term_arcs")

        if not isinstance(ending, dict):
            raise ContractError(
                "Initial Ending.endingはobjectが必要です"
            )
        if not isinstance(arcs, list):
            raise ContractError(
                "Initial Ending.long_term_arcsは配列が必要です"
            )

        ending_identifier: str | None = None
        arc_identifiers: list[str] = []

        if adopted:
            ending_identifier = ending.get("ending_id")
            if (
                not isinstance(ending_identifier, str)
                or not ending_identifier.startswith("ending-")
            ):
                raise ContractError(
                    "採用済みEndingにはending_idが必要です"
                )
            ending.pop("ending_id")
        elif "ending_id" in ending:
            raise ContractError(
                "Ending Candidateへending_idを含められません"
            )

        for arc in arcs:
            if not isinstance(arc, dict):
                raise ContractError(
                    "Long-term Arc recordはobjectが必要です"
                )
            if adopted:
                identifier = arc.get("arc_id")
                if (
                    not isinstance(identifier, str)
                    or not identifier.startswith("arc-")
                ):
                    raise ContractError(
                        "採用済みLong-term Arcには"
                        "arc_idが必要です"
                    )
                arc_identifiers.append(identifier)
                arc.pop("arc_id")
            elif "arc_id" in arc:
                raise ContractError(
                    "Long-term Arc Candidateへ"
                    "arc_idを含められません"
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_ending",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Ending契約違反: "
                f"{target}: {error.message}"
            )

        if adopted and len(arc_identifiers) != len(
            set(arc_identifiers)
        ):
            raise ContractError(
                "採用済みLong-term ArcのIDが重複しています"
            )

        character_ids = {
            record["character_id"]
            for record in characters["characters"]
        }
        principal_character_ids = {
            record["character_id"]
            for record in characters["characters"]
            if record["role"] in {
                "protagonist",
                "co_protagonist",
            }
        }
        relationship_ids = {
            record["relationship_id"]
            for record in relationships["relationships"]
        }
        thread_ids = {
            record["thread_id"]
            for record in threads["threads"]
        }
        required_thread_ids = {
            record["thread_id"]
            for record in threads["threads"]
            if record["required_for_completion"]
        }

        ending_character_ids = set(
            ending["character_end_states"]
        )
        unknown_characters = (
            ending_character_ids - character_ids
        )
        if unknown_characters:
            raise ContractError(
                "character_end_statesが未知の"
                "Characterを参照しています"
            )
        missing_principals = (
            principal_character_ids - ending_character_ids
        )
        if missing_principals:
            raise ContractError(
                "主人公のcharacter_end_statesが不足しています"
            )

        ending_relationship_ids = set(
            ending["relationship_end_states"]
        )
        if ending_relationship_ids - relationship_ids:
            raise ContractError(
                "relationship_end_statesが未知の"
                "Relationshipを参照しています"
            )

        requirement_ids = set(
            ending["thread_requirements"]
        )
        if requirement_ids - thread_ids:
            raise ContractError(
                "thread_requirementsが未知の"
                "Threadを参照しています"
            )
        if requirement_ids != required_thread_ids:
            raise ContractError(
                "thread_requirementsは完結必須Threadを"
                "漏れなく一度ずつ含める必要があります"
            )

        arc_targets: set[tuple[str, str]] = set()
        for arc in arcs:
            target_type = arc["target_type"]
            target_id = arc["target_id"]
            target = (target_type, target_id)

            if target in arc_targets:
                raise ContractError(
                    "同じ対象のLong-term Arcが重複しています"
                )
            arc_targets.add(target)

            valid_ids = {
                "character": character_ids,
                "relationship": relationship_ids,
                "thread": thread_ids,
            }[target_type]
            if target_id not in valid_ids:
                raise ContractError(
                    "Long-term Arcが未知の対象を"
                    "参照しています"
                )

        missing_character_arcs = {
            ("character", identifier)
            for identifier in principal_character_ids
        } - arc_targets
        if missing_character_arcs:
            raise ContractError(
                "主人公のLong-term Arcが不足しています"
            )

        missing_thread_arcs = {
            ("thread", identifier)
            for identifier in required_thread_ids
        } - arc_targets
        if missing_thread_arcs:
            raise ContractError(
                "完結必須ThreadのLong-term Arcが不足しています"
            )

    @staticmethod
    def _validate_initial_integrate_prerequisites(
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
        knowledge: dict[str, Any],
        threads: dict[str, Any],
        ending: dict[str, Any],
    ) -> None:
        """Initial Integrateの採用済み入力を検証する。"""
        ContractValidator._validate_brief(brief)
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )
        ContractValidator._validate_initial_characters(
            characters,
            brief,
            concept,
            adopted=True,
        )
        ContractValidator._validate_initial_relationships(
            relationships,
            concept,
            characters,
            adopted=True,
        )
        ContractValidator._validate_initial_world(
            world,
            brief,
            concept,
            characters,
            relationships,
            adopted=True,
        )
        ContractValidator._validate_initial_knowledge(
            knowledge,
            brief,
            concept,
            characters,
            relationships,
            world,
            adopted=True,
        )
        ContractValidator._validate_initial_threads(
            threads,
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
            adopted=True,
        )
        ContractValidator._validate_initial_ending(
            ending,
            brief,
            concept,
            characters,
            relationships,
            threads,
            adopted=True,
        )

    @staticmethod
    def _validate_initial_integrate(
        value: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
        knowledge: dict[str, Any],
        threads: dict[str, Any],
        ending: dict[str, Any],
    ) -> None:
        """V1統合Initial Design Candidateを検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Initial IntegrateはJSON objectでなければなりません"
            )

        ContractValidator._validate_initial_integrate_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
            threads,
            ending,
        )

        schema = get_template_loader().load_schema_object(
            "generate",
            "initial_integrate",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(value),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Initial Integrate契約違反: "
                f"{target}: {error.message}"
            )

        integrated_concept = value["concept"]
        integrated_characters = {
            "characters": value["characters"],
        }
        integrated_relationships = {
            "relationships": value["relationships"],
        }
        integrated_world = {
            "world": value["world"],
            "locations": value["locations"],
            "world_rules": value["world_rules"],
        }
        integrated_knowledge = {
            "knowledge_facts": value["knowledge_facts"],
            "character_knowledge": value[
                "character_knowledge"
            ],
        }
        integrated_threads = {
            "threads": value["threads"],
        }
        integrated_ending = {
            "ending": value["ending"],
            "long_term_arcs": value["long_term_arcs"],
        }

        ContractValidator._validate_initial_concept(
            integrated_concept,
            brief,
        )
        ContractValidator._validate_initial_characters(
            integrated_characters,
            brief,
            integrated_concept,
            adopted=True,
        )
        ContractValidator._validate_initial_relationships(
            integrated_relationships,
            integrated_concept,
            integrated_characters,
            adopted=True,
        )
        ContractValidator._validate_initial_world(
            integrated_world,
            brief,
            integrated_concept,
            integrated_characters,
            integrated_relationships,
            adopted=True,
        )
        ContractValidator._validate_initial_knowledge(
            integrated_knowledge,
            brief,
            integrated_concept,
            integrated_characters,
            integrated_relationships,
            integrated_world,
            adopted=True,
        )
        ContractValidator._validate_initial_threads(
            integrated_threads,
            brief,
            integrated_concept,
            integrated_characters,
            integrated_relationships,
            integrated_world,
            integrated_knowledge,
            adopted=True,
        )
        ContractValidator._validate_initial_ending(
            integrated_ending,
            brief,
            integrated_concept,
            integrated_characters,
            integrated_relationships,
            integrated_threads,
            adopted=True,
        )

        source_sequences = {
            "characters": tuple(
                record["character_id"]
                for record in characters["characters"]
            ),
            "relationships": tuple(
                record["relationship_id"]
                for record in relationships[
                    "relationships"
                ]
            ),
            "locations": tuple(
                record["location_id"]
                for record in world["locations"]
            ),
            "world_rules": tuple(
                record["rule_id"]
                for record in world["world_rules"]
            ),
            "knowledge_facts": tuple(
                record["knowledge_id"]
                for record in knowledge[
                    "knowledge_facts"
                ]
            ),
            "character_knowledge": tuple(
                (
                    record["character_id"],
                    record["knowledge_id"],
                )
                for record in knowledge[
                    "character_knowledge"
                ]
            ),
            "threads": tuple(
                record["thread_id"]
                for record in threads["threads"]
            ),
            "long_term_arcs": tuple(
                record["arc_id"]
                for record in ending[
                    "long_term_arcs"
                ]
            ),
        }
        integrated_sequences = {
            "characters": tuple(
                record["character_id"]
                for record in value["characters"]
            ),
            "relationships": tuple(
                record["relationship_id"]
                for record in value["relationships"]
            ),
            "locations": tuple(
                record["location_id"]
                for record in value["locations"]
            ),
            "world_rules": tuple(
                record["rule_id"]
                for record in value["world_rules"]
            ),
            "knowledge_facts": tuple(
                record["knowledge_id"]
                for record in value["knowledge_facts"]
            ),
            "character_knowledge": tuple(
                (
                    record["character_id"],
                    record["knowledge_id"],
                )
                for record in value["character_knowledge"]
            ),
            "threads": tuple(
                record["thread_id"]
                for record in value["threads"]
            ),
            "long_term_arcs": tuple(
                record["arc_id"]
                for record in value["long_term_arcs"]
            ),
        }

        for component, source_sequence in (
            source_sequences.items()
        ):
            if integrated_sequences[component] != source_sequence:
                raise ContractError(
                    "Initial Integrateは"
                    f"{component}のID、件数、順序を"
                    "変更できません"
                )

        if (
            value["ending"]["ending_id"]
            != ending["ending"]["ending_id"]
        ):
            raise ContractError(
                "Initial Integrateはending_idを変更できません"
            )

    @staticmethod
    def _validate_series_plan(
        value: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        basis_generation_id: str,
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Series Plan Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Series PlanはJSON objectでなければなりません"
            )

        ContractValidator._validate_brief(brief)

        if (
            not isinstance(basis_generation_id, str)
            or not basis_generation_id.startswith("gen-")
        ):
            raise ContractError(
                "Series Planのbasis_generation_idが不正です"
            )
        if not isinstance(initial_design, dict):
            raise ContractError(
                "採用済みInitial Designが必要です"
            )

        def identifier_set(
            field: str,
            identifier_field: str,
        ) -> set[str]:
            records = initial_design.get(field)
            if not isinstance(records, list):
                raise ContractError(
                    "Initial Designの参照元が不正です: "
                    f"{field}"
                )
            identifiers: list[str] = []
            for record in records:
                if not isinstance(record, dict):
                    raise ContractError(
                        "Initial Designのrecordが不正です: "
                        f"{field}"
                    )
                identifier = record.get(identifier_field)
                if not isinstance(identifier, str):
                    raise ContractError(
                        "Initial DesignのIDが不正です: "
                        f"{identifier_field}"
                    )
                identifiers.append(identifier)
            if len(identifiers) != len(set(identifiers)):
                raise ContractError(
                    "Initial DesignのIDが重複しています: "
                    f"{identifier_field}"
                )
            return set(identifiers)

        character_ids = identifier_set(
            "characters",
            "character_id",
        )
        relationship_ids = identifier_set(
            "relationships",
            "relationship_id",
        )
        thread_ids = identifier_set(
            "threads",
            "thread_id",
        )
        knowledge_ids = identifier_set(
            "knowledge_facts",
            "knowledge_id",
        )

        candidate = deepcopy(value)
        metadata_fields = {
            "schema_version",
            "series_plan_id",
            "version",
            "status",
            "basis_generation_id",
            "parent_plan_id",
            "created_at",
        }

        if adopted:
            if candidate.get("schema_version") != 1:
                raise ContractError(
                    "採用済みSeries Planのschema_versionは"
                    "1でなければなりません"
                )
            if candidate.get("series_plan_id") != (
                "series-plan-0001"
            ):
                raise ContractError(
                    "採用済みSeries PlanのIDが不正です"
                )
            if candidate.get("version") != 1:
                raise ContractError(
                    "採用済みSeries Planのversionは"
                    "1でなければなりません"
                )
            if candidate.get("status") != "accepted":
                raise ContractError(
                    "採用済みSeries Planのstatusは"
                    "acceptedでなければなりません"
                )
            if candidate.get("basis_generation_id") != (
                basis_generation_id
            ):
                raise ContractError(
                    "Series Planのbasis_generation_idが"
                    "現在Generationと一致しません"
                )
            if candidate.get("parent_plan_id") is not None:
                raise ContractError(
                    "最初のSeries Planのparent_plan_idは"
                    "nullでなければなりません"
                )

            created_at = candidate.get("created_at")
            if not isinstance(created_at, str):
                raise ContractError(
                    "採用済みSeries Planにはcreated_atが必要です"
                )
            try:
                parsed = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ContractError(
                    "採用済みSeries Planのcreated_atが不正です"
                ) from exc
            if parsed.tzinfo is None:
                raise ContractError(
                    "採用済みSeries Planのcreated_atには"
                    "timezoneが必要です"
                )

            for field in metadata_fields:
                candidate.pop(field, None)
        else:
            unexpected = metadata_fields & set(candidate)
            if unexpected:
                raise ContractError(
                    "Series Plan Candidateへ採用metadataを"
                    "含められません: "
                    + ", ".join(sorted(unexpected))
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "series_plan",
        )
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Series Plan契約違反: "
                f"{target}: {error.message}"
            )

        volume_count = candidate["volume_count"]
        if volume_count != brief["volume_count"]:
            raise ContractError(
                "Series Planのvolume_countがBriefと一致しません"
            )

        summaries = candidate["volume_summaries"]
        if len(summaries) != volume_count:
            raise ContractError(
                "volume_summariesの件数がvolume_countと"
                "一致しません"
            )
        expected_numbers = list(range(1, volume_count + 1))
        actual_numbers = [
            record["volume_number"]
            for record in summaries
        ]
        if actual_numbers != expected_numbers:
            raise ContractError(
                "Volume番号は1からの連番でなければなりません"
            )

        expected_maps = (
            (
                "character_arc_map",
                character_ids,
            ),
            (
                "relationship_arc_map",
                relationship_ids,
            ),
            (
                "thread_progression",
                thread_ids,
            ),
        )
        for field, expected_ids in expected_maps:
            mapping = candidate[field]
            actual_ids = set(mapping)
            if actual_ids != expected_ids:
                missing = expected_ids - actual_ids
                unknown = actual_ids - expected_ids
                details = []
                if missing:
                    details.append(
                        "missing=" + ",".join(sorted(missing))
                    )
                if unknown:
                    details.append(
                        "unknown=" + ",".join(sorted(unknown))
                    )
                raise ContractError(
                    f"{field}の参照IDがInitial Designと"
                    "一致しません: "
                    + "; ".join(details)
                )

            for identifier, numbers in mapping.items():
                if numbers != sorted(numbers):
                    raise ContractError(
                        f"{field}.{identifier}の巻番号は"
                        "昇順でなければなりません"
                    )
                if any(
                    number < 1 or number > volume_count
                    for number in numbers
                ):
                    raise ContractError(
                        f"{field}.{identifier}に範囲外の"
                        "巻番号があります"
                    )

        scheduled_knowledge: set[str] = set()
        for record in candidate["revelation_schedule"]:
            if record["volume_number"] > volume_count:
                raise ContractError(
                    "revelation_scheduleに範囲外の"
                    "巻番号があります"
                )
            knowledge_id = record["knowledge_id"]
            if knowledge_id not in knowledge_ids:
                raise ContractError(
                    "revelation_scheduleが未知のKnowledgeを"
                    f"参照しています: {knowledge_id}"
                )
            if knowledge_id in scheduled_knowledge:
                raise ContractError(
                    "同じKnowledgeを複数回開示できません: "
                    f"{knowledge_id}"
                )
            scheduled_knowledge.add(knowledge_id)

    @staticmethod
    def _validate_volume_plan(
        value: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_number: int,
        basis_generation_id: str,
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Volume Plan Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Volume PlanはJSON objectでなければなりません"
            )

        ContractValidator._validate_brief(brief)

        if not isinstance(initial_design, dict):
            raise ContractError(
                "採用済みInitial Designが必要です"
            )
        if not isinstance(series_plan, dict):
            raise ContractError(
                "採用済みSeries Planが必要です"
            )
        if (
            not isinstance(volume_number, int)
            or isinstance(volume_number, bool)
            or volume_number < 1
        ):
            raise ContractError(
                "Volume Planの対象巻番号が不正です"
            )
        if (
            not isinstance(basis_generation_id, str)
            or not basis_generation_id.startswith("gen-")
        ):
            raise ContractError(
                "Volume Planのbasis_generation_idが不正です"
            )

        series_basis = series_plan.get(
            "basis_generation_id"
        )
        if (
            not isinstance(series_basis, str)
            or not series_basis.startswith("gen-")
        ):
            raise ContractError(
                "Series Planのbasis_generation_idが不正です"
            )

        ContractValidator._validate_series_plan(
            series_plan,
            brief,
            initial_design,
            series_basis,
            adopted=True,
        )

        volume_count = series_plan["volume_count"]
        if volume_number > volume_count:
            raise ContractError(
                "Volume Planの対象巻がSeries Planの範囲外です"
            )

        summary = series_plan["volume_summaries"][
            volume_number - 1
        ]
        if summary["volume_number"] != volume_number:
            raise ContractError(
                "Series Planの対象巻summaryが不正です"
            )

        def allocated_ids(field: str) -> set[str]:
            mapping = series_plan[field]
            return {
                identifier
                for identifier, numbers in mapping.items()
                if volume_number in numbers
            }

        expected_character_ids = allocated_ids(
            "character_arc_map"
        )
        expected_relationship_ids = allocated_ids(
            "relationship_arc_map"
        )
        expected_thread_ids = allocated_ids(
            "thread_progression"
        )

        expected_revelation_count = sum(
            1
            for record in series_plan["revelation_schedule"]
            if record["volume_number"] == volume_number
        )

        candidate = deepcopy(value)
        metadata_fields = {
            "schema_version",
            "volume_plan_id",
            "volume_number",
            "version",
            "status",
            "basis_generation_id",
            "series_plan_id",
            "parent_plan_id",
            "created_at",
        }

        if adopted:
            expected_plan_id = (
                f"volume-plan-v{volume_number:02d}"
            )
            if candidate.get("schema_version") != 1:
                raise ContractError(
                    "採用済みVolume Planのschema_versionは"
                    "1でなければなりません"
                )
            if (
                candidate.get("volume_plan_id")
                != expected_plan_id
            ):
                raise ContractError(
                    "採用済みVolume PlanのIDが不正です"
                )
            if candidate.get("volume_number") != volume_number:
                raise ContractError(
                    "採用済みVolume Planの巻番号が不正です"
                )
            if candidate.get("version") != 1:
                raise ContractError(
                    "採用済みVolume Planのversionは"
                    "1でなければなりません"
                )
            if candidate.get("status") != "accepted":
                raise ContractError(
                    "採用済みVolume Planのstatusは"
                    "acceptedでなければなりません"
                )
            if (
                candidate.get("basis_generation_id")
                != basis_generation_id
            ):
                raise ContractError(
                    "Volume Planのbasis_generation_idが"
                    "現在Generationと一致しません"
                )
            if (
                candidate.get("series_plan_id")
                != series_plan["series_plan_id"]
            ):
                raise ContractError(
                    "Volume Planのseries_plan_idが不正です"
                )
            if candidate.get("parent_plan_id") is not None:
                raise ContractError(
                    "最初のVolume Planのparent_plan_idは"
                    "nullでなければなりません"
                )

            created_at = candidate.get("created_at")
            if not isinstance(created_at, str):
                raise ContractError(
                    "採用済みVolume Planにはcreated_atが必要です"
                )
            try:
                parsed = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ContractError(
                    "採用済みVolume Planのcreated_atが不正です"
                ) from exc
            if parsed.tzinfo is None:
                raise ContractError(
                    "採用済みVolume Planのcreated_atには"
                    "timezoneが必要です"
                )

            for field in metadata_fields:
                candidate.pop(field, None)
        else:
            unexpected = metadata_fields & set(candidate)
            if unexpected:
                raise ContractError(
                    "Volume Plan Candidateへ採用metadataを"
                    "含められません: "
                    + ", ".join(sorted(unexpected))
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "volume_plan",
        )
        errors = sorted(
            Draft202012Validator(schema).iter_errors(
                candidate
            ),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Volume Plan契約違反: "
                f"{target}: {error.message}"
            )

        expected_maps = (
            (
                "character_changes",
                expected_character_ids,
            ),
            (
                "relationship_changes",
                expected_relationship_ids,
            ),
            (
                "thread_goals",
                expected_thread_ids,
            ),
        )
        for field, expected_ids in expected_maps:
            actual_ids = set(candidate[field])
            if actual_ids != expected_ids:
                missing = expected_ids - actual_ids
                unknown = actual_ids - expected_ids
                details = []
                if missing:
                    details.append(
                        "missing=" + ",".join(sorted(missing))
                    )
                if unknown:
                    details.append(
                        "unknown=" + ",".join(sorted(unknown))
                    )
                raise ContractError(
                    f"{field}の参照IDが対象巻の割当と"
                    "一致しません: "
                    + "; ".join(details)
                )

        if (
            len(candidate["revelations"])
            != expected_revelation_count
        ):
            raise ContractError(
                "revelationsの件数が対象巻の"
                "Knowledge開示予定と一致しません"
            )

        chapters = candidate["chapter_summaries"]
        actual_numbers = [
            record["chapter_number"]
            for record in chapters
        ]
        expected_numbers = list(
            range(1, len(chapters) + 1)
        )
        if actual_numbers != expected_numbers:
            raise ContractError(
                "Chapter番号は1からの連番でなければなりません"
            )

        chapter_counts = brief.get(
            "chapters_per_volume"
        )
        if chapter_counts is not None:
            expected_count = chapter_counts[
                volume_number - 1
            ]
            if len(chapters) != expected_count:
                raise ContractError(
                    "chapter_summariesの件数がBriefと"
                    "一致しません"
                )

        if (
            volume_number < volume_count
            and not candidate["handoff_expectations"]
        ):
            raise ContractError(
                "最終巻以外にはhandoff_expectationsが必要です"
            )

    @staticmethod
    def _validate_chapter_plan(
        value: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        basis_generation_id: str,
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Chapter Plan Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Chapter PlanはJSON objectでなければなりません"
            )

        ContractValidator._validate_brief(brief)

        if not isinstance(initial_design, dict):
            raise ContractError(
                "採用済みInitial Designが必要です"
            )
        if not isinstance(series_plan, dict):
            raise ContractError(
                "採用済みSeries Planが必要です"
            )
        if not isinstance(volume_plan, dict):
            raise ContractError(
                "採用済みVolume Planが必要です"
            )

        for number, label in (
            (volume_number, "巻番号"),
            (chapter_number, "章番号"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"Chapter Planの対象{label}が不正です"
                )

        if (
            not isinstance(basis_generation_id, str)
            or not basis_generation_id.startswith("gen-")
        ):
            raise ContractError(
                "Chapter Planのbasis_generation_idが不正です"
            )

        series_basis = series_plan.get(
            "basis_generation_id"
        )
        if (
            not isinstance(series_basis, str)
            or not series_basis.startswith("gen-")
        ):
            raise ContractError(
                "Series Planのbasis_generation_idが不正です"
            )
        ContractValidator._validate_series_plan(
            series_plan,
            brief,
            initial_design,
            series_basis,
            adopted=True,
        )

        volume_basis = volume_plan.get(
            "basis_generation_id"
        )
        parent_volume_number = volume_plan.get(
            "volume_number"
        )
        if (
            not isinstance(volume_basis, str)
            or not volume_basis.startswith("gen-")
        ):
            raise ContractError(
                "Volume Planのbasis_generation_idが不正です"
            )
        if (
            not isinstance(parent_volume_number, int)
            or isinstance(parent_volume_number, bool)
            or parent_volume_number < 1
        ):
            raise ContractError(
                "Volume Planのvolume_numberが不正です"
            )

        ContractValidator._validate_volume_plan(
            volume_plan,
            brief,
            initial_design,
            series_plan,
            parent_volume_number,
            volume_basis,
            adopted=True,
        )

        if parent_volume_number != volume_number:
            raise ContractError(
                "Chapter Planの対象巻がVolume Planと"
                "一致しません"
            )

        summary = next(
            (
                record
                for record in volume_plan["chapter_summaries"]
                if record["chapter_number"] == chapter_number
            ),
            None,
        )
        if summary is None:
            raise ContractError(
                "Chapter Planの対象章がVolume Planに"
                "存在しません"
            )

        candidate = deepcopy(value)
        metadata_fields = {
            "schema_version",
            "chapter_plan_id",
            "volume_number",
            "chapter_number",
            "version",
            "status",
            "basis_generation_id",
            "volume_plan_id",
            "parent_plan_id",
            "created_at",
        }

        if adopted:
            expected_plan_id = (
                f"chapter-plan-v{volume_number:02d}"
                f"-c{chapter_number:03d}"
            )
            if candidate.get("schema_version") != 1:
                raise ContractError(
                    "採用済みChapter Planのschema_versionは"
                    "1でなければなりません"
                )
            if (
                candidate.get("chapter_plan_id")
                != expected_plan_id
            ):
                raise ContractError(
                    "採用済みChapter PlanのIDが不正です"
                )
            if candidate.get("volume_number") != volume_number:
                raise ContractError(
                    "採用済みChapter Planの巻番号が不正です"
                )
            if candidate.get("chapter_number") != chapter_number:
                raise ContractError(
                    "採用済みChapter Planの章番号が不正です"
                )
            if candidate.get("version") != 1:
                raise ContractError(
                    "採用済みChapter Planのversionは"
                    "1でなければなりません"
                )
            if candidate.get("status") != "accepted":
                raise ContractError(
                    "採用済みChapter Planのstatusは"
                    "acceptedでなければなりません"
                )
            if (
                candidate.get("basis_generation_id")
                != basis_generation_id
            ):
                raise ContractError(
                    "Chapter Planのbasis_generation_idが"
                    "現在Generationと一致しません"
                )
            if (
                candidate.get("volume_plan_id")
                != volume_plan["volume_plan_id"]
            ):
                raise ContractError(
                    "Chapter Planのvolume_plan_idが不正です"
                )
            if candidate.get("parent_plan_id") is not None:
                raise ContractError(
                    "最初のChapter Planのparent_plan_idは"
                    "nullでなければなりません"
                )

            created_at = candidate.get("created_at")
            if not isinstance(created_at, str):
                raise ContractError(
                    "採用済みChapter Planにはcreated_atが必要です"
                )
            try:
                parsed = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ContractError(
                    "採用済みChapter Planのcreated_atが不正です"
                ) from exc
            if parsed.tzinfo is None:
                raise ContractError(
                    "採用済みChapter Planのcreated_atには"
                    "timezoneが必要です"
                )

            for field in metadata_fields:
                candidate.pop(field, None)
        else:
            unexpected = metadata_fields & set(candidate)
            if unexpected:
                raise ContractError(
                    "Chapter Plan Candidateへ採用metadataを"
                    "含められません: "
                    + ", ".join(sorted(unexpected))
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "chapter_plan",
        )
        errors = sorted(
            Draft202012Validator(schema).iter_errors(
                candidate
            ),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Chapter Plan契約違反: "
                f"{target}: {error.message}"
            )

        scenes = candidate["scene_summaries"]
        actual_numbers = [
            record["scene_number"]
            for record in scenes
        ]
        expected_numbers = list(
            range(1, len(scenes) + 1)
        )
        if actual_numbers != expected_numbers:
            raise ContractError(
                "Scene番号は1からの連番でなければなりません"
            )

        revelation_count = len(
            candidate["required_revelations"]
        )
        parent_revelation_count = len(
            volume_plan["revelations"]
        )
        if revelation_count > parent_revelation_count:
            raise ContractError(
                "required_revelationsの件数が"
                "Volume Planの開示予定を超えています"
            )

    @staticmethod
    def _validate_scene_plan(
        value: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        current_generation: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        basis_generation_id: str,
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Scene Plan Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Scene PlanはJSON objectでなければなりません"
            )

        ContractValidator._validate_brief(brief)

        for parent, label in (
            (initial_design, "Initial Design"),
            (series_plan, "Series Plan"),
            (volume_plan, "Volume Plan"),
            (chapter_plan, "Chapter Plan"),
            (current_generation, "current Generation"),
        ):
            if not isinstance(parent, dict):
                raise ContractError(
                    f"採用済み{label}が必要です"
                )

        for number, label in (
            (volume_number, "巻番号"),
            (chapter_number, "章番号"),
            (scene_number, "Scene番号"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"Scene Planの対象{label}が不正です"
                )

        if (
            not isinstance(basis_generation_id, str)
            or not basis_generation_id.startswith("gen-")
        ):
            raise ContractError(
                "Scene Planのbasis_generation_idが不正です"
            )

        series_basis = series_plan.get(
            "basis_generation_id"
        )
        volume_basis = volume_plan.get(
            "basis_generation_id"
        )
        chapter_basis = chapter_plan.get(
            "basis_generation_id"
        )
        for parent_basis, label in (
            (series_basis, "Series Plan"),
            (volume_basis, "Volume Plan"),
            (chapter_basis, "Chapter Plan"),
        ):
            if (
                not isinstance(parent_basis, str)
                or not parent_basis.startswith("gen-")
            ):
                raise ContractError(
                    f"{label}のbasis_generation_idが不正です"
                )

        ContractValidator._validate_series_plan(
            series_plan,
            brief,
            initial_design,
            series_basis,
            adopted=True,
        )
        ContractValidator._validate_volume_plan(
            volume_plan,
            brief,
            initial_design,
            series_plan,
            volume_plan.get("volume_number"),
            volume_basis,
            adopted=True,
        )
        ContractValidator._validate_chapter_plan(
            chapter_plan,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan.get("volume_number"),
            chapter_plan.get("chapter_number"),
            chapter_basis,
            adopted=True,
        )

        if volume_plan.get("volume_number") != volume_number:
            raise ContractError(
                "Scene Planの対象巻がVolume Planと一致しません"
            )
        if (
            chapter_plan.get("volume_number") != volume_number
            or chapter_plan.get("chapter_number")
            != chapter_number
        ):
            raise ContractError(
                "Scene Planの対象巻章がChapter Planと"
                "一致しません"
            )

        summary = next(
            (
                record
                for record in chapter_plan["scene_summaries"]
                if record["scene_number"] == scene_number
            ),
            None,
        )
        if summary is None:
            raise ContractError(
                "Scene Planの対象SceneがChapter Planに"
                "存在しません"
            )

        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            document = current_generation.get(name)
            if not isinstance(document, dict):
                raise ContractError(
                    "current Generation fileが不正です: "
                    f"{name}"
                )
            if (
                document.get("generation_id")
                != basis_generation_id
            ):
                raise ContractError(
                    "current Generationのgeneration_idが"
                    f"一致しません: {name}"
                )

        state_document = current_generation["state.json"]
        character_states = state_document.get("characters")
        if not isinstance(character_states, dict):
            raise ContractError(
                "current Generationのcharactersが不正です"
            )

        candidate = deepcopy(value)
        metadata_fields = {
            "schema_version",
            "scene_plan_id",
            "volume_number",
            "chapter_number",
            "scene_number",
            "version",
            "status",
            "basis_generation_id",
            "chapter_plan_id",
            "parent_plan_id",
            "created_at",
        }

        if adopted:
            expected_plan_id = (
                f"scene-plan-v{volume_number:02d}"
                f"-c{chapter_number:03d}"
                f"-s{scene_number:03d}"
            )
            if candidate.get("schema_version") != 1:
                raise ContractError(
                    "採用済みScene Planのschema_versionは"
                    "1でなければなりません"
                )
            if candidate.get("scene_plan_id") != expected_plan_id:
                raise ContractError(
                    "採用済みScene PlanのIDが不正です"
                )
            if candidate.get("volume_number") != volume_number:
                raise ContractError(
                    "採用済みScene Planの巻番号が不正です"
                )
            if candidate.get("chapter_number") != chapter_number:
                raise ContractError(
                    "採用済みScene Planの章番号が不正です"
                )
            if candidate.get("scene_number") != scene_number:
                raise ContractError(
                    "採用済みScene PlanのScene番号が不正です"
                )
            if candidate.get("version") != 1:
                raise ContractError(
                    "採用済みScene Planのversionは"
                    "1でなければなりません"
                )
            if candidate.get("status") != "accepted":
                raise ContractError(
                    "採用済みScene Planのstatusは"
                    "acceptedでなければなりません"
                )
            if (
                candidate.get("basis_generation_id")
                != basis_generation_id
            ):
                raise ContractError(
                    "Scene Planのbasis_generation_idが"
                    "current Generationと一致しません"
                )
            if (
                candidate.get("chapter_plan_id")
                != chapter_plan["chapter_plan_id"]
            ):
                raise ContractError(
                    "Scene Planのchapter_plan_idが不正です"
                )
            if candidate.get("parent_plan_id") is not None:
                raise ContractError(
                    "最初のScene Planのparent_plan_idは"
                    "nullでなければなりません"
                )

            created_at = candidate.get("created_at")
            if not isinstance(created_at, str):
                raise ContractError(
                    "採用済みScene Planにはcreated_atが必要です"
                )
            try:
                parsed = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ContractError(
                    "採用済みScene Planのcreated_atが不正です"
                ) from exc
            if parsed.tzinfo is None:
                raise ContractError(
                    "採用済みScene Planのcreated_atには"
                    "timezoneが必要です"
                )

            for field in metadata_fields:
                candidate.pop(field, None)
        else:
            unexpected = metadata_fields & set(candidate)
            if unexpected:
                raise ContractError(
                    "Scene Plan Candidateへ採用metadataを"
                    "含められません: "
                    + ", ".join(sorted(unexpected))
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "scene_plan",
        )
        errors = sorted(
            Draft202012Validator(schema).iter_errors(
                candidate
            ),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Scene Plan契約違反: "
                f"{target}: {error.message}"
            )

        character_ids = {
            record["character_id"]
            for record in initial_design["characters"]
        }
        location_ids = {
            record["location_id"]
            for record in initial_design["locations"]
        }
        participants = candidate["participant_ids"]
        unknown_participants = set(participants) - character_ids
        if unknown_participants:
            raise ContractError(
                "Scene Planが未知のCharacterを参照しています: "
                + ", ".join(sorted(unknown_participants))
            )
        if candidate["pov_character_id"] not in character_ids:
            raise ContractError(
                "Scene PlanのPOV Characterが不正です"
            )
        if candidate["pov_character_id"] not in participants:
            raise ContractError(
                "POV Characterはparticipant_idsに"
                "含めなければなりません"
            )
        if candidate["location_id"] not in location_ids:
            raise ContractError(
                "Scene PlanのLocationが不正です"
            )

        missing_states = set(participants) - set(
            character_states
        )
        if missing_states:
            raise ContractError(
                "Scene参加人物のcurrent Stateがありません: "
                + ", ".join(sorted(missing_states))
            )

        revelation_count = len(
            candidate["intended_revelations"]
        )
        parent_revelation_count = len(
            chapter_plan["required_revelations"]
        )
        if revelation_count > parent_revelation_count:
            raise ContractError(
                "intended_revelationsの件数が"
                "Chapter Planの開示予定を超えています"
            )

        overlap = (
            set(candidate["intended_revelations"])
            & set(candidate["prohibited_disclosures"])
        )
        if overlap:
            raise ContractError(
                "同じ開示をintended_revelationsと"
                "prohibited_disclosuresへ重複指定できません"
            )

    @staticmethod
    def _validate_scene_card_v1(
        value: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        scene_plan: dict[str, Any],
        current_generation: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        basis_generation_id: str,
        *,
        adopted: bool = False,
    ) -> None:
        """V1 Scene Card Candidateまたは採用版を検証する。"""
        if not isinstance(value, dict):
            raise ContractError(
                "Scene CardはJSON objectでなければなりません"
            )

        ContractValidator._validate_scene_plan(
            scene_plan,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
            adopted=True,
        )

        candidate = deepcopy(value)
        metadata_fields = {
            "schema_version",
            "scene_id",
            "version",
            "basis_generation_id",
            "scene_plan_id",
            "created_at",
        }

        expected_scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        if adopted:
            if candidate.get("schema_version") != 1:
                raise ContractError(
                    "採用済みScene Cardのschema_versionは"
                    "1でなければなりません"
                )
            if candidate.get("scene_id") != expected_scene_id:
                raise ContractError(
                    "採用済みScene Cardのscene_idが不正です"
                )
            if candidate.get("version") != 1:
                raise ContractError(
                    "採用済みScene Cardのversionは"
                    "1でなければなりません"
                )
            if (
                candidate.get("basis_generation_id")
                != basis_generation_id
            ):
                raise ContractError(
                    "Scene Cardのbasis_generation_idが"
                    "current Generationと一致しません"
                )
            if (
                candidate.get("scene_plan_id")
                != scene_plan["scene_plan_id"]
            ):
                raise ContractError(
                    "Scene Cardのscene_plan_idが不正です"
                )

            created_at = candidate.get("created_at")
            if not isinstance(created_at, str):
                raise ContractError(
                    "採用済みScene Cardにはcreated_atが必要です"
                )
            try:
                parsed = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ContractError(
                    "採用済みScene Cardのcreated_atが不正です"
                ) from exc
            if parsed.tzinfo is None:
                raise ContractError(
                    "採用済みScene Cardのcreated_atには"
                    "timezoneが必要です"
                )

            for field in metadata_fields:
                candidate.pop(field, None)
        else:
            unexpected = metadata_fields & set(candidate)
            if unexpected:
                raise ContractError(
                    "Scene Card Candidateへ採用metadataを"
                    "含められません: "
                    + ", ".join(sorted(unexpected))
                )

        schema = get_template_loader().load_schema_object(
            "generate",
            "scene_card_v1",
        )
        errors = sorted(
            Draft202012Validator(schema).iter_errors(candidate),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            )
            target = location or "<root>"
            raise ContractError(
                "Scene Card契約違反: "
                f"{target}: {error.message}"
            )

        if (
            candidate["pov_character_id"]
            != scene_plan["pov_character_id"]
        ):
            raise ContractError(
                "Scene CardのPOVがScene Planと一致しません"
            )
        if (
            candidate["participant_ids"]
            != scene_plan["participant_ids"]
        ):
            raise ContractError(
                "Scene Cardの参加人物がScene Planと一致しません"
            )
        if candidate["location_id"] != scene_plan["location_id"]:
            raise ContractError(
                "Scene Cardの場所がScene Planと一致しません"
            )
        if (
            candidate["pov_character_id"]
            not in candidate["participant_ids"]
        ):
            raise ContractError(
                "Scene CardのPOVは参加人物に含める必要があります"
            )

        beats = candidate["required_beats"]
        if len(beats) < len(scene_plan["intended_beats"]):
            raise ContractError(
                "Scene Cardのrequired_beatsが"
                "Scene Planの予定beatを具体化できていません"
            )
        beat_ids = [beat["beat_id"] for beat in beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ContractError(
                "Scene Cardのbeat_idが重複しています"
            )
        order_hints = [beat["order_hint"] for beat in beats]
        if order_hints != list(range(1, len(beats) + 1)):
            raise ContractError(
                "Scene Cardのorder_hintは1からの連番が必要です"
            )
        if any(not beat["required"] for beat in beats):
            raise ContractError(
                "required_beatsのrequiredはtrueが必要です"
            )

        knowledge_ids = {
            record["knowledge_id"]
            for record in initial_design["knowledge_facts"]
        }
        thread_ids = {
            record["thread_id"]
            for record in initial_design["threads"]
        }
        disclosure_ids = knowledge_ids | thread_ids
        for field in (
            "allowed_revelations",
            "required_revelations",
            "forbidden_revelations",
        ):
            unknown = set(candidate[field]) - disclosure_ids
            if unknown:
                raise ContractError(
                    f"Scene Cardの{field}が未知の開示IDを"
                    "参照しています: "
                    + ", ".join(sorted(unknown))
                )

        allowed = set(candidate["allowed_revelations"])
        required = set(candidate["required_revelations"])
        forbidden = set(candidate["forbidden_revelations"])
        if not required <= allowed:
            raise ContractError(
                "required_revelationsはallowed_revelationsの"
                "部分集合でなければなりません"
            )
        overlap = forbidden & (allowed | required)
        if overlap:
            raise ContractError(
                "禁止開示を許可または必須開示へ"
                "重複指定できません: "
                + ", ".join(sorted(overlap))
            )

        state = current_generation["state.json"]
        update_sources = {
            "character_state": state["characters"],
            "relationship_state": state["relationships"],
            "thread_state": state["threads"],
            "inventory_state": state["inventory"],
            "commitment_state": state["commitments"],
        }
        seen_updates: set[tuple[str, str]] = set()
        participants = set(candidate["participant_ids"])

        for update in candidate["allowed_updates"]:
            target_type = update["target_type"]
            target_id = update["target_id"]
            key = (target_type, target_id)
            if key in seen_updates:
                raise ContractError(
                    "Scene Cardのallowed_updatesが重複しています"
                )
            seen_updates.add(key)

            if target_type == "timeline_state":
                if target_id != "timeline":
                    raise ContractError(
                        "timeline_stateのtarget_idはtimelineが必要です"
                    )
                record = state["timeline"]
            else:
                source = update_sources[target_type]
                if target_id not in source:
                    raise ContractError(
                        "Scene Cardのallowed_updatesが"
                        "存在しないcurrent Stateを参照しています"
                    )
                record = source[target_id]

            unknown_fields = (
                set(update["allowed_fields"]) - set(record)
            )
            if unknown_fields:
                raise ContractError(
                    "Scene Cardのallowed_updatesが"
                    "存在しないfieldを許可しています: "
                    + ", ".join(sorted(unknown_fields))
                )
            if (
                target_type == "character_state"
                and target_id not in participants
            ):
                raise ContractError(
                    "参加していないCharacterの更新を"
                    "Scene Cardで許可できません"
                )

    @staticmethod
    def _validate_chapter_count_length(brief: dict[str, Any], volume_count: int) -> None:
        counts = brief.get("chapters_per_volume")
        if counts is not None and len(counts) != volume_count:
            raise ContractError("chapters_per_volume は全巻構成の巻数と一致しなければなりません")

    @staticmethod
    def _validate_volume_map(volume_map: dict[str, Any], brief: dict[str, Any], threads: list[dict[str, Any]]) -> None:
        volumes = volume_map.get("volumes")
        if not isinstance(volumes, list) or not 4 <= len(volumes) <= 10 or (brief.get("volumes") and len(volumes) != brief["volumes"]):
            raise ContractError("巻配分の巻数が不正です")
        known = {record["id"] for record in threads}
        major = {record["id"] for record in threads if record.get("importance") == "major"}
        actions_by_thread: dict[str, list[str]] = {identifier: [] for identifier in known}
        for expected, volume in enumerate(volumes, 1):
            if not isinstance(volume, dict) or "number" in volume or "ending_condition" in volume:
                raise ContractError("巻配分に採番または結末条件を含めてはいけません")
            for key, limit in (("title", 48), ("reader_question", 160)):
                if not isinstance(volume.get(key), str) or len(volume[key]) > limit:
                    raise ContractError(f"巻配分の {key} が不正です")
                if any("\uac00" <= character <= "\ud7a3" for character in volume[key]):
                    raise ContractError(f"巻配分の {key} に日本語以外のハングル字形があります")
            targets = volume.get("thread_targets")
            if not isinstance(targets, list) or not targets:
                raise ContractError("各巻には少なくとも一つの主要項目配分が必要です")
            seen: set[str] = set()
            for target in targets:
                if not isinstance(target, dict) or target.get("thread_id") not in known:
                    raise ContractError("巻配分が未知の主要項目を参照しています")
                identifier = target["thread_id"]
                action = target.get("required_action")
                if identifier in seen or action not in {"introduce", "advance", "resolve"}:
                    raise ContractError("巻配分の主要項目操作が不正です")
                seen.add(identifier)
                actions_by_thread[identifier].append(action)
            if expected < len(volumes):
                if not volume["reader_question"].strip():
                    raise ContractError("最終巻以外には次巻へ続く問いが必要です")
            elif volume["reader_question"]:
                raise ContractError("最終巻の問いは空文字列でなければなりません")
        for identifier in major:
            actions = actions_by_thread[identifier]
            if not actions or actions[0] != "introduce" or actions[-1] != "resolve" or any(action == "introduce" for action in actions[1:]) or "resolve" in actions[:-1]:
                raise ContractError("major の主要項目は導入から回収まで巻配分しなければなりません")

    @staticmethod
    def _validate_characters(value: dict[str, Any]) -> None:
        records = value.get("characters")
        if not isinstance(records, list) or not records:
            raise ContractError("人物台帳が空です")
        for record in records:
            ContractValidator._require(record, "name", "role", "narrative_function", "fixed_profile")
            ContractValidator._initial_state(record)
            if "id" in record:
                raise ContractError("人物IDはプログラムが採番します")

    @staticmethod
    def _validate_relationships(value: dict[str, Any], characters: list[dict[str, Any]]) -> None:
        records = value.get("relationships")
        ids = {record["id"] for record in characters}
        if not isinstance(records, list):
            raise ContractError("関係台帳が配列ではありません")
        for record in records:
            ContractValidator._require(record, "character_a_id", "character_b_id", "fixed_meaning")
            ContractValidator._initial_state(record)
            if record["character_a_id"] not in ids or record["character_b_id"] not in ids:
                raise ContractError("関係台帳が未知の人物を参照しています")
            if "id" in record:
                raise ContractError("関係IDはプログラムが採番します")

    @staticmethod
    def _validate_world(value: dict[str, Any]) -> None:
        records = value.get("entities")
        if not isinstance(records, list):
            raise ContractError("世界台帳が配列ではありません")
        for record in records:
            ContractValidator._require(record, "kind", "name", "stable_fact", "use_or_access_rule")
            ContractValidator._validate_world_initial_state(record)
            if "id" in record:
                raise ContractError("世界IDはプログラムが採番します")

    @staticmethod
    def _validate_timeline(value: dict[str, Any], known_ids: set[str]) -> None:
        records = value.get("timelines")
        if not isinstance(records, list):
            raise ContractError("時間台帳が配列ではありません")
        for record in records:
            ContractValidator._require(record, "kind", "description", "related_ids", "fixed_rule")
            ContractValidator._validate_timeline_initial_state(record)
            sequence = record.get("sequence")
            if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
                raise ContractError("時間台帳の sequence が不正です")
            if not isinstance(record["related_ids"], list) or not set(record["related_ids"]).issubset(known_ids):
                raise ContractError("時間台帳が未知IDを参照しています")
            if "id" in record:
                raise ContractError("時間IDはプログラムが採番します")

    @staticmethod
    def _validate_threads(value: dict[str, Any], known_ids: set[str]) -> None:
        records = value.get("threads")
        if not isinstance(records, list) or not records:
            raise ContractError("主要項目台帳が空です")
        major_count = 0
        for record in records:
            ContractValidator._require(record, "kind", "importance", "description", "author_truth", "reader_knowledge", "character_knowledge", "presentation_rule", "resolution_condition")
            state = ContractValidator._validate_threads_initial_state(record)
            if record["importance"] not in {"major", "supporting"} or state.get("status") not in {"open", "in_progress", "resolved"}:
                raise ContractError("主要項目の状態または重要度が不正です")
            if not isinstance(record["character_knowledge"], dict) or not set(record["character_knowledge"]).issubset(known_ids):
                raise ContractError("主要項目が未知の人物を参照しています")
            if "id" in record:
                raise ContractError("主要項目IDはプログラムが採番します")
            if record["importance"] == "major":
                major_count += 1
        if major_count == 0:
            raise ContractError("主要項目台帳には major が必要です")

    @staticmethod
    def _validate_threads_initial_state(record: dict[str, Any]) -> dict[str, Any]:
        state = record.get("initial_state")
        if not isinstance(state, dict) or not state:
            raise ContractError("開始時の現在状態がありません")
        for field in ("status", "progress"):
            if field not in state:
                raise ContractError(f"initial_state に必須項目がありません: {field}")
        return state

    @staticmethod
    def _validate_chapters(value: dict[str, Any], volume: dict[str, Any], brief: dict[str, Any]) -> None:
        chapters = value.get("chapters")
        expected_count = (brief.get("chapters_per_volume") or [None] * len([volume]))[volume["number"] - 1] if brief.get("chapters_per_volume") else None
        if not isinstance(chapters, list) or not chapters or (expected_count is not None and len(chapters) != expected_count):
            raise ContractError("章一覧の件数が不正です")
        for number, chapter in enumerate(chapters, 1):
            if not isinstance(chapter, dict) or chapter.get("number") != number:
                raise ContractError("章番号が連番ではありません")
            ContractValidator._require(chapter, "title", "purpose", "start_state", "end_state")
            if not isinstance(chapter.get("scene_count"), int) or not 1 <= chapter["scene_count"] <= 4:
                raise ContractError("場面数は1〜4でなければなりません")

    def _validate_card(
        self, card: dict[str, Any], scene_id: str, state: dict[str, Any], volume: dict[str, Any] | None = None,
        required_thread_actions: list[dict[str, str]] | None = None,
    ) -> None:
        self._require(card, "scene_id", "pov_character_id", "location_id", "start_time_id", "end_time_id", "character_ids", "purpose", "required_events", "thread_actions", "reader_disclosure", "withheld_information", "presentation_rules", "end_change", "visible_ids", "allowed_update_ids")
        if card["scene_id"] != scene_id:
            raise ContractError("場面カードのIDが実行対象と一致しません")
        characters = {record["id"] for record in state["characters"]}
        time_records = {record["id"]: record for record in state["timeline"]}
        times = set(time_records)
        world = {record["id"] for record in state["world"]}
        threads = {record["id"] for record in state["threads"]}
        known = self._known_ids(state)
        if card["pov_character_id"] not in characters or card["location_id"] not in world:
            raise ContractError("場面カードの視点人物または場所が不正です")
        if card["start_time_id"] not in times or card["end_time_id"] not in times:
            raise ContractError("場面カードの時刻が不正です")
        if time_records[card["start_time_id"]]["sequence"] > time_records[card["end_time_id"]]["sequence"]:
            raise ContractError("場面カードの開始時刻が終了時刻より後です")
        volume_prefix = scene_id.split("-c", 1)[0] + "-"
        previous_ends = [
            time_records[prior_card["end_time_id"]]["sequence"]
            for prior_scene_id, prior_card in state["cards"].items()
            if prior_scene_id.startswith(volume_prefix)
        ]
        if previous_ends and time_records[card["start_time_id"]]["sequence"] < max(previous_ends):
            raise ContractError("場面カードの時刻が同一巻の既存場面より逆行しています")
        if not isinstance(card["character_ids"], list) or not card["character_ids"] or not set(card["character_ids"]).issubset(characters):
            raise ContractError("場面カードの登場人物が不正です")
        if card["pov_character_id"] not in card["character_ids"]:
            raise ContractError("場面カードの視点人物は登場人物に含めなければなりません")
        if not isinstance(card["thread_actions"], list):
            raise ContractError("場面カードの伏線操作が不正です")
        action_pairs: set[tuple[str, str]] = set()
        for action in card["thread_actions"]:
            self._require(action, "thread_id", "action")
            pair = (action["thread_id"], action["action"])
            if action["thread_id"] not in threads or action["action"] not in {"introduce", "advance", "resolve"}:
                raise ContractError("場面カードの伏線操作が不正です")
            if pair in action_pairs:
                raise ContractError("場面カードの伏線操作が重複しています")
            action_pairs.add(pair)
        if required_thread_actions is not None:
            required_pairs = Counter((action["thread_id"], action["action"]) for action in required_thread_actions)
            if Counter(action_pairs) != required_pairs:
                raise ContractError("場面カードの主要項目操作がこの場面への割当と一致しません")
        elif volume is not None:
            planned = {(target["thread_id"], target["required_action"]) for target in volume["thread_targets"]}
            if not action_pairs.issubset(planned):
                raise ContractError("場面カードに巻配分の対象外の主要項目操作があります")
        for field in ("visible_ids", "allowed_update_ids"):
            values = card[field]
            if not isinstance(values, list) or len(values) != len(set(values)) or not set(values).issubset(known):
                raise ContractError(f"場面カードの {field} が不正です")
        required_visible = {
            card["pov_character_id"], card["location_id"], card["start_time_id"], card["end_time_id"],
            *card["character_ids"], *(action["thread_id"] for action in card["thread_actions"]),
        }
        if not required_visible.issubset(card["visible_ids"]):
            raise ContractError("場面カードの visible_ids に必須の参照IDがありません")
        if not set(card["allowed_update_ids"]).issubset(card["visible_ids"]):
            raise ContractError("状態更新の許可IDは可視IDの部分集合でなければなりません")
        if not all(identifier.startswith(("char-", "thread-")) for identifier in card["allowed_update_ids"]):
            raise ContractError("状態更新は人物または主要項目だけに許可できます")

    @staticmethod
    def _validate_scene(value: dict[str, Any]) -> None:
        if set(value) != {"content"} or not isinstance(value.get("content"), str) or not value["content"].strip():
            raise ContractError("場面本文は空でない content だけを返さなければなりません")

    def _validate_continuity(self, value: dict[str, Any], content: str, card: dict[str, Any], state: dict[str, Any], is_final_scene: bool) -> None:
        self._require(value, "handoff_summary", "state_updates")
        if not isinstance(value["state_updates"], list):
            raise ContractError("状態更新が配列ではありません")
        seen: set[str] = set()
        unresolved = {record["id"] for record in state["threads"] if record["importance"] == "major" and record["current_state"].get("status") != "resolved"}
        resolved: set[str] = set()
        for update in value["state_updates"]:
            self._require(update, "source_scene_id", "id", "field", "value", "evidence")
            if update["source_scene_id"] != card["scene_id"]:
                raise ContractError("状態更新の場面IDが実行対象と一致しません")
            if update["id"] in seen or update["id"] not in card["allowed_update_ids"]:
                raise ContractError("状態更新が重複または未許可です")
            seen.add(update["id"])
            if not isinstance(update["evidence"], str) or not update["evidence"] or update["evidence"] not in content:
                raise ContractError("状態更新に本文根拠がありません")
            target = self._record_for_id(state, update["id"])
            if target is None:
                raise ContractError("状態更新が未知IDを参照しています")
            field = update["field"]
            if update["id"].startswith("thread-"):
                if target.get("importance") != "major":
                    raise ContractError("supporting主要項目は状態更新できません")
                if field == "status":
                    if update["value"] not in {"open", "in_progress", "resolved"}:
                        raise ContractError("主要項目の状態が不正です")
                    if update["value"] == "resolved":
                        if (update["id"], "resolve") not in {(action["thread_id"], action["action"]) for action in card["thread_actions"]}:
                            raise ContractError("主要項目を回収するには場面カードの resolve 操作が必要です")
                        resolved.add(update["id"])
                elif field == "progress":
                    if not isinstance(update["value"], (int, float)) or isinstance(update["value"], bool) or not 0.0 <= update["value"] <= 1.0:
                        raise ContractError("主要項目の進捗は0.0〜1.0の数値でなければなりません")
                else:
                    raise ContractError("主要項目の更新フィールドが不正です")
            elif update["id"].startswith("char-"):
                if field not in {"emotion", "situation", "recent_goal"} or not isinstance(update["value"], str) or not update["value"].strip():
                    raise ContractError("人物の更新フィールドまたは値が不正です")
            else:
                raise ContractError("更新できない台帳種別です")
        if is_final_scene and not unresolved.issubset(resolved):
            raise ContractError("最終場面で主要項目がすべて回収されていません")

    @staticmethod
    def _validate_volume_summary(value: dict[str, Any], state: dict[str, Any]) -> None:
        if not isinstance(value.get("volume_summary"), str) or not value["volume_summary"].strip() or not isinstance(value.get("unresolved_thread_ids"), list):
            raise ContractError("巻要約が不正です")
        expected = {
            record["id"] for record in state["threads"]
            if record["importance"] == "major" and record["current_state"].get("status") != "resolved"
        }
        actual = value["unresolved_thread_ids"]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ContractError("巻要約の未回収主要項目が現在状態と一致しません")

    def _validate_closure(self, value: dict[str, Any], state: dict[str, Any]) -> None:
        resolved = value.get("resolved_ids")
        required = {record["id"] for record in state["threads"] if record["importance"] == "major"}
        if not isinstance(resolved, list) or set(resolved) != required or len(resolved) != len(set(resolved)):
            raise ContractError("完結確認の主要項目が台帳と一致しません")
        for item in required:
            record = self._record_for_id(state, item)
            if record is None or record["current_state"].get("status") != "resolved":
                raise ContractError("未回収の主要項目があります")
        evidence = value.get("ending_evidence")
        final_scene = state["scenes"][-1] if state["scenes"] else {}
        if value.get("ending_authority") != state["brief"]["ending_preference"] or not isinstance(evidence, str) or not evidence or evidence not in final_scene.get("content", ""):
            raise ContractError("結末の本文根拠がありません")

    @staticmethod
    def _validate_critique(value: Any) -> None:
        if not isinstance(value, dict) or not isinstance(value.get("issues"), list):
            raise ContractError("批評の issues が配列ではありません")
        for issue in value["issues"]:
            if not isinstance(issue, dict) or issue.get("severity") not in {"critical", "major", "minor"}:
                raise ContractError("批評 issue が不正です")
            ContractValidator._require(issue, "field", "description", "suggestion")

    @staticmethod
    def _require(value: Any, *fields: str) -> None:
        if not isinstance(value, dict):
            raise ContractError("応答項目がオブジェクトではありません")
        for field in fields:
            if not isinstance(value.get(field), str) or not value[field].strip():
                if field in {"required_events", "character_ids", "thread_actions", "visible_ids", "allowed_update_ids", "state_updates", "related_ids"} and isinstance(value.get(field), list):
                    continue
                if field == "character_knowledge" and isinstance(value.get(field), dict):
                    continue
                raise ContractError(f"必須項目がありません: {field}")

    @staticmethod
    def _validate_world_initial_state(record: dict[str, Any]) -> dict[str, Any]:
        state = record.get("initial_state")
        if not isinstance(state, dict) or not state:
            raise ContractError("開始時の現在状態がありません")
        for field in ("status", "current_holder_or_manager", "recent_change"):
            if not isinstance(state.get(field), str) or not state[field].strip():
                raise ContractError(f"initial_state に必須項目がありません: {field}")
        return state

    @staticmethod
    def _validate_timeline_initial_state(record: dict[str, Any]) -> dict[str, Any]:
        state = record.get("initial_state")
        if not isinstance(state, dict) or not state:
            raise ContractError("開始時の現在状態がありません")
        for field in ("current_value", "next_change_trigger", "estimate_until_next"):
            if not isinstance(state.get(field), str) or not state[field].strip():
                raise ContractError(f"initial_state に必須項目がありません: {field}")
        return state

    @staticmethod
    def _initial_state(record: dict[str, Any]) -> dict[str, Any]:
        state = record.get("initial_state")
        if not isinstance(state, dict) or not state:
            raise ContractError("開始時の現在状態がありません")
        for field in ("emotion", "situation", "recent_goal"):
            if not isinstance(state.get(field), str) or not state[field].strip():
                raise ContractError(f"initial_state に必須項目がありません: {field}")
        return state

    @staticmethod
    def _assign_ids(records: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
        assigned: list[dict[str, Any]] = []
        for number, record in enumerate(records, 1):
            copy = dict(record)
            copy["id"] = f"{prefix}-{number:04d}"
            copy["current_state"] = dict(copy["initial_state"])
            assigned.append(copy)
        return assigned