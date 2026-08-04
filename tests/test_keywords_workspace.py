from __future__ import annotations
import tempfile
import unittest
import json
from pathlib import Path
from storycraft.run_state import RunStateStore
from storycraft.workspace import create_workspace
from storycraft.workspace import validate_workspace

SETTINGS={"provider":"ollama","endpoint":"http://127.0.0.1:11434","model":"test","technical_retry_limit":1,"quality_revision_limit":1,"invalid_response_limit":1,"chapter_per_volume_range":[1,1],"chapter_scene_range":[1,1],"scene_text_char_range":[1000,1000]}
class KeywordsWorkspaceTests(unittest.TestCase):
 def test_keywords_starts_request_intake_without_selection(self):
  with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'ws'
      create_workspace(root, workspace_id='ws-000001', request=None, keywords={'keywords':['霧'],'language':'ja'}, settings=SETTINGS, created_at='2026-07-29T00:00:00Z')
      state = RunStateStore(root).load()
      self.assertEqual(state['current_stage'],'request_intake'); self.assertIsNone(state['current_selection_id'])
      self.assertTrue((root/'inputs/keywords-000001/record.json').is_file())

 def test_keywords_have_no_artificial_count_or_length_limit_and_are_normalized(self):
  with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'ws'
      words = ['  e\u0301  '] + [str(i) for i in range(12)]
      create_workspace(root, workspace_id='ws-000001', request=None, keywords={'keywords': words, 'language':'ja'}, settings=SETTINGS, created_at='2026-07-29T00:00:00Z')
      record = json.loads((root/'inputs/keywords-000001/record.json').read_text())
      self.assertEqual(record['keywords'][0], 'é')

 def test_keywords_reject_control_characters(self):
  with tempfile.TemporaryDirectory() as temp:
      with self.assertRaises(Exception):
          create_workspace(Path(temp) / 'ws', workspace_id='ws-000001', request=None, keywords={'keywords':['bad\nvalue'], 'language':'ja'}, settings=SETTINGS, created_at='2026-07-29T00:00:00Z')

 def test_validate_rechecks_persisted_keywords_and_settings_payload(self):
  with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'ws'
      create_workspace(root, workspace_id='ws-000001', request=None, keywords={'keywords':['霧'],'language':'ja'}, settings=SETTINGS, created_at='2026-07-29T00:00:00Z')
      settings_path = root/'runtime/settings/settings-000001/record.json'
      settings_record = json.loads(settings_path.read_text())
      settings_record['payload']['technical_retry_limit'] = 0
      settings_path.write_text(json.dumps(settings_record, ensure_ascii=False))
      with self.assertRaises(Exception):
          validate_workspace(root)

 def test_validate_rejects_injected_sentinel_settings_payload(self):
  with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'ws'
      create_workspace(root, workspace_id='ws-000001', request=None, keywords={'keywords':['霧'],'language':'ja'}, settings=SETTINGS, created_at='2026-07-29T00:00:00Z')
      settings_path = root/'runtime/settings/settings-000001/record.json'
      settings_record = json.loads(settings_path.read_text())
      settings_record['payload'] = {'endpoint': 'injected'}
      settings_path.write_text(json.dumps(settings_record, ensure_ascii=False))
      with self.assertRaises(Exception):
          validate_workspace(root)
