"""Workspace fixture baseline cacheの契約。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import storycraft.workspace as workspace_module
from storycraft.workspace import (
    create_workspace_from_brief,
)

from tests.support.workspace_fixtures import (
    clone_cached_workspace,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-26T06:30:00Z"


def load_json(relative: str) -> dict:
    return json.loads(
        (ROOT / relative).read_text(
            encoding="utf-8"
        )
    )


def build_valid_workspace(
    parent: str,
) -> Path:
    workspace = Path(parent) / "workspace"

    create_workspace_from_brief(
        workspace,
        workspace_id="ws-fixture-cache-test",
        brief=load_json(
            "tests/fixtures/brief/valid.json"
        ),
        config=load_json(
            "tests/fixtures/workspace/config.json"
        ),
        created_at=CREATED_AT,
    )

    return workspace


class WorkspaceFixturesTests(unittest.TestCase):
    def test_builder_runs_once_and_clones_are_independent(
        self,
    ) -> None:
        calls = 0

        def builder(
            parent: str,
        ) -> tuple[Path, dict]:
            nonlocal calls
            calls += 1

            return (
                build_valid_workspace(parent),
                {"values": [1]},
            )

        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            key = (
                "workspace-fixture-valid-"
                + Path(first).name
            )

            original = (
                workspace_module
                .validate_workspace_layout
            )

            with patch.object(
                workspace_module,
                "validate_workspace_layout",
                wraps=original,
            ) as validate:
                first_workspace, first_payload = (
                    clone_cached_workspace(
                        key=key,
                        temporary=first,
                        builder=builder,
                    )
                )

                first_payload["values"].append(2)
                (
                    first_workspace / "local-only.txt"
                ).write_text(
                    "changed",
                    encoding="utf-8",
                )

                second_workspace, second_payload = (
                    clone_cached_workspace(
                        key=key,
                        temporary=second,
                        builder=builder,
                    )
                )

            self.assertEqual(calls, 1)
            self.assertEqual(validate.call_count, 1)
            self.assertEqual(
                second_payload,
                {"values": [1]},
            )
            self.assertFalse(
                (
                    second_workspace
                    / "local-only.txt"
                ).exists()
            )
            self.assertNotEqual(
                first_workspace,
                second_workspace,
            )

    def test_failed_builder_can_be_retried(
        self,
    ) -> None:
        calls = 0

        def builder(parent: str) -> Path:
            nonlocal calls
            calls += 1

            if calls == 1:
                incomplete = (
                    Path(parent) / "incomplete"
                )
                incomplete.mkdir()
                raise RuntimeError("builder failed")

            return build_valid_workspace(parent)

        with tempfile.TemporaryDirectory() as temporary:
            key = (
                "workspace-fixture-retry-"
                + Path(temporary).name
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "builder failed",
            ):
                clone_cached_workspace(
                    key=key,
                    temporary=temporary,
                    builder=builder,
                )

            workspace, payload = clone_cached_workspace(
                key=key,
                temporary=temporary,
                builder=builder,
            )

            self.assertEqual(calls, 2)
            self.assertIsNone(payload)
            workspace_module.validate_workspace_layout(
                workspace
            )


if __name__ == "__main__":
    unittest.main()
