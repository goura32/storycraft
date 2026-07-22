# Data contract examples

> 接続例の唯一の正本。field定義は[ledger contracts](ledger_contracts.md)、保存pathは[workspace layout](workspace_layout.md)を参照する。

## Baseline fixture

```json
{"fixture_id":"lighthouse-baseline-v1","baseline_fixture_id":null,"current_canon_after":{"records":[{"id":"char-000001","record_type":"character","scope":"series","record_lifecycle":"active","created_scene_id":null,"references":[]},{"id":"loc-000001","record_type":"world_entity","scope":"series","record_lifecycle":"active","created_scene_id":null,"references":[]},{"id":"thread-000001","record_type":"thread","scope":"series","record_lifecycle":"active","created_scene_id":null,"references":[]},{"id":"ending-000001","record_type":"ending_criterion","scope":"series","record_lifecycle":"active","created_scene_id":null,"references":[]}],"knowledge_items":[{"id":"fact-000001","subject_type":"thread","subject_id":"thread-000001","canonical_fact":"予備鍵が灯台停止の原因に関係する","writer_visible_label":"予備鍵が原因に関係するかもしれない","author_truth":"予備鍵は灯室の修理庫を開ける","scope":"series","created_scene_id":null,"record_lifecycle":"active"}]},"story_state_after":{"thread_states":{"thread-000001":{"thread_status":"open","progress":0}},"knowledge_state":{"fact-000001:char-000001":{"status":"unknown"}},"story_clock":{"current_order":0,"time_label":"初日夕方","parallel_group_id":null,"last_scene_id":null}}}
```

## Adopted scene fixture

`fixture_id` is `lighthouse-scene-01`; `baseline_fixture_id` is `lighthouse-baseline-v1`.

```json
{"fixture_id":"lighthouse-scene-01","baseline_fixture_id":"lighthouse-baseline-v1","scene_id":"v01-c001-s001","prose":"澪は錆びた予備鍵を拾い、これが灯台停止の原因に関係するのではないかと疑った。最終日の夜ではなく、まだ初日夕方だった。","current_canon_delta":{"new_records":[],"new_knowledge_items":[]},"story_state_delta":{"thread_updates":[{"thread_id":"thread-000001","before_status":"open","after_status":"in_progress","before_progress":0,"after_progress":1,"evidence":"これが灯台停止の原因に関係するのではないかと疑った"}],"knowledge_updates":[{"fact_id":"fact-000001","audience_id":"char-000001","before":"unknown","after":"suspects","evidence":"これが灯台停止の原因に関係するのではないかと疑った"}],"time_update":{"time_relation":"same_time","time_label":"初日夕方","elapsed_hint":null,"parallel_group_id":null,"evidence":null}},"current_canon_after":{"same_as_baseline":true},"story_state_after":{"thread_states":{"thread-000001":{"thread_status":"in_progress","progress":1}},"knowledge_state":{"fact-000001:char-000001":{"status":"suspects"}},"story_clock":{"current_order":1,"time_label":"初日夕方","parallel_group_id":null,"last_scene_id":"v01-c001-s001"}},"evidence_index_after":[{"evidence_id":"ev-000001","evidence_type":"knowledge_update","target_id":"fact-000001","scene_id":"v01-c001-s001","quote":"これが灯台停止の原因に関係するのではないかと疑った","relation":"supports","start_offset":12,"end_offset":37,"quote_sha256":"2a07dc228e37dd36031d293e4cdbf0eb3d56f286b23f37e844442f4a10317807"}]}
```

`before_order=0` and `after_order=1` are code fields, not LLM output. The sample keeps `time_label` unchanged, therefore time evidence is nullable. If a delta sets `time_label:"最終日夜"`, prose must contain exactly `最終日の夜`.

## Completion fixture

`fixture_id` is `lighthouse-complete-v1`; `baseline_fixture_id` is `lighthouse-scene-01`.

```json
{"fixture_id":"lighthouse-complete-v1","baseline_fixture_id":"lighthouse-scene-01","scene_id":"v04-c003-s002","prose":"最終日の夜、町の人々は灯台の灯を見上げ、明日からもこの灯を守ろうと頷いた。","story_state_delta":{"thread_updates":[{"thread_id":"thread-000001","before_status":"in_progress","after_status":"resolved","before_progress":3,"after_progress":4,"evidence":"明日からもこの灯を守ろうと頷いた"}],"time_update":{"time_relation":"later","time_label":"最終日夜","elapsed_hint":"数日後","parallel_group_id":null,"evidence":"最終日の夜"}},"story_state_after":{"thread_states":{"thread-000001":{"thread_status":"resolved","progress":4}},"story_clock":{"current_order":48,"time_label":"最終日夜","parallel_group_id":null,"last_scene_id":"v04-c003-s002"}},"evidence_index_after":[{"evidence_id":"ev-000002","evidence_type":"ending_criterion","target_id":"ending-000001","scene_id":"v04-c003-s002","quote":"町の人々は灯台の灯を見上げ、明日からもこの灯を守ろうと頷いた","relation":"supports","start_offset":6,"end_offset":36,"quote_sha256":"5919b2aa6f54cd88f3efea1fc16796e9de57ed886f4126798549ea0111e0ae2c"}]}
```

## Commit and publication examples

```json
{"head_before":"00000000","new_generation":"00000001","commit_manifest":{"commit_id":"commit-00000001","parent_commit_id":"commit-00000000","scene_id":"v01-c001-s001","before_generation":"00000000","after_generation":"00000001"},"scene_manifest":{"scene_id":"v01-c001-s001","commit_id":"commit-00000001"},"head_after":"00000001"}
```

```json
{"publication_generation":"00000048","output_current_before":"00000003","publication_id":"00000004","output_current_after":"00000004","publication_path":"publications/00000004"}
```

## Required semantic checks

The sample validator must parse every block, resolve every ID via its named baseline fixture, verify before/after, require quote substring equality, verify `start_offset/end_offset` and actual `quote_sha256`, and evaluate the stated knowledge/ending meaning rather than merely accepting an ID match.
