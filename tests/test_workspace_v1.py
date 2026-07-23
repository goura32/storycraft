"""Storycraft Version 1 workspace初期化契約。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.workspace import (
    REQUIRED_DIRECTORIES,
    create_workspace_from_brief,
    validate_workspace_layout,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-23T13:00:00Z"


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


class WorkspaceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.config = load_json(
            "tests/fixtures/workspace/config.json"
        )

    def test_create_workspace_from_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"

            created = create_workspace_from_brief(
                workspace,
                workspace_id="ws-test-0001",
                brief=self.brief,
                config=self.config,
                created_at=CREATED_AT,
            )

            self.assertEqual(created, workspace)
            validate_workspace_layout(workspace)

            for relative in REQUIRED_DIRECTORIES:
                self.assertTrue((workspace / relative).is_dir())

            state = RunStateStore(workspace).load()
            self.assertEqual(state["status"], "initializing")
            self.assertEqual(state["current_stage"], "input")
            self.assertEqual(
                state["current_target"],
                {"series": "ws-test-0001"},
            )
            self.assertIsNone(
                state["current_generation_id"]
            )

    def test_workspace_persists_brief_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_brief(
                workspace,
                workspace_id="ws-test-0001",
                brief=self.brief,
                config=self.config,
                created_at=CREATED_AT,
            )

            stored_brief = json.loads(
                (
                    workspace / "input/brief.json"
                ).read_text(encoding="utf-8")
            )
            source = json.loads(
                (
                    workspace / "input/source.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(stored_brief, self.brief)
            self.assertEqual(source["source_type"], "brief")
            self.assertEqual(
                source["source_path"],
                "input/brief.json",
            )

    def test_workspace_initializes_counters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_brief(
                workspace,
                workspace_id="ws-test-0001",
                brief=self.brief,
                config=self.config,
                created_at=CREATED_AT,
            )

            counters = json.loads(
                (
                    workspace / "runtime/counters.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(counters["next_run"], 2)
            self.assertEqual(
                counters["next_generation"],
                1,
            )
            self.assertEqual(
                counters["updated_at"],
                CREATED_AT,
            )

    def test_existing_workspace_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            workspace.mkdir()
            marker = workspace / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(
                ContractError,
                "resume",
            ):
                create_workspace_from_brief(
                    workspace,
                    workspace_id="ws-test-0001",
                    brief=self.brief,
                    config=self.config,
                    created_at=CREATED_AT,
                )

            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "keep",
            )

    def test_invalid_brief_creates_no_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            invalid = dict(self.brief)
            del invalid["premise"]

            with self.assertRaisesRegex(
                ContractError,
                "Brief契約違反",
            ):
                create_workspace_from_brief(
                    workspace,
                    workspace_id="ws-test-0001",
                    brief=invalid,
                    config=self.config,
                    created_at=CREATED_AT,
                )

            self.assertFalse(workspace.exists())
            self.assertEqual(
                list(Path(temporary).iterdir()),
                [],
            )

    def test_unsafe_workspace_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"

            with self.assertRaisesRegex(
                ContractError,
                "workspace_id",
            ):
                create_workspace_from_brief(
                    workspace,
                    workspace_id="ws-../escape",
                    brief=self.brief,
                    config=self.config,
                    created_at=CREATED_AT,
                )

            self.assertFalse(workspace.exists())

    def test_missing_required_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_brief(
                workspace,
                workspace_id="ws-test-0001",
                brief=self.brief,
                config=self.config,
                created_at=CREATED_AT,
            )
            (workspace / "scenes").rmdir()

            with self.assertRaisesRegex(
                ContractError,
                "scenes",
            ):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
