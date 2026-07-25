"""Storycraft V1 CLI試験。"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.cli import (
    _default_workspace_id,
    _keywords_payload,
    _require_existing_v1_workspace,
    _workspace_config,
    cmd_resume,
    cmd_run,
    cmd_step,
)
from storycraft.config import Settings
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.workspace import create_workspace


def _brief() -> dict:
    return json.loads(
        Path("example_brief.json").read_text(
            encoding="utf-8"
        )
    )


def _run_args(
    workspace: Path,
    brief_path: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        out=str(workspace),
        config=None,
        workspace_id="ws-cli-test",
        brief=str(brief_path),
        keywords_file=None,
        keywords=None,
        avoid=[],
        ending_preference="救いのある結末",
        volume_hint=4,
        notes=None,
    )


def _existing_args(
    workspace: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        out=str(workspace),
        config=None,
    )


class V1CliTests(unittest.TestCase):
    def test_run_creates_v1_workspace_without_root_state_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "novel"
            brief_path = root / "brief.json"

            brief_path.write_text(
                json.dumps(
                    _brief(),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            model_calls: list[object] = []

            class FakeWorkflow:
                def __init__(
                    self,
                    workspace_root: Path,
                    *,
                    model_factory,
                ) -> None:
                    self.root = workspace_root
                    self.model_factory = model_factory

                def step(self) -> dict:
                    state = RunStateStore(
                        self.root
                    ).load()

                    blocked = deepcopy(state)
                    blocked["status"] = "blocked"
                    blocked["stop_reason"] = (
                        "test_stop"
                    )

                    RunStateStore(
                        self.root
                    ).save(blocked)

                    return blocked

            with (
                patch(
                    "storycraft.cli."
                    "V1WorkflowService",
                    FakeWorkflow,
                ),
                patch(
                    "storycraft.cli."
                    "_setup_logging"
                ),
                patch(
                    "storycraft.cli."
                    "OpenAIStoryModel",
                    side_effect=(
                        lambda *args, **kwargs: (
                            model_calls.append(
                                object()
                            )
                        )
                    ),
                ),
            ):
                cmd_run(
                    _run_args(
                        workspace,
                        brief_path,
                    )
                )

            self.assertTrue(
                (
                    workspace
                    / "runtime/run-state.json"
                ).is_file()
            )
            self.assertFalse(
                (
                    workspace / "state.json"
                ).exists()
            )
            self.assertEqual(
                model_calls,
                [],
            )

    def test_step_brief_uses_real_v1_code_only_input(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "workspace"
            )

            create_workspace(
                workspace,
                workspace_id="ws-cli-step",
                config=_workspace_config(
                    Settings.load()
                ),
                brief=_brief(),
            )

            with (
                patch(
                    "storycraft.cli."
                    "_setup_logging"
                ),
                patch(
                    "storycraft.cli."
                    "OpenAIStoryModel",
                    side_effect=AssertionError(
                        "brief inputで"
                        "Providerを生成しました"
                    ),
                ) as model,
            ):
                cmd_step(
                    _existing_args(workspace)
                )

            state = RunStateStore(
                workspace
            ).load()

            self.assertEqual(
                state["current_stage"],
                "initial_concept",
            )
            model.assert_not_called()

    def test_resume_repeats_until_terminal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "workspace"
            )

            create_workspace(
                workspace,
                workspace_id="ws-cli-resume",
                config=_workspace_config(
                    Settings.load()
                ),
                brief=_brief(),
            )

            class FakeWorkflow:
                calls = 0

                def __init__(
                    self,
                    workspace_root: Path,
                    *,
                    model_factory,
                ) -> None:
                    self.root = workspace_root

                def step(self) -> dict:
                    type(self).calls += 1

                    state = RunStateStore(
                        self.root
                    ).load()

                    if type(self).calls == 1:
                        running = deepcopy(state)
                        running["status"] = "running"
                        running["current_stage"] = (
                            "initial_concept"
                        )
                        return running

                    completed = deepcopy(state)
                    completed["status"] = "completed"
                    completed["current_stage"] = (
                        "publication"
                    )
                    completed["current_target"] = {
                        "series": (
                            state["workspace_id"]
                        ),
                        "publication_id": (
                            "pub-000001"
                        ),
                    }
                    completed[
                        "current_publication_id"
                    ] = "pub-000001"

                    return completed

            with (
                patch(
                    "storycraft.cli."
                    "V1WorkflowService",
                    FakeWorkflow,
                ),
                patch(
                    "storycraft.cli."
                    "_setup_logging"
                ),
            ):
                cmd_resume(
                    _existing_args(workspace)
                )

            self.assertEqual(
                FakeWorkflow.calls,
                2,
            )

    def test_directory_without_v1_state_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "invalid"
            )
            workspace.mkdir()

            (
                workspace / "notes.txt"
            ).write_text(
                "not a Storycraft workspace\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "有効なV1 workspace",
            ):
                _require_existing_v1_workspace(
                    workspace
                )

    def test_v1_workspace_detection_uses_run_state_only(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "workspace"
            )

            create_workspace(
                workspace,
                workspace_id="ws-cli-detection",
                config=_workspace_config(
                    Settings.load()
                ),
                brief=_brief(),
            )

            # rootの無関係なfile名を旧版markerとして解釈しない。
            (
                workspace / "state.json"
            ).write_text(
                "{}\n",
                encoding="utf-8",
            )

            _require_existing_v1_workspace(
                workspace
            )

    def test_direct_keywords_build_v1_payload(
        self,
    ) -> None:
        args = argparse.Namespace(
            keywords_file=None,
            keywords=[
                "海辺",
                "再会",
            ],
            avoid=[
                "残虐描写",
            ],
            ending_preference=(
                "希望のある結末"
            ),
            volume_hint=4,
            notes="女性向け",
        )

        self.assertEqual(
            _keywords_payload(args),
            {
                "schema_version": 1,
                "source_type": "keywords",
                "keywords": [
                    "海辺",
                    "再会",
                ],
                "avoid": [
                    "残虐描写",
                ],
                "ending_preference": (
                    "希望のある結末"
                ),
                "volume_hint": 4,
                "language": "ja",
                "notes": "女性向け",
            },
        )

    def test_default_workspace_id_is_safe_and_stable(
        self,
    ) -> None:
        workspace = Path(
            "/tmp/日本語 workspace"
        )

        first = _default_workspace_id(
            workspace
        )
        second = _default_workspace_id(
            workspace
        )

        self.assertEqual(
            first,
            second,
        )
        self.assertTrue(
            first.startswith("ws-")
        )
        self.assertNotIn("..", first)
        self.assertNotIn("/", first)
        self.assertNotIn("\\", first)


if __name__ == "__main__":
    unittest.main()
