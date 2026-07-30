"""V2 artifact counter reservation contracts."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.artifact_ids import initial_counters, reserve_counter
from storycraft.series_contracts import ContractError


class ArtifactIdTests(unittest.TestCase):
    def _root(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "runtime").mkdir()
        (root / "runtime" / "counters.json").write_text(json.dumps(initial_counters()), encoding="utf-8")
        return temporary, root

    def test_reservation_is_monotonic(self) -> None:
        temporary, root = self._root()
        with temporary:
            self.assertEqual(reserve_counter(root, "next_initial_design"), 1)
            self.assertEqual(reserve_counter(root, "next_initial_design"), 2)
            counters = json.loads((root / "runtime/counters.json").read_text(encoding="utf-8"))
            self.assertEqual(counters["next_initial_design"], 3)

    def test_rejects_unknown_or_incomplete_counter_schema(self) -> None:
        temporary, root = self._root()
        with temporary:
            with self.assertRaises(ContractError):
                reserve_counter(root, "next_unknown")
            (root / "runtime/counters.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ContractError):
                reserve_counter(root, "next_selection")
