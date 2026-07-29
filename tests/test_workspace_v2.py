"""v2 新規 workspace 初期化の最小不変契約。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.workspace_v2 import create_v2_workspace, validate_v2_workspace


class WorkspaceV2Tests(unittest.TestCase):
    def test_creates_fresh_v2_workspace_with_request_settings_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            create_v2_workspace(
                root,
                workspace_id="ws-test",
                request={"title": "題名", "volume_count": 1},
                settings={"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000], "max_input_chars": 50000},
                created_at="2026-07-28T00:00:00Z",
            )
            state = RunStateStore(root).load()
            self.assertEqual(state["schema_version"], 2)
            self.assertEqual(state["current_stage"], "initial_design")
            snapshot = SelectionSnapshotStore(root).load(state["current_selection_id"])
            self.assertEqual(set(snapshot["slots"]), {"request", "settings"})
            validate_v2_workspace(root)

    def test_refuses_existing_workspace_without_mutating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            root.mkdir()
            marker = root / "marker"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "既に存在"):
                create_v2_workspace(root, workspace_id="ws-test", request={}, settings={}, created_at="2026-07-28T00:00:00Z")
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
