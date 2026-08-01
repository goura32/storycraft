"""新規 v2 workspace の初期化・静的検証。"""
from __future__ import annotations

import json
import ipaddress
import math
import os
from pathlib import Path
import socket
import tempfile
from typing import Any, Optional
from urllib.parse import urlsplit

from .artifact_ids import initial_counters
from .artifact_record import validate_call_record, validate_candidate_record, validate_record, validate_review_record
from .artifact_registry import ARTIFACT_SPECS
from .publication_builder import validate_volume_publication_files
from .run_state import RunStateStore
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore, validate_selection_snapshot
from .series_contracts import ContractError


_V2_DIRECTORIES = (
    "inputs", "quality", "candidates", "reviews", "runtime", "runtime/settings",
    "runtime/staging", "runtime/selections", "runtime/calls", "runtime/validations",
    "runtime/adoptions", "design", "design/initial", "design/series-plans",
    "design/volume-plans", "design/chapter-plans", "design/scene-plans", "generations",
    "scenes", "publications",
)


def create_workspace(
    workspace_root: Path,
    *,
    workspace_id: str,
    request: Optional[dict[str, Any]],
    settings: dict[str, Any],
    created_at: str,
    keywords: Optional[dict[str, Any]] = None,
) -> Path:
    """既存worktreeを触らず、新形式だけを持つ作業場所を作る。"""
    root = workspace_root.expanduser()
    if root.exists() or root.is_symlink():
        raise ContractError("workspaceが既に存在します")
    if (request is None) == (keywords is None):
        raise ContractError("requestまたはkeywordsの一方だけが必要です")
    if request is not None and not isinstance(request, dict):
        raise ContractError("requestはobjectでなければなりません")
    if keywords is not None and not isinstance(keywords, dict):
        raise ContractError("keywordsはobjectでなければなりません")
    if request is not None:
        _validate_request(request)
    if keywords is not None:
        _validate_keywords(keywords)
    _validate_settings(settings)
    if not isinstance(workspace_id, str) or not workspace_id.startswith("ws-"):
        raise ContractError("workspace_idが不正です")
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.v2-", dir=root.parent))
    try:
        for relative in _V2_DIRECTORIES:
            (staging / relative).mkdir(parents=True, exist_ok=True)
        (staging / "design/scene-cards").mkdir(parents=True, exist_ok=True)
        settings_id = "settings-000001"
        _write_json(staging / "runtime/settings" / settings_id / "record.json", {
            "schema_version": 1,
            "settings_id": settings_id,
            "payload": settings,
            "created_at": created_at,
        })
        counters = initial_counters()
        counters["next_settings"] = 2
        if request is not None:
            request_id = "request-000001"
            _write_json(staging / "inputs" / request_id / "record.json", {
                "schema_version": 1,
                "artifact_id": request_id,
                "artifact_kind": "request",
                "input_selection_id": None,
                "content": request,
                "created_at": created_at,
            })
            counters["next_request"] = 2
            _write_json(staging / "runtime/counters.json", counters)
            selection = SelectionSnapshotStore(staging).create(slots={
                "request": request_id,
                "settings": settings_id,
            }, created_at=created_at)
            stage, selection_id = "initial_design", selection["selection_id"]
        else:
            assert keywords is not None
            keywords_id = "keywords-000001"
            _write_json(staging / "inputs" / keywords_id / "record.json", {
                "schema_version": 1,
                "keywords_id": keywords_id,
                **keywords,
                "created_at": created_at,
            })
            counters["next_keywords"] = 2
            _write_json(staging / "runtime/counters.json", counters)
            stage, selection_id = "request_intake", None
        state = {
            "schema_version": 3,  # V1 の schema_version に合わせる
            "workspace_id": workspace_id,
            # v1 では run_id と stop_reason は保存しない
            "status": "running",
            "last_error": None,
            "current_stage": stage,
            "current_target": {},
            "current_selection_id": selection_id,
            "pending_commit": None,
            "published_volumes": [],
            "created_at": created_at,
            "updated_at": created_at,
        }
        RunStateStore(staging).save(state)
        (staging / "runtime/lock").touch(exist_ok=False)
        validate_workspace(staging)
        os.rename(staging, root)
        return root
    except Exception:
        # staging はこの関数だけが作った未公開領域。失敗時に残さない。
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
        raise


