# Initial and planning fixture

All JSON uses canonical UTF-8, NFC, LF, sorted-key compact JSON with a trailing LF. The fixture is independent and all local-key references resolve.

## Brief

```json
{"avoid":"町を失望させる","brief_version":1,"created_at":"2026-07-22T00:00:00Z","editorial_profile_id":"default-ja","ending":"町が灯を守る意思を持つ","genre":"海洋幻想譚","key_people":[{"initial_relation_to_protagonist":"幼なじみ","name":"凪","present_position":"修理工"}],"protagonist":{"core_trait":"粘り強い","current_pressure":"日没までに灯を戻す","initial_wish":"家の灯台を守る","name":"澪","present_position":"灯台守見習い"},"publishing_profile_id":"default-md","source_hash":"0000000000000000000000000000000000000000000000000000000000000000","source_type":"brief","target_reader":"成人読者","title":"岬の灯","volumes":4,"want":"灯を守る"}
```

## INIT candidates

```json
{"character_candidates":[{"local_key":"mio","name":"澪"},{"local_key":"nagi","name":"凪"}],"concept":{"logline":"見習い灯台守が停止した灯の原因を追う","theme":"責任を引き受ける"},"ending_criteria":[{"description":"町が灯を守る意思を持つ","local_key":"town-light","required":true}],"major_threads":[{"author_truth":"予備鍵が修理庫を開ける","local_key":"light-cause","resolution_condition":"灯を再び点ける"}],"protagonist_arc":{"end":"責任を引き受ける","start":"責任を避ける"},"relationship_arcs":[{"end":"協力","relationship_local_key":"mio-nagi","start":"疎遠"}],"relationship_candidates":[{"local_key":"mio-nagi","participant_a_local_key":"mio","participant_b_local_key":"nagi"}],"temporal_rule_candidates":[{"description":"日没後に点灯する","local_key":"sunset"}],"world_entity_candidates":[{"kind":"location","local_key":"cape-lighthouse"}]}
```

## Genesis projection

```json
{"baseline_fixture_id":null,"fixture_id":"lighthouse-initial-v1","generation_manifest":{"commit_id":"commit-00000000","continuity_delta_sha256":null,"current_canon_sha256":null,"evidence_index_sha256":null,"generation_id":"00000000","knowledge_items_sha256":null,"parent_generation_id":null,"prose_sha256":null,"scene_card_sha256":null,"story_state_sha256":null},"head_after":"00000000","initial_design":{"character_candidates":[{"local_key":"mio","name":"澪"},{"local_key":"nagi","name":"凪"}],"concept":{"logline":"見習い灯台守が停止した灯の原因を追う","theme":"責任を引き受ける"},"ending_criteria":[{"description":"町が灯を守る意思を持つ","local_key":"town-light","required":true}],"major_threads":[{"author_truth":"予備鍵が修理庫を開ける","local_key":"light-cause","resolution_condition":"灯を再び点ける"}],"protagonist_arc":{"end":"責任を引き受ける","start":"責任を避ける"},"relationship_arcs":[{"end":"協力","relationship_local_key":"mio-nagi","start":"疎遠"}],"relationship_candidates":[{"local_key":"mio-nagi","participant_a_local_key":"mio","participant_b_local_key":"nagi"}],"temporal_rule_candidates":[{"description":"日没後に点灯する","local_key":"sunset"}],"world_entity_candidates":[{"kind":"location","local_key":"cape-lighthouse"}]},"local_key_mappings":[{"local_key":"mio","persistent_id":"char-000001","record_type":"character"},{"local_key":"nagi","persistent_id":"char-000002","record_type":"character"},{"local_key":"mio-nagi","persistent_id":"rel-000001","record_type":"relationship"},{"local_key":"cape-lighthouse","persistent_id":"loc-000001","record_type":"world_entity"},{"local_key":"light-cause","persistent_id":"thread-000001","record_type":"thread"},{"local_key":"town-light","persistent_id":"ending-000001","record_type":"ending_criterion"}]}
```

## Series map, volume, chapter

```json
{"chapter_design":{"chapter_number":1,"objective":"予備鍵を発見する","required_thread_actions":["thread-000001"],"scene_count":1,"volume_number":1},"series_map":{"volumes":[{"ending_position":"advance","major_thread_targets":["thread-000001"],"protagonist_change_target":"責任を受け入れる","reader_question":"灯は戻るか","relationship_change_targets":["rel-000001"],"volume_number":1,"volume_promise":"灯への問いを進める","volume_role":"導入"},{"ending_position":"advance","major_thread_targets":["thread-000001"],"protagonist_change_target":"責任を受け入れる","reader_question":"灯は戻るか","relationship_change_targets":["rel-000001"],"volume_number":2,"volume_promise":"灯への問いを進める","volume_role":"進展"},{"ending_position":"advance","major_thread_targets":["thread-000001"],"protagonist_change_target":"責任を受け入れる","reader_question":"灯は戻るか","relationship_change_targets":["rel-000001"],"volume_number":3,"volume_promise":"灯への問いを進める","volume_role":"危機"},{"ending_position":"resolve","major_thread_targets":["thread-000001"],"protagonist_change_target":"責任を受け入れる","reader_question":"灯は戻るか","relationship_change_targets":["rel-000001"],"volume_number":4,"volume_promise":"灯への問いを進める","volume_role":"解決"}]},"volume_design":{"chapter_count":1,"objective":"停止原因の手掛かりを得る","required_thread_ids":["thread-000001"],"volume_number":1}}
```
