"""Provider-free convergence of the closed pending-commit manifest."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .artifact_record import validate_call_record, validate_candidate_record, validate_quality_evidence, validate_record, validate_review_record
from .artifact_registry import ARTIFACT_SPECS, artifact_directory, artifact_spec
from .immutable_directory import finalize_immutable_directory
from .filesystem_security import read_text_nofollow
from .publication_builder import validate_volume_publication_files
from .review_contracts import validate_critique_fields
from .run_state import RunStateStore, target_artifact_kind
from .selection_authority import resolve_selection
from .selection_snapshot import validate_selection_snapshot
from .series_contracts import ContractError
from .state_derivation import apply_continuity_state, build_initial_state
from .time_contract import parse_utc_timestamp


def recover_pending_commit(workspace_root: Path) -> dict[str, Any]:
    """Finalize only declared targets, validate them, then atomically advance state.

    Run-state validation is deliberately the sole manifest-schema authority.  This
    module neither calls a provider nor compares digests: target validity comes from
    each immutable record's closed validator and its declared placement.
    """
    root = workspace_root.expanduser()
    store = RunStateStore(root)
    state = store.load_recovery()
    manifest = state["pending_commit"]
    if not isinstance(manifest, dict):
        raise ContractError("pending_commitがありません")
    input_selection_id = manifest["input_selection_id"]
    if input_selection_id is not None and input_selection_id != state["current_selection_id"]:
        raise ContractError("pending_commit.input_selection_idはrun-state.current_selection_idと一致しなければなりません")
    targets = manifest["targets"]
    assert isinstance(targets, list)
    _reject_unlisted_staging(root, manifest)
    # Preflight every target before moving anything.  Recovery rejection must not
    # mutate pending_commit status or partially finalize the manifest.  This
    # includes final-only crash states and already-finalized targets; validating
    # only staging directories would allow a malformed later final to fail after
    # an earlier target had already been moved.
    for target in targets:
        staging = root / target["staging_path"]
        final = root / target["final_path"]
        _reject_symlinked_path_components(root, staging)
        _reject_symlinked_path_components(root, final)
        validator = _target_validator(root, target, input_selection_id)
        _reject_ambiguous_target(staging, final)
        if target["status"] == "finalized":
            if not final.exists():
                raise ContractError("finalized targetには有効なfinalが必要です")
            validator(final)
        elif final.exists():
            validator(final)
        elif staging.exists():
            validator(staging)
        else:
            raise ContractError("pending targetにはstagingが必要です")
        if target["status"] == "pending" and not final.exists():
            _preflight_finalize_location(staging, final)
    target_paths = _recovery_target_paths(root, targets)
    for target in targets:
        if target_artifact_kind(target) == "scene-commit":
            scene_commit_path = target_paths[("scene-commit", target["artifact_id"])]
            _validate_scene_commit_lineage(
                root,
                _single_record(scene_commit_path),
                manifest["input_selection_id"],
                manifest["output_selection_id"],
                target_paths=target_paths,
            )
    if manifest["kind"] == "candidate_adoption":
        adoption_target = next(target for target in targets if target_artifact_kind(target) == "adoption")
        adoption_path = target_paths[("adoption", adoption_target["artifact_id"])]
        if _single_record(adoption_path).get("source_kind") == "candidate":
            _validate_candidate_adoption_lineage(root, manifest, target_paths=target_paths)
    for target in targets:
        if target_artifact_kind(target) == "selection":
            selection_path = target_paths[("selection", target["artifact_id"])]
            resolve_selection(
                root,
                _single_record(selection_path),
                record_paths=target_paths,
            )
    working = deepcopy(state)
    for index, target in enumerate(targets):
        staging = root / target["staging_path"]
        final = root / target["final_path"]
        _reject_symlinked_path_components(root, staging)
        _reject_symlinked_path_components(root, final)
        validator = _target_validator(root, target, input_selection_id)
        _reject_ambiguous_target(staging, final)
        if target["status"] == "finalized":
            if not final.exists():
                raise ContractError("finalized targetには有効なfinalが必要です")
            validator(final)
        elif target["status"] == "pending":
            if final.exists():
                # Rename can complete before manifest-status persistence.  A valid
                # final-only pending target is therefore a normal crash state.
                validator(final)
            elif not staging.exists():
                raise ContractError("pending targetにはstagingが必要です")
            else:
                finalize_immutable_directory(staging=staging, final=final, validator=validator)
                validator(final)
        else:  # run-state validation makes this unreachable, keep recovery closed.
            raise ContractError("pending_commit target statusが不正です")
        working["pending_commit"]["targets"][index]["status"] = "finalized"
    for target in targets:
        _target_validator(root, target, input_selection_id)(root / target["final_path"])
        if target_artifact_kind(target) == "scene-commit":
            _validate_scene_commit_lineage(root, _single_record(root / target["final_path"]), manifest["input_selection_id"], manifest["output_selection_id"])
    if manifest["kind"] == "candidate_adoption":
        adoption_target = next(target for target in targets if target_artifact_kind(target) == "adoption")
        if _single_record(root / adoption_target["final_path"]).get("source_kind") == "candidate":
            _validate_candidate_adoption_lineage(root, manifest)
    for target in targets:
        if target_artifact_kind(target) == "selection":
            resolve_selection(root, _single_record(root / target["final_path"]))
    result = deepcopy(working)
    result.update(manifest["state_update"])
    result["pending_commit"] = None
    store.save(result)
    return result


def _reject_symlinked_path_components(root: Path, path: Path) -> None:
    """Reject every lexical component from workspace root to a manifest target."""
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ContractError("pending_commit targetがworkspace外を参照します") from exc
    current = root
    if current.is_symlink():
        raise ContractError("pending_commit targetにsymlinkは許可されません")
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ContractError("pending_commit targetにsymlinkは許可されません")


def _reject_unlisted_staging(root: Path, manifest: dict[str, Any]) -> None:
    staging_root = root / manifest["staging_path"]
    if staging_root.is_symlink() or not staging_root.is_dir():
        # A fully finalized manifest need not retain its staging root.
        if all(target["status"] == "finalized" for target in manifest["targets"]):
            return
        raise ContractError("pending_commit staging rootがありません")
    expected = {Path(target["staging_path"]).relative_to(manifest["staging_path"]) for target in manifest["targets"]}
    for path in staging_root.rglob("*"):
        relative = path.relative_to(staging_root)
        if not any(
            relative == target or relative in target.parents or target in relative.parents
            for target in expected
        ):
            raise ContractError("manifest外のstaging配置があります")


def _reject_ambiguous_target(staging: Path, final: Path) -> None:
    if staging.is_symlink() or final.is_symlink():
        raise ContractError("pending_commit targetにsymlinkは許可されません")
    if staging.exists() and final.exists():
        raise ContractError("pending_commit targetのstagingとfinalが同時にあります")


def _recovery_target_paths(root: Path, targets: list[dict[str, Any]]) -> dict[tuple[str, str], Path]:
    """Resolve declared target records before any staging directory is moved."""
    paths: dict[tuple[str, str], Path] = {}
    for target in targets:
        kind = target_artifact_kind(target)
        identifier = target["artifact_id"]
        staging = root / target["staging_path"]
        final = root / target["final_path"]
        paths[(kind, identifier)] = final if final.exists() else staging
    return paths


def _preflight_finalize_location(staging: Path, final: Path) -> None:
    """Check rename prerequisites before any target is finalized."""
    if staging == final:
        raise ContractError("staging directoryとfinal directoryは異なる必要があります")
    final_parent = final.parent
    if final_parent.is_symlink() or not final_parent.is_dir():
        raise ContractError(f"final directoryの親directoryが存在しません: {final_parent}")
    try:
        staging_device = staging.stat(follow_symlinks=False).st_dev
        final_device = final_parent.stat(follow_symlinks=False).st_dev
    except OSError as exc:
        raise ContractError("immutable directoryのfilesystemを確認できません") from exc
    if staging_device != final_device:
        raise ContractError("stagingとfinalは同一filesystem上に存在する必要があります")


def _target_path(
    root: Path,
    target_paths: Mapping[tuple[str, str], Path] | None,
    kind: str,
    identifier: str,
) -> Path:
    if target_paths is not None and (kind, identifier) in target_paths:
        return target_paths[(kind, identifier)]
    return root / artifact_directory(kind, identifier)


def _target_validator(root: Path, target: dict[str, Any], input_selection_id: str | None):
    kind = target_artifact_kind(target)
    artifact_id = target["artifact_id"]
    if kind == "volume-publication":
        def validate_publication(directory: Path) -> None:
            if directory.is_symlink() or not directory.is_dir():
                raise ContractError("volume publication targetがdirectoryではありません")
            if {path.name for path in directory.iterdir()} != {"record.json", "manuscript.md"}:
                raise ContractError("volume publication targetのfile構成が不正です")
            record_path = directory / "record.json"
            manuscript_path = directory / "manuscript.md"
            if any(path.is_symlink() or not path.is_file() for path in (record_path, manuscript_path)):
                raise ContractError("volume publication targetのleaf fileは通常fileでなければなりません")
            try:
                files = {"record.json": json.loads(read_text_nofollow(record_path)), "manuscript.md": read_text_nofollow(manuscript_path)}
            except (OSError, json.JSONDecodeError) as exc:
                raise ContractError("volume publication targetを読めません") from exc
            validate_volume_publication_files(files)
            if files["record.json"]["volume_publication_id"] != artifact_id:
                raise ContractError("volume publication target IDが配置IDと一致しません")
            record_selection_id = files["record.json"].get("input_selection_id")
            if input_selection_id is None or record_selection_id != input_selection_id:
                raise ContractError("volume publication recordのinput_selection_idがmanifestと一致しません")
            _validate_publication_source_evidence(root, files)
        return validate_publication
    # The commit record is not a content envelope, but it uses the shared
    # registry-owned closed-record validator during generic recovery.
    if kind == "scene-commit":
        def validate_scene_commit(directory: Path) -> None:
            validate_record(kind, artifact_id, _single_record(directory))
        return validate_scene_commit
    if kind == "selection":
        def validate_selection(directory: Path) -> None:
            record = _single_record(directory)
            if validate_selection_snapshot(record)["selection_id"] != artifact_id:
                raise ContractError("selection target IDが配置IDと一致しません")
        return validate_selection
    if kind == "adoption":
        def validate_adoption(directory: Path) -> None:
            record = _single_record(directory)
            _validate_adoption(record, artifact_id)
        return validate_adoption
    if kind in ARTIFACT_SPECS:
        def validate_content(directory: Path) -> None:
            record = _single_record(directory)
            validate_record(kind, artifact_id, record)
            if kind == "settings":
                from .workspace import _validate_settings
                _validate_settings(record["payload"])
        return validate_content
    raise ContractError("pending_commit target kindが未定義です")


def _single_record(directory: Path) -> dict[str, Any]:
    if directory.is_symlink() or not directory.is_dir() or {path.name for path in directory.iterdir()} != {"record.json"}:
        raise ContractError("immutable targetのfile構成が不正です")
    record_path = directory / "record.json"
    if record_path.is_symlink() or not record_path.is_file():
        raise ContractError("immutable targetのrecord.jsonが不正です")
    try:
        record = json.loads(read_text_nofollow(record_path))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("immutable targetのrecord.jsonを読めません") from exc
    if not isinstance(record, dict):
        raise ContractError("immutable targetのrecord.jsonはobjectでなければなりません")
    return record


def _validate_scene_commit_lineage(
    root: Path,
    record: dict[str, Any],
    input_selection_id: str,
    output_selection_id: str,
    *,
    target_paths: Mapping[tuple[str, str], Path] | None = None,
) -> None:
    """Require scene-commit references to resolve and remain selection-bound."""
    references = (
        ("scene", "scene_id"),
        ("scene-card", "scene_card_id"),
        ("scene-prose", "scene_prose_id"),
        ("continuity-update", "continuity_update_id"),
        ("generation", "current_state_id"),
        ("quality-disposition", "quality_disposition_id"),
    )
    input_current_state_id: str | None = None
    continuity_record: dict[str, Any] | None = None
    output_generation_record: dict[str, Any] | None = None
    for kind, field in references:
        identifier = record[field]
        directory = _target_path(root, target_paths, kind, identifier)
        referenced = _single_record(directory)
        validate_record(kind, identifier, referenced)
        if kind == "continuity-update":
            continuity_record = referenced
        elif kind == "generation":
            output_generation_record = referenced
        if kind == "scene":
            content = referenced.get("content")
            if not isinstance(content, dict) or not isinstance(content.get("current_state_id"), str):
                raise ContractError("scene-commit sceneの入力current_state参照が不正です")
            expected_scene = {
                "scene_prose_id": record["scene_prose_id"],
                "continuity_update_id": record["continuity_update_id"],
                "scene_card_id": record["scene_card_id"],
                "quality_disposition_id": record["quality_disposition_id"],
                "coordinate": {
                    "volume_number": record["volume_number"],
                    "chapter_number": record["chapter_number"],
                    "scene_number": record["scene_number"],
                },
            }
            if any(content.get(field) != expected for field, expected in expected_scene.items()):
                raise ContractError("scene-commit scene contentとrecordの参照束が一致しません")
            input_current_state_id = content["current_state_id"]
    input_snapshot = _single_record(_target_path(root, target_paths, "selection", input_selection_id))
    input_slots = validate_selection_snapshot(input_snapshot)["slots"]
    output_snapshot = _single_record(_target_path(root, target_paths, "selection", output_selection_id))
    if output_snapshot["input_selection_id"] != input_selection_id:
        raise ContractError("scene-commit output selectionの親selectionがinput selectionと一致しません")
    output_slots = validate_selection_snapshot(output_snapshot)["slots"]
    volume, chapter, scene = (record[key] for key in ("volume_number", "chapter_number", "scene_number"))
    prefix = f"v{volume:02d}.c{chapter:02d}.s{scene:02d}"
    if input_current_state_id is None:
        raise ContractError("scene-commit sceneの入力current_state参照がありません")
    expected_input_slots = {
        f"scene_card.{prefix}": record["scene_card_id"],
        f"scene_prose.{prefix}": record["scene_prose_id"],
        f"continuity_update.{prefix}": record["continuity_update_id"],
        f"scene_prose_disposition.{prefix}": record["quality_disposition_id"],
        f"continuity_disposition.{prefix}": input_slots.get(f"continuity_disposition.{prefix}"),
        "current_state": input_current_state_id,
    }
    for slot, identifier in expected_input_slots.items():
        if slot not in input_slots:
            raise ContractError(f"scene-commit input selectionに必須slotがありません: {slot}")
        if input_slots[slot] != identifier:
            raise ContractError(f"scene-commit input selectionの{slot}が参照と一致しません")
    scene_slot = f"scene.{prefix}"
    output_slot = f"scene_commit.{prefix}"
    if output_slots.get(f"scene.{prefix}") != record["scene_id"]:
        raise ContractError("scene-commit output selectionのscene座標slotが参照と一致しません")
    if output_slots.get("current_state") != record["current_state_id"]:
        raise ContractError("scene-commit output selectionのcurrent_stateが参照と一致しません")
    expected_output_slots = dict(input_slots)
    expected_output_slots[scene_slot] = record["scene_id"]
    expected_output_slots["current_state"] = record["current_state_id"]
    expected_output_slots[output_slot] = record["scene_commit_id"]
    if output_slots != expected_output_slots:
        raise ContractError("scene-commit output selectionのslot deltaが不正です")
    if output_slots.get(output_slot) != record["scene_commit_id"]:
        raise ContractError("scene-commit output selectionの座標slotが参照と一致しません")
    if continuity_record is None or output_generation_record is None:
        raise ContractError("scene-commitのgeneration/continuity参照がありません")
    input_generation = _single_record(_target_path(root, target_paths, "generation", input_current_state_id))
    validate_record("generation", input_current_state_id, input_generation)
    expected_generation = apply_continuity_state(input_generation["content"], continuity_record["content"])
    if output_generation_record.get("input_selection_id") != input_selection_id or output_generation_record.get("content") != expected_generation:
        raise ContractError("scene-commit output generationがinput generationとcontinuity updateから導出した状態と一致しません")


def _validate_publication_source_evidence(root: Path, files: dict[str, Any]) -> None:
    """Rebuild publication inputs from its immutable selection during recovery."""
    record = files["record.json"]
    selection_id = record["input_selection_id"]
    selection = _single_record(root / "runtime" / "selections" / selection_id)
    slots = resolve_selection(root, selection)
    # Keep this check at the recovery boundary: a syntactically valid manuscript
    # must not be enough to publish if its selected scene/quality evidence differs.
    from .volume_publication_stage import VolumePublicationStageService
    sources = VolumePublicationStageService(root)._publication_inputs(slots, record["volume_number"])
    expected_manuscript = "\n\n".join(scene["prose"].strip() for scene in sources["scenes"]) + "\n"
    if sources["has_remaining_major_issues"]:
        expected_manuscript = "編集上の注意があります。\n\n" + expected_manuscript
    if files["manuscript.md"] != expected_manuscript:
        raise ContractError("volume publication manuscriptがselection source evidenceと一致しません")


def _validate_adoption(record: dict[str, Any], artifact_id: str) -> None:
    fields = {"schema_version", "adoption_id", "source_kind", "candidate_id", "quality_id", "output_content_artifact_ids", "output_selection_id", "input_selection_id", "created_at"}
    if set(record) != fields or record["schema_version"] != 1 or record["adoption_id"] != artifact_id:
        raise ContractError("adoption recordが不正です")
    if record["source_kind"] not in {"candidate", "direct_request"} or not isinstance(record["output_content_artifact_ids"], list) or not record["output_content_artifact_ids"]:
        raise ContractError("adoption recordが不正です")
    try:
        artifact_spec("selection").match_id(record["output_selection_id"])
    except ContractError as exc:
        raise ContractError("adoption recordのoutput_selection_idが不正です") from exc
    if record["input_selection_id"] is not None:
        try:
            artifact_spec("selection").match_id(record["input_selection_id"])
        except ContractError as exc:
            raise ContractError("adoption recordのinput_selection_idが不正です") from exc
    if record["source_kind"] == "candidate":
        try:
            artifact_spec("quality-disposition").match_id(record["quality_id"])
        except ContractError as exc:
            raise ContractError("adoption recordのquality_idが不正です") from exc
        if not isinstance(record["candidate_id"], str) or re.fullmatch(r"candidate-[0-9]{6}", record["candidate_id"]) is None:
            raise ContractError("adoption recordのcandidate_idが不正です")
    elif record["candidate_id"] is not None or record["quality_id"] is not None:
        raise ContractError("direct_request adoptionのcandidate/quality参照が不正です")
    parse_utc_timestamp(record["created_at"], "adoption recordのcreated_at")


def _validate_candidate_adoption_lineage(
    root: Path,
    manifest: dict[str, Any],
    *,
    target_paths: Mapping[tuple[str, str], Path] | None = None,
) -> None:
    """Bind a candidate adoption's audit chain and immutable selection delta."""
    targets = manifest["targets"]
    content_targets = [target for target in targets if target_artifact_kind(target) not in {"adoption", "selection"}]
    content_target = next(target for target in content_targets if target_artifact_kind(target) != "generation")
    adoption_target = next(target for target in targets if target_artifact_kind(target) == "adoption")
    selection_target = next(target for target in targets if target_artifact_kind(target) == "selection")
    content = _single_record(_target_path(root, target_paths, target_artifact_kind(content_target), content_target["artifact_id"]))
    adoption = _single_record(_target_path(root, target_paths, "adoption", adoption_target["artifact_id"]))
    selection = _single_record(_target_path(root, target_paths, "selection", selection_target["artifact_id"]))
    _validate_adoption(adoption, adoption_target["artifact_id"])
    if adoption["source_kind"] != "candidate" or adoption["output_content_artifact_ids"] != [target["artifact_id"] for target in content_targets]:
        raise ContractError("candidate adoptionのoutput content参照が不正です")
    if adoption["input_selection_id"] != manifest["input_selection_id"] or adoption["output_selection_id"] != manifest["output_selection_id"]:
        raise ContractError("candidate adoptionのselection参照がmanifestと一致しません")
    candidate_id = adoption["candidate_id"]
    quality_id = adoption["quality_id"]
    if not isinstance(candidate_id, str) or not isinstance(quality_id, str):
        raise ContractError("candidate adoptionのcandidate/quality参照が不正です")
    candidate = _audit_record(root, "candidates", candidate_id)
    quality = _audit_record(root, "quality", quality_id)
    validate_candidate_record(candidate_id, candidate)
    validate_record("quality-disposition", quality_id, quality)
    if candidate.get("input_selection_id") != manifest["input_selection_id"]:
        raise ContractError("candidate adoptionのinput_selection_idがmanifestと一致しません")
    call_id = candidate["call_id"]
    call = _audit_record(root, "runtime/calls", call_id)
    validate_call_record(call_id, call)
    operation = call.get("operation")
    if operation not in {"generate", "revise"}:
        raise ContractError("candidate adoptionのcall operationが不正です")
    if operation == "generate":
        if call.get("target_candidate_id") is not None:
            raise ContractError("candidate adoptionのgenerate call targetが不正です")
    elif candidate.get("parent_candidate_id") is None or call.get("target_candidate_id") != candidate.get("parent_candidate_id"):
        raise ContractError("candidate adoptionのrevise call targetが不正です")
    if call.get("settings_id") != candidate.get("settings_id"):
        raise ContractError("candidate adoptionのcall/settings lineageが不正です")
    if candidate.get("candidate_id") != candidate_id or candidate.get("artifact_kind") != target_artifact_kind(content_target):
        raise ContractError("candidate adoptionのcandidate参照が不正です")
    if candidate.get("payload") != content.get("content"):
        raise ContractError("candidate adoptionのcontentがcandidateと一致しません")
    if target_artifact_kind(content_target) == "initial-design":
        generation_targets = [target for target in content_targets if target_artifact_kind(target) == "generation"]
        if len(generation_targets) != 1:
            raise ContractError("initial-design adoptionのgeneration targetが一意ではありません")
        generation_target = generation_targets[0]
        generation = _single_record(_target_path(root, target_paths, "generation", generation_target["artifact_id"]))
        validate_record("generation", generation_target["artifact_id"], generation)
        if generation.get("input_selection_id") != manifest["input_selection_id"] or generation.get("content") != build_initial_state(content["content"]):
            raise ContractError("initial-design adoptionのgenerationがinitial-designから導出した状態と一致しません")
    if quality["candidate_id"] != candidate_id:
        raise ContractError("candidate adoptionのquality candidate参照が不正です")
    lineage = _candidate_lineage(root, candidate_id)
    if candidate not in lineage:
        raise ContractError("candidate adoptionのcandidate lineageが不正です")
    review_records: dict[str, dict[str, Any]] = {}
    for review_id in quality["review_record_ids"]:
        review = _audit_record(root, "reviews", review_id)
        review_records[review_id] = review
        validate_review_record(review_id, review)
        review_candidate = _audit_record(root, "candidates", review["candidate_id"])
        validate_candidate_record(review["candidate_id"], review_candidate)
        validate_critique_fields(review["response"], review_candidate["payload"])
        review_call_id = review["call_id"]
        review_call = _audit_record(root, "runtime/calls", review_call_id)
        validate_call_record(review_call_id, review_call)
        if review.get("review_id") != review_id or review.get("candidate_id") != candidate_id or review_call.get("operation") != "review" or review_call.get("target_candidate_id") != review.get("candidate_id") or review_call.get("settings_id") != candidate.get("settings_id"):
            raise ContractError("quality dispositionのreview/call参照が不正です")
    validate_quality_evidence(quality, candidate["payload"], review_records)
    _validate_candidate_selection_delta(root, manifest, content_targets, adoption_target, quality_id, selection)


