"""Storycraft Version 1の決定的Publication構築。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .series_contracts import ContractError


_PUBLICATION_ID = re.compile(r"^pub-[0-9]{6}$")
_GENERATION_ID = re.compile(r"^gen-[0-9]{6}$")
_COMPLETION_ID = re.compile(r"^completion-[0-9]{6}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_SCENE_SEPARATOR = "* * *"

_FORBIDDEN_CONTROL = re.compile(
    r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]"
)
_MARKDOWN_HEADING = re.compile(
    r"^#{1,6}(?:[ \t]|$)"
)

_METADATA_FIELDS = {
    "schema_version",
    "publication_id",
    "title",
    "language",
    "volume_count",
    "volume_entries",
    "basis_generation_id",
    "completion_id",
    "completion_status",
    "series_character_count",
    "series_sha256",
    "created_at",
}

_VOLUME_ENTRY_FIELDS = {
    "volume_number",
    "title",
    "chapter_count",
    "scene_count",
    "output_name",
    "character_count",
    "sha256",
}

_VOLUME_FIELDS = {
    "volume_number",
    "title",
    "chapters",
}

_CHAPTER_FIELDS = {
    "chapter_number",
    "title",
    "scenes",
}

_SCENE_FIELDS = {
    "scene_number",
    "prose",
}

_PUBLISHABLE_COMPLETION_STATUSES = {
    "complete",
    "complete_with_issues",
}


def build_publication_files(
    *,
    publication_id: str,
    title: str,
    language: str,
    basis_generation_id: str,
    completion: dict[str, Any],
    volumes: list[dict[str, Any]],
    created_at: str,
) -> dict[str, dict[str, Any] | str]:
    """採用済み本文からPublication file一式を決定的に構築する。"""
    _validate_identifier(
        publication_id,
        _PUBLICATION_ID,
        "Publication ID",
    )
    normalized_title = _required_heading_text(
        title,
        "Publication title",
    )
    normalized_language = _required_text(
        language,
        "Publication language",
    )
    _validate_identifier(
        basis_generation_id,
        _GENERATION_ID,
        "Publication basis Generation ID",
    )
    _validate_timestamp(
        created_at,
        "Publication created_at",
    )
    _validate_completion(
        completion,
        basis_generation_id=basis_generation_id,
    )
    normalized_volumes = _validate_volumes(volumes)

    volume_files: dict[str, str] = {}
    volume_entries: list[dict[str, Any]] = []

    for volume in normalized_volumes:
        volume_number = volume["volume_number"]
        output_name = f"v{volume_number:02d}.md"
        markdown = _build_volume_markdown(
            normalized_title,
            volume,
        )

        volume_files[output_name] = markdown
        volume_entries.append({
            "volume_number": volume_number,
            "title": volume["title"],
            "chapter_count": len(volume["chapters"]),
            "scene_count": sum(
                len(chapter["scenes"])
                for chapter in volume["chapters"]
            ),
            "output_name": output_name,
            "character_count": len(markdown),
            "sha256": _sha256_text(markdown),
        })

    series_markdown = _build_series_markdown(
        normalized_title,
        [
            volume_files[
                f"v{volume_number:02d}.md"
            ]
            for volume_number in range(
                1,
                len(normalized_volumes) + 1,
            )
        ],
    )

    metadata = {
        "schema_version": 1,
        "publication_id": publication_id,
        "title": normalized_title,
        "language": normalized_language,
        "volume_count": len(normalized_volumes),
        "volume_entries": volume_entries,
        "basis_generation_id": basis_generation_id,
        "completion_id": completion["completion_id"],
        "completion_status": completion["status"],
        "series_character_count": len(
            series_markdown
        ),
        "series_sha256": _sha256_text(
            series_markdown
        ),
        "created_at": created_at,
    }

    files: dict[str, dict[str, Any] | str] = {
        "metadata.json": metadata,
        "completion.json": deepcopy(completion),
        "series.md": series_markdown,
        **volume_files,
    }
    validate_publication_files(files)
    return files


def validate_publication_files(
    files: dict[str, dict[str, Any] | str],
) -> None:
    """Publication file集合の内部整合性を検証する。"""
    if not isinstance(files, dict):
        raise ContractError(
            "Publication filesはobjectでなければなりません"
        )

    metadata = files.get("metadata.json")
    completion = files.get("completion.json")
    series_markdown = files.get("series.md")

    if not isinstance(metadata, dict):
        raise ContractError(
            "Publication metadata.jsonがありません"
        )
    if not isinstance(completion, dict):
        raise ContractError(
            "Publication completion.jsonがありません"
        )
    if not isinstance(series_markdown, str):
        raise ContractError(
            "Publication series.mdがありません"
        )

    if set(metadata) != _METADATA_FIELDS:
        raise ContractError(
            "Publication Metadataのfield構成が不正です"
        )
    if metadata["schema_version"] != 1:
        raise ContractError(
            "Publication Metadata schema_versionが不正です"
        )

    publication_id = metadata["publication_id"]
    title = _required_heading_text(
        metadata["title"],
        "Publication title",
    )
    _required_text(
        metadata["language"],
        "Publication language",
    )
    _validate_identifier(
        publication_id,
        _PUBLICATION_ID,
        "Publication ID",
    )
    _validate_identifier(
        metadata["basis_generation_id"],
        _GENERATION_ID,
        "Publication basis Generation ID",
    )
    _validate_identifier(
        metadata["completion_id"],
        _COMPLETION_ID,
        "Publication Completion ID",
    )
    _validate_timestamp(
        metadata["created_at"],
        "Publication created_at",
    )

    _validate_manuscript_text(
        series_markdown,
        "Publication series.md",
    )

    series_character_count = _positive_integer(
        metadata["series_character_count"],
        "Publication series_character_count",
    )
    if series_character_count != len(
        series_markdown
    ):
        raise ContractError(
            "Publication series.mdの文字数が"
            "metadataと一致しません"
        )

    _validate_sha256(
        metadata["series_sha256"],
        "Publication series_sha256",
    )
    if metadata["series_sha256"] != (
        _sha256_text(series_markdown)
    ):
        raise ContractError(
            "Publication series.mdのSHA-256が"
            "metadataと一致しません"
        )

    status = metadata["completion_status"]
    if status not in _PUBLISHABLE_COMPLETION_STATUSES:
        raise ContractError(
            "Publicationには公開可能Completionが必要です"
        )

    volume_count = _positive_integer(
        metadata["volume_count"],
        "Publication volume_count",
    )
    entries = metadata["volume_entries"]

    if not isinstance(entries, list):
        raise ContractError(
            "Publication volume_entriesはarrayが必要です"
        )
    if len(entries) != volume_count:
        raise ContractError(
            "Publication volume_countと"
            "volume_entries件数が一致しません"
        )

    expected_names = {
        "metadata.json",
        "completion.json",
        "series.md",
    }
    volume_markdowns: list[str] = []

    for expected_number, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ContractError(
                "Publication volume entryはobjectが必要です"
            )
        if set(entry) != _VOLUME_ENTRY_FIELDS:
            raise ContractError(
                "Publication volume entryのfield構成が不正です"
            )
        if entry["volume_number"] != expected_number:
            raise ContractError(
                "Publication Volume番号は"
                "1からの連番でなければなりません"
            )

        entry_title = _required_heading_text(
            entry["title"],
            "Publication Volume title",
        )
        chapter_count = _positive_integer(
            entry["chapter_count"],
            "Publication chapter_count",
        )
        scene_count = _positive_integer(
            entry["scene_count"],
            "Publication scene_count",
        )
        character_count = _positive_integer(
            entry["character_count"],
            "Publication character_count",
        )
        _validate_sha256(
            entry["sha256"],
            "Publication Volume sha256",
        )

        output_name = f"v{expected_number:02d}.md"
        if entry["output_name"] != output_name:
            raise ContractError(
                "Publication Volume output_nameが不正です"
            )

        expected_names.add(output_name)
        markdown = files.get(output_name)

        if not isinstance(markdown, str) or not markdown.strip():
            raise ContractError(
                f"Publication巻本文がありません: {output_name}"
            )
        _validate_manuscript_text(
            markdown,
            f"Publication {output_name}",
        )

        expected_heading = (
            f"# {title}\n\n"
            f"## 第{_japanese_number(expected_number)}巻"
            f"　{entry_title}\n\n"
        )
        if not markdown.startswith(expected_heading):
            raise ContractError(
                f"Publication巻見出しが不正です: {output_name}"
            )
        if markdown.count("\n### ") != chapter_count:
            raise ContractError(
                f"Publication章数がmetadataと一致しません: "
                f"{output_name}"
            )

        separator_count = markdown.count(
            f"\n\n{_SCENE_SEPARATOR}\n\n"
        )
        if (
            chapter_count + separator_count
            != scene_count
        ):
            raise ContractError(
                f"Publication Scene数がmetadataと"
                f"一致しません: {output_name}"
            )

        if character_count != len(markdown):
            raise ContractError(
                f"Publication巻本文の文字数が"
                f"metadataと一致しません: {output_name}"
            )

        if entry["sha256"] != _sha256_text(
            markdown
        ):
            raise ContractError(
                f"Publication巻本文のSHA-256が"
                f"metadataと一致しません: {output_name}"
            )

        volume_markdowns.append(markdown)

    if set(files) != expected_names:
        raise ContractError(
            "Publication directoryのfile構成が不正です"
        )

    _validate_completion(
        completion,
        basis_generation_id=metadata[
            "basis_generation_id"
        ],
    )
    if completion["completion_id"] != metadata["completion_id"]:
        raise ContractError(
            "Publication MetadataとCompletion IDが一致しません"
        )
    if completion["status"] != status:
        raise ContractError(
            "Publication MetadataとCompletion statusが一致しません"
        )

    expected_series = _build_series_markdown(
        title,
        volume_markdowns,
    )
    if series_markdown != expected_series:
        raise ContractError(
            "Publication series.mdが巻別本文と一致しません"
        )


def validate_publication_directory(
    directory: Path,
    *,
    expected_files: (
        dict[str, dict[str, Any] | str] | None
    ) = None,
) -> dict[str, dict[str, Any] | str]:
    """Publication directoryを読み込み、構成と内容を検証する。"""
    if (
        not directory.is_dir()
        or directory.is_symlink()
    ):
        raise ContractError(
            "Publication directoryが不正です"
        )

    names = {
        path.name
        for path in directory.iterdir()
    }
    if not {
        "metadata.json",
        "completion.json",
        "series.md",
    }.issubset(names):
        raise ContractError(
            "Publication必須fileがありません"
        )

    metadata = _read_json(
        directory / "metadata.json"
    )
    volume_count = _positive_integer(
        metadata.get("volume_count"),
        "Publication volume_count",
    )

    expected_names = {
        "metadata.json",
        "completion.json",
        "series.md",
        *{
            f"v{number:02d}.md"
            for number in range(1, volume_count + 1)
        },
    }
    if names != expected_names:
        raise ContractError(
            "Publication directoryのfile構成が不正です"
        )

    files: dict[str, dict[str, Any] | str] = {
        "metadata.json": metadata,
        "completion.json": _read_json(
            directory / "completion.json"
        ),
        "series.md": _read_text(
            directory / "series.md"
        ),
    }

    for number in range(1, volume_count + 1):
        name = f"v{number:02d}.md"
        files[name] = _read_text(directory / name)

    validate_publication_files(files)

    if expected_files is not None:
        validate_publication_files(expected_files)
        if files != expected_files:
            raise ContractError(
                "Publication directoryが"
                "決定的構築結果と一致しません"
            )

    return files


def _validate_volumes(
    volumes: object,
) -> list[dict[str, Any]]:
    if not isinstance(volumes, list) or not volumes:
        raise ContractError(
            "Publicationには1巻以上が必要です"
        )

    normalized: list[dict[str, Any]] = []

    for expected_volume, volume in enumerate(volumes, 1):
        if not isinstance(volume, dict):
            raise ContractError(
                "Publication Volumeはobjectが必要です"
            )
        if set(volume) != _VOLUME_FIELDS:
            raise ContractError(
                "Publication Volumeのfield構成が不正です"
            )
        if volume["volume_number"] != expected_volume:
            raise ContractError(
                "Publication Volume番号は"
                "1からの連番でなければなりません"
            )

        volume_title = _required_heading_text(
            volume["title"],
            "Publication Volume title",
        )
        chapters = volume["chapters"]

        if not isinstance(chapters, list) or not chapters:
            raise ContractError(
                "Publication Volumeには1章以上が必要です"
            )

        normalized_chapters: list[dict[str, Any]] = []

        for expected_chapter, chapter in enumerate(
            chapters,
            1,
        ):
            if not isinstance(chapter, dict):
                raise ContractError(
                    "Publication Chapterはobjectが必要です"
                )
            if set(chapter) != _CHAPTER_FIELDS:
                raise ContractError(
                    "Publication Chapterのfield構成が不正です"
                )
            if chapter["chapter_number"] != expected_chapter:
                raise ContractError(
                    "Publication Chapter番号は"
                    "1からの連番でなければなりません"
                )

            chapter_title = _required_heading_text(
                chapter["title"],
                "Publication Chapter title",
            )
            scenes = chapter["scenes"]

            if not isinstance(scenes, list) or not scenes:
                raise ContractError(
                    "Publication Chapterには"
                    "1 Scene以上が必要です"
                )

            normalized_scenes: list[dict[str, Any]] = []

            for expected_scene, scene in enumerate(scenes, 1):
                if not isinstance(scene, dict):
                    raise ContractError(
                        "Publication Sceneはobjectが必要です"
                    )
                if set(scene) != _SCENE_FIELDS:
                    raise ContractError(
                        "Publication Sceneのfield構成が不正です"
                    )
                if scene["scene_number"] != expected_scene:
                    raise ContractError(
                        "Publication Scene番号は"
                        "1からの連番でなければなりません"
                    )

                prose = _normalize_prose(
                    scene["prose"],
                    "Publication Scene prose",
                )
                normalized_scenes.append({
                    "scene_number": expected_scene,
                    "prose": prose,
                })

            normalized_chapters.append({
                "chapter_number": expected_chapter,
                "title": chapter_title,
                "scenes": normalized_scenes,
            })

        normalized.append({
            "volume_number": expected_volume,
            "title": volume_title,
            "chapters": normalized_chapters,
        })

    return normalized


def _build_volume_markdown(
    series_title: str,
    volume: dict[str, Any],
) -> str:
    parts = [
        f"# {series_title}",
        (
            f"## 第{_japanese_number(volume['volume_number'])}巻"
            f"　{volume['title']}"
        ),
    ]

    for chapter in volume["chapters"]:
        parts.append(
            f"### 第{_japanese_number(chapter['chapter_number'])}章"
            f"　{chapter['title']}"
        )

        for index, scene in enumerate(
            chapter["scenes"]
        ):
            if index > 0:
                parts.append(_SCENE_SEPARATOR)
            parts.append(scene["prose"])

    markdown = "\n\n".join(parts) + "\n"
    _validate_manuscript_text(
        markdown,
        "Publication Volume Markdown",
    )
    return markdown


def _build_series_markdown(
    title: str,
    volume_markdowns: list[str],
) -> str:
    if not volume_markdowns:
        raise ContractError(
            "Publication series.mdには"
            "1巻以上が必要です"
        )

    prefix = f"# {title}\n\n"
    bodies: list[str] = []

    for markdown in volume_markdowns:
        if not markdown.startswith(prefix):
            raise ContractError(
                "Publication巻本文のシリーズ題名が"
                "一致しません"
            )

        body = markdown[
            len(prefix):
        ].rstrip("\n")
        if not body:
            raise ContractError(
                "Publication巻本文が空です"
            )
        bodies.append(body)

    series = (
        prefix
        + "\n\n".join(bodies)
        + "\n"
    )
    _validate_manuscript_text(
        series,
        "Publication series.md",
    )
    return series


def _validate_completion(
    completion: object,
    *,
    basis_generation_id: str,
) -> None:
    if not isinstance(completion, dict):
        raise ContractError(
            "Publication Completionはobjectが必要です"
        )

    _validate_identifier(
        completion.get("completion_id"),
        _COMPLETION_ID,
        "Publication Completion ID",
    )
    _validate_identifier(
        completion.get("basis_generation_id"),
        _GENERATION_ID,
        "Completion basis Generation ID",
    )

    if completion["basis_generation_id"] != (
        basis_generation_id
    ):
        raise ContractError(
            "PublicationとCompletionの"
            "basis Generationが一致しません"
        )

    if completion.get("status") not in (
        _PUBLISHABLE_COMPLETION_STATUSES
    ):
        raise ContractError(
            "Publicationには公開可能Completionが必要です"
        )


def _japanese_number(value: int) -> str:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
        or value > 999
    ):
        raise ContractError(
            "Publication番号は1以上999以下が必要です"
        )

    digits = (
        "零",
        "一",
        "二",
        "三",
        "四",
        "五",
        "六",
        "七",
        "八",
        "九",
    )
    parts: list[str] = []

    hundreds, remainder = divmod(value, 100)
    tens, ones = divmod(remainder, 10)

    if hundreds:
        if hundreds > 1:
            parts.append(digits[hundreds])
        parts.append("百")
    if tens:
        if tens > 1:
            parts.append(digits[tens])
        parts.append("十")
    if ones:
        parts.append(digits[ones])

    return "".join(parts)


def _normalize_newlines(
    value: str,
) -> str:
    return value.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )


def _reject_control_characters(
    value: str,
    label: str,
) -> None:
    if _FORBIDDEN_CONTROL.search(value):
        raise ContractError(
            f"{label}に不正な制御文字を含められません"
        )


def _required_text(
    value: object,
    label: str,
) -> str:
    if not isinstance(value, str):
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )

    normalized = _normalize_newlines(value)
    _reject_control_characters(
        normalized,
        label,
    )
    normalized = normalized.strip()

    if not normalized:
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )

    return normalized


def _required_heading_text(
    value: object,
    label: str,
) -> str:
    normalized = _required_text(
        value,
        label,
    )

    if "\n" in normalized:
        raise ContractError(
            f"{label}に改行を含められません"
        )

    return normalized


def _normalize_prose(
    value: object,
    label: str,
) -> str:
    normalized = _required_text(
        value,
        label,
    )

    for line in normalized.split("\n"):
        if line == _SCENE_SEPARATOR:
            raise ContractError(
                f"{label}にPublication用Scene区切りを"
                "含められません"
            )
        if _MARKDOWN_HEADING.match(line):
            raise ContractError(
                f"{label}にMarkdown見出しを"
                "含められません"
            )

    return normalized


def _validate_manuscript_text(
    value: object,
    label: str,
) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )

    if "\r" in value:
        raise ContractError(
            f"{label}の改行はLFでなければなりません"
        )

    _reject_control_characters(
        value,
        label,
    )

    if (
        not value.endswith("\n")
        or value.endswith("\n\n")
    ):
        raise ContractError(
            f"{label}の終端はLF一つでなければなりません"
        )

    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def _validate_sha256(
    value: object,
    label: str,
) -> None:
    if (
        not isinstance(value, str)
        or _SHA256.fullmatch(value) is None
    ):
        raise ContractError(
            f"{label}が不正です"
        )


def _positive_integer(
    value: object,
    label: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ContractError(
            f"{label}は1以上の整数が必要です"
        )
    return value


def _validate_identifier(
    value: object,
    pattern: re.Pattern[str],
    label: str,
) -> None:
    if (
        not isinstance(value, str)
        or pattern.fullmatch(value) is None
    ):
        raise ContractError(
            f"{label}が不正です"
        )


def _validate_timestamp(
    value: object,
    label: str,
) -> None:
    if not isinstance(value, str):
        raise ContractError(
            f"{label}はISO 8601文字列が必要です"
        )
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ContractError(
            f"{label}がISO 8601形式ではありません"
        ) from exc

    if parsed.tzinfo is None:
        raise ContractError(
            f"{label}にはtimezoneが必要です"
        )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            f"Publication JSONを読み込めません: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise ContractError(
            f"Publication JSONはobjectが必要です: {path}"
        )
    return value


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(
            f"Publication本文を読み込めません: {path}"
        ) from exc