def validate_workspace(workspace_root: Path) -> None:
    """providerを初期化せず、新形式の正本・参照を静的に検証する。"""
    root = workspace_root.expanduser()
    if not root.is_dir() or root.is_symlink():
        raise ContractError("v2 workspace directoryが存在しません")
    for relative in _V2_DIRECTORIES:
        if not (root / relative).is_dir() or (root / relative).is_symlink():
            raise ContractError(f"v2 workspace必須directoryがありません: {relative}")
    state = RunStateStore(root).load()
    selection_id = state["current_selection_id"]
    if selection_id is None:
        if state["current_stage"] != "request_intake":
            raise ContractError("selectionなしのstageが不正です")
        resolved: dict[str, dict[str, Any]] = {}
    else:
        assert isinstance(selection_id, str)
        snapshot = SelectionSnapshotStore(root).load(selection_id)
        resolved = resolve_selection(root, snapshot)
    _validate_persisted_records(root)
    if selection_id is not None:
        _validate_selection_ancestry(root, selection_id)
    _validate_published_publications(root, state, resolved)


def _validate_selection_ancestry(root: Path, selection_id: str) -> None:
    """Validate the current selection and every immutable parent snapshot."""
    store = SelectionSnapshotStore(root)
    seen: set[str] = set()
    current_id: str | None = selection_id
    while current_id is not None:
        if current_id in seen:
            raise ContractError("ancestor selection chainが循環しています")
        seen.add(current_id)
        try:
            snapshot = store.load(current_id)
            resolve_selection(root, snapshot)
        except ContractError as exc:
            raise ContractError("ancestor selectionが不正です") from exc
        current_id = snapshot["input_selection_id"]