def _audit_record(root: Path, directory: str, identifier: str) -> dict[str, Any]:
    if not isinstance(identifier, str) or Path(identifier).name != identifier or "/" in identifier or "\\" in identifier:
        raise ContractError("audit record IDが不正です")
    return _single_record(root / directory / identifier)


def _candidate_lineage(root: Path, candidate_id: str) -> list[dict[str, Any]]:
    lineage: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_id: str | None = candidate_id
    while current_id is not None:
        if current_id in seen:
            raise ContractError("candidate lineageが循環しています")
        seen.add(current_id)
        current = _audit_record(root, "candidates", current_id)
        if current.get("candidate_id") != current_id:
            raise ContractError("candidate lineageのIDが不正です")
        parent = current.get("parent_candidate_id")
        review_id = current.get("review_record_id")
        if parent is None:
            if review_id is not None:
                raise ContractError("初回candidateのreview参照が不正です")
        elif not isinstance(parent, str) or not isinstance(review_id, str):
            raise ContractError("revision candidateのparent/review参照が不正です")
        else:
            review = _audit_record(root, "reviews", review_id)
            if review.get("review_id") != review_id or review.get("candidate_id") != parent:
                raise ContractError("revision candidateのreview参照が親candidateと一致しません")
        lineage.append(current)
        current_id = parent
    return lineage


