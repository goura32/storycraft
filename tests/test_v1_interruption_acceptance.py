"""Storycraft V1 Workflow中断・再起動Acceptance試験。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

from storycraft.run_state import RunStateStore
from storycraft.scene_commit_stage import (
    SceneCommitStageService,
)
from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import (
    create_workspace_from_brief,
    validate_workspace_layout,
)

from tests.test_v1_acceptance import (
    AcceptanceModel,
    CREATED_AT,
)


ROOT = Path(__file__).parent.parent
BASE_TIME = datetime(
    2026,
    7,
    25,
    3,
    0,
    tzinfo=timezone.utc,
)


def _load_json(relative: str) -> dict[str, Any]:
    return json.loads(
        (ROOT / relative).read_text(
            encoding="utf-8"
        )
    )


def _timestamp(step_number: int) -> str:
    return (
        BASE_TIME
        + timedelta(seconds=step_number)
    ).isoformat().replace(
        "+00:00",
        "Z",
    )


def _create_workspace(
    root: Path,
    name: str,
) -> Path:
    workspace = root / name

    create_workspace_from_brief(
        workspace,
        workspace_id="ws-test-0001",
        brief=_load_json(
            "tests/fixtures/brief/valid.json"
        ),
        config=_load_json(
            "tests/fixtures/workspace/config.json"
        ),
        created_at=CREATED_AT,
    )

    return workspace


def _publication_snapshot(
    workspace: Path,
    publication_id: str,
) -> dict[str, bytes]:
    root = (
        workspace
        / "publications"
        / publication_id
    )

    if not root.is_dir() or root.is_symlink():
        raise AssertionError(
            "Publication directoryが存在しません"
        )

    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes()
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _model_factory(
    model: AcceptanceModel,
    calls: list[AcceptanceModel],
) -> AcceptanceModel:
    calls.append(model)
    return model


def _run_to_completion(
    workspace: Path,
    *,
    model: AcceptanceModel,
    factory_calls: list[AcceptanceModel],
    step_number: int,
) -> tuple[dict[str, Any], int]:
    workflow = V1WorkflowService(
        workspace,
        model_factory=lambda: _model_factory(
            model,
            factory_calls,
        ),
    )
    store = RunStateStore(workspace)

    for _ in range(200):
        current = store.load_recovery()

        if current["status"] == "completed":
            return current, step_number

        if current["pending_commit"] is not None:
            raise AssertionError(
                "通常継続中に未処理pending_commitが"
                "残っています"
            )

        step_number += 1
        state = workflow.step(
            updated_at=_timestamp(step_number)
        )

        if state["status"] not in {
            "initializing",
            "running",
            "completed",
        }:
            raise AssertionError(
                "Workflowが完了前に停止しました: "
                f"{state}"
            )

        if state["status"] == "completed":
            return state, step_number

    raise AssertionError(
        "Workflowが200工程以内に完了しません"
    )


class V1InterruptionAcceptanceTests(
    unittest.TestCase
):
    def test_scene_commit_crash_recovers_to_identical_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            baseline_workspace = _create_workspace(
                root,
                "baseline",
            )
            interrupted_workspace = _create_workspace(
                root,
                "interrupted",
            )

            baseline_model = AcceptanceModel()
            baseline_factory_calls: list[
                AcceptanceModel
            ] = []

            (
                baseline_final,
                baseline_step_number,
            ) = _run_to_completion(
                baseline_workspace,
                model=baseline_model,
                factory_calls=baseline_factory_calls,
                step_number=0,
            )

            interrupted_model = AcceptanceModel()
            interrupted_factory_calls: list[
                AcceptanceModel
            ] = []
            interrupted_step_number = 0

            interrupted_workflow = V1WorkflowService(
                interrupted_workspace,
                model_factory=lambda: _model_factory(
                    interrupted_model,
                    interrupted_factory_calls,
                ),
            )
            interrupted_store = RunStateStore(
                interrupted_workspace
            )

            for _ in range(200):
                current = (
                    interrupted_store.load_recovery()
                )

                if (
                    current["current_stage"]
                    == "scene_commit"
                    and current["pending_commit"] is None
                ):
                    break

                if current["pending_commit"] is not None:
                    self.fail(
                        "Scene Commit到達前に"
                        "pending_commitが残りました"
                    )

                interrupted_step_number += 1
                state = interrupted_workflow.step(
                    updated_at=_timestamp(
                        interrupted_step_number
                    )
                )

                if state["status"] not in {
                    "initializing",
                    "running",
                }:
                    self.fail(
                        "Scene Commit到達前に"
                        f"Workflowが停止しました: {state}"
                    )
            else:
                self.fail(
                    "Scene Commitへ到達しませんでした"
                )

            interrupted_step_number += 1
            original_save_phase = (
                SceneCommitStageService
                ._save_pending_phase
            )

            def crash_after_generation_finalized(
                service: SceneCommitStageService,
                state: dict[str, Any],
                **kwargs: Any,
            ) -> dict[str, Any]:
                saved = original_save_phase(
                    service,
                    state,
                    **kwargs,
                )

                if (
                    kwargs.get("phase")
                    == "generation_finalized"
                ):
                    raise RuntimeError(
                        "acceptance scene commit crash"
                    )

                return saved

            with (
                patch.object(
                    SceneCommitStageService,
                    "_save_pending_phase",
                    new=crash_after_generation_finalized,
                ),
                self.assertRaisesRegex(
                    RuntimeError,
                    "acceptance scene commit crash",
                ),
            ):
                interrupted_workflow.step(
                    updated_at=_timestamp(
                        interrupted_step_number
                    )
                )

            crashed = (
                interrupted_store.load_recovery()
            )
            pending = crashed["pending_commit"]

            self.assertIsInstance(pending, dict)
            self.assertEqual(
                pending["kind"],
                "scene_commit",
            )
            self.assertEqual(
                pending["phase"],
                "generation_finalized",
            )

            scene_id = pending["target_id"]
            generation_id = pending[
                "expected_generation_id"
            ]

            self.assertTrue(
                (
                    interrupted_workspace
                    / "scenes"
                    / scene_id
                ).is_dir()
            )
            self.assertTrue(
                (
                    interrupted_workspace
                    / "generations"
                    / generation_id
                ).is_dir()
            )

            calls_before_recovery = len(
                interrupted_factory_calls
            )

            # process再起動相当としてServiceを作り直す。
            restarted_workflow = V1WorkflowService(
                interrupted_workspace,
                model_factory=lambda: _model_factory(
                    interrupted_model,
                    interrupted_factory_calls,
                ),
            )

            recovered = restarted_workflow.step()

            # Recovery工程ではProviderを生成しない。
            self.assertEqual(
                len(interrupted_factory_calls),
                calls_before_recovery,
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(
                recovered["current_generation_id"],
                generation_id,
            )
            self.assertNotEqual(
                recovered["current_stage"],
                "scene_commit",
            )

            (
                interrupted_final,
                interrupted_step_number,
            ) = _run_to_completion(
                interrupted_workspace,
                model=interrupted_model,
                factory_calls=interrupted_factory_calls,
                step_number=interrupted_step_number,
            )

            self.assertEqual(
                interrupted_final["status"],
                "completed",
            )
            self.assertIsNone(
                interrupted_final["pending_commit"]
            )
            self.assertEqual(
                interrupted_step_number,
                baseline_step_number,
            )

            # CrashとRecoveryでLLM Stageを重複実行しない。
            self.assertEqual(
                len(interrupted_factory_calls),
                len(baseline_factory_calls),
            )

            # 同一入力・同一論理時刻なら最終stateも同一。
            self.assertEqual(
                interrupted_final,
                baseline_final,
            )

            baseline_publication_id = baseline_final[
                "current_publication_id"
            ]
            interrupted_publication_id = (
                interrupted_final[
                    "current_publication_id"
                ]
            )

            self.assertIsInstance(
                baseline_publication_id,
                str,
            )
            self.assertEqual(
                interrupted_publication_id,
                baseline_publication_id,
            )

            # Publication全fileをbyte単位で比較する。
            self.assertEqual(
                _publication_snapshot(
                    interrupted_workspace,
                    interrupted_publication_id,
                ),
                _publication_snapshot(
                    baseline_workspace,
                    baseline_publication_id,
                ),
            )

            validate_workspace_layout(
                baseline_workspace
            )
            validate_workspace_layout(
                interrupted_workspace
            )


if __name__ == "__main__":
    unittest.main()