def _validate_persisted_records(root: Path) -> None:
    """Validate every immutable/audit record, then bind its references by ID."""
    records: dict[str, dict[str, Any]] = {}
    special = {"adoption", "selection", "volume-publication", "quality-disposition"}
    roots = {spec.directory_root for kind, spec in ARTIFACT_SPECS.items() if kind not in special}
    for relative in sorted(roots):
        for identifier, record in _records(root / relative, "artifact record"):
            kind = record.get("artifact_kind") if isinstance(record.get("artifact_kind"), str) else next((name for name, spec in ARTIFACT_SPECS.items() if name not in special and spec.directory_root == relative and _matches_identifier(name, identifier)), None)
            if not isinstance(kind, str) or kind not in ARTIFACT_SPECS or kind in special or ARTIFACT_SPECS[kind].directory_root != relative:
                raise ContractError("artifact recordのkindまたは配置が不正です")
            validate_record(kind, identifier, record)
            records[identifier] = record
    selections = dict(_records(root / "runtime/selections", "selection record"))
    for identifier, record in selections.items():
        if validate_selection_snapshot(record)["selection_id"] != identifier:
            raise ContractError("selection recordのIDが配置IDと一致しません")
        resolve_selection(root, record)
    candidates = dict(_records(root / "candidates", "candidate record"))
    reviews = dict(_records(root / "reviews", "review record"))
    qualities = dict(_records(root / "quality", "quality record"))
    adoptions = dict(_records(root / "runtime/adoptions", "adoption record"))
    calls = dict(_records(root / "runtime/calls", "call record"))
    for identifier, record in candidates.items(): validate_candidate_record(identifier, record)
    for identifier, record in reviews.items(): validate_review_record(identifier, record)
    for identifier, record in qualities.items(): validate_record("quality-disposition", identifier, record)
    for identifier, record in adoptions.items(): validate_record("adoption", identifier, record)
    for identifier, record in calls.items(): validate_call_record(identifier, record)
    known = set(records) | set(selections) | set(candidates) | set(reviews) | set(qualities) | set(adoptions) | set(calls)
    for identifier, record in calls.items():
        _require_references(record["input_refs"], known, f"call {identifier} input_refs")
        _require_reference(record["settings_id"], records, f"call {identifier} settings_id")
        target = record["target_candidate_id"]
        if target is not None: _require_reference(target, candidates, f"call {identifier} target_candidate_id")
    for identifier, record in candidates.items():
        _require_reference(record["settings_id"], records, f"candidate {identifier} settings_id")
        call = _reference(record["call_id"], calls, f"candidate {identifier} call_id")
        operation = call["operation"]
        if operation not in {"generate", "revise"}:
            raise ContractError(f"candidate {identifier} call operationが不正です")
        if operation == "generate":
            if call["target_candidate_id"] is not None:
                raise ContractError(f"candidate {identifier} generate callのtargetが不正です")
        else:
            if record["parent_candidate_id"] is None or call["target_candidate_id"] != record["parent_candidate_id"]:
                raise ContractError(f"candidate {identifier} revise callのtargetが親candidateと一致しません")
            if record["review_record_id"] not in call["input_refs"]:
                raise ContractError(f"candidate {identifier} revise callがreviewを入力参照していません")
        if call["settings_id"] != record["settings_id"]:
            raise ContractError(f"candidate {identifier} call settings_idがcandidateと一致しません")
        if record["input_selection_id"] is not None:
            selection = _reference(record["input_selection_id"], selections, f"candidate {identifier} input_selection_id")
            if selection["slots"].get("settings") != record["settings_id"]:
                raise ContractError(f"candidate {identifier} input selectionのsettingsが一致しません")
        if record["input_selection_id"] is not None: _require_reference(record["input_selection_id"], selections, f"candidate {identifier} input_selection_id")
        if record["keywords_id"] is not None: _require_reference(record["keywords_id"], records, f"candidate {identifier} keywords_id")
        for expected in (record["input_selection_id"], record["keywords_id"], record["parent_candidate_id"]):
            if expected is not None and expected not in call["input_refs"]:
                raise ContractError(f"candidate {identifier} callが宣言入力を参照していません")
        if record["parent_candidate_id"] is not None:
            _require_reference(record["parent_candidate_id"], candidates, f"candidate {identifier} parent_candidate_id")
            review = _reference(record["review_record_id"], reviews, f"candidate {identifier} review_record_id")
            if review["candidate_id"] != record["parent_candidate_id"]:
                raise ContractError("candidate revision reviewが親candidateを参照しません")
    for identifier, record in reviews.items():
        candidate = _reference(record["candidate_id"], candidates, f"review {identifier} candidate_id")
        call = _reference(record["call_id"], calls, f"review {identifier} call_id")
        if call["settings_id"] != candidate["settings_id"]:
            raise ContractError(f"review {identifier} call settings_idがcandidateと一致しません")
        if call["operation"] != "review" or call["target_candidate_id"] != record["candidate_id"] or record["candidate_id"] not in call["input_refs"]:
            raise ContractError(f"review {identifier} call provenanceが不正です")
    for identifier, record in qualities.items():
        _require_reference(record["candidate_id"], candidates, f"quality {identifier} candidate_id")
        _require_references(record["review_record_ids"], reviews, f"quality {identifier} review_record_ids")
        for review_id in record["review_record_ids"]:
            if reviews[review_id]["candidate_id"] != record["candidate_id"]:
                raise ContractError("quality reviewがquality candidateを参照しません")
    for identifier, record in adoptions.items():
        _require_reference(record["output_selection_id"], selections, f"adoption {identifier} output_selection_id")
        output_selection = _reference(record["output_selection_id"], selections, f"adoption {identifier} output_selection_id")
        if record["input_selection_id"] is not None: _require_reference(record["input_selection_id"], selections, f"adoption {identifier} input_selection_id")
        _require_references(record["output_content_artifact_ids"], records, f"adoption {identifier} output content")
        if record["source_kind"] == "candidate":
            candidate = _reference(record["candidate_id"], candidates, f"adoption {identifier} candidate_id")
            quality = _reference(record["quality_id"], qualities, f"adoption {identifier} quality_id")
            if quality["candidate_id"] != candidate["candidate_id"]:
                raise ContractError("adoptionのcandidate/quality参照が一致しません")
            candidate_kind = candidate["artifact_kind"]
            output_ids = record["output_content_artifact_ids"]
            allowed_kinds = {candidate_kind, "generation"} if candidate_kind == "initial-design" else {candidate_kind}
            if any(records[artifact_id].get("artifact_kind") not in allowed_kinds or artifact_id not in output_selection["slots"].values() for artifact_id in output_ids):
                raise ContractError(f"adoption {identifier}の出力content参照がoutput selectionと一致しません")
            matching = [records[artifact_id] for artifact_id in output_ids if records[artifact_id].get("artifact_kind") == candidate_kind]
            if not matching or any(item.get("content") != candidate["payload"] for item in matching):
                raise ContractError(f"adoption {identifier}の出力内容がcandidate payloadと一致しません")
            from .commit_recovery import _validate_candidate_selection_delta
            _validate_candidate_selection_delta(
                root,
                {"input_selection_id": record["input_selection_id"], "output_selection_id": record["output_selection_id"]},
                [{"artifact_kind": records[item]["artifact_kind"], "artifact_id": item} for item in output_ids],
                {"artifact_id": identifier}, quality["quality_id"], output_selection,
            )
        elif record["source_kind"] == "direct_request":
            if record["candidate_id"] is not None or record["quality_id"] is not None:
                raise ContractError("direct_request adoptionにcandidate/quality参照があります")
            output_ids = record["output_content_artifact_ids"]
            if len(output_ids) != 1:
                raise ContractError(f"direct_request adoption {identifier}の出力content数が不正です")
            output_slots = output_selection["slots"]
            output_record = records[output_ids[0]]
            output_kind = output_record.get("artifact_kind")
            if output_kind not in {"request", "initial-design"} or output_ids[0] not in output_slots.values():
                raise ContractError(f"direct_request adoption {identifier}の出力content参照がoutput selectionと一致しません")

    scene_commits = {
        identifier: record
        for identifier, record in _records(root / ARTIFACT_SPECS["scene-commit"].directory_root, "scene-commit record")
        if _matches_identifier("scene-commit", identifier)
    }
    for identifier, record in scene_commits.items():
        validate_record("scene-commit", identifier, record)
        for field, kind in (("scene_id", "scene"), ("scene_card_id", "scene-card"), ("scene_prose_id", "scene-prose"), ("continuity_update_id", "continuity-update"), ("current_state_id", "generation"), ("quality_disposition_id", "quality-disposition")):
            ref = record[field]
            if kind == "quality-disposition":
                _require_reference(ref, qualities, f"scene-commit {identifier} {field}")
            else:
                _require_reference(ref, records, f"scene-commit {identifier} {field}")



