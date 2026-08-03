"""V2 generic candidate/review/adoption runner.

The runner owns immutable candidate, review, quality, and adoption records.  Stage
adapters supply only stage-specific IDs and deterministic content validation; model
transport/retry policy deliberately stays outside this module.
"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Protocol

from .artifact_ids import reserve_counter
from .artifact_registry import artifact_directory, canonical_slot
from .commit_recovery import recover_pending_commit
from .run_state import RunStateStore
from .selection_snapshot import SelectionSnapshotStore, validate_selection_snapshot
from .series_contracts import ContractError, LLMCallError
from .review_contracts import field_tokens


class InvalidResponseLimitError(ContractError):
    """A candidate/review/revision response remained malformed through its limit."""


class CandidateModel(Protocol):
    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]: ...
    def review(self, stage: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]: ...
    def revise(self, stage: str, context: dict[str, Any], candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]: ...


ContentIdFactory = Callable[[Path, dict[str, Any]], str]
ContentValidator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class CandidateStageSpec:
    stage: str
    artifact_kind: str
    next_stage: str
    next_target: dict[str, Any]
    content_id_factory: ContentIdFactory
    content_validator: ContentValidator | None = None


class CandidateStageRunner:
    """Persist valid candidate history and adopt the selected valid revision once."""

    def __init__(self, workspace_root: Path, spec: CandidateStageSpec) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.spec = spec
        self.state_store = RunStateStore(self.workspace_root)

    def run(self, model: CandidateModel | None, *, context: dict[str, Any], updated_at: str) -> dict[str, Any]:
        state = self.state_store.load()
        if state["status"] != "running" or state["current_stage"] != self.spec.stage:
            raise ContractError("現在のrun-stateは実行可能なcandidate stageではありません")
        if state["pending_commit"] is not None:
            return recover_pending_commit(self.workspace_root)
        if model is None:
            raise ContractError("candidate生成には注入されたmodelが必要です")

        input_selection_id = state["current_selection_id"]
        if not isinstance(input_selection_id, str):
            raise ContractError("candidate stageには入力selectionが必要です")
        slots = self._input_slots(input_selection_id)
        settings_id = slots.get("settings")
        if not isinstance(settings_id, str):
            raise ContractError("candidate stageのselectionにsettingsがありません")

        invalid_limit = self._invalid_response_limit(settings_id)
        self._set_model_call_context(model, settings_id=settings_id, input_refs=[input_selection_id])
        candidate = self._valid_response(
            model, "generate", (self.spec.stage, deepcopy(context)), self._candidate,
            invalid_limit=invalid_limit,
        )
        candidate_id = self._reserve("candidates", "candidate")
        generate_call = self._physical_call_id(model, "generate")
        self._write_record("candidates", candidate_id, {
            "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": self.spec.artifact_kind,
            "input_selection_id": input_selection_id, "keywords_id": None, "settings_id": settings_id,
            "payload": candidate["payload"], "parent_candidate_id": None, "review_record_id": None,
            "call_id": generate_call, "created_at": updated_at,
        })

        revision_count = 0
        review_ids: list[str] = []
        while True:
            self._set_model_call_context(
                model, settings_id=settings_id,
                input_refs=[input_selection_id, candidate_id],
                target_candidate_id=candidate_id,
            )
            review = self._valid_response(
                model, "review", (self.spec.stage, deepcopy(context), deepcopy(candidate)),
                lambda value: self._review_with_evidence(value, candidate["payload"]),
                invalid_limit=invalid_limit,
            )
            review_id = self._reserve("reviews", "review")
            review_call = self._physical_call_id(model, "review")
            self._write_record("reviews", review_id, {
                "schema_version": 1, "review_id": review_id, "candidate_id": candidate_id,
                "response": review, "call_id": review_call, "created_at": updated_at,
            })
            review_ids.append(review_id)
            critical = [issue for issue in review["issues"] if issue["severity"] == "critical"]
            if not critical:
                return self._adopt(state, slots, input_selection_id, candidate_id, candidate, review_ids, revision_count, [], updated_at)

            limit = self._quality_limit(settings_id)
            if limit != 0 and revision_count >= limit:
                return self._adopt(state, slots, input_selection_id, candidate_id, candidate, review_ids, revision_count, critical, updated_at)

            try:
                self._set_model_call_context(
                    model, settings_id=settings_id,
                    input_refs=[input_selection_id, candidate_id, review_id],
                    target_candidate_id=candidate_id,
                )
                revised = self._valid_response(
                    model, "revise", (self.spec.stage, deepcopy(context), deepcopy(candidate), deepcopy(review)), self._candidate,
                    invalid_limit=invalid_limit,
                )
            except InvalidResponseLimitError:
                # Only an explicitly unbounded quality loop may accept the last
                # valid candidate after a malformed revision.  A finite quality
                # limit is a contract boundary: a failed revision blocks rather
                # than silently turning into accepted_with_notice.
                if limit != 0:
                    raise
                return self._adopt(state, slots, input_selection_id, candidate_id, candidate, review_ids, revision_count, critical, updated_at)
            revised_id = self._reserve("candidates", "candidate")
            revise_call = self._physical_call_id(model, "revise")
            self._write_record("candidates", revised_id, {
                "schema_version": 1, "candidate_id": revised_id, "artifact_kind": self.spec.artifact_kind,
                "input_selection_id": input_selection_id, "keywords_id": None, "settings_id": settings_id,
                "payload": revised["payload"], "parent_candidate_id": candidate_id, "review_record_id": review_id,
                "call_id": revise_call, "created_at": updated_at,
            })
            candidate, candidate_id = revised, revised_id
            # A quality disposition binds only reviews of its adopted candidate;
            # prior reviews remain linked through the immutable revision lineage.
            review_ids = []
            revision_count += 1

    def updated_slots(self, input_slots: dict[str, str], content_id: str, adoption_id: str, quality_id: str) -> dict[str, str]:
        """Return next immutable selection slots, invalidating continuity after prose changes."""
        slots = dict(input_slots)
        if self.spec.artifact_kind == "scene-prose":
            slots = {key: value for key, value in slots.items() if not key.startswith("continuity_")}
        slot = canonical_slot(self.spec.artifact_kind, content_id)
        slots[slot] = content_id
        if self.spec.artifact_kind == "initial-design":
            slots["initial_design_adoption"] = adoption_id
        elif self.spec.artifact_kind in {"series-plan", "volume-plan", "chapter-plan", "scene-plan"}:
            stem, coordinate = slot.split(".", 1) if "." in slot else (slot, "")
            slots[f"{stem}_adoption" + (f".{coordinate}" if coordinate else "")] = adoption_id
        elif self.spec.artifact_kind in {"scene-card", "scene-prose", "continuity-update"}:
            stem, coordinate = slot.split(".", 1)
            adoption_stem = "continuity" if self.spec.artifact_kind == "continuity-update" else stem
            slots[f"{adoption_stem}_adoption.{coordinate}"] = adoption_id
            if self.spec.artifact_kind == "scene-prose":
                slots[f"scene_prose_disposition.{coordinate}"] = quality_id
            elif self.spec.artifact_kind == "continuity-update":
                slots[f"continuity_disposition.{coordinate}"] = quality_id
        return slots

    def _adopt(self, state: dict[str, Any], input_slots: dict[str, str], input_selection_id: str, candidate_id: str, candidate: dict[str, Any], review_ids: list[str], revision_count: int, critical: list[dict[str, Any]], updated_at: str) -> dict[str, Any]:
        quality_id = self._reserve("quality", "quality")
        quality = {
            "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
            "review_record_ids": review_ids, "revision_count": revision_count,
            "result": "accepted_with_notice" if critical else "accepted",
            "remaining_major_issues": [{"code": "quality.critical", "message": issue["explanation"], "evidence_locations": issue["evidence_locations"]} for issue in critical],
            "created_at": updated_at,
        }
        if critical:
            quality["notice_type"] = "編集"
        self._write_record("quality", quality_id, quality)

        content_id = self.spec.content_id_factory(self.workspace_root, dict(state["current_target"]))
        # Validate the supplied ID/slot before filesystem mutation.
        slot = canonical_slot(self.spec.artifact_kind, content_id)
        adoption_id = self._reserve("runtime/adoptions", "adoption")
        output_selection_id = self._reserve("runtime/selections", "selection")
        staging_root = f"runtime/staging/{adoption_id}"
        next_slots = self.updated_slots(input_slots, content_id, adoption_id, quality_id)
        selection = {"schema_version": 1, "selection_id": output_selection_id, "input_selection_id": input_selection_id, "slots": next_slots, "created_at": updated_at}
        validate_selection_snapshot(selection)
        content = {"schema_version": 1, "artifact_id": content_id, "artifact_kind": self.spec.artifact_kind, "input_selection_id": input_selection_id, "created_at": updated_at, "content": candidate["payload"]}
        if self.spec.content_validator is not None:
            self.spec.content_validator(content["content"])
        adoption = {"schema_version": 1, "adoption_id": adoption_id, "source_kind": "candidate", "candidate_id": candidate_id, "quality_id": quality_id, "output_content_artifact_ids": [content_id], "output_selection_id": output_selection_id, "input_selection_id": input_selection_id, "created_at": updated_at}
        records = ((content_id, self.spec.artifact_kind, content), (adoption_id, "adoption", adoption), (output_selection_id, "selection", selection))
        targets: list[dict[str, str]] = []
        for artifact_id, kind, record in records:
            staged = f"{staging_root}/{artifact_id}"
            self._write_record(staged, "", record)
            final = self._final_path(kind, artifact_id)
            targets.append({"artifact_id": artifact_id, "artifact_kind": kind, "staging_path": staged, "final_path": final, "status": "pending"})
        working = dict(state)
        working["updated_at"] = updated_at
        working["pending_commit"] = {"kind": "candidate_adoption", "staging_path": staging_root, "input_selection_id": input_selection_id, "output_selection_id": output_selection_id, "state_update": {"current_selection_id": output_selection_id, "current_stage": self.spec.next_stage, "current_target": dict(self.spec.next_target)}, "targets": targets}
        self.state_store.save(working)
        return recover_pending_commit(self.workspace_root)

    def _candidate(self, value: object) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != {"schema_version", "artifact_kind", "payload"} or value.get("schema_version") != "candidate-response-v1" or value.get("artifact_kind") != self.spec.artifact_kind or not isinstance(value.get("payload"), dict):
            raise ContractError("candidate responseが不正です")
        if self.spec.content_validator is not None:
            self.spec.content_validator(value["payload"])
        return value

    @staticmethod
    def _review(value: object) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != {"schema_version", "decision", "issues"} or value.get("schema_version") != "review-response-v1" or value.get("decision") not in {"pass", "issues"} or not isinstance(value.get("issues"), list):
            raise ContractError("review responseが不正です")
        issues = value["issues"]
        if (value["decision"] == "pass") != (not issues):
            raise ContractError("review decisionとissuesが一致しません")
        for issue in issues:
            if not isinstance(issue, dict) or set(issue) != {"severity", "evidence_locations", "explanation"} or issue.get("severity") not in {"critical", "notice"} or not isinstance(issue.get("evidence_locations"), list) or not issue["evidence_locations"] or not isinstance(issue.get("explanation"), str) or not issue["explanation"]:
                raise ContractError("review issueが不正です")
        return value

    @classmethod
    def _review_with_evidence(cls, value: object, candidate: dict[str, Any]) -> dict[str, Any]:
        review = cls._review(value)
        for issue in review["issues"]:
            for location in issue["evidence_locations"]:
                if not isinstance(location, str) or not location:
                    raise ContractError("review evidence_locationsが不正です")
                if location.startswith(("prose:", "offset:")):
                    try:
                        offset = int(location.split(":", 1)[1])
                    except ValueError as exc:
                        raise ContractError("review prose offsetが不正です") from exc
                    text = candidate.get("text")
                    if not isinstance(text, str) or not 0 <= offset < len(text):
                        raise ContractError("review prose evidenceが候補を指しません")
                elif location.startswith("paragraph:"):
                    try:
                        paragraph = int(location.split(":", 1)[1])
                    except ValueError as exc:
                        raise ContractError("review paragraph indexが不正です") from exc
                    text = candidate.get("text")
                    if not isinstance(text, str) or not 0 <= paragraph < len(text.split("\\n\\n")):
                        raise ContractError("review paragraph evidenceが候補を指しません")
                else:
                    current: Any = candidate
                    for token in field_tokens(location):
                        if isinstance(current, dict) and isinstance(token, str) and token in current:
                            current = current[token]
                        elif isinstance(current, list) and isinstance(token, int) and 0 <= token < len(current):
                            current = current[token]
                        else:
                            raise ContractError("review JSON evidenceが候補を指しません")
        return review

    def _input_slots(self, selection_id: str) -> dict[str, str]:
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        return dict(snapshot["slots"])

    def _quality_limit(self, settings_id: str) -> int:
        path = self.workspace_root / "runtime/settings" / settings_id / "record.json"
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            payload = record["payload"]
            limit = payload["quality_revision_limit"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ContractError("settings quality_revision_limitを読めません") from exc
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ContractError("quality_revision_limitが不正です")
        return limit

    def _invalid_response_limit(self, settings_id: str) -> int:
        settings = self._settings_payload(settings_id)
        limit = settings.get("invalid_response_limit", 1)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ContractError("invalid_response_limitが不正です")
        return limit
    def _physical_call_id(self, model: CandidateModel, operation: str) -> str:
        call_id = getattr(model, "last_call_id", None)
        path = self.workspace_root / "runtime/calls" / str(call_id) / "record.json"
        if not isinstance(call_id, str) or not call_id.startswith("call-") or not path.is_file():
            raise ContractError(f"{operation}の物理call_idがmodelから得られません")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"{operation}の物理call recordを読めません") from exc
        if record.get("call_id") != call_id:
            raise ContractError(f"{operation}の物理call recordがcall_idと一致しません")
        return call_id

    @staticmethod
    def _set_model_call_context(
        model: CandidateModel,
        *,
        settings_id: str,
        input_refs: list[str],
        target_candidate_id: str | None = None,
    ) -> None:
        """Supply V2 audit bindings without imposing them on injected test models."""
        setter = getattr(model, "set_call_context", None)
        if callable(setter):
            setter(
                settings_id=settings_id,
                input_refs=input_refs,
                target_candidate_id=target_candidate_id,
            )

    @staticmethod
    def _valid_response(
        model: CandidateModel,
        operation: str,
        arguments: tuple[Any, ...],
        validator: Callable[[object], dict[str, Any]],
        *,
        invalid_limit: int,
    ) -> dict[str, Any]:
        method = getattr(model, operation)
        last_error: ContractError | None = None
        for attempt in range(invalid_limit):
            if attempt:
                begin = getattr(model, "begin_format_attempt", None)
                if callable(begin):
                    begin()
            try:
                return validator(method(*arguments))
            except LLMCallError:
                raise
            except ContractError as exc:
                last_error = exc
        raise InvalidResponseLimitError(f"{operation} responseがinvalid_response_limitまで不正です") from last_error


    def _settings_payload(self, settings_id: str) -> dict[str, Any]:
        try:
            value = json.loads((self.workspace_root / "runtime/settings" / settings_id / "record.json").read_text(encoding="utf-8"))["payload"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ContractError("settingsを読めません") from exc
        if not isinstance(value, dict):
            raise ContractError("settings payloadが不正です")
        return value

    def _reserve(self, relative_root: str, prefix: str) -> str:
        del relative_root
        counters = {
            "candidate": "next_candidate",
            "review": "next_review",
            "quality": "next_quality",
            "adoption": "next_adoption",
            "selection": "next_selection",
            "call": "next_call",
        }
        try:
            counter = counters[prefix]
        except KeyError as exc:
            raise ContractError("未知のaudit artifact prefixです") from exc
        return f"{prefix}-{reserve_counter(self.workspace_root, counter):06d}"

    def _write_record(self, relative_root: str, identifier: str, record: dict[str, Any]) -> None:
        directory = self.workspace_root / relative_root
        if identifier:
            directory /= identifier
        if directory.exists():
            raise ContractError("不変recordを上書きできません")
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


    @staticmethod
    def _final_path(kind: str, artifact_id: str) -> str:
        if kind == "adoption":
            return f"runtime/adoptions/{artifact_id}"
        if kind == "selection":
            return f"runtime/selections/{artifact_id}"
        return str(artifact_directory(kind, artifact_id))
