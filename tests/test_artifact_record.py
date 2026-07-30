from __future__ import annotations
import unittest
from storycraft.artifact_record import validate_record
from storycraft.series_contracts import ContractError

class ArtifactRecordTests(unittest.TestCase):
    def test_validates_common_and_specialized_records(self) -> None:
        validate_record("initial-design", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "selection_id": "selection-000001", "created_at": "2026-07-29T00:00:00Z", "content": {}})
        validate_record("request", "request-000001", {"schema_version": 1, "request_id": "request-000001", "payload": {}, "created_at": "2026-07-29T00:00:00Z"})
        validate_record("settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": "2026-07-29T00:00:00Z"})

    def test_rejects_id_kind_and_unknown_field_mismatch(self) -> None:
        with self.assertRaises(ContractError):
            validate_record("initial-design", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000002", "artifact_kind": "initial-design", "selection_id": "selection-000001", "created_at": "2026-07-29T00:00:00Z", "content": {}})
        with self.assertRaises(ContractError):
            validate_record("request", "request-000001", {"schema_version": 1, "request_id": "request-000001", "payload": {}, "created_at": "x", "extra": True})