def _records(directory: Path, label: str) -> list[tuple[str, dict[str, Any]]]:
    result: list[tuple[str, dict[str, Any]]] = []
    if directory.is_symlink():
        raise ContractError(f"{label}の配置が不正です")
    if not directory.exists():
        return result
    for child in sorted(directory.iterdir(), key=lambda path: path.name):
        if child.is_symlink() or not child.is_dir() or {path.name for path in child.iterdir()} != {"record.json"}:
            raise ContractError(f"{label}の配置が不正です")
        path = child / "record.json"
        if path.is_symlink() or not path.is_file():
            raise ContractError(f"{label}の配置が不正です")
        try: value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise ContractError(f"{label}を読めません") from exc
        if not isinstance(value, dict): raise ContractError(f"{label}はobjectでなければなりません")
        result.append((child.name, value))
    return result


def _matches_identifier(kind: str, identifier: str) -> bool:
    try:
        ARTIFACT_SPECS[kind].match_id(identifier)
    except ContractError:
        return False
    return True


def _reference(identifier: object, mapping: dict[str, dict[str, Any]], label: str) -> dict[str, Any]:
    if not isinstance(identifier, str) or identifier not in mapping: raise ContractError(f"{label}の参照先がありません")
    return mapping[identifier]


def _require_reference(identifier: object, mapping: dict[str, dict[str, Any]], label: str) -> None:
    _reference(identifier, mapping, label)