def _validate_candidate_selection_delta(root: Path, manifest: dict[str, Any], content_targets: list[dict[str, Any]], adoption_target: dict[str, Any], quality_id: str, selection: dict[str, Any]) -> None:
    validate_selection_snapshot(selection)
    if selection["selection_id"] != manifest["output_selection_id"] or selection["input_selection_id"] != manifest["input_selection_id"]:
        raise ContractError("candidate adoptionのoutput selection参照が不正です")
    input_selection_id = manifest["input_selection_id"]
    if not isinstance(input_selection_id, str):
        return
    input_selection = _audit_record(root, "runtime/selections", input_selection_id)
    validate_selection_snapshot(input_selection)
    expected = dict(input_selection["slots"])
    content_target = next(target for target in content_targets if target_artifact_kind(target) != "generation")
    kind, content_id = target_artifact_kind(content_target), content_target["artifact_id"]
    content_slot = artifact_spec(kind).slot_for(content_id)
    if kind == "scene-prose":
        coordinate = content_slot.split(".", 1)[1]
        stale = {
            f"continuity_update.{coordinate}",
            f"continuity_adoption.{coordinate}",
            f"continuity_disposition.{coordinate}",
        }
        expected = {slot: artifact_id for slot, artifact_id in expected.items() if slot not in stale}
    expected[content_slot] = content_id
    adoption_id = adoption_target["artifact_id"]
    if kind == "initial-design":
        expected["initial_design_adoption"] = adoption_id
        generation = next(target for target in content_targets if target_artifact_kind(target) == "generation")
        expected["current_state"] = generation["artifact_id"]
    elif kind in {"series-plan", "volume-plan", "chapter-plan", "scene-plan"}:
        stem, coordinate = content_slot.split(".", 1) if "." in content_slot else (content_slot, "")
        expected[f"{stem}_adoption" + (f".{coordinate}" if coordinate else "")] = adoption_id
    elif kind in {"scene-card", "scene-prose", "continuity-update"}:
        stem, coordinate = content_slot.split(".", 1)
        adoption_stem = "continuity" if kind == "continuity-update" else stem
        expected[f"{adoption_stem}_adoption.{coordinate}"] = adoption_id
        if kind == "scene-prose":
            expected[f"scene_prose_disposition.{coordinate}"] = quality_id
        elif kind == "continuity-update":
            expected[f"continuity_disposition.{coordinate}"] = quality_id
    if selection["slots"] != expected:
        raise ContractError("candidate adoptionのoutput selection deltaが不正です")


