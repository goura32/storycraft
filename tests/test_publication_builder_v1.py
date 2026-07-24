"""Storycraft Version 1 Publication Builder契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.publication_builder import (
    build_publication_files,
    validate_publication_directory,
)
from storycraft.series_contracts import ContractError


ROOT = Path(__file__).parent.parent
FIXTURE_ROOT = (
    ROOT
    / "tests/fixtures/publication/pub-000001"
)
CREATED_AT = "2026-07-23T12:10:00Z"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_volumes() -> list[dict]:
    return [
        {
            "volume_number": 1,
            "title": "帰郷",
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "灯台",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "prose": (
                                "灯台の扉は、澪が覚えていた"
                                "よりも低かった。\n\n"
                                "十年ぶりに向き合った凪は、"
                                "火災の夜に灯台へいたことだけを"
                                "認めた。"
                            ),
                        },
                    ],
                },
            ],
        },
        {
            "volume_number": 2,
            "title": "欠けた記録",
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "保管庫",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "prose": (
                                "地下保管庫には、焼け残った"
                                "管理記録があった。\n\n"
                                "欠けた頁の番号だけが、"
                                "誰かの意図を示していた。"
                            ),
                        },
                    ],
                },
            ],
        },
        {
            "volume_number": 3,
            "title": "火の記憶",
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "目撃",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "prose": (
                                "澪は、火より先に記録箱を運ぶ"
                                "人影を見たことを思い出した。\n\n"
                                "その夜、凪が沈黙した理由も"
                                "初めて輪郭を持った。"
                            ),
                        },
                    ],
                },
            ],
        },
        {
            "volume_number": 4,
            "title": "同じ灯",
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "朝の灯台",
                    "scenes": [
                        {
                            "scene_number": 1,
                            "prose": (
                                "姉妹は残された記録を机に並べ、"
                                "互いの秘密を一つずつ話した。\n\n"
                                "夜明けの灯台で、"
                                "澪は町に残ると決めた。"
                            ),
                        },
                    ],
                },
            ],
        },
    ]


def build_fixture_files() -> dict:
    completion = read_json(
        FIXTURE_ROOT / "completion.json"
    )
    return build_publication_files(
        publication_id="pub-000001",
        title="潮騒の記憶",
        language="ja",
        basis_generation_id="gen-000240",
        completion=completion,
        volumes=fixture_volumes(),
        created_at=CREATED_AT,
    )


def write_files(
    directory: Path,
    files: dict,
) -> None:
    directory.mkdir(parents=True)

    for name, value in files.items():
        path = directory / name
        if isinstance(value, dict):
            path.write_text(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            path.write_text(
                value,
                encoding="utf-8",
            )


class PublicationBuilderV1Tests(unittest.TestCase):
    def test_builder_matches_publication_fixture(self) -> None:
        files = build_fixture_files()

        self.assertEqual(
            files["metadata.json"],
            read_json(FIXTURE_ROOT / "metadata.json"),
        )
        self.assertEqual(
            files["completion.json"],
            read_json(FIXTURE_ROOT / "completion.json"),
        )

        for name in (
            "series.md",
            "v01.md",
            "v02.md",
            "v03.md",
            "v04.md",
        ):
            self.assertEqual(
                files[name],
                (FIXTURE_ROOT / name).read_text(
                    encoding="utf-8"
                ),
                name,
            )

    def test_complete_with_issues_is_publishable(self) -> None:
        completion = read_json(
            ROOT
            / "tests/fixtures/completion"
            / "complete-with-issues.json"
        )

        files = build_publication_files(
            publication_id="pub-000002",
            title="潮騒の記憶",
            language="ja",
            basis_generation_id="gen-000240",
            completion=completion,
            volumes=fixture_volumes(),
            created_at=CREATED_AT,
        )

        self.assertEqual(
            files["metadata.json"]["completion_status"],
            "complete_with_issues",
        )

    def test_incomplete_completion_is_rejected(self) -> None:
        completion = read_json(
            ROOT
            / "tests/fixtures/completion"
            / "incomplete.json"
        )

        with self.assertRaisesRegex(
            ContractError,
            "公開可能Completion",
        ):
            build_publication_files(
                publication_id="pub-000003",
                title="潮騒の記憶",
                language="ja",
                basis_generation_id="gen-000240",
                completion=completion,
                volumes=fixture_volumes(),
                created_at=CREATED_AT,
            )

    def test_volume_order_must_be_consecutive(self) -> None:
        volumes = fixture_volumes()
        volumes[1]["volume_number"] = 3

        with self.assertRaisesRegex(
            ContractError,
            "Volume番号",
        ):
            build_publication_files(
                publication_id="pub-000001",
                title="潮騒の記憶",
                language="ja",
                basis_generation_id="gen-000240",
                completion=read_json(
                    FIXTURE_ROOT / "completion.json"
                ),
                volumes=volumes,
                created_at=CREATED_AT,
            )

    def test_private_source_fields_are_rejected(self) -> None:
        volumes = fixture_volumes()
        volumes[0]["chapters"][0]["scenes"][0][
            "private_notes"
        ] = "作者だけが知る情報"

        with self.assertRaisesRegex(
            ContractError,
            "Sceneのfield構成",
        ):
            build_publication_files(
                publication_id="pub-000001",
                title="潮騒の記憶",
                language="ja",
                basis_generation_id="gen-000240",
                completion=read_json(
                    FIXTURE_ROOT / "completion.json"
                ),
                volumes=volumes,
                created_at=CREATED_AT,
            )

    def test_directory_validator_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "pub-000001"
            files = build_fixture_files()
            write_files(directory, files)

            validated = validate_publication_directory(
                directory,
                expected_files=files,
            )
            self.assertEqual(validated, files)

            path = directory / "v02.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "本文外の追記\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_publication_directory(
                    directory,
                    expected_files=files,
                )


if __name__ == "__main__":
    unittest.main()