def _require_references(identifiers: object, mapping: dict[str, dict[str, Any]] | set[str], label: str) -> None:
    if not isinstance(identifiers, list) or any(not isinstance(identifier, str) or identifier not in mapping for identifier in identifiers):
        raise ContractError(f"{label}の参照先がありません")


def _validate_published_publications(root: Path, state: dict[str, Any], resolved: dict[str, dict[str, Any]]) -> None:
    """Validate every publication declared by run-state, including active runs."""
    entries = state["published_volumes"]
    assert isinstance(entries, list)
    expected = {entry["publication_id"] for entry in entries}
    actual = {child.name for child in root.joinpath("publications").iterdir() if child.is_dir() and not child.is_symlink()}
    if actual != expected:
        raise ContractError("published_volumesと公開record集合が一致しません")
    if state["status"] == "completed":
        series = resolved.get("series_plan")
        volumes = series.get("content", {}).get("volumes") if isinstance(series, dict) and isinstance(series.get("content"), dict) else None
        if not isinstance(volumes, list) or [item.get("volume_number") if isinstance(item, dict) else None for item in volumes] != list(range(1, len(volumes) + 1)) or len(entries) != len(volumes):
            raise ContractError("completedのpublished_volumesとseries plan巻数が一致しません")
    for entry in entries:
        directory = root / "publications" / entry["publication_id"]
        if directory.is_symlink() or not directory.is_dir() or {path.name for path in directory.iterdir()} != {"record.json", "manuscript.md"}:
            raise ContractError("published publicationファイル構成が不正です")
        try: files = {"record.json": json.loads((directory / "record.json").read_text(encoding="utf-8")), "manuscript.md": (directory / "manuscript.md").read_text(encoding="utf-8")}
        except (OSError, json.JSONDecodeError) as exc: raise ContractError("published publicationを読めません") from exc
        validate_volume_publication_files(files)
        from .commit_recovery import _validate_publication_source_evidence
        _validate_publication_source_evidence(root, files)
        record = files["record.json"]
        if record["volume_publication_id"] != entry["publication_id"] or record["volume_number"] != entry["volume_number"]:
            raise ContractError("published_volumesがpublication recordと一致しません")


