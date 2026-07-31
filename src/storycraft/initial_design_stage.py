"""V2 initial-design adapter: selection input, immutable adoption, generic recovery."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .commit_recovery import recover_pending_commit
from .llm_responses import review_response
from .run_state import RunStateStore
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore, validate_selection_snapshot
from .series_contracts import ContractError
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
        content = model.generate("initial_design", context)
        if not isinstance(content, dict):
            raise ContractError("initial_designモデル出力はobjectでなければなりません")
        review_method = getattr(model, "review", None)
        if not callable(review_method):
            raise ContractError("initial_design確認にはreview可能なStoryModelが必要です")
        review = review_response(review_method("initial_design", context, content))

        initial_design_id = f"initial-design-{reserve_counter(self.workspace_root, 'next_initial_design'):06d}"
        generation_id = f"gen-{reserve_counter(self.workspace_root, 'next_generation'):06d}"
        candidate_id = f"candidate-{reserve_counter(self.workspace_root, 'next_candidate'):06d}"
        review_id = f"review-{reserve_counter(self.workspace_root, 'next_review'):06d}"
        quality_id = f"quality-{reserve_counter(self.workspace_root, 'next_quality'):06d}"
        adoption_id = f"adoption-{reserve_counter(self.workspace_root, 'next_adoption'):06d}"
        output_selection_id = f"selection-{reserve_counter(self.workspace_root, 'next_selection'):06d}"
        generate_call_id = f"call-{reserve_counter(self.workspace_root, 'next_call'):06d}"
        review_call_id = f"call-{reserve_counter(self.workspace_root, 'next_call'):06d}"
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
                "content": {
                    "story_facts": [],
                    "character_knowledge": {},
                    "reader_disclosures": "",
                    "unresolved_thread_states": {},
                    "timeline_position": 0
                },
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
        critical = [issue for issue in review["issues"] if issue.get("severity") == "critical"]
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
        quality = {
            "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
            "review_record_ids": [review_id], "revision_count": 0,
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


    def _write_audit_record(self, relative_directory: str, identifier: str, record: dict[str, Any]) -> None:
        directory = self.workspace_root / relative_directory / identifier
        if directory.exists():
            raise ContractError("不変audit recordを上書きできません")
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
