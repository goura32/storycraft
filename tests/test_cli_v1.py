"""Storycraft V1 CLI試験。"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.cli import (
    _build_parser,
    _default_workspace_id,
    _keywords_payload,
    _require_existing_v1_workspace,
    _workspace_config,
    cmd_resume,
    cmd_run,
    cmd_status,
    cmd_step,
    cmd_validate,
)
from storycraft.config import Settings
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.workspace import (
    create_workspace,
    validate_workspace_layout,
)


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


def _capture_json(
    command,
    args: argparse.Namespace,
) -> dict:
    output = io.StringIO()

    with redirect_stdout(output):
        command(args)

    value = json.loads(output.getvalue())
    if not isinstance(value, dict):
        raise AssertionError(
            "CLI JSON outputはobjectが必要です"
        )
    return value


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

            # rootの無関係なfile名をworkspace markerとして解釈しない。
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



    def test_status_reads_run_state_without_full_layout_validation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "workspace"
            )

            create_workspace(
                workspace,
                workspace_id="ws-cli-status",
                config=_workspace_config(
                    Settings.load()
                ),
                brief=_brief(),
            )

            expected = RunStateStore(
                workspace
            ).load_recovery()
            state_bytes = (
                workspace
                / "runtime/run-state.json"
            ).read_bytes()

            # statusは診断用なので、run-state以外の破損が
            # あっても現在状態を表示できる。
            (workspace / "scenes").rmdir()

            with (
                patch(
                    "storycraft.cli.Settings.load",
                    side_effect=AssertionError(
                        "statusがSettingsを読み込みました"
                    ),
                ),
                patch(
                    "storycraft.cli.OpenAIStoryModel",
                    side_effect=AssertionError(
                        "statusがProviderを生成しました"
                    ),
                ),
                patch(
                    "storycraft.cli._setup_logging",
                    side_effect=AssertionError(
                        "statusがlogを変更しました"
                    ),
                ),
            ):
                actual = _capture_json(
                    cmd_status,
                    _existing_args(workspace),
                )

            self.assertEqual(actual, expected)
            self.assertEqual(
                (
                    workspace
                    / "runtime/run-state.json"
                ).read_bytes(),
                state_bytes,
            )

    def test_validate_checks_complete_workspace_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "workspace"
            )

            create_workspace(
                workspace,
                workspace_id="ws-cli-validate",
                config=_workspace_config(
                    Settings.load()
                ),
                brief=_brief(),
            )

            state = RunStateStore(
                workspace
            ).load_recovery()
            state_bytes = (
                workspace
                / "runtime/run-state.json"
            ).read_bytes()

            with (
                patch(
                    "storycraft.cli.Settings.load",
                    side_effect=AssertionError(
                        "validateがSettingsを読み込みました"
                    ),
                ),
                patch(
                    "storycraft.cli.OpenAIStoryModel",
                    side_effect=AssertionError(
                        "validateがProviderを生成しました"
                    ),
                ),
                patch(
                    "storycraft.cli._setup_logging",
                    side_effect=AssertionError(
                        "validateがlogを変更しました"
                    ),
                ),
                patch(
                    "storycraft.cli."
                    "validate_workspace_layout",
                    wraps=validate_workspace_layout,
                ) as validator,
            ):
                actual = _capture_json(
                    cmd_validate,
                    _existing_args(workspace),
                )

            validator.assert_called_once_with(
                workspace,
                run_state=state,
            )

            self.assertEqual(
                actual,
                {
                    "schema_version": 1,
                    "valid": True,
                    "workspace_id": (
                        "ws-cli-validate"
                    ),
                    "run_id": "run-000001",
                    "status": "initializing",
                    "current_stage": "input",
                    "pending_commit": None,
                },
            )
            self.assertEqual(
                (
                    workspace
                    / "runtime/run-state.json"
                ).read_bytes(),
                state_bytes,
            )

    def test_validate_rejects_broken_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "workspace"
            )

            create_workspace(
                workspace,
                workspace_id=(
                    "ws-cli-invalid-validate"
                ),
                config=_workspace_config(
                    Settings.load()
                ),
                brief=_brief(),
            )

            (workspace / "scenes").rmdir()

            with self.assertRaisesRegex(
                ContractError,
                "scenes",
            ):
                cmd_validate(
                    _existing_args(workspace)
                )

    def test_parser_registers_status_and_validate(
        self,
    ) -> None:
        parser = _build_parser()

        for name, handler in (
            ("status", cmd_status),
            ("validate", cmd_validate),
        ):
            with self.subTest(command=name):
                args = parser.parse_args([
                    name,
                    "--out",
                    "/tmp/storycraft-workspace",
                ])

                self.assertIs(
                    args.handler,
                    handler,
                )
                self.assertEqual(
                    args.out,
                    "/tmp/storycraft-workspace",
                )


if __name__ == "__main__":
    unittest.main()