def _validate_request(value: Optional[dict[str, Any]]) -> None:
    if value is None:
        return
    fields = {"title", "genre", "premise", "required_elements", "forbidden_elements", "ending_preference", "volume_count", "language"}
    if set(value) != fields or value.get("language") != "ja":
        raise ContractError("request schemaが不正です")
    for key in ("title", "genre", "premise", "ending_preference"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ContractError(f"request {key}が不正です")
    for key in ("required_elements", "forbidden_elements"):
        item = value.get(key)
        if not isinstance(item, list) or any(not isinstance(x, str) or not x.strip() for x in item) or len(item) != len(set(item)):
            raise ContractError(f"request {key}が不正です")
    count = value.get("volume_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= 10:
        raise ContractError("request volume_countが不正です")


def _validate_keywords(value: Optional[dict[str, Any]]) -> None:
    if value is None:
        return
    if set(value) != {"keywords", "language"} or value.get("language") != "ja":
        raise ContractError("keywords schemaが不正です")
    words = value.get("keywords")
    if not isinstance(words, list) or not 1 <= len(words) <= 12 or any(not isinstance(x, str) or not 1 <= len(x.strip()) <= 80 for x in words) or len(words) != len(set(words)):
        raise ContractError("keywordsが不正です")


def _validate_settings(value: object) -> None:
    required_fields = {"provider", "endpoint", "model", "technical_retry_limit", "quality_revision_limit", "invalid_response_limit",
              "chapter_per_volume_range", "chapter_scene_range", "scene_text_char_range"}
    optional_fields = {"request_options"}
    if not isinstance(value, dict):
        raise ContractError("settings schemaが不正です")
    missing = required_fields - set(value.keys())
    if missing:
        raise ContractError(f"#/config/{sorted(missing)[0]}: 必須フィールドがありません")
    unknown = set(value) - required_fields - optional_fields
    if unknown:
        raise ContractError(f"#/config/{sorted(unknown)[0]}: 未知項目です")
    if value.get("provider") != "ollama":
        raise ContractError("#/config/provider: 'ollama'でなければなりません")
    _validate_endpoint(value.get("endpoint"))
    if not isinstance(value.get("model"), str) or not value["model"]:
        raise ContractError("#/config/model: 空でない文字列が必要です")
    for key, minimum in (("technical_retry_limit", 1), ("quality_revision_limit", 0), ("invalid_response_limit", 1)):
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < minimum:
            raise ContractError(f"#/config/{key}: 不正です")
    for key in ("chapter_per_volume_range", "chapter_scene_range", "scene_text_char_range"):
        pair = value.get(key)
        if not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(x, int) or isinstance(x, bool) or x < 1 for x in pair) or pair[0] > pair[1]:
            raise ContractError(f"#/config/{key}: 1以上の昇順整数ペアが必要です")
    _validate_request_options(value.get("request_options"))


def _validate_endpoint(endpoint: object) -> None:
    if not isinstance(endpoint, str):
        raise ContractError("#/config/endpoint: LANまたはloopbackのHTTP URLが必要です")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise ContractError("#/config/endpoint: 不正なHTTP URLです") from exc
    if (
        parsed.scheme != "http"
        or not parsed.hostname
        or (port is None and parsed.netloc.endswith(":"))
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ContractError("#/config/endpoint: userinfo、query、fragmentなしのLANまたはloopback HTTP URLが必要です")
    host = parsed.hostname
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(entry[4][0])
                for entry in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError) as exc:
            raise ContractError("#/config/endpoint: hostを解決できません") from exc
    if not addresses or any(not (address.is_loopback or _is_private_lan_address(address)) for address in addresses):
        raise ContractError("#/config/endpoint: loopbackまたはプライベートLANのhostだけが許可されます")


def _is_private_lan_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if address.version == 4:
        return any(address in network for network in (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
        ))
    return address in ipaddress.ip_network("fc00::/7")


def _validate_request_options(options: object) -> None:
    if options is None:
        return
    if not isinstance(options, dict):
        raise ContractError("#/config/request_options: objectが必要です")
    allowed = {"temperature", "top_p", "top_k", "repeat_penalty"}
    unknown = set(options) - allowed
    if unknown:
        raise ContractError(f"#/config/request_options/{sorted(unknown)[0]}: 未知または禁止されたoptionです")
    for key, lower, upper, exclusive_lower in (("temperature", 0, 2, False), ("top_p", 0, 1, True), ("repeat_penalty", 0, None, True)):
        if key not in options:
            continue
        item = options[key]
        if (
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(item)
            or (item <= lower if exclusive_lower else item < lower)
            or (upper is not None and item > upper)
        ):
            raise ContractError(f"#/config/request_options/{key}: 範囲外です")
    top_k = options.get("top_k")
    if top_k is not None and (not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1):
        raise ContractError("#/config/request_options/top_k: 1以上の整数が必要です")
    # Reject think/streaming/num_ctx as they are controlled by the provider boundary
    for forbidden in ("think", "stream", "num_ctx"):
        if forbidden in options:
            raise ContractError(f"#/config/request_options/{forbidden}: このオプションは指定できません（プロバイダ境界で制御）")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")