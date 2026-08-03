"""V2 initial-design adapter: selection input, immutable adoption, generic recovery."""
from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import InvalidResponseLimitError
from .commit_recovery import recover_pending_commit
from .llm_responses import review_response
from .run_state import RunStateStore
from .selection_authority import resolve_selection, _validate_initial_design_content
from .selection_snapshot import SelectionSnapshotStore, validate_selection_snapshot
from .series_contracts import ContractError, LLMCallError
from .workspace import validate_workspace


def create_initial_design_stage_service(workspace_root: Path) -> "InitialDesignStageService":
    return InitialDesignStageService(workspace_root)


class InitialDesignStageService:
    """Generate one v2 initial-design from the current request/settings selection."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: Any | None,
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        state = self.state_store.load()
        if state["status"] != "running" or state["current_stage"] != "initial_design":
            raise ContractError("現在のrun-stateは実行可能なinitial_designではありません")
        if state["pending_commit"] is not None:
            return recover_pending_commit(self.workspace_root)
        if model is None:
            raise ContractError("initial_design生成にはStoryModelが必要です")
        if updated_at is None:
            raise ContractError("initial_designの確定時刻が必要です")

        input_selection_id = state["current_selection_id"]
        assert isinstance(input_selection_id, str)
        inputs = resolve_selection(
            self.workspace_root,
            SelectionSnapshotStore(self.workspace_root).load(input_selection_id),
        )
        if set(inputs) != {"request", "settings"}:
            raise ContractError("initial_design入力selectionはrequestとsettingsだけでなければなりません")
        request = inputs["request"]["content"]
        settings = inputs["settings"]["payload"]
        if not isinstance(request, dict) or not isinstance(settings, dict):
            raise ContractError("initial_design入力recordが不正です")
        context = {"request": request, "settings": settings}
        invalid_limit = settings.get("invalid_response_limit")
        if not isinstance(invalid_limit, int) or isinstance(invalid_limit, bool) or invalid_limit < 1:
            raise ContractError("initial_designのinvalid_response_limitが不正です")
        quality_limit = settings.get("quality_revision_limit")
        if not isinstance(quality_limit, int) or isinstance(quality_limit, bool) or quality_limit < 0:
            raise ContractError("initial_designのquality_revision_limitが不正です")

        def valid_candidate(value: object) -> dict[str, Any]:
            if not isinstance(value, dict) or set(value) != {"schema_version", "artifact_kind", "payload"}:
                raise ContractError("initial_designのCandidateResponse envelopeが不正です")
            if value.get("schema_version") != "candidate-response-v1" or value.get("artifact_kind") != "initial-design":
                raise ContractError("initial_designのCandidateResponse種別が不正です")
            payload = value.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("initial_designのCandidateResponse payloadが不正です")
            _validate_initial_design_content(payload, inputs)
            return payload

        def valid_review(value: object) -> dict[str, Any]:
            return review_response(value)

        def call_valid(operation: str, *arguments: Any, validator: Any) -> dict[str, Any]:
            last_error: ContractError | None = None
            for attempt in range(invalid_limit):
                if attempt:
                    begin = getattr(model, "begin_format_attempt", None)
                    if callable(begin):
                        begin()
                try:
                    return validator(getattr(model, operation)(*arguments))
                except LLMCallError:
                    raise
                except ContractError as exc:
                    last_error = exc
            raise InvalidResponseLimitError(f"initial_design {operation}がinvalid_response_limitまで不正です") from last_error

        def bind_call(input_refs: list[str], target_candidate_id: str | None = None) -> None:
            setter = getattr(model, "set_call_context", None)
            if callable(setter):
                setter(settings_id=inputs["settings"]["settings_id"], input_refs=input_refs, target_candidate_id=target_candidate_id)

        bind_call([input_selection_id])
        content = call_valid("generate", "initial_design", context, validator=valid_candidate)
        review_method = getattr(model, "review", None)
        if not callable(review_method):
            raise ContractError("initial_design確認にはreview可能なStoryModelが必要です")

        initial_design_id = f"initial-design-{reserve_counter(self.workspace_root, 'next_initial_design'):06d}"
        generation_id = f"gen-{reserve_counter(self.workspace_root, 'next_generation'):06d}"
        candidate_id = f"candidate-{reserve_counter(self.workspace_root, 'next_candidate'):06d}"
        adoption_id = f"adoption-{reserve_counter(self.workspace_root, 'next_adoption'):06d}"
        output_selection_id = f"selection-{reserve_counter(self.workspace_root, 'next_selection'):06d}"
        generate_call_id = self._call_id(model, "generate")
        self._write_audit_record("runtime/calls", generate_call_id, {
            "schema_version": 1, "call_id": generate_call_id, "operation": "generate",
            "role": "initial_design", "target_candidate_id": None,
            "input_refs": [input_selection_id], "technical_attempt": 1, "format_attempt": 1,
            "seed": 1, "endpoint": settings.get("endpoint", "injected-model"),
            "model": settings.get("model", "injected-model"), "settings_id": inputs["settings"]["settings_id"],
            "request": json.dumps({"stage": "initial_design", "operation": "generate"}, ensure_ascii=False, sort_keys=True),
            "response": json.dumps(content, ensure_ascii=False, sort_keys=True), "transport": "success",
            "validation": {"result": "valid", "checks": [], "failure_code": None},
        })
        self._write_audit_record("candidates", candidate_id, {
            "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": "initial-design",
            "input_selection_id": input_selection_id, "keywords_id": None,
            "settings_id": inputs["settings"]["settings_id"], "payload": content,
            "parent_candidate_id": None, "review_record_id": None, "call_id": generate_call_id,
            "created_at": updated_at,
        })
        review_ids: list[str] = []
        revision_count = 0
        while True:
            bind_call([input_selection_id, candidate_id], candidate_id)
            from .candidate_stage import CandidateStageRunner
            review = call_valid("review", "initial_design", context, content, validator=lambda value: CandidateStageRunner._review_with_evidence(value, content))
            review_id = f"review-{reserve_counter(self.workspace_root, 'next_review'):06d}"
            review_call_id = self._call_id(model, "review")
            self._write_audit_record("runtime/calls", review_call_id, {
                "schema_version": 1, "call_id": review_call_id, "operation": "review",
                "role": "initial_design", "target_candidate_id": candidate_id,
                "input_refs": [input_selection_id, candidate_id], "technical_attempt": 1, "format_attempt": 1,
                "seed": 1, "endpoint": settings.get("endpoint", "injected-model"),
                "model": settings.get("model", "injected-model"), "settings_id": inputs["settings"]["settings_id"],
                "request": json.dumps({"stage": "initial_design", "operation": "review"}, ensure_ascii=False, sort_keys=True),
                "response": json.dumps(review, ensure_ascii=False, sort_keys=True), "transport": "success",
                "validation": {"result": "valid", "checks": [], "failure_code": None},
            })
            self._write_audit_record("reviews", review_id, {
                "schema_version": 1, "review_id": review_id, "candidate_id": candidate_id,
                "response": review, "call_id": review_call_id, "created_at": updated_at,
            })
            review_ids.append(review_id)
            critical = [issue for issue in review["issues"] if issue.get("severity") == "critical"]
            if not critical or (quality_limit != 0 and revision_count >= quality_limit):
                break
            bind_call([input_selection_id, candidate_id, review_id], candidate_id)
            try:
                revised = call_valid("revise", "initial_design", context, content, review, validator=valid_candidate)
            except InvalidResponseLimitError:
                if quality_limit != 0:
                    raise
                # An unbounded quality loop may retain the last structurally
                # valid candidate when a revision never becomes valid.
                break
            revised_id = f"candidate-{reserve_counter(self.workspace_root, 'next_candidate'):06d}"
            revise_call_id = self._call_id(model, "revise")
            self._write_audit_record("runtime/calls", revise_call_id, {
                "schema_version": 1, "call_id": revise_call_id, "operation": "revise",
                "role": "initial_design", "target_candidate_id": candidate_id,
                "input_refs": [input_selection_id, candidate_id, review_id], "technical_attempt": 1, "format_attempt": 1,
                "seed": 1, "endpoint": settings.get("endpoint", "injected-model"),
                "model": settings.get("model", "injected-model"), "settings_id": inputs["settings"]["settings_id"],
                "request": json.dumps({"stage": "initial_design", "operation": "revise"}, ensure_ascii=False, sort_keys=True),
                "response": json.dumps(revised, ensure_ascii=False, sort_keys=True), "transport": "success",
                "validation": {"result": "valid", "checks": [], "failure_code": None},
            })
            self._write_audit_record("candidates", revised_id, {
                "schema_version": 1, "candidate_id": revised_id, "artifact_kind": "initial-design",
                "input_selection_id": input_selection_id, "keywords_id": None,
                "settings_id": inputs["settings"]["settings_id"], "payload": revised,
                "parent_candidate_id": candidate_id, "review_record_id": review_id, "call_id": revise_call_id,
                "created_at": updated_at,
            })
            content, candidate_id = revised, revised_id
            review_ids = []
            revision_count += 1
        quality_id = f"quality-{reserve_counter(self.workspace_root, 'next_quality'):06d}"
        staging_root = f"runtime/staging/{adoption_id}"
        slots = {
            "request": inputs["request"]["artifact_id"],
            "settings": inputs["settings"]["settings_id"],
            "initial_design": initial_design_id,
            "initial_design_adoption": adoption_id,
            "current_state": generation_id,
        }
        selection = {
            "schema_version": 1,
            "selection_id": output_selection_id,
            "input_selection_id": input_selection_id,
            "slots": slots,
            "created_at": updated_at,
        }
        validate_selection_snapshot(selection)
        records = {
            f"{staging_root}/{initial_design_id}": {
                "schema_version": 1, "artifact_id": initial_design_id,
                "artifact_kind": "initial-design", "input_selection_id": input_selection_id,
                "created_at": updated_at, "content": content,
            },
            f"{staging_root}/{generation_id}": {
                "schema_version": 1, "artifact_id": generation_id,
                "artifact_kind": "generation", "input_selection_id": input_selection_id,
                "created_at": updated_at,
                "content": self._build_initial_state(content),
            },
            f"{staging_root}/{adoption_id}": {
                "schema_version": 1, "adoption_id": adoption_id, "source_kind": "candidate",
                "candidate_id": candidate_id, "quality_id": quality_id,
                "output_content_artifact_ids": [initial_design_id, generation_id],
                "output_selection_id": output_selection_id, "input_selection_id": input_selection_id,
                "created_at": updated_at,
            },
            f"{staging_root}/{output_selection_id}": selection,
        }
        quality = {
            "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
            "review_record_ids": review_ids, "revision_count": revision_count,
            "result": "accepted_with_notice" if critical else "accepted",
            "remaining_major_issues": [
                {"code": "quality.critical", "message": issue["explanation"], "evidence_locations": issue["evidence_locations"]}
                for issue in critical
            ], "created_at": updated_at,
        }
        if critical:
            quality["notice_type"] = "編集"
        self._write_audit_record("quality", quality_id, quality)
        targets = [
            self._target(initial_design_id, "initial-design", staging_root),
            self._target(generation_id, "generation", staging_root),
            self._target(adoption_id, "adoption", staging_root),
            self._target(output_selection_id, "selection", staging_root),
        ]
        for path, record in records.items():
            self._write_staged_record(path, record)
        working = dict(state)
        working["updated_at"] = updated_at
        working["pending_commit"] = {
            "kind": "candidate_adoption", "staging_path": staging_root,
            "input_selection_id": input_selection_id, "output_selection_id": output_selection_id,
            "state_update": {
                "current_selection_id": output_selection_id,
                "current_stage": "series_plan", "current_target": {},
            },
            "targets": targets,
        }
        self.state_store.save(working)
        return recover_pending_commit(self.workspace_root)

    @staticmethod
    def _build_initial_state(content: dict[str, Any]) -> dict[str, Any]:
        """Construct the first current-state payload from adopted design intent."""
        core = content["core"]
        world = content["world"]
        facts: list[dict[str, Any]] = [
            {"fact_id": "fact-000001", "scope": "core", "value": deepcopy(core)},
            {"fact_id": "fact-000002", "scope": "world", "value": deepcopy(world)},
        ]
        cast = content["cast"]
        knowledge_model = content.get("knowledge_model")
        character_knows = knowledge_model.get("character_knows", {}) if isinstance(knowledge_model, dict) else {}
        character_knowledge: dict[str, Any] = {}
        for index, person in enumerate(cast, start=1):
            character_id = f"char-{index:06d}"
            name = person.get("name") if isinstance(person, dict) else None
            public_knowledge = character_knows.get(name, []) if isinstance(character_knows, dict) else []
            if not isinstance(public_knowledge, list):
                public_knowledge = []
            character_knowledge[character_id] = deepcopy(public_knowledge)
            facts.append({
                "fact_id": f"fact-{index + 2:06d}",
                "scope": "character",
                "subject_id": character_id,
                "value": deepcopy(person),
            })

        thread_states: dict[str, Any] = {}
        for index, thread in enumerate(content["unresolved_threads"], start=1):
            thread_id = f"thread-{index:06d}"
            if isinstance(thread, dict):
                description = thread.get("description", "")
                required_for_ending = bool(thread.get("required_for_ending", False))
            else:
                description = str(thread)
                required_for_ending = False
            thread_states[thread_id] = {
                "status": "open",
                "description": description,
                "required_for_ending": required_for_ending,
            }
        return {
            "story_facts": facts,
            "character_knowledge": character_knowledge,
            "reader_disclosures": [],
            "unresolved_thread_states": thread_states,
            "timeline_position": 0,
        }

    def _target(self, artifact_id: str, artifact_kind: str, staging_root: str) -> dict[str, str]:
        final_roots = {
            "initial-design": "design/initial", "generation": "generations",
            "adoption": "runtime/adoptions", "selection": "runtime/selections",
        }
        return {
            "artifact_id": artifact_id, "artifact_kind": artifact_kind,
            "staging_path": f"{staging_root}/{artifact_id}",
            "final_path": f"{final_roots[artifact_kind]}/{artifact_id}", "status": "pending",
        }

    def _write_staged_record(self, relative_directory: str, record: dict[str, Any]) -> None:
        directory = self.workspace_root / relative_directory
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )


    def _call_id(self, model: Any, operation: str) -> str:
        physical_id = getattr(model, "last_call_id", None)
        physical_path = self.workspace_root / "runtime/calls" / str(physical_id) / "record.json"
        if not isinstance(physical_id, str) or not physical_id.startswith("call-") or not physical_path.is_file():
            if not (
                getattr(model, "allow_test_synthetic_calls", False)
                and getattr(model.__class__, "__storycraft_test_double__", False)
                and getattr(model.__class__, "__module__", "").startswith("test")
            ):
                raise ContractError(f"{operation}の物理call recordがmodelから得られません")
            return f"call-{reserve_counter(self.workspace_root, 'next_call'):06d}"
        return physical_id

    def _write_audit_record(self, relative_directory: str, identifier: str, record: dict[str, Any]) -> None:
        directory = self.workspace_root / relative_directory / identifier
        if directory.exists():
            if relative_directory == "runtime/calls" and (directory / "record.json").is_file():
                return
            raise ContractError("不変audit recordを上書きできません")
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
