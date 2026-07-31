"""V2 keyword-bootstrap request-intake adapter.

This is the sole selection-free candidate stage.  It derives its input bundle from
exactly one immutable keywords record and the immutable settings record, then hands
its request/adoption/selection targets to generic recovery.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .artifact_record import validate_record
from .artifact_registry import artifact_directory
from .commit_recovery import recover_pending_commit
from .run_state import RunStateStore
from .selection_snapshot import validate_selection_snapshot
from .series_contracts import ContractError
from .workspace import _validate_request, validate_workspace


def create_request_intake_stage_service(workspace_root: Path) -> "RequestIntakeStageService":
    return RequestIntakeStageService(workspace_root)


class RequestIntakeStageService:
    """Adopt a reviewed request from the immutable keyword bootstrap input."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self, model: Any | None, *, workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        state = self.state_store.load()
        if state["status"] != "running" or state["current_stage"] != "request_intake":
            raise ContractError("現在のrun-stateは実行可能なrequest_intakeではありません")
        # Keep direct service callers recovery-first too; this path is provider-free.
        if state["pending_commit"] is not None:
            return recover_pending_commit(self.workspace_root)
        if model is None:
            raise ContractError("request_intake生成には注入されたmodelが必要です")
        if updated_at is None:
            raise ContractError("request_intakeの確定時刻が必要です")

        keywords_id, keywords = self._sole_input("keywords", "inputs")
        settings_id, settings_record = self._sole_input("settings", "runtime/settings")
        settings = settings_record.get("payload")
        if not isinstance(settings, dict):
            raise ContractError("request_intake settings payloadが不正です")
        context = {"keywords": {"keywords": keywords["keywords"], "language": keywords["language"]}, "settings": settings}

        candidate = self._candidate(model.generate("request_intake", deepcopy(context)))
        candidate_id = self._reserve_directory_id("candidates", "candidate")
        generate_call = self._write_call("generate", None, [keywords_id, settings_id], candidate, settings_id, updated_at)
        self._write_audit("candidates", candidate_id, {
            "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": "request",
            "input_selection_id": None, "keywords_id": keywords_id, "settings_id": settings_id,
            "payload": candidate["payload"], "parent_candidate_id": None,
            "review_record_id": None, "call_id": generate_call, "created_at": updated_at,
        })

        revision_count = 0
        review_ids: list[str] = []
        while True:
            review = self._review(model.review("request_intake", deepcopy(context), deepcopy(candidate)))
            review_id = self._reserve_directory_id("reviews", "review")
            review_call = self._write_call("review", candidate_id, [keywords_id, settings_id, candidate_id], review, settings_id, updated_at)
            self._write_audit("reviews", review_id, {
                "schema_version": 1, "review_id": review_id, "candidate_id": candidate_id,
                "response": review, "call_id": review_call, "created_at": updated_at,
            })
            review_ids.append(review_id)
            critical = [issue for issue in review["issues"] if issue["severity"] == "critical"]
            if not critical:
                break
            if self._quality_limit(settings) != 0 and revision_count >= self._quality_limit(settings):
                break
            revised = self._candidate(model.revise("request_intake", deepcopy(context), deepcopy(candidate), deepcopy(review)))
            revised_id = self._reserve_directory_id("candidates", "candidate")
            revise_call = self._write_call("revise", candidate_id, [keywords_id, settings_id, candidate_id, review_id], revised, settings_id, updated_at)
            self._write_audit("candidates", revised_id, {
                "schema_version": 1, "candidate_id": revised_id, "artifact_kind": "request",
                "input_selection_id": None, "keywords_id": keywords_id, "settings_id": settings_id,
                "payload": revised["payload"], "parent_candidate_id": candidate_id,
                "review_record_id": review_id, "call_id": revise_call, "created_at": updated_at,
            })
            candidate, candidate_id = revised, revised_id
            revision_count += 1

        quality_id = f"quality-{reserve_counter(self.workspace_root, 'next_quality'):06d}"
        quality = {
            "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
            "review_record_ids": review_ids, "revision_count": revision_count,
            "result": "accepted_with_notice" if critical else "accepted",
            "remaining_major_issues": [
                {"code": "quality.critical", "message": issue["explanation"],
                 "evidence_locations": issue["evidence_locations"]} for issue in critical
            ], "created_at": updated_at,
        }
        if critical:
            quality["notice_type"] = "編集"
        self._write_audit("quality", quality_id, quality)
        return self._stage_adoption(state, candidate_id, candidate["payload"], quality_id, settings_id, updated_at)

    def _stage_adoption(
        self, state: dict[str, Any], candidate_id: str, request: dict[str, Any],
        quality_id: str, settings_id: str, updated_at: str,
    ) -> dict[str, Any]:
        request_id = f"request-{reserve_counter(self.workspace_root, 'next_request'):06d}"
        adoption_id = self._reserve_directory_id("runtime/adoptions", "adoption")
        selection_id = f"selection-{reserve_counter(self.workspace_root, 'next_selection'):06d}"
        staging_root = f"runtime/staging/{adoption_id}"
        selection = {
            "schema_version": 1, "selection_id": selection_id, "input_selection_id": None,
            "slots": {"request": request_id, "settings": settings_id}, "created_at": updated_at,
        }
        validate_selection_snapshot(selection)
        request_record = {"schema_version": 1, "artifact_id": request_id, "artifact_kind": "request",
                          "input_selection_id": None, "content": request, "created_at": updated_at}
        adoption = {
            "schema_version": 1, "adoption_id": adoption_id, "source_kind": "candidate",
            "candidate_id": candidate_id, "quality_id": quality_id,
            "output_content_artifact_ids": [request_id], "output_selection_id": selection_id,
            "input_selection_id": None, "created_at": updated_at,
        }
        records = ((request_id, "request", request_record), (adoption_id, "adoption", adoption), (selection_id, "selection", selection))
        targets: list[dict[str, str]] = []
        for artifact_id, kind, record in records:
            staging_path = f"{staging_root}/{artifact_id}"
            self._write_staged(staging_path, record)
            targets.append({"artifact_id": artifact_id, "artifact_kind": kind,
                            "staging_path": staging_path,
                            "final_path": artifact_directory(kind, artifact_id).as_posix(),
                            "status": "pending"})
        working = dict(state)
        working["updated_at"] = updated_at
        working["pending_commit"] = {
            "kind": "candidate_adoption", "staging_path": staging_root,
            "input_selection_id": None, "output_selection_id": selection_id,
            "state_update": {"current_selection_id": selection_id,
                             "current_stage": "initial_design", "current_target": {}},
            "targets": targets,
        }
        self.state_store.save(working)
        return recover_pending_commit(self.workspace_root)

    def _sole_input(self, kind: str, relative_root: str) -> tuple[str, dict[str, Any]]:
        directory = self.workspace_root / relative_root
        entries = sorted(path for path in directory.iterdir() if path.is_dir() and not path.is_symlink())
        if len(entries) != 1:
            raise ContractError(f"request_intakeには一つだけの{kind}入力が必要です")
        artifact_id = entries[0].name
        try:
            value = json.loads((entries[0] / "record.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"request_intakeの{kind}入力を読めません") from exc
        return artifact_id, validate_record(kind, artifact_id, value)

    @staticmethod
    def _candidate(value: object) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != {"schema_version", "artifact_kind", "payload"} or value.get("schema_version") != "candidate-response-v1" or value.get("artifact_kind") != "request" or not isinstance(value.get("payload"), dict):
            raise ContractError("request_intake candidate responseが不正です")
        _validate_request(value["payload"])
        return value

    @staticmethod
    def _review(value: object) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != {"schema_version", "decision", "issues"} or value.get("schema_version") != "review-response-v1" or value.get("decision") not in {"pass", "issues"} or not isinstance(value.get("issues"), list) or (value["decision"] == "pass") != (not value["issues"]):
            raise ContractError("request_intake review responseが不正です")
        for issue in value["issues"]:
            if not isinstance(issue, dict) or set(issue) != {"severity", "evidence_locations", "explanation"} or issue.get("severity") not in {"critical", "notice"} or not isinstance(issue.get("evidence_locations"), list) or not isinstance(issue.get("explanation"), str) or not issue["explanation"]:
                raise ContractError("request_intake review issueが不正です")
        return value

    @staticmethod
    def _quality_limit(settings: dict[str, Any]) -> int:
        value = settings.get("quality_revision_limit")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ContractError("quality_revision_limitが不正です")
        return value

    def _write_call(self, operation: str, target_candidate_id: str | None, input_refs: list[str], response: dict[str, Any], settings_id: str, updated_at: str) -> str:
        call_id = f"call-{reserve_counter(self.workspace_root, 'next_call'):06d}"
        record = {"schema_version": 1, "call_id": call_id, "operation": operation,
                  "role": "request_intake", "target_candidate_id": target_candidate_id,
                  "input_refs": input_refs, "technical_attempt": 1, "format_attempt": 1,
                  "seed": 1, "endpoint": "injected-model", "model": "injected-model",
                  "settings_id": settings_id,
                  "request": json.dumps({"stage": "request_intake", "operation": operation}, sort_keys=True),
                  "response": json.dumps(response, ensure_ascii=False, sort_keys=True),
                  "transport": "success", "validation": {"result": "valid", "checks": [], "failure_code": None}}
        self._write_audit("runtime/calls", call_id, record)
        return call_id

    def _reserve_directory_id(self, relative_root: str, prefix: str) -> str:
        directory = self.workspace_root / relative_root
        highest = 0
        for entry in directory.iterdir():
            if entry.is_dir() and entry.name.startswith(prefix + "-"):
                try:
                    highest = max(highest, int(entry.name.rsplit("-", 1)[1]))
                except ValueError:
                    continue
        return f"{prefix}-{highest + 1:06d}"

    def _write_audit(self, relative_root: str, artifact_id: str, record: dict[str, Any]) -> None:
        self._write_staged(f"{relative_root}/{artifact_id}", record)

    def _write_staged(self, relative_directory: str, record: dict[str, Any]) -> None:
        directory = self.workspace_root / relative_directory
        if directory.exists() or directory.is_symlink():
            raise ContractError("不変recordを上書きできません")
        directory.mkdir(parents=True)
        (directory / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
