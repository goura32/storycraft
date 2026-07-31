from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from storycraft.run_state import RunStateStore
from storycraft.workspace import create_workspace

SETTINGS={"provider":"ollama","endpoint":"http://127.0.0.1:11434","model":"test","technical_retry_limit":1,"quality_revision_limit":0,"invalid_response_limit":1,"chapter_per_volume_range":[1,1],"chapter_scene_range":[1,1],"scene_text_char_range":[1000,1000]}
class KeywordsWorkspaceTests(unittest.TestCase):
 def test_keywords_starts_request_intake_without_selection(self):
  with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'ws'
      create_workspace(root, workspace_id='ws-000001', request=None, keywords={'keywords':['霧'],'language':'ja'}, settings=SETTINGS, created_at='2026-07-29T00:00:00Z')
      state = RunStateStore(root).load()
      self.assertEqual(state['current_stage'],'request_intake'); self.assertIsNone(state['current_selection_id'])
      self.assertTrue((root/'inputs/keywords-000001/record.json').is_file())
