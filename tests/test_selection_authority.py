from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from storycraft.selection_authority import resolve_selection
from storycraft.workspace import create_workspace
from storycraft.series_contracts import ContractError

SETTINGS={"provider":"ollama","endpoint":"http://127.0.0.1:11434","model":"test","technical_retry_limit":1,"quality_revision_limit":0,"invalid_response_limit":1,"chapter_per_volume_range":[1,1],"chapter_scene_range":[1,1],"scene_text_char_range":[1000,1000],"max_input_chars":50000}
REQUEST={"title":"t","genre":"g","premise":"p","required_elements":[],"forbidden_elements":[],"ending_preference":"e","volume_count":4,"language":"ja"}
class SelectionAuthorityTests(unittest.TestCase):
 def test_resolves_bootstrap_authority(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/"ws"; create_workspace(root, workspace_id="ws-000001", request=REQUEST, settings=SETTINGS, created_at="2026-07-29T00:00:00Z")
   snapshot=__import__('json').loads((root/'runtime/run-state.json').read_text())
   record=__import__('json').loads((root/'runtime/selections'/snapshot['current_selection_id']/'record.json').read_text())
   self.assertEqual(set(resolve_selection(root,record)),{'request','settings'})
 def test_rejects_missing_authority_record(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)/"ws"; create_workspace(root, workspace_id="ws-000001", request=REQUEST, settings=SETTINGS, created_at="2026-07-29T00:00:00Z")
   snapshot=__import__('json').loads((root/'runtime/run-state.json').read_text())
   record=__import__('json').loads((root/'runtime/selections'/snapshot['current_selection_id']/'record.json').read_text())
   (root/'inputs/request-000001/record.json').unlink()
   with self.assertRaises(ContractError): resolve_selection(root,record)