def _validate_scene_commit_record(record: dict[str, Any], artifact_id: str) -> None:
    fields = {"schema_version", "scene_commit_id", "scene_id", "scene_card_id", "scene_prose_id", "continuity_update_id", "current_state_id", "quality_disposition_id", "volume_number", "chapter_number", "scene_number", "created_at"}
    if set(record) != fields or record["schema_version"] != 1 or record["scene_commit_id"] != artifact_id:
        raise ContractError("scene_commit recordが不正です")
    commit = artifact_spec("scene-commit").match_id(artifact_id)
    coordinate = {"volume": record["volume_number"], "chapter": record["chapter_number"], "scene": record["scene_number"]}
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in coordinate.values()):
        raise ContractError("scene_commit recordが不正です")
    if {name: int(commit.group(name)) for name in coordinate} != coordinate:
        raise ContractError("scene_commit recordの座標がIDと一致しません")
    for kind, field in (("scene", "scene_id"), ("scene-card", "scene_card_id"), ("scene-prose", "scene_prose_id"), ("continuity-update", "continuity_update_id")):
        match = artifact_spec(kind).match_id(record[field])
        if {name: int(match.group(name)) for name in coordinate} != coordinate:
            raise ContractError("scene_commit recordの参照座標が一致しません")
    artifact_spec("generation").match_id(record["current_state_id"])
    artifact_spec("quality-disposition").match_id(record["quality_disposition_id"])
    parse_utc_timestamp(record["created_at"], "scene_commit recordのcreated_at")
