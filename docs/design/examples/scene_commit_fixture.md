# Scene commit fixture

This document is the complete representative Scene transaction fixture for:

```text
fixture_id = lighthouse-scene-commit-v3
baseline_fixture_id = lighthouse-planning-v3
baseline_inventory_sha256 = d76edaa75abeee5b133c207007f973b049b3199bffba5d50f6711b93f62f7811

scene_id = v01-c001-s001
source_generation_id = 00000000
adopted_generation_id = 00000001
commit_id = commit-00000001
```

It covers:

```text
SC-01 Planner Context
Scene-card response, Review, Candidate manifest
SC-CHK frozen Scene card
Writer Context
prose response, Review, Candidate manifest
PROSE-CHK frozen prose
Continuity Context
DELTA-01 response
normalized candidate delta, Review, Candidate manifest
DELTA-CHK checkpoint
COMMIT-01 Commit plan
COMMIT-02 Evidence allocation and merge plan
COMMIT-03 committed delta, Evidence index, after roots, Scene/Commit/Generation manifests
COMMIT-04 HEAD adoption and next-Scene routing
post-commit counters and Run state
```

The owning contracts are:

- [`../contracts/data/scene_artifacts.md`](../contracts/data/scene_artifacts.md)
- [`../contracts/ledger/evidence_and_updates.md`](../contracts/ledger/evidence_and_updates.md)
- [`../contracts/ledger/runtime_records.md`](../contracts/ledger/runtime_records.md)
- [`../contracts/pipeline/scene_generation.md`](../contracts/pipeline/scene_generation.md)
- [`../contracts/pipeline/commit_and_output.md`](../contracts/pipeline/commit_and_output.md)
- [`../context_contracts.md`](../context_contracts.md)
- [`../data_contract_examples.md`](../data_contract_examples.md)
- [`initial_and_planning_fixture.md`](initial_and_planning_fixture.md)

Every JSON block is a complete logical value. Hashes use compact canonical JSON plus one LF. Pretty indentation is presentation-only.

---

## 1. Transaction purpose

This Scene exercises:

```text
one Relationship-State trust transition
one Character Knowledge transition
one Reader Knowledge transition
one required Major Thread introduce operation
one Story-clock time-label transition
five code-allocated Evidence records
no new Canon or Knowledge item
no persistent story-record allocation
```

The Scene is the opening Scene of Chapter 1.

After commit:

```text
next target = v01-c001-s002
successful Scene commits = 1
HEAD = 00000001
```

---

# Part I: Runtime and Context identity
## 2. Effective config

```text
EXACT ARTIFACT
path = runtime/effective-config.json
example_id = EX-POS-SCENE-FIX-CFG-001
```

```json
{
  "audit_compression": "gzip",
  "audit_max_total_bytes": 1073741824,
  "audit_redaction_mode": "strict",
  "audit_retention_days": 30,
  "audit_store_request_body": true,
  "audit_store_response_body": true,
  "audit_warning_threshold_bytes": 805306368,
  "base_url": "http://127.0.0.1:8765",
  "cached_input_cost_per_million_tokens": null,
  "chapter_target_chars": 12000,
  "code_version": "1.0.0-fixture",
  "config_version": "1.0",
  "connect_timeout_seconds": 30,
  "credential_env_var": null,
  "editorial_profile": {
    "dialogue_guidance": "会話は人物ごとのspeech anchorを保ち、説明の代替ではなく判断と感情の変化を担わせる。",
    "forbidden_content": [
      "主人公だけが全責任を負う結末",
      "説明だけで謎を解決する場面"
    ],
    "language_tag": "ja-JP",
    "narrative_person": "third_person",
    "pov_distance": "close",
    "pov_policy": "single_pov_per_scene",
    "profile_id": "default-ja",
    "prose_constraints": [
      "do not add unsupported Canon facts",
      "do not reveal forbidden disclosures",
      "maintain one POV per scene",
      "preserve established speech anchors"
    ],
    "tense": "past"
  },
  "editorial_profile_id": "default-ja",
  "fallback_tokens_per_code_point": 2.0,
  "first_event_timeout_seconds": 120,
  "idle_timeout_seconds": 120,
  "immutable_config_fingerprint": "6bfeea3f4d9c2f052c058c253dc196d3ec3ca88e3e7800bb3f7b12af6de49ade",
  "input_cost_per_million_tokens": 0.0,
  "log_level": "info",
  "materialized_at": "2026-07-22T00:00:00Z",
  "max_active_elapsed_seconds": null,
  "max_completion_audit_attempts": 2,
  "max_context_tokens_by_operation": {
    "brief": 32768,
    "chapter_design": 32768,
    "completion_audit": 32768,
    "continuity_delta": 32768,
    "initial_design": 32768,
    "prose": 32768,
    "scene_card": 32768,
    "series_map": 32768,
    "volume_design": 32768,
    "volume_handoff": 32768
  },
  "max_estimated_cost": null,
  "max_llm_calls": null,
  "max_new_items_per_scene": 2,
  "max_response_structure_retries": 0,
  "max_revision_rounds": 0,
  "max_total_input_tokens": null,
  "max_total_output_tokens": null,
  "max_transport_retries": 0,
  "model": "fixture-ja-1",
  "model_context_window_tokens": 32768,
  "output_cost_per_million_tokens": 0.0,
  "pricing_currency": "USD",
  "pricing_table_version": "fixture-zero-v1",
  "prompt_bundle_version": "prompts-v1",
  "protocol_overhead_tokens": 1024,
  "provider": "fixture",
  "publishing_profile": {
    "auto_publish": false,
    "first_volume_access": "free",
    "later_volume_access": "paid",
    "manuscript_format": "markdown",
    "max_volumes": 10,
    "min_volumes": 4,
    "platform": "kdp",
    "profile_id": "kdp-ja-v1",
    "require_nonfinal_reader_question": true,
    "require_volume_local_resolution": true
  },
  "publishing_profile_id": "kdp-ja-v1",
  "reserved_output_tokens_by_operation": {
    "brief": 2048,
    "chapter_design": 4096,
    "completion_audit": 8192,
    "continuity_delta": 6144,
    "initial_design": 8192,
    "prose": 8192,
    "scene_card": 4096,
    "series_map": 4096,
    "volume_design": 4096,
    "volume_handoff": 4096
  },
  "retry_initial_backoff_seconds": 1.0,
  "retry_jitter_ratio": 0.0,
  "retry_max_backoff_seconds": 30.0,
  "scene_guide_max_chars": 2200,
  "scene_guide_min_chars": 500,
  "scene_target_chars": 1200,
  "schema_bundle_version": "schemas-v1",
  "seed": 42,
  "state_version": "1.0",
  "stream": false,
  "structured_output_mode": "json_schema",
  "temperature": 0.0,
  "thinking": false,
  "top_p": 1.0,
  "total_call_timeout_seconds": 900,
  "volume_target_chars": 60000,
  "workspace_version": "1.0"
}
```

Canonical SHA-256:

```text
4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c
```

Immutable-config fingerprint:

```text
6bfeea3f4d9c2f052c058c253dc196d3ec3ca88e3e7800bb3f7b12af6de49ade
```

## 3. Run manifest

```text
EXACT ARTIFACT
path = runtime/run-manifest.json
example_id = EX-POS-SCENE-FIX-RUN-001
```

```json
{
  "base_url": "http://127.0.0.1:8765",
  "code_version": "1.0.0-fixture",
  "created_at": "2026-07-22T00:00:00Z",
  "created_by": "storycraft",
  "editorial_profile_id": "default-ja",
  "immutable_config_fingerprint": "6bfeea3f4d9c2f052c058c253dc196d3ec3ca88e3e7800bb3f7b12af6de49ade",
  "initial_effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "input_mode": "keywords",
  "input_source_path": "input/keywords.json",
  "input_source_sha256": "cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f",
  "manifest_version": "1.0",
  "model": "fixture-ja-1",
  "pricing_table_version": "fixture-zero-v1",
  "prompt_bundle_version": "prompts-v1",
  "provider": "fixture",
  "publishing_profile_id": "kdp-ja-v1",
  "run_id": "run-000001",
  "schema_bundle_version": "schemas-v1",
  "seed": 42,
  "state_version": "1.0",
  "stream": false,
  "structured_output_mode": "json_schema",
  "temperature": 0.0,
  "thinking": false,
  "top_p": 1.0,
  "workspace_version": "1.0"
}
```

Canonical SHA-256:

```text
2286207ba97cb075b3b94aa01ea1de0a50aa91d8bb12acdae3fb84d771cf2418
```

## 4. SC-01 Planner Context snapshot

```text
EXACT ARTIFACT
path = runtime/context-snapshots/sc-01/v01-c001-s001/3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e.json
example_id = EX-POS-SCENE-FIX-CTX-001
```

```json
{
  "builder_id": "scene_planner_builder",
  "builder_version": "context-builders-v1",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "exclusions": [],
  "operation_id": "SC-01",
  "payload": {
    "brief": {
      "avoid": [
        "主人公だけが全責任を負う結末",
        "説明だけで謎を解決する場面"
      ],
      "brief_version": "1.0",
      "created_at": "2026-07-22T00:00:00Z",
      "editorial_profile_id": "default-ja",
      "ending": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける",
      "genre": "海洋幻想譚",
      "key_people": [
        {
          "initial_relation_to_protagonist": "疎遠になった幼なじみ",
          "name": "凪",
          "present_position": "港の修理工"
        }
      ],
      "protagonist": {
        "core_trait": "粘り強い",
        "current_pressure": "日没までに停止原因を特定する必要がある",
        "initial_wish": "家業としてではなく自分の意思で灯を守りたい",
        "name": "澪",
        "present_position": "岬の灯台守見習い"
      },
      "publishing_profile_id": "kdp-ja-v1",
      "source_hash": "cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f",
      "source_type": "keywords",
      "target_reader": "成人読者",
      "title": "岬の灯",
      "volumes": 4,
      "want": "停止した灯台の原因を追い、町全体が灯を守る仕組みを作る"
    },
    "chapter_design": {
      "accepted_candidate_sha256": "bd613bc160693488b0139be9782bf30fc1e5655982efbaa456470bc6eef8ca71",
      "chapter_end_function": "hook",
      "chapter_number": 1,
      "created_at": "2026-07-22T00:08:00Z",
      "end_goal": {
        "handoff_to_next_chapter": "予備鍵が最後に保管された港の修理台帳を調べる。",
        "reader_effect": "停止原因へ通じる具体的な物の手掛かりが提示される。",
        "required_decision_or_event": "澪が凪へ予備鍵の記録を見せ、二人で所在を探すと決める。",
        "state_summary": "澪と凪が予備鍵の存在と調査上の意味を共有し、所在を追う共同作業へ移る。"
      },
      "ending_criterion_targets": [
        {
          "criterion_id": "ending-000001",
          "plan_action": "withhold",
          "prohibited_disclosure": "町の最終的な共同管理を断定しない",
          "purpose": "責任を一人で負う限界だけを示す",
          "required": true
        }
      ],
      "prior_chapter_handoff_path": null,
      "prior_chapter_handoff_sha256": null,
      "protagonist_or_relationship_change": {
        "purpose": "Volume 1の主人公変化を開始する",
        "required_change": "単独調査から情報共有へ移る",
        "start_state_summary": "凪へ必要最低限しか話さず、自分で原因を見つけようとしている。",
        "target_id": "char-000001",
        "target_state_summary": "凪へ記録を見せ、共同で予備鍵の所在を追うと決めている。",
        "target_type": "character"
      },
      "purpose": "停止した主灯を確認し、予備鍵の存在を澪と凪が共有することで、主要Threadを最初に導入する。",
      "required_world_entity_ids": [
        "item-000001",
        "loc-000001"
      ],
      "scene_plan": [
        {
          "completion_role": "opening",
          "emotional_change_target": "澪が凪の安全確認を拒まず聞く",
          "ending_criterion_ids": [],
          "pov_character_id": "char-000001",
          "purpose": "消えた主灯を確認し、澪と凪の現在の距離と日没期限を示す。",
          "required_beats": [
            "澪が消えたレンズを確認する",
            "凪が安全手順を求める",
            "日没までの時間が示される"
          ],
          "required_character_ids": [
            "char-000001",
            "char-000002"
          ],
          "required_location_id": "loc-000001",
          "scene_number": 1,
          "thread_action_ids": [
            "thread-000001"
          ]
        },
        {
          "completion_role": "development",
          "emotional_change_target": "澪が自分だけでは記録を読めないと認める",
          "ending_criterion_ids": [
            "ending-000001"
          ],
          "pov_character_id": "char-000001",
          "purpose": "日誌の欠落と予備鍵の記録を発見し、停止原因の問いを具体化する。",
          "required_beats": [
            "旧日誌の欄が欠けている",
            "真鍮の予備鍵の記録が見つかる",
            "凪が修理庫との関係を知っていると示す"
          ],
          "required_character_ids": [
            "char-000001",
            "char-000002"
          ],
          "required_location_id": "loc-000001",
          "scene_number": 2,
          "thread_action_ids": [
            "thread-000001"
          ]
        },
        {
          "completion_role": "resolution",
          "emotional_change_target": "澪が反発より共同調査を優先する",
          "ending_criterion_ids": [],
          "pov_character_id": "char-000001",
          "purpose": "予備鍵の所在を共同で追う決定を成立させ、次章へのhookを作る。",
          "required_beats": [
            "澪が記録を凪へ渡す",
            "凪が港の修理台帳を提案する",
            "二人が共同調査を決める"
          ],
          "required_character_ids": [
            "char-000001",
            "char-000002"
          ],
          "required_location_id": "loc-000001",
          "scene_number": 3,
          "thread_action_ids": [
            "thread-000001"
          ]
        }
      ],
      "schema_version": "1.0",
      "source_generation_id": "00000000",
      "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
      "start_state": {
        "active_character_ids": [
          "char-000001",
          "char-000002"
        ],
        "active_relationship_ids": [
          "rel-000001"
        ],
        "active_thread_ids": [
          "thread-000001"
        ],
        "location_ids": [
          "loc-000001"
        ],
        "summary": "初日の夕方、澪と凪は停止した岬の灯台にいる。二人は疎遠で、主要Threadはopen/0である。",
        "time_label": "初日の夕方"
      },
      "target_scene_count": 3,
      "thread_actions": [
        {
          "purpose": "予備鍵と修理庫を停止原因の問いへ接続する",
          "required": true,
          "required_action": "introduce",
          "start_progress": 0,
          "start_status": "open",
          "target_progress": 1,
          "target_status": "in_progress",
          "thread_id": "thread-000001"
        }
      ],
      "title": "消えた主灯",
      "volume_design_sha256": "c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e",
      "volume_number": 1
    },
    "characters": [
      {
        "record": {
          "aliases": [],
          "appearance_anchor": "潮に色褪せた青い外套と、腰の小さな工具袋。",
          "background": "岬の灯台守の家に生まれ、家業を継ぐことを当然とされてきた見習い。",
          "core_trait": "粘り強い",
          "created_scene_id": null,
          "id": "char-000001",
          "immutable_facts": [
            "凪とは幼なじみである",
            "灯台の主灯と日誌の基本手順を知っている"
          ],
          "name": "澪",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "character",
          "role": "protagonist",
          "scope": "series",
          "speech_anchor": "短く確かめるように話し、決めた後は言い切る。",
          "values": [
            "灯を絶やさないこと",
            "自分で選んだ責任"
          ]
        },
        "selection_reasons": [
          "pov_character",
          "required_participant"
        ],
        "state": {
          "character_id": "char-000001",
          "current_goal": "日没までに灯台停止の原因を特定する",
          "current_pressure": "町が灯台守の家だけを責め始める前に結果を出す必要がある",
          "emotional_state": "焦りを抑えて手順を守ろうとしている",
          "location_id": "loc-000001",
          "physical_condition": "疲労や負傷はない"
        }
      },
      {
        "record": {
          "aliases": [],
          "appearance_anchor": "油の染みた革手袋と、右手首の古い傷。",
          "background": "港の修理工。幼い頃は澪と灯台で遊んだが、灯台管理をめぐる両家の対立で疎遠になった。",
          "core_trait": "慎重",
          "created_scene_id": null,
          "id": "char-000002",
          "immutable_facts": [
            "澪とは幼なじみである",
            "港と灯台の旧式機構に詳しい"
          ],
          "name": "凪",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "character",
          "role": "ally",
          "scope": "series",
          "speech_anchor": "確認事項を順番に挙げ、断定の前に根拠を求める。",
          "values": [
            "共有できる記録",
            "安全な整備"
          ]
        },
        "selection_reasons": [
          "required_participant"
        ],
        "state": {
          "character_id": "char-000002",
          "current_goal": "灯台設備を安全に調べ、再故障を防ぐ",
          "current_pressure": "無理な再点灯で港へ二次被害を出せない",
          "emotional_state": "澪への距離を測りながら設備を警戒している",
          "location_id": "loc-000001",
          "physical_condition": "右手首に古傷があるが作業可能"
        }
      }
    ],
    "editorial_profile": {
      "dialogue_guidance": "会話は人物ごとのspeech anchorを保ち、説明の代替ではなく判断と感情の変化を担わせる。",
      "forbidden_content": [
        "主人公だけが全責任を負う結末",
        "説明だけで謎を解決する場面"
      ],
      "language_tag": "ja-JP",
      "narrative_person": "third_person",
      "pov_distance": "close",
      "pov_policy": "single_pov_per_scene",
      "profile_id": "default-ja",
      "prose_constraints": [
        "do not add unsupported Canon facts",
        "do not reveal forbidden disclosures",
        "maintain one POV per scene",
        "preserve established speech anchors"
      ],
      "tense": "past"
    },
    "ending_criteria": [
      {
        "record": {
          "created_scene_id": null,
          "description": "町が灯台を共同で守る意思と具体的な役割分担を示す。",
          "id": "ending-000001",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "ending_criterion",
          "required": true,
          "scope": "series",
          "source_ending_text": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける"
        },
        "relevant_evidence_ids": [],
        "selection_reasons": [
          "required_ending_criterion"
        ]
      }
    ],
    "initial_design": {
      "accepted_bundle_sha256": "d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034",
      "brief_path": "input/brief.json",
      "brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
      "character_ids": [
        "char-000001",
        "char-000002"
      ],
      "concept": {
        "central_conflict": "灯台を家の責任として背負おうとする澪と、設備と記録を共同管理すべきだという現実の間で、日没までに停止原因を追う必要がある。",
        "core_concept": "停止した岬の灯台を調べる見習い灯台守の澪が、疎遠な幼なじみの凪と協力し、隠されてきた予備鍵と町の責任の関係を明らかにする。",
        "ending_direction": "町が灯台を共同で守る意思を表明し、澪と凪が再点灯を見届けることで、個人の義務を共同の選択へ変える。",
        "genre_promise": "潮風と灯火の感覚的な描写を軸に、手掛かりを段階的に積み上げる海洋幻想ミステリを提供する。",
        "reader_experience": "各巻で一つの実務的な問題が解ける達成感と、町全体の選択へ近づく連続的な謎を両立させる。",
        "themes": [
          "責任の共有",
          "継承と選択",
          "信頼の再構築"
        ],
        "tone_constraints": [
          "説明だけで真相を処理しない",
          "危機の中にも静かな海辺の余韻を残す",
          "主人公一人へ責任を集中させない"
        ]
      },
      "created_at": "2026-07-22T00:05:01Z",
      "ending_criterion_ids": [
        "ending-000001"
      ],
      "genesis_commit_id": "commit-00000000",
      "knowledge_item_ids": [
        "fact-000001"
      ],
      "major_thread_ids": [
        "thread-000001"
      ],
      "protagonist_arc": {
        "change_function": "孤立した義務感を、他者と選び直す責任へ変える。",
        "end_state": "町と責任を分け合いながら、自分の意思で灯台を守る。",
        "protagonist_id": "char-000001",
        "start_state": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
        "turning_points": [
          {
            "description": "凪と修理庫の手掛かりを共有し、単独調査では進めないと認める。",
            "purpose": "協力を選ぶ最初の変化",
            "sequence": 1
          },
          {
            "description": "灯台停止が個人の失敗ではなく、町の管理の空白と結びつくと知る。",
            "purpose": "責任の範囲を広げる",
            "sequence": 2
          },
          {
            "description": "原因を公にし、町へ共同の判断を求める。",
            "purpose": "共同責任を要求する",
            "sequence": 3
          },
          {
            "description": "町と役割を分け合ったうえで、自分の意思で灯を守る。",
            "purpose": "継承を選択へ変える",
            "sequence": 4
          }
        ]
      },
      "relationship_arcs": [
        {
          "change_function": "疎遠な幼なじみを、責任を分け合う主要な協力者へ戻す。",
          "end_state": "互いの専門性と選択を信頼し、灯台を共同で支える。",
          "relationship_id": "rel-000001",
          "start_state": "互いの能力は認めるが、過去の対立を避けて必要最低限しか話さない。",
          "turning_points": [
            {
              "description": "修理庫の調査で互いの判断根拠を共有する。",
              "purpose": "実務上の信頼を回復する",
              "sequence": 1
            },
            {
              "description": "両家の対立と隠された記録を互いに説明する。",
              "purpose": "過去の誤解を解く",
              "sequence": 2
            },
            {
              "description": "町への説明を二人で引き受ける。",
              "purpose": "協力関係を公にする",
              "sequence": 3
            },
            {
              "description": "再点灯を対等な共同作業として完了する。",
              "purpose": "主要な信頼関係を確立する",
              "sequence": 4
            }
          ]
        }
      ],
      "relationship_ids": [
        "rel-000001"
      ],
      "schema_version": "1.0",
      "temporal_rule_ids": [
        "rule-000001"
      ],
      "world_entity_ids": [
        "item-000001",
        "loc-000001"
      ]
    },
    "knowledge_items": [
      {
        "record": {
          "author_truth": "予備鍵で地下修理庫を開けると、停止原因につながる旧式切替器と管理台帳を調べられる。",
          "canonical_fact": "真鍮の予備鍵は地下修理庫の錠に対応する。",
          "created_scene_id": null,
          "id": "fact-000001",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "knowledge_item",
          "scope": "series",
          "subject_id": "item-000001",
          "subject_type": "world_entity",
          "writer_visible_label": "予備鍵の役割"
        },
        "selection_reasons": [
          "scene_knowledge_target_candidate",
          "thread_clue"
        ],
        "states": [
          {
            "audience_id": "char-000002",
            "audience_type": "character",
            "fact_id": "fact-000001",
            "status": "knows"
          },
          {
            "audience_id": null,
            "audience_type": "reader",
            "fact_id": "fact-000001",
            "status": "hinted"
          }
        ]
      }
    ],
    "previous_handoff": null,
    "publishing_profile": {
      "auto_publish": false,
      "first_volume_access": "free",
      "later_volume_access": "paid",
      "manuscript_format": "markdown",
      "max_volumes": 10,
      "min_volumes": 4,
      "platform": "kdp",
      "profile_id": "kdp-ja-v1",
      "require_nonfinal_reader_question": true,
      "require_volume_local_resolution": true
    },
    "relationships": [
      {
        "record": {
          "created_scene_id": null,
          "id": "rel-000001",
          "participant_a_id": "char-000001",
          "participant_b_id": "char-000002",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "relationship",
          "relationship_origin": "幼なじみだったが、灯台管理をめぐる両家の対立で疎遠になった。",
          "relationship_type": "friendship",
          "scope": "series",
          "structural_role": "primary"
        },
        "selection_reasons": [
          "chapter_change_target",
          "participant_relationship"
        ],
        "state": {
          "a_to_b": {
            "current_intention": "必要な範囲だけ協力を得る",
            "emotional_stance": "反発を隠しながら助けを求めている",
            "perception": "設備には頼れるが、自分の家を責めていると思っている",
            "trust": "low"
          },
          "b_to_a": {
            "current_intention": "危険な単独行動を止め、記録を共有させる",
            "emotional_stance": "心配と距離の両方を保っている",
            "perception": "手順を守れるが、責任を一人で抱え込みすぎる",
            "trust": "medium"
          },
          "public_relation": "必要な作業のために再会した疎遠な幼なじみ",
          "relationship_id": "rel-000001",
          "shared_state": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。"
        }
      }
    ],
    "residual_constraints": [],
    "series_map": {
      "accepted_candidate_sha256": "450a883f030353874d490cbecd699d7f71ed9fa8d32a535e0edbd4a3217367eb",
      "brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
      "created_at": "2026-07-22T00:06:00Z",
      "final_required_criterion_ids": [
        "ending-000001"
      ],
      "initial_design_sha256": "e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce",
      "protagonist_end_state": "町と責任を分け合いながら、自分の意思で灯台を守っている。",
      "protagonist_start_state": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
      "schema_version": "1.0",
      "series_question": "灯台停止の原因を明らかにし、町は灯を誰の責任として守るのか。",
      "source_generation_id": "00000000",
      "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
      "volumes": [
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "withhold",
              "prohibited_disclosure": "町の最終的な役割分担を断定しない",
              "purpose": "共同責任という結末条件をまだ確定せず、個人責任の限界だけを示す",
              "required": true
            }
          ],
          "ending_function": "局所的な調査成功を与えつつ、町の管理記録へ疑問を広げる。",
          "estimated_chapter_count": 4,
          "local_resolution": "地下修理庫への進入経路を確保し、最初の設備調査を完了する。",
          "major_thread_targets": [
            {
              "purpose": "停止原因の問いと予備鍵の手掛かりを導入する",
              "required_action": "introduce",
              "start_progress": 0,
              "start_status": "open",
              "target_progress": 1,
              "target_status": "in_progress",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "孤立した義務感から協力へ動かす",
            "required_change": "単独で抱えず凪と調査根拠を共有する",
            "start_state_summary": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
            "target_state_summary": "凪と調査根拠を共有し、自分の意思で原因を追い始めている。"
          },
          "reader_question": "予備鍵の先に、誰が隠した停止原因の記録があるのか。",
          "relationship_change_targets": [
            {
              "purpose": "主要Relationshipの再始動",
              "relationship_id": "rel-000001",
              "required_change": "実務上の判断根拠を共有する",
              "start_state_summary": "能力は認めるが過去の対立を避け、必要最低限しか話さない。",
              "target_state_summary": "調査手順と根拠を共有し、実務上の信頼を取り戻し始める。"
            }
          ],
          "structural_role": "opening",
          "volume_function": "澪と凪を再会させ、予備鍵と修理庫という最初の実物手掛かりへ到達させる。",
          "volume_number": 1
        },
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "prepare",
              "prohibited_disclosure": "最終合意が成立したとは書かない",
              "purpose": "町の複数の担い手が必要だと読者に理解させる",
              "required": true
            }
          ],
          "ending_function": "原因を設備から制度へ拡大し、町の関係者を巻き込む。",
          "estimated_chapter_count": 4,
          "local_resolution": "故障箇所と記録欠落の時期を特定する。",
          "major_thread_targets": [
            {
              "purpose": "旧式切替器と欠落した台帳記録を結びつける",
              "required_action": "advance",
              "start_progress": 1,
              "start_status": "in_progress",
              "target_progress": 2,
              "target_status": "in_progress",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "個人対設備の問題を町の問題へ広げる",
            "required_change": "町の複数の立場を聞き、責任を共有する可能性を認める",
            "start_state_summary": "凪と調査根拠を共有し、自分の意思で原因を追い始めている。",
            "target_state_summary": "町の利害を聞き、自分だけで責任を背負わない選択肢を認めている。"
          },
          "reader_question": "管理記録の空白は事故なのか、意図的な隠蔽なのか。",
          "relationship_change_targets": [
            {
              "purpose": "誤解を解き信頼を深める",
              "relationship_id": "rel-000001",
              "required_change": "過去の両家の対立を互いに説明する",
              "start_state_summary": "調査手順と根拠を共有し、実務上の信頼を取り戻し始める。",
              "target_state_summary": "両家の対立を話し、互いの判断を相談できる。"
            }
          ],
          "structural_role": "midpoint",
          "volume_function": "修理庫と台帳を調べ、設備故障と町の管理空白が結びつく証拠を集める。",
          "volume_number": 2
        },
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "support",
              "prohibited_disclosure": "最終的な全町合意と再点灯を先取りしない",
              "purpose": "共同管理へ賛同する町の行動を積み上げる",
              "required": true
            }
          ],
          "ending_function": "真相開示を終え、最終巻の共同決断と再点灯へ移る。",
          "estimated_chapter_count": 3,
          "local_resolution": "停止原因と管理上の空白を町へ説明し、再点灯計画を合意可能な形にする。",
          "major_thread_targets": [
            {
              "purpose": "停止原因と管理責任を公の判断材料にする",
              "required_action": "advance",
              "start_progress": 2,
              "start_status": "in_progress",
              "target_progress": 3,
              "target_status": "in_progress",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "最終決断を町全体へ渡す",
            "required_change": "原因と責任の関係を公にし共同解決を要求する",
            "start_state_summary": "町の利害を聞き、自分だけで責任を背負わない選択肢を認めている。",
            "target_state_summary": "停止原因と町の管理責任を結びつけ、共同解決を公に求めている。"
          },
          "reader_question": "町は責任と作業を実際に分け合えるのか。",
          "relationship_change_targets": [
            {
              "purpose": "私的な信頼を公的な協力へ変える",
              "relationship_id": "rel-000001",
              "required_change": "町への説明を二人で引き受ける",
              "start_state_summary": "両家の対立を話し、互いの判断を相談できる。",
              "target_state_summary": "町への説明を共同で引き受け、対等な協力関係を公にする。"
            }
          ],
          "structural_role": "pre_final",
          "volume_function": "隠された判断と責任の所在を公にし、町へ共同管理の選択を迫る。",
          "volume_number": 3
        },
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "satisfy",
              "prohibited_disclosure": null,
              "purpose": "町の具体的な役割分担と再点灯を証拠化する",
              "required": true
            }
          ],
          "ending_function": "主要ThreadとEnding criterionを満たし、灯が共同の意思で維持される未来を示す。",
          "estimated_chapter_count": 3,
          "local_resolution": "町の役割分担が決まり、澪と凪が再点灯を見届ける。",
          "major_thread_targets": [
            {
              "purpose": "停止原因を確定し、安全な再点灯と共同管理を実現する",
              "required_action": "resolve",
              "start_progress": 3,
              "start_status": "in_progress",
              "target_progress": 4,
              "target_status": "resolved",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "主人公arcを完結させる",
            "required_change": "共同の役割を受け入れたうえで自分の意思で灯を守る",
            "start_state_summary": "停止原因と町の管理責任を結びつけ、共同解決を公に求めている。",
            "target_state_summary": "町と責任を分け合いながら、自分の意思で灯台を守っている。"
          },
          "reader_question": null,
          "relationship_change_targets": [
            {
              "purpose": "主要Relationshipを確立する",
              "relationship_id": "rel-000001",
              "required_change": "対等な共同作業として再点灯を完了する",
              "start_state_summary": "町への説明を共同で引き受け、対等な協力関係を公にする。",
              "target_state_summary": "互いの専門性と選択を信頼し、灯台を共同で支える。"
            }
          ],
          "structural_role": "final",
          "volume_function": "町の役割分担を成立させ、灯台を安全に再点灯して全ての主要条件を完結させる。",
          "volume_number": 4
        }
      ]
    },
    "story_clock": {
      "current_chapter_number": null,
      "current_order": 0,
      "current_scene_number": null,
      "current_volume_number": null,
      "last_scene_id": null,
      "parallel_group_id": null,
      "time_label": "初日の夕方"
    },
    "target": {
      "chapter_number": 1,
      "planning_level": "scene",
      "scene_number": 1,
      "target_plan_entry": {
        "completion_role": "opening",
        "emotional_change_target": "澪が凪の安全確認を拒まず聞く",
        "ending_criterion_ids": [],
        "pov_character_id": "char-000001",
        "purpose": "消えた主灯を確認し、澪と凪の現在の距離と日没期限を示す。",
        "required_beats": [
          "澪が消えたレンズを確認する",
          "凪が安全手順を求める",
          "日没までの時間が示される"
        ],
        "required_character_ids": [
          "char-000001",
          "char-000002"
        ],
        "required_location_id": "loc-000001",
        "scene_number": 1,
        "thread_action_ids": [
          "thread-000001"
        ]
      },
      "volume_number": 1
    },
    "temporal_rules": [
      {
        "record": {
          "created_scene_id": null,
          "description": "主灯は日没後に必要となり、初日は日没までに停止原因を特定しなければならない。",
          "fixed_rule": "初日の夕方から日没までが最初の調査期限である。",
          "id": "rule-000001",
          "kind": "deadline",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "temporal_rule",
          "related_ids": [
            "loc-000001"
          ],
          "scope": "volume"
        },
        "selection_reasons": [
          "scene_deadline"
        ]
      }
    ],
    "threads": [
      {
        "record": {
          "author_truth": "地下修理庫に残された旧式切替器と管理台帳が停止原因を示し、予備鍵がその調査を可能にする。",
          "created_scene_id": null,
          "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
          "id": "thread-000001",
          "presentation_rule": "予備鍵、修理庫、台帳、切替器の順に根拠を開示し、説明だけで真相を確定しない。",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "thread",
          "required": true,
          "resolution_condition": "旧式切替器の故障と管理記録の空白を公に確認し、安全な再点灯と共同管理を実現する。",
          "scope": "series",
          "thread_type": "major"
        },
        "relevant_evidence_ids": [],
        "selection_reasons": [
          "chapter_required_thread",
          "required_major_thread"
        ],
        "state": {
          "progress": 0,
          "thread_id": "thread-000001",
          "thread_status": "open",
          "volume_disposition": null
        }
      }
    ],
    "volume_design": {
      "accepted_candidate_sha256": "24f1e841f8c898db93d94cb4d8fcc2b8b498a1e567159b70f7b1cfb83a4288dc",
      "chapter_functions": [
        {
          "chapter_end_function": "hook",
          "chapter_number": 1,
          "function": "停止した主灯を確認し、予備鍵の存在を最初の手掛かりとして共有する。",
          "primary_change_target_id": "char-000001",
          "primary_change_target_type": "character",
          "required_thread_ids": [
            "thread-000001"
          ],
          "target_scene_count": 3
        },
        {
          "chapter_end_function": "escalation",
          "chapter_number": 2,
          "function": "予備鍵の所在を追い、澪と凪が互いの手順を信頼する必要を作る。",
          "primary_change_target_id": "rel-000001",
          "primary_change_target_type": "relationship",
          "required_thread_ids": [
            "thread-000001"
          ],
          "target_scene_count": 3
        },
        {
          "chapter_end_function": "revelation",
          "chapter_number": 3,
          "function": "地下修理庫を開け、旧設備と欠落記録の存在を確認する。",
          "primary_change_target_id": "char-000001",
          "primary_change_target_type": "character",
          "required_thread_ids": [
            "thread-000001"
          ],
          "target_scene_count": 3
        },
        {
          "chapter_end_function": "bridge",
          "chapter_number": 4,
          "function": "安全確認を終え、共同記録を残して次巻の台帳調査へ移る。",
          "primary_change_target_id": "rel-000001",
          "primary_change_target_type": "relationship",
          "required_thread_ids": [
            "thread-000001"
          ],
          "target_scene_count": 3
        }
      ],
      "created_at": "2026-07-22T00:07:00Z",
      "ending_criterion_targets": [
        {
          "criterion_id": "ending-000001",
          "plan_action": "withhold",
          "prohibited_disclosure": "町の最終合意を成立済みとして書かない",
          "purpose": "個人だけでは灯を守れない兆候を示す",
          "required": true
        }
      ],
      "ending_function": {
        "final_image_or_decision": "澪と凪が同じ調査記録へ署名し、欠けた台帳の頁を見つめる。",
        "local_resolution": "修理庫への進入と最初の設備確認を完了する。",
        "prohibited_outcomes": [
          "停止原因を全て説明だけで確定する",
          "町が既に共同管理へ合意する"
        ],
        "series_transition": "発見した台帳の欠落を追い、町の管理責任へ調査を広げる。"
      },
      "major_conflict": {
        "conflict_statement": "日没が近づく中、閉ざされた修理庫と不完全な記録を、疎遠な二人が安全手順を守りながら調べなければならない。",
        "escalation_rule": "各章で時間制約、設備上の障害、過去の対立のいずれかを一段強める。",
        "opposing_force_ids": [],
        "resolution_condition": "地下修理庫へ入り、設備と記録の最初の異常を共同で確認する。",
        "stakes": "原因を特定できなければ主灯を安全に戻せず、港と町の信頼が灯台守の家へ集中して崩れる。"
      },
      "preceding_volume_handoff_path": null,
      "preceding_volume_handoff_sha256": null,
      "protagonist_change": {
        "character_id": "char-000001",
        "purpose": "家の責任を一人で抱える状態から、凪との共同調査へ移す。",
        "required_turns": [
          {
            "description": "凪の安全確認を受け入れる",
            "purpose": "単独行動を止める",
            "sequence": 1
          },
          {
            "description": "予備鍵の情報を凪と共有する",
            "purpose": "根拠を共有する",
            "sequence": 2
          },
          {
            "description": "修理庫調査の役割を分ける",
            "purpose": "協力を行動にする",
            "sequence": 3
          },
          {
            "description": "調査結果を二人の共同記録に残す",
            "purpose": "次巻へ共有責任を持ち越す",
            "sequence": 4
          }
        ],
        "start_state_summary": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
        "target_state_summary": "凪と調査根拠を共有し、自分の意思で原因を追い始めている。"
      },
      "reader_question": "予備鍵の先に、誰が隠した停止原因の記録があるのか。",
      "relationship_changes": [
        {
          "purpose": "主要Relationshipの再始動",
          "relationship_id": "rel-000001",
          "required_change": "実務上の判断根拠を共有する",
          "required_turns": [
            {
              "description": "互いの安全判断を確認する",
              "purpose": "最低限の信頼を作る",
              "sequence": 1
            },
            {
              "description": "過去の反発より調査を優先する",
              "purpose": "共同作業を成立させる",
              "sequence": 2
            },
            {
              "description": "共同記録へ署名する",
              "purpose": "協力を継続可能にする",
              "sequence": 3
            }
          ],
          "start_state_summary": "能力は認めるが過去の対立を避け、必要最低限しか話さない。",
          "target_state_summary": "調査手順と根拠を共有し、実務上の信頼を取り戻し始める。"
        }
      ],
      "schema_version": "1.0",
      "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
      "source_generation_id": "00000000",
      "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
      "starting_state_summary": "初日の夕方。主灯は停止し、澪と凪は岬の灯台で疎遠なまま調査を始める。主要Threadは未導入である。",
      "target_chapter_count": 4,
      "thread_actions": [
        {
          "purpose": "予備鍵と修理庫を停止原因の問いへ接続する",
          "required": true,
          "required_action": "introduce",
          "start_progress": 0,
          "start_status": "open",
          "target_progress": 1,
          "target_status": "in_progress",
          "thread_id": "thread-000001"
        }
      ],
      "title": "閉ざされた修理庫",
      "volume_number": 1,
      "volume_promise": "澪と凪が再び協力し、灯台停止の最初の物的手掛かりへ到達する。"
    },
    "world_entities": [
      {
        "record": {
          "created_scene_id": null,
          "description": "灯台の旧管理台帳に記録された小型の真鍮鍵。",
          "id": "item-000001",
          "immutable_rules": [
            "地下修理庫の錠に対応する"
          ],
          "kind": "item",
          "name": "真鍮の予備鍵",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "world_entity",
          "scope": "series",
          "sensory_anchors": [
            "掌に残る冷たい重み",
            "緑青の浮いた縁"
          ]
        },
        "selection_reasons": [
          "knowledge_subject",
          "scene_clue"
        ]
      },
      {
        "record": {
          "created_scene_id": null,
          "description": "断崖の先に建つ石造灯台。主灯室、螺旋階段、地下の修理庫がある。",
          "id": "loc-000001",
          "immutable_rules": [
            "主灯は日没後に点灯する",
            "地下修理庫は専用鍵でのみ開く"
          ],
          "kind": "location",
          "name": "岬の灯台",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "world_entity",
          "scope": "series",
          "sensory_anchors": [
            "塩を含んだ冷たい風",
            "消えた主灯の黒いレンズ",
            "石壁を伝う低い振動"
          ]
        },
        "selection_reasons": [
          "scene_location"
        ]
      }
    ]
  },
  "prompt_version": "sc-01-v1",
  "response_schema_version": "scene-card-content-v1",
  "schema_version": "1.0",
  "sensitivity": "private_author",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "source_refs": [
    {
      "generation_id": null,
      "path": "input/brief.json",
      "required": true,
      "role": "brief",
      "sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7"
    },
    {
      "generation_id": null,
      "path": "runtime/effective-config.json",
      "required": true,
      "role": "effective_config",
      "sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c"
    },
    {
      "generation_id": null,
      "path": "canon/initial-design.json",
      "required": true,
      "role": "initial_design",
      "sha256": "e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce"
    },
    {
      "generation_id": null,
      "path": "plans/series-map.json",
      "required": true,
      "role": "series_map",
      "sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294"
    },
    {
      "generation_id": null,
      "path": "plans/volumes/v01/volume-design.json",
      "required": true,
      "role": "volume_design",
      "sha256": "c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e"
    },
    {
      "generation_id": null,
      "path": "plans/volumes/v01/chapters/c001/chapter-design.json",
      "required": true,
      "role": "chapter_design",
      "sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/current-canon.json",
      "required": true,
      "role": "current_canon",
      "sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/knowledge-items.json",
      "required": true,
      "role": "knowledge_items",
      "sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/story-state.json",
      "required": true,
      "role": "story_state",
      "sha256": "d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/evidence-index.json",
      "required": true,
      "role": "evidence_index",
      "sha256": "d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/generation-manifest.json",
      "required": true,
      "role": "generation_manifest",
      "sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/commit-manifest.json",
      "required": true,
      "role": "commit_manifest",
      "sha256": "0dd625924fd5cef951ba2aceb3547c91bbef8ba0a0814642fd643cff67d3ac05"
    }
  ],
  "target_id": "v01-c001-s001",
  "token_budget": {
    "context_payload_limit": 27028,
    "final_input_tokens": 5740,
    "hard_input_limit": 27648,
    "max_operation_input_tokens": 32768,
    "model_context_window_tokens": 32768,
    "operation_key": "scene_card",
    "overflowed": false,
    "payload_tokens": 5120,
    "protocol_overhead_tokens": 1024,
    "reserved_output_tokens": 4096,
    "static_prompt_tokens": 620,
    "token_count_method": "provider_tokenizer",
    "tokenizer_id": "fixture-tokenizer-v1"
  },
  "view_type": "planner"
}
```

Canonical SHA-256:

```text
3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e
```

This private Author view contains Thread author truth and Ending source text. The Scene-card response below must not copy either value.

# Part II: Scene-card candidate and checkpoint
## 5. SC-01 response

```text
EXACT RESPONSE
operation = SC-01
example_id = EX-POS-SCENE-001
```

```json
{
  "canon_metadata_change_targets": [],
  "character_knowledge_targets": [
    {
      "character_id": "char-000001",
      "fact_id": "fact-000001",
      "purpose": "澪が予備鍵の用途を理解し、共同調査の次の行動を選べるようにする。",
      "required": true,
      "target_status": "knows"
    }
  ],
  "emotional_change_target": "澪が凪への反発より安全な共同調査を優先する。",
  "ending_criterion_targets": [],
  "location_id": "loc-000001",
  "new_item_policy": {
    "allow_knowledge_items": false,
    "allowed_types": [],
    "max_items": 0,
    "max_scope": null,
    "purpose": "このSceneは既存の人物・場所・予備鍵・主要Threadだけで完結し、新しい永続項目を必要としない。"
  },
  "parallel_group_id": null,
  "participant_ids": [
    "char-000001",
    "char-000002"
  ],
  "pov_character_id": "char-000001",
  "reader_disclosures": [
    {
      "fact_id": "fact-000001",
      "purpose": "予備鍵が地下修理庫の錠に対応することを読者へ明確にする。",
      "required": true,
      "target_status": "revealed"
    }
  ],
  "relationship_change_targets": [
    {
      "purpose": "主要Relationshipの実務上の信頼回復を開始する。",
      "relationship_id": "rel-000001",
      "required": true,
      "required_change": "澪から凪へのtrustをlowからmediumへ進める行動を描く。",
      "start_state_summary": "澪は凪の能力を認めながら、自分の家を責めていると思い必要最低限しか頼ろうとしない。",
      "target_state_summary": "澪は凪の安全判断を受け入れ、日誌を共有して共同点検を求める。"
    }
  ],
  "required_beats": [
    "澪が消えたレンズを確認する",
    "凪が安全手順を求める",
    "日没までの時間が示される",
    "凪が地下修理庫の予備鍵について説明する",
    "澪が日誌を共有し共同点検を選ぶ"
  ],
  "required_temporal_rule_ids": [
    "rule-000001"
  ],
  "required_world_entity_ids": [
    "item-000001",
    "loc-000001"
  ],
  "scene_purpose": "消えた主灯と日没期限を確認し、澪が凪の安全判断と予備鍵の知識を受け入れて共同点検を選ぶことで、灯台停止の主要Threadを導入する。",
  "thread_actions": [
    {
      "operation": "introduce",
      "purpose": "主灯停止の原因が地下修理庫の調査へつながる問いを具体的に提示する。",
      "required": true,
      "target_progress": 1,
      "target_status": "in_progress",
      "thread_id": "thread-000001"
    }
  ],
  "time_label": "初日の日没前",
  "time_relation": "later"
}
```

Canonical SHA-256:

```text
c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17
```

## 6. Saved SC-02 Review

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/review.json
example_id = EX-POS-SCENE-FIX-REVIEW-001
```

```json
{
  "call_id": "call-000015",
  "candidate_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/scene-card.json",
  "candidate_sha256": "c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17",
  "candidate_version": 1,
  "created_at": "2026-07-22T00:10:01Z",
  "input_snapshot_sha256": "3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e",
  "issue_counts": {
    "error": 0,
    "total": 0,
    "warning": 0
  },
  "issues": [],
  "operation_id": "SC-02",
  "review_prompt_version": "sc-02-v1",
  "review_round": 1,
  "review_schema_version": "review-v1",
  "review_status": "issues_empty",
  "reviewed_artifact_role": "scene_card",
  "schema_version": "1.0",
  "summary": "Scene function、現在State、開示境界、更新目標に重大な問題はありません。",
  "target_id": "v01-c001-s001"
}
```

Canonical SHA-256:

```text
0492efdf2feb3038382b61d67033e8bcd8cbd03dc04effa331b42ec1822820a6
```

## 7. Scene-card Candidate manifest

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json
example_id = EX-POS-SCENE-FIX-CAND-001
```

```json
{
  "candidate_artifact_format": "json",
  "candidate_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/scene-card.json",
  "candidate_sha256": "c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17",
  "candidate_status": "ready_for_adoption",
  "candidate_version": 1,
  "completion_audit_attempt": null,
  "created_at": "2026-07-22T00:10:00Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "input_snapshot_path": "runtime/context-snapshots/sc-01/v01-c001-s001/3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e.json",
  "input_snapshot_sha256": "3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e",
  "last_call_id": "call-000014",
  "last_structurally_valid": true,
  "manifest_version": "1.0",
  "next_stage": "SC-CHK",
  "operation_id": "SC-01",
  "previous_candidate_manifest_path": null,
  "previous_candidate_manifest_sha256": null,
  "processor_type": "llm_generate",
  "prompt_version": "sc-01-v1",
  "residual_issues_path": null,
  "response_schema_version": "scene-card-content-v1",
  "response_structure_retries_used": 0,
  "review_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/review.json",
  "review_sha256": "0492efdf2feb3038382b61d67033e8bcd8cbd03dc04effa331b42ec1822820a6",
  "revision_rounds_used": 0,
  "target_id": "v01-c001-s001",
  "transport_retries_used": 0,
  "updated_at": "2026-07-22T00:10:01Z"
}
```

Canonical SHA-256:

```text
ab18dbec13c898a4cda42f73c65f9b9517e2277b9ba2c376fe779a21d38d958b
```

## 8. Frozen Scene card

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/scene-card.json
example_id = EX-POS-SCENE-002
```

```json
{
  "accepted_candidate_sha256": "c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17",
  "allowed_update_targets": [
    {
      "field_rules": [
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/current_goal"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/current_pressure"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/emotional_state"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/location_id"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/physical_condition"
        }
      ],
      "target_id": "char-000001",
      "target_kind": "existing_item",
      "target_type": "character_state"
    },
    {
      "field_rules": [
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/current_goal"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/current_pressure"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/emotional_state"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/location_id"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/physical_condition"
        }
      ],
      "target_id": "char-000002",
      "target_kind": "existing_item",
      "target_type": "character_state"
    },
    {
      "field_rules": [
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/a_to_b/current_intention"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/a_to_b/emotional_stance"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/a_to_b/perception"
        },
        {
          "allowed_operations": [
            "transition"
          ],
          "field_path": "/a_to_b/trust"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/b_to_a/current_intention"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/b_to_a/emotional_stance"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/b_to_a/perception"
        },
        {
          "allowed_operations": [
            "transition"
          ],
          "field_path": "/b_to_a/trust"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/public_relation"
        },
        {
          "allowed_operations": [
            "set"
          ],
          "field_path": "/shared_state"
        }
      ],
      "target_id": "rel-000001",
      "target_kind": "existing_item",
      "target_type": "relationship_state"
    },
    {
      "allowed_after_statuses": [
        "knows"
      ],
      "audience_id": "char-000001",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "start_status": "unknown",
      "target_kind": "knowledge_state"
    },
    {
      "allowed_after_statuses": [
        "revealed"
      ],
      "audience_id": null,
      "audience_type": "reader",
      "fact_id": "fact-000001",
      "start_status": "hinted",
      "target_kind": "knowledge_state"
    },
    {
      "allowed_operations": [
        "introduce"
      ],
      "start_progress": 0,
      "start_status": "open",
      "target_kind": "thread_state",
      "target_progress": 1,
      "target_status": "in_progress",
      "thread_id": "thread-000001"
    },
    {
      "allowed_time_relations": [
        "later"
      ],
      "target_kind": "story_clock",
      "target_parallel_group_id": null,
      "target_time_label": "初日の日没前"
    }
  ],
  "canon_metadata_change_targets": [],
  "chapter_completion_role": "opening",
  "chapter_design_path": "plans/volumes/v01/chapters/c001/chapter-design.json",
  "chapter_design_sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5",
  "chapter_number": 1,
  "character_knowledge_targets": [
    {
      "character_id": "char-000001",
      "fact_id": "fact-000001",
      "purpose": "澪が予備鍵の用途を理解し、共同調査の次の行動を選べるようにする。",
      "required": true,
      "start_status": "unknown",
      "target_status": "knows"
    }
  ],
  "created_at": "2026-07-22T00:10:02Z",
  "emotional_change_target": "澪が凪への反発より安全な共同調査を優先する。",
  "ending_criterion_targets": [],
  "forbidden_disclosures": [
    {
      "constraint_id": "fd-0001",
      "label": "主人公だけが全責任を負う結末",
      "reason": "澪だけが灯を守るべきだという結論や称賛へ進めない。",
      "release_hint": null,
      "source_id": null,
      "source_type": "brief_avoid"
    },
    {
      "constraint_id": "fd-0002",
      "label": "修理庫内部の停止原因",
      "reason": "今回は予備鍵の用途までを開示し、修理庫内の設備故障や台帳内容を確定しない。",
      "release_hint": "修理庫を実際に調べるScene以降",
      "source_id": "fact-000001",
      "source_type": "knowledge_item"
    },
    {
      "constraint_id": "fd-0003",
      "label": "灯台停止の確定原因",
      "reason": "主要Threadは導入に留め、原因を解決または断定しない。",
      "release_hint": "複数の物的根拠が揃った後",
      "source_id": "thread-000001",
      "source_type": "thread"
    },
    {
      "constraint_id": "fd-0004",
      "label": "町の最終的な役割分担",
      "reason": "町が既に共同管理へ合意したとは書かない。",
      "release_hint": "最終巻の合意Scene",
      "source_id": "ending-000001",
      "source_type": "ending_criterion"
    }
  ],
  "length_guidance": {
    "counting_rule": "unicode_code_points_excluding_final_lf",
    "guide_max_chars": 2200,
    "guide_min_chars": 500,
    "hard_limit": false,
    "target_chars": 1200
  },
  "location_id": "loc-000001",
  "new_item_policy": {
    "allow_knowledge_items": false,
    "allowed_types": [],
    "max_items": 0,
    "max_scope": null,
    "purpose": "このSceneは既存の人物・場所・予備鍵・主要Threadだけで完結し、新しい永続項目を必要としない。"
  },
  "parallel_group_id": null,
  "participant_ids": [
    "char-000001",
    "char-000002"
  ],
  "pov_character_id": "char-000001",
  "reader_disclosures": [
    {
      "fact_id": "fact-000001",
      "purpose": "予備鍵が地下修理庫の錠に対応することを読者へ明確にする。",
      "required": true,
      "start_status": "hinted",
      "target_status": "revealed"
    }
  ],
  "relationship_change_targets": [
    {
      "purpose": "主要Relationshipの実務上の信頼回復を開始する。",
      "relationship_id": "rel-000001",
      "required": true,
      "required_change": "澪から凪へのtrustをlowからmediumへ進める行動を描く。",
      "start_state_summary": "澪は凪の能力を認めながら、自分の家を責めていると思い必要最低限しか頼ろうとしない。",
      "target_state_summary": "澪は凪の安全判断を受け入れ、日誌を共有して共同点検を求める。"
    }
  ],
  "required_beats": [
    "澪が消えたレンズを確認する",
    "凪が安全手順を求める",
    "日没までの時間が示される",
    "凪が地下修理庫の予備鍵について説明する",
    "澪が日誌を共有し共同点検を選ぶ"
  ],
  "required_temporal_rule_ids": [
    "rule-000001"
  ],
  "required_world_entity_ids": [
    "item-000001",
    "loc-000001"
  ],
  "scene_id": "v01-c001-s001",
  "scene_number": 1,
  "scene_purpose": "消えた主灯と日没期限を確認し、澪が凪の安全判断と予備鍵の知識を受け入れて共同点検を選ぶことで、灯台停止の主要Threadを導入する。",
  "schema_version": "1.0",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "thread_actions": [
    {
      "operation": "introduce",
      "purpose": "主灯停止の原因が地下修理庫の調査へつながる問いを具体的に提示する。",
      "required": true,
      "start_progress": 0,
      "start_status": "open",
      "target_progress": 1,
      "target_status": "in_progress",
      "thread_id": "thread-000001"
    }
  ],
  "time_label": "初日の日没前",
  "time_relation": "later",
  "volume_number": 1
}
```

Canonical SHA-256:

```text
74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194
```

Code injects all source identity, starting Thread/Knowledge values, safe forbidden disclosures, update authorization, length guidance, and Scene coordinates.

## 9. CARD_ACCEPTED Checkpoint manifest

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json
example_id = EX-POS-SCENE-FIX-CHK-001
```

```json
{
  "commit_plan_path": null,
  "commit_plan_sha256": null,
  "continuity_candidate_manifest_path": null,
  "continuity_delta_path": null,
  "continuity_delta_sha256": null,
  "created_at": "2026-07-22T00:10:02Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "manifest_version": "1.0",
  "phase": "CARD_ACCEPTED",
  "prose_candidate_manifest_path": null,
  "prose_path": null,
  "prose_sha256": null,
  "scene_card_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json",
  "scene_card_path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "staging_transaction_path": null,
  "updated_at": "2026-07-22T00:10:02Z"
}
```

Canonical SHA-256:

```text
a600d23e49dc8a69cfd5a7ebf219a627ae19ff50e1b1b36556bcbe70fc498dd9
```

# Part III: Writer Context and prose
## 10. Writer Context snapshot

```text
EXACT ARTIFACT
path = runtime/context-snapshots/prose-01/v01-c001-s001/49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda.json
example_id = EX-POS-SCENE-003
```

```json
{
  "builder_id": "prose_writer_builder",
  "builder_version": "context-builders-v1",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "exclusions": [],
  "operation_id": "PROSE-01",
  "payload": {
    "context_identity": {
      "editorial_profile_id": "default-ja",
      "previous_handoff_sha256": null,
      "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
      "scene_id": "v01-c001-s001",
      "source_generation_id": "00000000"
    },
    "pov_character": {
      "aliases": [],
      "appearance_anchor": "潮に色褪せた青い外套と、腰の小さな工具袋。",
      "background": "岬の灯台守の家に生まれ、家業を継ぐことを当然とされてきた見習い。",
      "character_id": "char-000001",
      "core_trait": "粘り強い",
      "current_goal": "日没までに灯台停止の原因を特定する",
      "current_pressure": "町が灯台守の家だけを責め始める前に結果を出す必要がある",
      "emotional_state": "焦りを抑えて手順を守ろうとしている",
      "immutable_facts": [
        "凪とは幼なじみである",
        "灯台の主灯と日誌の基本手順を知っている"
      ],
      "location_id": "loc-000001",
      "name": "澪",
      "physical_condition": "疲労や負傷はない",
      "role": "protagonist",
      "speech_anchor": "短く確かめるように話し、決めた後は言い切る。",
      "values": [
        "灯を絶やさないこと",
        "自分で選んだ責任"
      ]
    },
    "pov_known_facts": [
      {
        "fact_id": "fact-000001",
        "scene_purpose": "凪の説明を受け、地下修理庫の錠に対応することを理解する。",
        "scene_target_status": "knows",
        "status": "unknown",
        "writer_visible_label": "予備鍵の役割"
      }
    ],
    "previous_handoff": null,
    "reader_known_facts": [
      {
        "fact_id": "fact-000001",
        "scene_purpose": "予備鍵と地下修理庫の対応を明確にする。",
        "scene_target_status": "revealed",
        "status": "hinted",
        "writer_visible_label": "予備鍵の役割"
      }
    ],
    "scene_card": {
      "canon_change_targets": [],
      "chapter_completion_role": "opening",
      "chapter_number": 1,
      "character_knowledge_targets": [
        {
          "character_id": "char-000001",
          "fact_id": "fact-000001",
          "purpose": "澪が予備鍵の用途を理解し、共同調査の次の行動を選べるようにする。",
          "required": true,
          "start_status": "unknown",
          "target_status": "knows"
        }
      ],
      "emotional_change_target": "澪が凪への反発より安全な共同調査を優先する。",
      "ending_criterion_targets": [],
      "forbidden_disclosures": [
        {
          "constraint_id": "fd-0001",
          "label": "主人公だけが全責任を負う結末",
          "reason": "澪だけが灯を守るべきだという結論や称賛へ進めない。",
          "release_hint": null,
          "source_id": null,
          "source_type": "brief_avoid"
        },
        {
          "constraint_id": "fd-0002",
          "label": "修理庫内部の停止原因",
          "reason": "今回は予備鍵の用途までを開示し、修理庫内の設備故障や台帳内容を確定しない。",
          "release_hint": "修理庫を実際に調べるScene以降",
          "source_id": "fact-000001",
          "source_type": "knowledge_item"
        },
        {
          "constraint_id": "fd-0003",
          "label": "灯台停止の確定原因",
          "reason": "主要Threadは導入に留め、原因を解決または断定しない。",
          "release_hint": "複数の物的根拠が揃った後",
          "source_id": "thread-000001",
          "source_type": "thread"
        },
        {
          "constraint_id": "fd-0004",
          "label": "町の最終的な役割分担",
          "reason": "町が既に共同管理へ合意したとは書かない。",
          "release_hint": "最終巻の合意Scene",
          "source_id": "ending-000001",
          "source_type": "ending_criterion"
        }
      ],
      "length_guidance": {
        "counting_rule": "unicode_code_points_excluding_final_lf",
        "guide_max_chars": 2200,
        "guide_min_chars": 500,
        "hard_limit": false,
        "target_chars": 1200
      },
      "location_id": "loc-000001",
      "new_item_policy": {
        "allow_knowledge_items": false,
        "allowed_types": [],
        "max_items": 0,
        "max_scope": null,
        "purpose": "このSceneは既存の人物・場所・予備鍵・主要Threadだけで完結し、新しい永続項目を必要としない。"
      },
      "parallel_group_id": null,
      "participant_ids": [
        "char-000001",
        "char-000002"
      ],
      "pov_character_id": "char-000001",
      "reader_disclosures": [
        {
          "fact_id": "fact-000001",
          "purpose": "予備鍵が地下修理庫の錠に対応することを読者へ明確にする。",
          "required": true,
          "start_status": "hinted",
          "target_status": "revealed"
        }
      ],
      "relationship_change_targets": [
        {
          "purpose": "主要Relationshipの実務上の信頼回復を開始する。",
          "relationship_id": "rel-000001",
          "required": true,
          "required_change": "澪から凪へのtrustをlowからmediumへ進める行動を描く。",
          "start_state_summary": "澪は凪の能力を認めながら、自分の家を責めていると思い必要最低限しか頼ろうとしない。",
          "target_state_summary": "澪は凪の安全判断を受け入れ、日誌を共有して共同点検を求める。"
        }
      ],
      "required_beats": [
        "澪が消えたレンズを確認する",
        "凪が安全手順を求める",
        "日没までの時間が示される",
        "凪が地下修理庫の予備鍵について説明する",
        "澪が日誌を共有し共同点検を選ぶ"
      ],
      "scene_id": "v01-c001-s001",
      "scene_number": 1,
      "scene_purpose": "消えた主灯と日没期限を確認し、澪が凪の安全判断と予備鍵の知識を受け入れて共同点検を選ぶことで、灯台停止の主要Threadを導入する。",
      "thread_actions": [
        {
          "operation": "introduce",
          "purpose": "主灯停止の原因が地下修理庫の調査へつながる問いを具体的に提示する。",
          "required": true,
          "start_progress": 0,
          "start_status": "open",
          "target_progress": 1,
          "target_status": "in_progress",
          "thread_id": "thread-000001"
        }
      ],
      "time_label": "初日の日没前",
      "time_relation": "later",
      "volume_number": 1
    },
    "style_profile": {
      "dialogue_guidance": "会話は人物ごとのspeech anchorを保ち、説明の代替ではなく判断と感情の変化を担わせる。",
      "forbidden_content": [
        "主人公だけが全責任を負う結末",
        "説明だけで謎を解決する場面"
      ],
      "language_tag": "ja-JP",
      "narrative_person": "third_person",
      "pov_distance": "close",
      "pov_policy": "single_pov_per_scene",
      "profile_id": "default-ja",
      "prose_constraints": [
        "do not add unsupported Canon facts",
        "do not reveal forbidden disclosures",
        "maintain one POV per scene",
        "preserve established speech anchors"
      ],
      "tense": "past"
    },
    "visible_characters": [
      {
        "aliases": [],
        "appearance_anchor": "油の染みた革手袋と、右手首の古い傷。",
        "character_id": "char-000002",
        "immutable_facts": [
          "澪とは幼なじみである",
          "港と灯台の旧式機構に詳しい"
        ],
        "location_id": "loc-000001",
        "name": "凪",
        "observable_physical_condition": "右手首を庇うことがあるが作業できる",
        "relationship_role_labels": [
          "疎遠な幼なじみ",
          "設備調査の協力者"
        ],
        "role": "ally",
        "scene_intention_label": "主灯へ手を入れる前に安全確認と共同点検を求める",
        "speech_anchor": "確認事項を順番に挙げ、断定の前に根拠を求める。"
      }
    ],
    "visible_relationships": [
      {
        "other_to_pov": {
          "current_intention": null,
          "emotional_stance": "距離を保ちながら心配しているように見える",
          "perception": "澪の手順を確かめている",
          "trust": null
        },
        "participant_a_id": "char-000001",
        "participant_b_id": "char-000002",
        "pov_to_other": {
          "current_intention": "必要な範囲だけ協力を得る",
          "emotional_stance": "反発を隠しながら助けを求めている",
          "perception": "設備には頼れるが、自分の家を責めていると思っている",
          "trust": "low"
        },
        "public_relation": "必要な作業のために再会した疎遠な幼なじみ",
        "relationship_id": "rel-000001",
        "relationship_type": "friendship",
        "scene_target": "澪が凪の安全判断を受け入れ、日誌を共有して共同点検を選ぶ。",
        "shared_state": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。"
      }
    ],
    "visible_temporal_rules": [
      {
        "description": "主灯は日没後に必要となり、初日は日没までに停止原因を特定しなければならない。",
        "fixed_rule": "初日の夕方から日没までが最初の調査期限である。",
        "kind": "deadline",
        "temporal_rule_id": "rule-000001"
      }
    ],
    "visible_threads": [
      {
        "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
        "presentation_constraint": "予備鍵と修理庫を手掛かりとして示すが、停止原因を確定しない。",
        "progress": 0,
        "purpose": "主灯停止の原因が地下修理庫の調査へつながる問いを具体的に提示する。",
        "scene_operation": "introduce",
        "status": "open",
        "target_progress": 1,
        "target_status": "in_progress",
        "thread_id": "thread-000001",
        "thread_type": "major"
      }
    ],
    "visible_world": [
      {
        "description": "灯台の旧管理台帳に記録された小型の真鍮鍵。",
        "immutable_rules": [
          "地下修理庫の錠に対応する"
        ],
        "kind": "item",
        "name": "真鍮の予備鍵",
        "sensory_anchors": [
          "掌に残る冷たい重み",
          "緑青の浮いた縁"
        ],
        "world_entity_id": "item-000001"
      },
      {
        "description": "断崖の先に建つ石造灯台。主灯室、螺旋階段、地下の修理庫がある。",
        "immutable_rules": [
          "主灯は日没後に点灯する",
          "地下修理庫は専用鍵でのみ開く"
        ],
        "kind": "location",
        "name": "岬の灯台",
        "sensory_anchors": [
          "塩を含んだ冷たい風",
          "消えた主灯の黒いレンズ",
          "石壁を伝う低い振動"
        ],
        "world_entity_id": "loc-000001"
      }
    ]
  },
  "prompt_version": "prose-01-v1",
  "response_schema_version": null,
  "schema_version": "1.0",
  "sensitivity": "writer_safe",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "source_refs": [
    {
      "generation_id": null,
      "path": "runtime/effective-config.json",
      "required": true,
      "role": "effective_config",
      "sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c"
    },
    {
      "generation_id": null,
      "path": "plans/volumes/v01/chapters/c001/chapter-design.json",
      "required": true,
      "role": "chapter_design",
      "sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5"
    },
    {
      "generation_id": "00000000",
      "path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
      "required": true,
      "role": "scene_card",
      "sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/current-canon.json",
      "required": true,
      "role": "current_canon",
      "sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/knowledge-items.json",
      "required": true,
      "role": "knowledge_items",
      "sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/story-state.json",
      "required": true,
      "role": "story_state",
      "sha256": "d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/generation-manifest.json",
      "required": true,
      "role": "generation_manifest",
      "sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40"
    }
  ],
  "target_id": "v01-c001-s001",
  "token_budget": {
    "context_payload_limit": 23072,
    "final_input_tokens": 2890,
    "hard_input_limit": 23552,
    "max_operation_input_tokens": 32768,
    "model_context_window_tokens": 32768,
    "operation_key": "prose",
    "overflowed": false,
    "payload_tokens": 2410,
    "protocol_overhead_tokens": 1024,
    "reserved_output_tokens": 8192,
    "static_prompt_tokens": 480,
    "token_count_method": "provider_tokenizer",
    "tokenizer_id": "fixture-tokenizer-v1"
  },
  "view_type": "writer"
}
```

Canonical SHA-256:

```text
49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda
```

Byte-search requirements:

```text
Thread author_truth: absent
Thread resolution_condition: absent
Knowledge author_truth: absent
Ending source_ending_text: absent
non-POV private goal/pressure/emotion: absent
allowed_update_targets: absent from Writer Scene-card projection
```

## 11. PROSE-01 response and frozen prose

```text
EXACT RESPONSE
operation = PROSE-01

EXACT ARTIFACT paths =
  runtime/candidates/scenes/v01/c001/s001/prose/v0001/prose.md
  runtime/checkpoints/scenes/v01/c001/s001/prose.md
  artifacts/scenes/v01/c001/s001/prose.md

example_id = EX-POS-SCENE-004
```

```markdown
主灯のレンズは、夕方の光を黒く返していた。澪は制御盤へ手を伸ばしたが、凪の革手袋がその前へ差し出された。

「通電の前に、手順を一つずつ確認する。急いで壊したら、今夜だけの問題じゃなくなる」

反発の言葉が喉まで上がった。灯台を守るのは自分の家だ、と言えば簡単だった。けれど石壁の奥から伝わる振動はいつもより低く、制御盤の表示は二つ同時に消えている。澪は手を引いた。

西窓の光は細く、日没まで一時間もなかった。

凪は古い点検口を指でなぞった。「主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない」

澪が地下へ続く扉を見やると、凪は首を振った。地下修理庫を開ける予備鍵が要る、と凪は言った。凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。澪は家の管理日誌を抱え直した。日誌には空欄が多く、鍵の所在を示す頁も見当たらない。

一人で探せば早い、と考えた瞬間、右手首を庇いながらも配線の順を確かめる凪の横顔が見えた。凪は急かさず、次に調べる場所だけを待っていた。

澪は日誌を凪の前に開き、点検を一緒に進めようと言った。

凪は短くうなずき、二人の間へ工具箱を置いた。消えた灯の原因はまだ見えない。それでも、何を確かめるべきかという問いだけは、もう澪一人のものではなかった。
```

Canonical prose SHA-256:

```text
45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b
```

Character count:

```text
549
```

Counting excludes the single final LF.

## 12. Saved PROSE-02 Review

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/prose/v0001/review.json
example_id = EX-POS-SCENE-FIX-REVIEW-002
```

```json
{
  "call_id": "call-000017",
  "candidate_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/prose.md",
  "candidate_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "candidate_version": 1,
  "created_at": "2026-07-22T00:12:01Z",
  "input_snapshot_sha256": "49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda",
  "issue_counts": {
    "error": 0,
    "total": 0,
    "warning": 0
  },
  "issues": [],
  "operation_id": "PROSE-02",
  "review_prompt_version": "prose-02-v1",
  "review_round": 1,
  "review_schema_version": "review-v1",
  "review_status": "issues_empty",
  "reviewed_artifact_role": "prose",
  "schema_version": "1.0",
  "summary": "Scene function、現在State、開示境界、更新目標に重大な問題はありません。",
  "target_id": "v01-c001-s001"
}
```

Canonical SHA-256:

```text
2307b5894dbce018c15d371fbd3f9739912bacfe9511585d891b31b52b0f0a47
```

## 13. Prose Candidate manifest

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/prose/v0001/candidate-manifest.json
example_id = EX-POS-SCENE-FIX-CAND-002
```

```json
{
  "candidate_artifact_format": "markdown",
  "candidate_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/prose.md",
  "candidate_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "candidate_status": "ready_for_adoption",
  "candidate_version": 1,
  "completion_audit_attempt": null,
  "created_at": "2026-07-22T00:12:00Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "input_snapshot_path": "runtime/context-snapshots/prose-01/v01-c001-s001/49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda.json",
  "input_snapshot_sha256": "49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda",
  "last_call_id": "call-000016",
  "last_structurally_valid": true,
  "manifest_version": "1.0",
  "next_stage": "PROSE-CHK",
  "operation_id": "PROSE-01",
  "previous_candidate_manifest_path": null,
  "previous_candidate_manifest_sha256": null,
  "processor_type": "llm_generate",
  "prompt_version": "prose-01-v1",
  "residual_issues_path": null,
  "response_schema_version": null,
  "response_structure_retries_used": 0,
  "review_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/review.json",
  "review_sha256": "2307b5894dbce018c15d371fbd3f9739912bacfe9511585d891b31b52b0f0a47",
  "revision_rounds_used": 0,
  "target_id": "v01-c001-s001",
  "transport_retries_used": 0,
  "updated_at": "2026-07-22T00:12:01Z"
}
```

Canonical SHA-256:

```text
53f5a620e41e7714f783a6f45b68f4adc3763c88c981a7379332cf0b9d7c789f
```

## 14. PROSE_FROZEN Checkpoint manifest

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json
example_id = EX-POS-SCENE-FIX-CHK-002
```

```json
{
  "commit_plan_path": null,
  "commit_plan_sha256": null,
  "continuity_candidate_manifest_path": null,
  "continuity_delta_path": null,
  "continuity_delta_sha256": null,
  "created_at": "2026-07-22T00:10:02Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "manifest_version": "1.0",
  "phase": "PROSE_FROZEN",
  "prose_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/candidate-manifest.json",
  "prose_path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "scene_card_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json",
  "scene_card_path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "staging_transaction_path": null,
  "updated_at": "2026-07-22T00:12:02Z"
}
```

Canonical SHA-256:

```text
4561825bc585273d3631b568e1c1b2caf209175391351a68601a403da77bb37c
```

# Part IV: Continuity extraction and checkpoint
## 15. Continuity Context snapshot

```text
EXACT ARTIFACT
path = runtime/context-snapshots/delta-01/v01-c001-s001/ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29.json
example_id = EX-POS-SCENE-005
```

```json
{
  "builder_id": "continuity_builder",
  "builder_version": "context-builders-v1",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "exclusions": [],
  "operation_id": "DELTA-01",
  "payload": {
    "context_identity": {
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
      "scene_id": "v01-c001-s001",
      "source_generation_id": "00000000"
    },
    "delta_contract_rules": [
      {
        "applies_to": [
          "continuity_delta"
        ],
        "description": "Every code-injected before value must equal the source HEAD value.",
        "rule_id": "DELTA_BEFORE_HEAD",
        "severity": "error",
        "source_contract": "contracts/ledger/evidence_and_updates.md#existing-item-update-candidate"
      },
      {
        "applies_to": [
          "continuity_delta"
        ],
        "description": "Every Evidence quote must occur exactly once in canonical frozen prose.",
        "rule_id": "DELTA_EVIDENCE_UNIQUE",
        "severity": "error",
        "source_contract": "contracts/ledger/evidence_and_updates.md#canonical-prose-offsets-and-hashes"
      },
      {
        "applies_to": [
          "continuity_delta"
        ],
        "description": "The provider response must not contain persistent new IDs, Evidence IDs, hashes, offsets, Commit IDs, or Generation IDs.",
        "rule_id": "DELTA_NO_CODE_IDS",
        "severity": "error",
        "source_contract": "contracts/ledger/evidence_and_updates.md#forbidden-candidate-content"
      },
      {
        "applies_to": [
          "continuity_delta"
        ],
        "description": "Every proposed update must be authorized by the frozen Scene card allowed-update-target union.",
        "rule_id": "DELTA_TARGET_AUTH",
        "severity": "error",
        "source_contract": "contracts/data/scene_artifacts.md#scene-card-authorization-of-continuity"
      }
    ],
    "ending_criteria": [],
    "existing_record_catalog": [
      {
        "aliases": [],
        "appearance_anchor": "潮に色褪せた青い外套と、腰の小さな工具袋。",
        "id": "char-000001",
        "immutable_facts": [
          "凪とは幼なじみである",
          "灯台の主灯と日誌の基本手順を知っている"
        ],
        "name": "澪",
        "record_kind": "character",
        "role": "protagonist",
        "speech_anchor": "短く確かめるように話し、決めた後は言い切る。"
      },
      {
        "aliases": [],
        "appearance_anchor": "油の染みた革手袋と、右手首の古い傷。",
        "id": "char-000002",
        "immutable_facts": [
          "澪とは幼なじみである",
          "港と灯台の旧式機構に詳しい"
        ],
        "name": "凪",
        "record_kind": "character",
        "role": "ally",
        "speech_anchor": "確認事項を順番に挙げ、断定の前に根拠を求める。"
      },
      {
        "id": "rel-000001",
        "participant_a_id": "char-000001",
        "participant_b_id": "char-000002",
        "public_relation": "必要な作業のために再会した疎遠な幼なじみ",
        "record_kind": "relationship",
        "relationship_type": "friendship",
        "shared_state": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。"
      },
      {
        "description": "灯台の旧管理台帳に記録された小型の真鍮鍵。",
        "id": "item-000001",
        "immutable_rules": [
          "地下修理庫の錠に対応する"
        ],
        "kind": "item",
        "name": "真鍮の予備鍵",
        "record_kind": "world_entity",
        "sensory_anchors": [
          "掌に残る冷たい重み",
          "緑青の浮いた縁"
        ]
      },
      {
        "description": "断崖の先に建つ石造灯台。主灯室、螺旋階段、地下の修理庫がある。",
        "id": "loc-000001",
        "immutable_rules": [
          "主灯は日没後に点灯する",
          "地下修理庫は専用鍵でのみ開く"
        ],
        "kind": "location",
        "name": "岬の灯台",
        "record_kind": "world_entity",
        "sensory_anchors": [
          "塩を含んだ冷たい風",
          "消えた主灯の黒いレンズ",
          "石壁を伝う低い振動"
        ]
      },
      {
        "description": "主灯は日没後に必要となり、初日は日没までに停止原因を特定しなければならない。",
        "fixed_rule": "初日の夕方から日没までが最初の調査期限である。",
        "id": "rule-000001",
        "kind": "deadline",
        "record_kind": "temporal_rule"
      }
    ],
    "knowledge_catalog": [
      {
        "fact_id": "fact-000001",
        "selected_audience_states": [
          {
            "audience_id": "char-000002",
            "audience_type": "character",
            "status": "knows"
          },
          {
            "audience_id": null,
            "audience_type": "reader",
            "status": "hinted"
          }
        ],
        "subject_id": "item-000001",
        "subject_type": "world_entity",
        "writer_visible_label": "予備鍵の役割"
      }
    ],
    "new_item_policy": {
      "allow_knowledge_items": false,
      "allowed_types": [],
      "max_items": 0,
      "max_scope": null,
      "purpose": "このSceneは既存の人物・場所・予備鍵・主要Threadだけで完結し、新しい永続項目を必要としない。"
    },
    "prose": "主灯のレンズは、夕方の光を黒く返していた。澪は制御盤へ手を伸ばしたが、凪の革手袋がその前へ差し出された。\n\n「通電の前に、手順を一つずつ確認する。急いで壊したら、今夜だけの問題じゃなくなる」\n\n反発の言葉が喉まで上がった。灯台を守るのは自分の家だ、と言えば簡単だった。けれど石壁の奥から伝わる振動はいつもより低く、制御盤の表示は二つ同時に消えている。澪は手を引いた。\n\n西窓の光は細く、日没まで一時間もなかった。\n\n凪は古い点検口を指でなぞった。「主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない」\n\n澪が地下へ続く扉を見やると、凪は首を振った。地下修理庫を開ける予備鍵が要る、と凪は言った。凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。澪は家の管理日誌を抱え直した。日誌には空欄が多く、鍵の所在を示す頁も見当たらない。\n\n一人で探せば早い、と考えた瞬間、右手首を庇いながらも配線の順を確かめる凪の横顔が見えた。凪は急かさず、次に調べる場所だけを待っていた。\n\n澪は日誌を凪の前に開き、点検を一緒に進めようと言った。\n\n凪は短くうなずき、二人の間へ工具箱を置いた。消えた灯の原因はまだ見えない。それでも、何を確かめるべきかという問いだけは、もう澪一人のものではなかった。\n",
    "scene_card": {
      "accepted_candidate_sha256": "c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17",
      "allowed_update_targets": [
        {
          "field_rules": [
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/current_goal"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/current_pressure"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/emotional_state"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/location_id"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/physical_condition"
            }
          ],
          "target_id": "char-000001",
          "target_kind": "existing_item",
          "target_type": "character_state"
        },
        {
          "field_rules": [
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/current_goal"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/current_pressure"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/emotional_state"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/location_id"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/physical_condition"
            }
          ],
          "target_id": "char-000002",
          "target_kind": "existing_item",
          "target_type": "character_state"
        },
        {
          "field_rules": [
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/a_to_b/current_intention"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/a_to_b/emotional_stance"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/a_to_b/perception"
            },
            {
              "allowed_operations": [
                "transition"
              ],
              "field_path": "/a_to_b/trust"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/b_to_a/current_intention"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/b_to_a/emotional_stance"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/b_to_a/perception"
            },
            {
              "allowed_operations": [
                "transition"
              ],
              "field_path": "/b_to_a/trust"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/public_relation"
            },
            {
              "allowed_operations": [
                "set"
              ],
              "field_path": "/shared_state"
            }
          ],
          "target_id": "rel-000001",
          "target_kind": "existing_item",
          "target_type": "relationship_state"
        },
        {
          "allowed_after_statuses": [
            "knows"
          ],
          "audience_id": "char-000001",
          "audience_type": "character",
          "fact_id": "fact-000001",
          "start_status": "unknown",
          "target_kind": "knowledge_state"
        },
        {
          "allowed_after_statuses": [
            "revealed"
          ],
          "audience_id": null,
          "audience_type": "reader",
          "fact_id": "fact-000001",
          "start_status": "hinted",
          "target_kind": "knowledge_state"
        },
        {
          "allowed_operations": [
            "introduce"
          ],
          "start_progress": 0,
          "start_status": "open",
          "target_kind": "thread_state",
          "target_progress": 1,
          "target_status": "in_progress",
          "thread_id": "thread-000001"
        },
        {
          "allowed_time_relations": [
            "later"
          ],
          "target_kind": "story_clock",
          "target_parallel_group_id": null,
          "target_time_label": "初日の日没前"
        }
      ],
      "canon_metadata_change_targets": [],
      "chapter_completion_role": "opening",
      "chapter_design_path": "plans/volumes/v01/chapters/c001/chapter-design.json",
      "chapter_design_sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5",
      "chapter_number": 1,
      "character_knowledge_targets": [
        {
          "character_id": "char-000001",
          "fact_id": "fact-000001",
          "purpose": "澪が予備鍵の用途を理解し、共同調査の次の行動を選べるようにする。",
          "required": true,
          "start_status": "unknown",
          "target_status": "knows"
        }
      ],
      "created_at": "2026-07-22T00:10:02Z",
      "emotional_change_target": "澪が凪への反発より安全な共同調査を優先する。",
      "ending_criterion_targets": [],
      "forbidden_disclosures": [
        {
          "constraint_id": "fd-0001",
          "label": "主人公だけが全責任を負う結末",
          "reason": "澪だけが灯を守るべきだという結論や称賛へ進めない。",
          "release_hint": null,
          "source_id": null,
          "source_type": "brief_avoid"
        },
        {
          "constraint_id": "fd-0002",
          "label": "修理庫内部の停止原因",
          "reason": "今回は予備鍵の用途までを開示し、修理庫内の設備故障や台帳内容を確定しない。",
          "release_hint": "修理庫を実際に調べるScene以降",
          "source_id": "fact-000001",
          "source_type": "knowledge_item"
        },
        {
          "constraint_id": "fd-0003",
          "label": "灯台停止の確定原因",
          "reason": "主要Threadは導入に留め、原因を解決または断定しない。",
          "release_hint": "複数の物的根拠が揃った後",
          "source_id": "thread-000001",
          "source_type": "thread"
        },
        {
          "constraint_id": "fd-0004",
          "label": "町の最終的な役割分担",
          "reason": "町が既に共同管理へ合意したとは書かない。",
          "release_hint": "最終巻の合意Scene",
          "source_id": "ending-000001",
          "source_type": "ending_criterion"
        }
      ],
      "length_guidance": {
        "counting_rule": "unicode_code_points_excluding_final_lf",
        "guide_max_chars": 2200,
        "guide_min_chars": 500,
        "hard_limit": false,
        "target_chars": 1200
      },
      "location_id": "loc-000001",
      "new_item_policy": {
        "allow_knowledge_items": false,
        "allowed_types": [],
        "max_items": 0,
        "max_scope": null,
        "purpose": "このSceneは既存の人物・場所・予備鍵・主要Threadだけで完結し、新しい永続項目を必要としない。"
      },
      "parallel_group_id": null,
      "participant_ids": [
        "char-000001",
        "char-000002"
      ],
      "pov_character_id": "char-000001",
      "reader_disclosures": [
        {
          "fact_id": "fact-000001",
          "purpose": "予備鍵が地下修理庫の錠に対応することを読者へ明確にする。",
          "required": true,
          "start_status": "hinted",
          "target_status": "revealed"
        }
      ],
      "relationship_change_targets": [
        {
          "purpose": "主要Relationshipの実務上の信頼回復を開始する。",
          "relationship_id": "rel-000001",
          "required": true,
          "required_change": "澪から凪へのtrustをlowからmediumへ進める行動を描く。",
          "start_state_summary": "澪は凪の能力を認めながら、自分の家を責めていると思い必要最低限しか頼ろうとしない。",
          "target_state_summary": "澪は凪の安全判断を受け入れ、日誌を共有して共同点検を求める。"
        }
      ],
      "required_beats": [
        "澪が消えたレンズを確認する",
        "凪が安全手順を求める",
        "日没までの時間が示される",
        "凪が地下修理庫の予備鍵について説明する",
        "澪が日誌を共有し共同点検を選ぶ"
      ],
      "required_temporal_rule_ids": [
        "rule-000001"
      ],
      "required_world_entity_ids": [
        "item-000001",
        "loc-000001"
      ],
      "scene_id": "v01-c001-s001",
      "scene_number": 1,
      "scene_purpose": "消えた主灯と日没期限を確認し、澪が凪の安全判断と予備鍵の知識を受け入れて共同点検を選ぶことで、灯台停止の主要Threadを導入する。",
      "schema_version": "1.0",
      "source_generation_id": "00000000",
      "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
      "thread_actions": [
        {
          "operation": "introduce",
          "purpose": "主灯停止の原因が地下修理庫の調査へつながる問いを具体的に提示する。",
          "required": true,
          "start_progress": 0,
          "start_status": "open",
          "target_progress": 1,
          "target_status": "in_progress",
          "thread_id": "thread-000001"
        }
      ],
      "time_label": "初日の日没前",
      "time_relation": "later",
      "volume_number": 1
    },
    "target_baselines": [
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "日没までに灯台停止の原因を特定する",
        "field_path": "/current_goal",
        "target_id": "char-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "町が灯台守の家だけを責め始める前に結果を出す必要がある",
        "field_path": "/current_pressure",
        "target_id": "char-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "焦りを抑えて手順を守ろうとしている",
        "field_path": "/emotional_state",
        "target_id": "char-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "loc-000001",
        "field_path": "/location_id",
        "target_id": "char-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "疲労や負傷はない",
        "field_path": "/physical_condition",
        "target_id": "char-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "灯台設備を安全に調べ、再故障を防ぐ",
        "field_path": "/current_goal",
        "target_id": "char-000002",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "無理な再点灯で港へ二次被害を出せない",
        "field_path": "/current_pressure",
        "target_id": "char-000002",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "澪への距離を測りながら設備を警戒している",
        "field_path": "/emotional_state",
        "target_id": "char-000002",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "loc-000001",
        "field_path": "/location_id",
        "target_id": "char-000002",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "右手首に古傷があるが作業可能",
        "field_path": "/physical_condition",
        "target_id": "char-000002",
        "target_kind": "existing_item_baseline",
        "target_type": "character_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "必要な範囲だけ協力を得る",
        "field_path": "/a_to_b/current_intention",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "反発を隠しながら助けを求めている",
        "field_path": "/a_to_b/emotional_stance",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "設備には頼れるが、自分の家を責めていると思っている",
        "field_path": "/a_to_b/perception",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "transition"
        ],
        "current_value": "low",
        "field_path": "/a_to_b/trust",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "危険な単独行動を止め、記録を共有させる",
        "field_path": "/b_to_a/current_intention",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "心配と距離の両方を保っている",
        "field_path": "/b_to_a/emotional_stance",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "手順を守れるが、責任を一人で抱え込みすぎる",
        "field_path": "/b_to_a/perception",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "transition"
        ],
        "current_value": "medium",
        "field_path": "/b_to_a/trust",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "必要な作業のために再会した疎遠な幼なじみ",
        "field_path": "/public_relation",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_operations": [
          "set"
        ],
        "current_value": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。",
        "field_path": "/shared_state",
        "target_id": "rel-000001",
        "target_kind": "existing_item_baseline",
        "target_type": "relationship_state"
      },
      {
        "allowed_after_statuses": [
          "knows"
        ],
        "audience_id": "char-000001",
        "audience_type": "character",
        "current_status": "unknown",
        "fact_id": "fact-000001",
        "target_kind": "knowledge_state_baseline"
      },
      {
        "allowed_after_statuses": [
          "revealed"
        ],
        "audience_id": null,
        "audience_type": "reader",
        "current_status": "hinted",
        "fact_id": "fact-000001",
        "target_kind": "knowledge_state_baseline"
      },
      {
        "allowed_operations": [
          "introduce"
        ],
        "current_progress": 0,
        "current_status": "open",
        "target_kind": "thread_state_baseline",
        "target_progress": 1,
        "target_status": "in_progress",
        "thread_id": "thread-000001"
      },
      {
        "allowed_time_relations": [
          "later"
        ],
        "current_parallel_group_id": null,
        "current_time_label": "初日の夕方",
        "target_kind": "story_clock_baseline",
        "target_parallel_group_id": null,
        "target_time_label": "初日の日没前"
      }
    ],
    "thread_catalog": [
      {
        "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
        "presentation_constraint": "予備鍵と修理庫を手掛かりとして導入するが、停止原因を解決しない。",
        "progress": 0,
        "status": "open",
        "thread_id": "thread-000001",
        "thread_type": "major"
      }
    ]
  },
  "prompt_version": "delta-01-v1",
  "response_schema_version": "continuity-response-v1",
  "schema_version": "1.0",
  "sensitivity": "writer_safe",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "source_refs": [
    {
      "generation_id": null,
      "path": "runtime/effective-config.json",
      "required": true,
      "role": "effective_config",
      "sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c"
    },
    {
      "generation_id": null,
      "path": "plans/volumes/v01/chapters/c001/chapter-design.json",
      "required": true,
      "role": "chapter_design",
      "sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5"
    },
    {
      "generation_id": "00000000",
      "path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
      "required": true,
      "role": "scene_card",
      "sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194"
    },
    {
      "generation_id": "00000000",
      "path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
      "required": true,
      "role": "prose",
      "sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/current-canon.json",
      "required": true,
      "role": "current_canon",
      "sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/knowledge-items.json",
      "required": true,
      "role": "knowledge_items",
      "sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/story-state.json",
      "required": true,
      "role": "story_state",
      "sha256": "d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660"
    },
    {
      "generation_id": "00000000",
      "path": "canon/generations/00000000/generation-manifest.json",
      "required": true,
      "role": "generation_manifest",
      "sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40"
    }
  ],
  "target_id": "v01-c001-s001",
  "token_budget": {
    "context_payload_limit": 24860,
    "final_input_tokens": 5940,
    "hard_input_limit": 25600,
    "max_operation_input_tokens": 32768,
    "model_context_window_tokens": 32768,
    "operation_key": "continuity_delta",
    "overflowed": false,
    "payload_tokens": 5200,
    "protocol_overhead_tokens": 1024,
    "reserved_output_tokens": 6144,
    "static_prompt_tokens": 740,
    "token_count_method": "provider_tokenizer",
    "tokenizer_id": "fixture-tokenizer-v1"
  },
  "view_type": "continuity"
}
```

Canonical SHA-256:

```text
ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29
```

This view contains exact frozen prose and update baselines. It contains no hidden Thread, Knowledge, or Ending truth.

## 16. DELTA-01 provider response

```text
EXACT RESPONSE
operation = DELTA-01
example_id = EX-POS-SCENE-FIX-DELTA-RESP-001
```

```json
{
  "ending_evidence_proposals": [],
  "existing_item_updates": [
    {
      "after": "medium",
      "evidence": [
        {
          "quote": "澪は日誌を凪の前に開き、点検を一緒に進めようと言った。",
          "relation": "supports"
        }
      ],
      "field_path": "/a_to_b/trust",
      "operation": "transition",
      "target_id": "rel-000001",
      "target_type": "relationship_state"
    }
  ],
  "handoff_summary": "日没前、澪は凪の安全判断を受け入れて日誌を共有した。二人は予備鍵が地下修理庫の錠に対応すると確認し、主灯停止の原因を共同で調べ始めた。",
  "knowledge_item_proposals": [],
  "knowledge_updates": [
    {
      "after": "knows",
      "audience_id": "char-000001",
      "audience_type": "character",
      "evidence": [
        {
          "quote": "地下修理庫を開ける予備鍵が要る、と凪は言った。",
          "relation": "supports"
        }
      ],
      "fact_ref": "fact-000001"
    },
    {
      "after": "revealed",
      "audience_id": null,
      "audience_type": "reader",
      "evidence": [
        {
          "quote": "凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。",
          "relation": "supports"
        }
      ],
      "fact_ref": "fact-000001"
    }
  ],
  "new_item_proposals": [],
  "thread_updates": [
    {
      "after_progress": 1,
      "after_status": "in_progress",
      "evidence": [
        {
          "quote": "主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない",
          "relation": "supports"
        }
      ],
      "operation": "introduce",
      "thread_ref": "thread-000001"
    }
  ],
  "time_update": {
    "after_parallel_group_id": null,
    "after_time_label": "初日の日没前",
    "elapsed_hint": null,
    "evidence": [
      {
        "quote": "西窓の光は細く、日没まで一時間もなかった。",
        "relation": "supports"
      }
    ],
    "time_relation": "later"
  }
}
```

Canonical SHA-256:

```text
8076a24f755216e83c7cfc8fb5a37b6b08789b34cfcb0998a64be849fbf45d93
```

The response contains no `before` values, Scene ID, Schema version, persistent new ID, Evidence ID, offset, hash, Commit ID, Generation ID, or timestamp.

## 17. Normalized continuity candidate

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/continuity/v0001/continuity-delta.json
example_id = EX-POS-DELTA-003
```

```json
{
  "delta_status": "candidate",
  "ending_evidence_proposals": [],
  "existing_item_updates": [
    {
      "after": "medium",
      "before": "low",
      "evidence": [
        {
          "quote": "澪は日誌を凪の前に開き、点検を一緒に進めようと言った。",
          "relation": "supports"
        }
      ],
      "field_path": "/a_to_b/trust",
      "operation": "transition",
      "target_id": "rel-000001",
      "target_type": "relationship_state"
    }
  ],
  "handoff_summary": "日没前、澪は凪の安全判断を受け入れて日誌を共有した。二人は予備鍵が地下修理庫の錠に対応すると確認し、主灯停止の原因を共同で調べ始めた。",
  "knowledge_item_proposals": [],
  "knowledge_updates": [
    {
      "after": "knows",
      "audience_id": "char-000001",
      "audience_type": "character",
      "before": "unknown",
      "evidence": [
        {
          "quote": "地下修理庫を開ける予備鍵が要る、と凪は言った。",
          "relation": "supports"
        }
      ],
      "fact_ref": "fact-000001"
    },
    {
      "after": "revealed",
      "audience_id": null,
      "audience_type": "reader",
      "before": "hinted",
      "evidence": [
        {
          "quote": "凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。",
          "relation": "supports"
        }
      ],
      "fact_ref": "fact-000001"
    }
  ],
  "new_item_proposals": [],
  "scene_id": "v01-c001-s001",
  "schema_version": "1.0",
  "thread_updates": [
    {
      "after_progress": 1,
      "after_status": "in_progress",
      "before_progress": 0,
      "before_status": "open",
      "evidence": [
        {
          "quote": "主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない",
          "relation": "supports"
        }
      ],
      "operation": "introduce",
      "thread_ref": "thread-000001"
    }
  ],
  "time_update": {
    "after_parallel_group_id": null,
    "after_time_label": "初日の日没前",
    "before_parallel_group_id": null,
    "before_time_label": "初日の夕方",
    "elapsed_hint": null,
    "evidence": [
      {
        "quote": "西窓の光は細く、日没まで一時間もなかった。",
        "relation": "supports"
      }
    ],
    "time_relation": "later"
  }
}
```

Canonical SHA-256:

```text
67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784
```

## 18. Saved DELTA-02 Review

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/continuity/v0001/review.json
example_id = EX-POS-SCENE-FIX-REVIEW-003
```

```json
{
  "call_id": "call-000019",
  "candidate_path": "runtime/candidates/scenes/v01/c001/s001/continuity/v0001/continuity-delta.json",
  "candidate_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
  "candidate_version": 1,
  "created_at": "2026-07-22T00:14:01Z",
  "input_snapshot_sha256": "ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29",
  "issue_counts": {
    "error": 0,
    "total": 0,
    "warning": 0
  },
  "issues": [],
  "operation_id": "DELTA-02",
  "review_prompt_version": "delta-02-v1",
  "review_round": 1,
  "review_schema_version": "review-v1",
  "review_status": "issues_empty",
  "reviewed_artifact_role": "continuity_delta",
  "schema_version": "1.0",
  "summary": "Scene function、現在State、開示境界、更新目標に重大な問題はありません。",
  "target_id": "v01-c001-s001"
}
```

Canonical SHA-256:

```text
894d4f45cb424631a030a754307c3c0096b673af9001b36648487054ca29cc23
```

## 19. Continuity Candidate manifest

```text
EXACT ARTIFACT
path = runtime/candidates/scenes/v01/c001/s001/continuity/v0001/candidate-manifest.json
example_id = EX-POS-SCENE-FIX-CAND-003
```

```json
{
  "candidate_artifact_format": "json",
  "candidate_path": "runtime/candidates/scenes/v01/c001/s001/continuity/v0001/continuity-delta.json",
  "candidate_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
  "candidate_status": "ready_for_adoption",
  "candidate_version": 1,
  "completion_audit_attempt": null,
  "created_at": "2026-07-22T00:14:00Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "input_snapshot_path": "runtime/context-snapshots/delta-01/v01-c001-s001/ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29.json",
  "input_snapshot_sha256": "ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29",
  "last_call_id": "call-000018",
  "last_structurally_valid": true,
  "manifest_version": "1.0",
  "next_stage": "DELTA-CHK",
  "operation_id": "DELTA-01",
  "previous_candidate_manifest_path": null,
  "previous_candidate_manifest_sha256": null,
  "processor_type": "llm_extract",
  "prompt_version": "delta-01-v1",
  "residual_issues_path": null,
  "response_schema_version": "continuity-response-v1",
  "response_structure_retries_used": 0,
  "review_path": "runtime/candidates/scenes/v01/c001/s001/continuity/v0001/review.json",
  "review_sha256": "894d4f45cb424631a030a754307c3c0096b673af9001b36648487054ca29cc23",
  "revision_rounds_used": 0,
  "target_id": "v01-c001-s001",
  "transport_retries_used": 0,
  "updated_at": "2026-07-22T00:14:01Z"
}
```

Canonical SHA-256:

```text
f49bb05075e36c9e42f2729a496bc753a0d23319423411f1abc89e4f713baf3d
```

## 20. DELTA_ACCEPTED Checkpoint manifest

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json
example_id = EX-POS-SCENE-FIX-CHK-003
```

```json
{
  "commit_plan_path": null,
  "commit_plan_sha256": null,
  "continuity_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/continuity/v0001/candidate-manifest.json",
  "continuity_delta_path": "runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json",
  "continuity_delta_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
  "created_at": "2026-07-22T00:10:02Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "manifest_version": "1.0",
  "phase": "DELTA_ACCEPTED",
  "prose_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/candidate-manifest.json",
  "prose_path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "scene_card_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json",
  "scene_card_path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "staging_transaction_path": null,
  "updated_at": "2026-07-22T00:14:02Z"
}
```

Canonical SHA-256:

```text
05a8f801c5a4eceb67bf90aa543508e9846fd715f367bdb193745094e7860664
```

# Part V: Commit planning and allocation
## 21. COMMIT-01 Commit plan

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json
example_id = EX-POS-COMMIT-001
```

```json
{
  "all_checks_pass": true,
  "candidate_delta_path": "runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json",
  "candidate_delta_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
  "checkpoint_manifest_path": "runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json",
  "checkpoint_manifest_sha256": "05a8f801c5a4eceb67bf90aa543508e9846fd715f367bdb193745094e7860664",
  "checks": [
    {
      "artifact_path": "runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json",
      "artifact_sha256": "05a8f801c5a4eceb67bf90aa543508e9846fd715f367bdb193745094e7860664",
      "check_id": "CHECKPOINT_HASHES",
      "message": "Checkpoint manifest and frozen artifact hashes match.",
      "status": "pass"
    },
    {
      "artifact_path": "runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json",
      "artifact_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
      "check_id": "DELTA_AUTHORIZATION",
      "message": "Every update is authorized by the frozen Scene card.",
      "status": "pass"
    },
    {
      "artifact_path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
      "artifact_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "check_id": "EVIDENCE_QUOTES",
      "message": "Every Evidence quote occurs exactly once in canonical prose.",
      "status": "pass"
    },
    {
      "artifact_path": "plans/volumes/v01/chapters/c001/chapter-design.json",
      "artifact_sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5",
      "check_id": "ROUTE_AFTER_COMMIT",
      "message": "The next planned target is v01-c001-s002.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000000/generation-manifest.json",
      "artifact_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
      "check_id": "SOURCE_HEAD",
      "message": "Checkpoint source generation equals current canon/HEAD.",
      "status": "pass"
    }
  ],
  "created_at": "2026-07-22T00:15:00Z",
  "evidence_allocation_requests": [
    {
      "quote": "澪は日誌を凪の前に開き、点検を一緒に進めようと言った。",
      "relation": "supports",
      "sort_order": 1,
      "source_pointer": "/existing_item_updates/0/evidence/0",
      "target_kind": "relationship_state"
    },
    {
      "quote": "地下修理庫を開ける予備鍵が要る、と凪は言った。",
      "relation": "supports",
      "sort_order": 2,
      "source_pointer": "/knowledge_updates/0/evidence/0",
      "target_kind": "knowledge_state"
    },
    {
      "quote": "凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。",
      "relation": "supports",
      "sort_order": 3,
      "source_pointer": "/knowledge_updates/1/evidence/0",
      "target_kind": "knowledge_state"
    },
    {
      "quote": "主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない",
      "relation": "supports",
      "sort_order": 4,
      "source_pointer": "/thread_updates/0/evidence/0",
      "target_kind": "thread_state"
    },
    {
      "quote": "西窓の光は細く、日没まで一時間もなかった。",
      "relation": "supports",
      "sort_order": 5,
      "source_pointer": "/time_update/evidence/0",
      "target_kind": "story_clock"
    }
  ],
  "expected_after_current_order": 1,
  "prose_path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "record_allocation_requests": [],
  "route_after_commit": {
    "next_chapter_number": 1,
    "next_scene_number": 2,
    "next_stage": "SC-01",
    "next_target_id": "v01-c001-s002",
    "next_volume_number": 1,
    "route_type": "next_scene"
  },
  "scene_card_path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "schema_version": "1.0",
  "source_commit_id": "commit-00000000",
  "source_current_order": 0,
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40"
}
```

Canonical SHA-256:

```text
501a9c35b6e049ecabbecbe8ca4e52fa42e83a9dc2a70665b3961a1171d51916
```

No counter has changed when this artifact is written.

## 22. Checkpoint after COMMIT-01

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json
example_id = EX-POS-SCENE-FIX-CHK-004
```

```json
{
  "commit_plan_path": "runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json",
  "commit_plan_sha256": "501a9c35b6e049ecabbecbe8ca4e52fa42e83a9dc2a70665b3961a1171d51916",
  "continuity_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/continuity/v0001/candidate-manifest.json",
  "continuity_delta_path": "runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json",
  "continuity_delta_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
  "created_at": "2026-07-22T00:10:02Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "manifest_version": "1.0",
  "phase": "DELTA_ACCEPTED",
  "prose_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/candidate-manifest.json",
  "prose_path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "scene_card_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json",
  "scene_card_path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "staging_transaction_path": null,
  "updated_at": "2026-07-22T00:15:00Z"
}
```

Canonical SHA-256:

```text
63a757cd10daf3edc51339f7dc5b792f7608050b290a3f9c8915cd6c51e5a305
```

## 23. Evidence source mappings

```text
EXACT VALUE
operation = COMMIT-02
example_id = EX-POS-EVIDENCE-MAP-001
```

```json
[
  {
    "end_offset": 472,
    "evidence_id": "ev-000001",
    "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
    "quote_sha256": "a34fa92bd168ec83ec657299850aee4ac958d9449d15104a8a2c97fdd584a560",
    "source_pointer": "/existing_item_updates/0/evidence/0",
    "start_offset": 445
  },
  {
    "end_offset": 308,
    "evidence_id": "ev-000002",
    "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
    "quote_sha256": "073aefdfb8c95046751c19f046c1eaed3a8c09e933f4b8fe2cbaf5fa7ce9442d",
    "source_pointer": "/knowledge_updates/0/evidence/0",
    "start_offset": 285
  },
  {
    "end_offset": 333,
    "evidence_id": "ev-000003",
    "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
    "quote_sha256": "c5c72be8b211cf673a8fcaa50159feaf810efcb5abca334756fe7a350359e70f",
    "source_pointer": "/knowledge_updates/1/evidence/0",
    "start_offset": 308
  },
  {
    "end_offset": 260,
    "evidence_id": "ev-000004",
    "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
    "quote_sha256": "1afa078e121dfd04a61c90e168b2c5fb3a6b790ca6902782764e43132cccfc0a",
    "source_pointer": "/thread_updates/0/evidence/0",
    "start_offset": 224
  },
  {
    "end_offset": 206,
    "evidence_id": "ev-000005",
    "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
    "quote_sha256": "bab0523e7b23e24657c6bec37bbdd2b7e537f2999b7ea367af2f4adb6d2733d4",
    "source_pointer": "/time_update/evidence/0",
    "start_offset": 185
  }
]
```

Canonical SHA-256:

```text
26550de029c939db199423cf67d6e4885e0d326644b0b0111e753e973fe6d128
```

Offsets are zero-based Unicode code-point positions in canonical prose and `end_offset` is exclusive.

## 24. COMMIT-02 merge plan

```text
EXACT ARTIFACT
path = .staging/scene-commits/v01-c001-s001/merge-plan.json
example_id = EX-POS-COMMIT-002
```

```json
{
  "after_generation": "00000001",
  "before_generation": "00000000",
  "commit_id": "commit-00000001",
  "created_at": "2026-07-22T00:16:00Z",
  "current_order_after": 1,
  "current_order_before": 0,
  "evidence_source_mappings": [
    {
      "end_offset": 472,
      "evidence_id": "ev-000001",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "a34fa92bd168ec83ec657299850aee4ac958d9449d15104a8a2c97fdd584a560",
      "source_pointer": "/existing_item_updates/0/evidence/0",
      "start_offset": 445
    },
    {
      "end_offset": 308,
      "evidence_id": "ev-000002",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "073aefdfb8c95046751c19f046c1eaed3a8c09e933f4b8fe2cbaf5fa7ce9442d",
      "source_pointer": "/knowledge_updates/0/evidence/0",
      "start_offset": 285
    },
    {
      "end_offset": 333,
      "evidence_id": "ev-000003",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "c5c72be8b211cf673a8fcaa50159feaf810efcb5abca334756fe7a350359e70f",
      "source_pointer": "/knowledge_updates/1/evidence/0",
      "start_offset": 308
    },
    {
      "end_offset": 260,
      "evidence_id": "ev-000004",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "1afa078e121dfd04a61c90e168b2c5fb3a6b790ca6902782764e43132cccfc0a",
      "source_pointer": "/thread_updates/0/evidence/0",
      "start_offset": 224
    },
    {
      "end_offset": 206,
      "evidence_id": "ev-000005",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "bab0523e7b23e24657c6bec37bbdd2b7e537f2999b7ea367af2f4adb6d2733d4",
      "source_pointer": "/time_update/evidence/0",
      "start_offset": 185
    }
  ],
  "local_key_mappings": [],
  "normalized_character_state_initializations": [],
  "normalized_existing_updates": [
    {
      "after": "medium",
      "before": "low",
      "evidence_ids": [
        "ev-000001"
      ],
      "field_path": "/a_to_b/trust",
      "operation": "transition",
      "target_id": "rel-000001",
      "target_type": "relationship_state"
    }
  ],
  "normalized_knowledge_updates": [
    {
      "after": "knows",
      "audience_id": "char-000001",
      "audience_type": "character",
      "before": "unknown",
      "evidence_ids": [
        "ev-000002"
      ],
      "fact_id": "fact-000001"
    },
    {
      "after": "revealed",
      "audience_id": null,
      "audience_type": "reader",
      "before": "hinted",
      "evidence_ids": [
        "ev-000003"
      ],
      "fact_id": "fact-000001"
    }
  ],
  "normalized_new_canon_records": [],
  "normalized_new_knowledge_records": [],
  "normalized_relationship_state_initializations": [],
  "normalized_story_clock_update": {
    "after_parallel_group_id": null,
    "after_time_label": "初日の日没前",
    "before_parallel_group_id": null,
    "before_time_label": "初日の夕方",
    "elapsed_hint": null,
    "evidence_ids": [
      "ev-000005"
    ],
    "time_relation": "later"
  },
  "normalized_thread_state_initializations": [],
  "normalized_thread_updates": [
    {
      "after_progress": 1,
      "after_status": "in_progress",
      "before_progress": 0,
      "before_status": "open",
      "evidence_ids": [
        "ev-000004"
      ],
      "operation": "introduce",
      "thread_id": "thread-000001"
    }
  ],
  "parent_commit_id": "commit-00000000",
  "resulting_route": {
    "next_chapter_number": 1,
    "next_scene_number": 2,
    "next_stage": "SC-01",
    "next_target_id": "v01-c001-s002",
    "next_volume_number": 1,
    "route_type": "next_scene"
  },
  "scene_id": "v01-c001-s001",
  "schema_version": "1.0"
}
```

Canonical SHA-256:

```text
e4206d2b25ab46882dad28fbb1367824ded6e30e504dcee425100e2af99770ce
```

# Part VI: Resulting roots and committed artifacts
## 25. Generation-1 current Canon

```text
EXACT ARTIFACT
path = canon/generations/00000001/current-canon.json
example_id = EX-POS-SCENE-FIX-CANON-001
```

```json
{
  "records": [
    {
      "aliases": [],
      "appearance_anchor": "潮に色褪せた青い外套と、腰の小さな工具袋。",
      "background": "岬の灯台守の家に生まれ、家業を継ぐことを当然とされてきた見習い。",
      "core_trait": "粘り強い",
      "created_scene_id": null,
      "id": "char-000001",
      "immutable_facts": [
        "凪とは幼なじみである",
        "灯台の主灯と日誌の基本手順を知っている"
      ],
      "name": "澪",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "character",
      "role": "protagonist",
      "scope": "series",
      "speech_anchor": "短く確かめるように話し、決めた後は言い切る。",
      "values": [
        "灯を絶やさないこと",
        "自分で選んだ責任"
      ]
    },
    {
      "aliases": [],
      "appearance_anchor": "油の染みた革手袋と、右手首の古い傷。",
      "background": "港の修理工。幼い頃は澪と灯台で遊んだが、灯台管理をめぐる両家の対立で疎遠になった。",
      "core_trait": "慎重",
      "created_scene_id": null,
      "id": "char-000002",
      "immutable_facts": [
        "澪とは幼なじみである",
        "港と灯台の旧式機構に詳しい"
      ],
      "name": "凪",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "character",
      "role": "ally",
      "scope": "series",
      "speech_anchor": "確認事項を順番に挙げ、断定の前に根拠を求める。",
      "values": [
        "共有できる記録",
        "安全な整備"
      ]
    },
    {
      "created_scene_id": null,
      "id": "rel-000001",
      "participant_a_id": "char-000001",
      "participant_b_id": "char-000002",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "relationship",
      "relationship_origin": "幼なじみだったが、灯台管理をめぐる両家の対立で疎遠になった。",
      "relationship_type": "friendship",
      "scope": "series",
      "structural_role": "primary"
    },
    {
      "created_scene_id": null,
      "description": "断崖の先に建つ石造灯台。主灯室、螺旋階段、地下の修理庫がある。",
      "id": "loc-000001",
      "immutable_rules": [
        "主灯は日没後に点灯する",
        "地下修理庫は専用鍵でのみ開く"
      ],
      "kind": "location",
      "name": "岬の灯台",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "world_entity",
      "scope": "series",
      "sensory_anchors": [
        "塩を含んだ冷たい風",
        "消えた主灯の黒いレンズ",
        "石壁を伝う低い振動"
      ]
    },
    {
      "created_scene_id": null,
      "description": "灯台の旧管理台帳に記録された小型の真鍮鍵。",
      "id": "item-000001",
      "immutable_rules": [
        "地下修理庫の錠に対応する"
      ],
      "kind": "item",
      "name": "真鍮の予備鍵",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "world_entity",
      "scope": "series",
      "sensory_anchors": [
        "掌に残る冷たい重み",
        "緑青の浮いた縁"
      ]
    },
    {
      "created_scene_id": null,
      "description": "主灯は日没後に必要となり、初日は日没までに停止原因を特定しなければならない。",
      "fixed_rule": "初日の夕方から日没までが最初の調査期限である。",
      "id": "rule-000001",
      "kind": "deadline",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "temporal_rule",
      "related_ids": [
        "loc-000001"
      ],
      "scope": "volume"
    },
    {
      "author_truth": "地下修理庫に残された旧式切替器と管理台帳が停止原因を示し、予備鍵がその調査を可能にする。",
      "created_scene_id": null,
      "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
      "id": "thread-000001",
      "presentation_rule": "予備鍵、修理庫、台帳、切替器の順に根拠を開示し、説明だけで真相を確定しない。",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "thread",
      "required": true,
      "resolution_condition": "旧式切替器の故障と管理記録の空白を公に確認し、安全な再点灯と共同管理を実現する。",
      "scope": "series",
      "thread_type": "major"
    },
    {
      "created_scene_id": null,
      "description": "町が灯台を共同で守る意思と具体的な役割分担を示す。",
      "id": "ending-000001",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "ending_criterion",
      "required": true,
      "scope": "series",
      "source_ending_text": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける"
    }
  ]
}
```

Canonical SHA-256:

```text
080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff
```

Byte/hash identity with Genesis:

```text
Genesis current Canon SHA-256 = 080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff
Generation-1 current Canon SHA-256 = 080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff
```

## 26. Generation-1 Knowledge items

```text
EXACT ARTIFACT
path = canon/generations/00000001/knowledge-items.json
example_id = EX-POS-SCENE-FIX-KNOWLEDGE-001
```

```json
{
  "items": [
    {
      "author_truth": "予備鍵で地下修理庫を開けると、停止原因につながる旧式切替器と管理台帳を調べられる。",
      "canonical_fact": "真鍮の予備鍵は地下修理庫の錠に対応する。",
      "created_scene_id": null,
      "id": "fact-000001",
      "record_lifecycle": "active",
      "record_origin": "initial_design",
      "record_type": "knowledge_item",
      "scope": "series",
      "subject_id": "item-000001",
      "subject_type": "world_entity",
      "writer_visible_label": "予備鍵の役割"
    }
  ]
}
```

Canonical SHA-256:

```text
3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d
```

## 27. Generation-1 Story state

```text
EXACT ARTIFACT
path = canon/generations/00000001/story-state.json
example_id = EX-POS-SCENE-FIX-STATE-001
```

```json
{
  "character_states": [
    {
      "character_id": "char-000001",
      "current_goal": "日没までに灯台停止の原因を特定する",
      "current_pressure": "町が灯台守の家だけを責め始める前に結果を出す必要がある",
      "emotional_state": "焦りを抑えて手順を守ろうとしている",
      "location_id": "loc-000001",
      "physical_condition": "疲労や負傷はない"
    },
    {
      "character_id": "char-000002",
      "current_goal": "灯台設備を安全に調べ、再故障を防ぐ",
      "current_pressure": "無理な再点灯で港へ二次被害を出せない",
      "emotional_state": "澪への距離を測りながら設備を警戒している",
      "location_id": "loc-000001",
      "physical_condition": "右手首に古傷があるが作業可能"
    }
  ],
  "knowledge_states": [
    {
      "audience_id": "char-000001",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": "char-000002",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": null,
      "audience_type": "reader",
      "fact_id": "fact-000001",
      "status": "revealed"
    }
  ],
  "relationship_states": [
    {
      "a_to_b": {
        "current_intention": "必要な範囲だけ協力を得る",
        "emotional_stance": "反発を隠しながら助けを求めている",
        "perception": "設備には頼れるが、自分の家を責めていると思っている",
        "trust": "medium"
      },
      "b_to_a": {
        "current_intention": "危険な単独行動を止め、記録を共有させる",
        "emotional_stance": "心配と距離の両方を保っている",
        "perception": "手順を守れるが、責任を一人で抱え込みすぎる",
        "trust": "medium"
      },
      "public_relation": "必要な作業のために再会した疎遠な幼なじみ",
      "relationship_id": "rel-000001",
      "shared_state": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。"
    }
  ],
  "story_clock": {
    "current_chapter_number": 1,
    "current_order": 1,
    "current_scene_number": 1,
    "current_volume_number": 1,
    "last_scene_id": "v01-c001-s001",
    "parallel_group_id": null,
    "time_label": "初日の日没前"
  },
  "thread_states": [
    {
      "progress": 1,
      "thread_id": "thread-000001",
      "thread_status": "in_progress",
      "volume_disposition": null
    }
  ]
}
```

Canonical SHA-256:

```text
cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7
```

## 28. Generation-1 Evidence index

```text
EXACT ARTIFACT
path = canon/generations/00000001/evidence-index.json
example_id = EX-POS-EVID-002
```

```json
{
  "records": [
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000001",
      "created_at": "2026-07-22T00:16:00Z",
      "end_offset": 472,
      "evidence_id": "ev-000001",
      "evidence_type": "relationship_state_update",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote": "澪は日誌を凪の前に開き、点検を一緒に進めようと言った。",
      "quote_sha256": "a34fa92bd168ec83ec657299850aee4ac958d9449d15104a8a2c97fdd584a560",
      "relation": "supports",
      "scene_id": "v01-c001-s001",
      "start_offset": 445,
      "target_field": "/a_to_b/trust",
      "target_id": "rel-000001",
      "target_type": "relationship_state"
    },
    {
      "audience_id": "char-000001",
      "audience_type": "character",
      "commit_id": "commit-00000001",
      "created_at": "2026-07-22T00:16:00Z",
      "end_offset": 308,
      "evidence_id": "ev-000002",
      "evidence_type": "knowledge_state_update",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote": "地下修理庫を開ける予備鍵が要る、と凪は言った。",
      "quote_sha256": "073aefdfb8c95046751c19f046c1eaed3a8c09e933f4b8fe2cbaf5fa7ce9442d",
      "relation": "supports",
      "scene_id": "v01-c001-s001",
      "start_offset": 285,
      "target_field": "/status",
      "target_id": "fact-000001",
      "target_type": "knowledge_state"
    },
    {
      "audience_id": null,
      "audience_type": "reader",
      "commit_id": "commit-00000001",
      "created_at": "2026-07-22T00:16:00Z",
      "end_offset": 333,
      "evidence_id": "ev-000003",
      "evidence_type": "knowledge_state_update",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote": "凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。",
      "quote_sha256": "c5c72be8b211cf673a8fcaa50159feaf810efcb5abca334756fe7a350359e70f",
      "relation": "supports",
      "scene_id": "v01-c001-s001",
      "start_offset": 308,
      "target_field": "/status",
      "target_id": "fact-000001",
      "target_type": "knowledge_state"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000001",
      "created_at": "2026-07-22T00:16:00Z",
      "end_offset": 260,
      "evidence_id": "ev-000004",
      "evidence_type": "thread_state_update",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote": "主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない",
      "quote_sha256": "1afa078e121dfd04a61c90e168b2c5fb3a6b790ca6902782764e43132cccfc0a",
      "relation": "supports",
      "scene_id": "v01-c001-s001",
      "start_offset": 224,
      "target_field": "/thread_status",
      "target_id": "thread-000001",
      "target_type": "thread_state"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000001",
      "created_at": "2026-07-22T00:16:00Z",
      "end_offset": 206,
      "evidence_id": "ev-000005",
      "evidence_type": "time_update",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote": "西窓の光は細く、日没まで一時間もなかった。",
      "quote_sha256": "bab0523e7b23e24657c6bec37bbdd2b7e537f2999b7ea367af2f4adb6d2733d4",
      "relation": "supports",
      "scene_id": "v01-c001-s001",
      "start_offset": 185,
      "target_field": "/time_label",
      "target_id": null,
      "target_type": "story_clock"
    }
  ]
}
```

Canonical SHA-256:

```text
b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a
```

## 29. Committed continuity delta

```text
EXACT ARTIFACT
path = artifacts/scenes/v01/c001/s001/continuity-delta.json
example_id = EX-POS-DELTA-004
```

```json
{
  "delta_status": "committed",
  "ending_evidence": [],
  "existing_item_updates": [
    {
      "after": "medium",
      "before": "low",
      "evidence_ids": [
        "ev-000001"
      ],
      "field_path": "/a_to_b/trust",
      "operation": "transition",
      "target_id": "rel-000001",
      "target_type": "relationship_state"
    }
  ],
  "handoff_summary": "日没前、澪は凪の安全判断を受け入れて日誌を共有した。二人は予備鍵が地下修理庫の錠に対応すると確認し、主灯停止の原因を共同で調べ始めた。",
  "knowledge_item_adoptions": [],
  "knowledge_updates": [
    {
      "after": "knows",
      "audience_id": "char-000001",
      "audience_type": "character",
      "before": "unknown",
      "evidence_ids": [
        "ev-000002"
      ],
      "fact_id": "fact-000001"
    },
    {
      "after": "revealed",
      "audience_id": null,
      "audience_type": "reader",
      "before": "hinted",
      "evidence_ids": [
        "ev-000003"
      ],
      "fact_id": "fact-000001"
    }
  ],
  "new_item_adoptions": [],
  "scene_id": "v01-c001-s001",
  "schema_version": "1.0",
  "thread_updates": [
    {
      "after_progress": 1,
      "after_status": "in_progress",
      "before_progress": 0,
      "before_status": "open",
      "evidence_ids": [
        "ev-000004"
      ],
      "operation": "introduce",
      "thread_id": "thread-000001"
    }
  ],
  "time_update": {
    "after_parallel_group_id": null,
    "after_time_label": "初日の日没前",
    "before_parallel_group_id": null,
    "before_time_label": "初日の夕方",
    "elapsed_hint": null,
    "evidence_ids": [
      "ev-000005"
    ],
    "time_relation": "later"
  }
}
```

Canonical SHA-256:

```text
1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406
```

## 30. Evidence offset table

| Evidence ID | target | quote | start | end | quote SHA-256 |
|---|---|---|---:|---:|---|
| `ev-000001` | `relationship_state:rel-000001/a_to_b/trust` | `澪は日誌を凪の前に開き、点検を一緒に進めようと言った。` | 445 | 472 | `a34fa92bd168ec83ec657299850aee4ac958d9449d15104a8a2c97fdd584a560` |
| `ev-000002` | `knowledge_state:fact-000001/status` | `地下修理庫を開ける予備鍵が要る、と凪は言った。` | 285 | 308 | `073aefdfb8c95046751c19f046c1eaed3a8c09e933f4b8fe2cbaf5fa7ce9442d` |
| `ev-000003` | `knowledge_state:fact-000001/status` | `凪は、予備鍵が地下修理庫の錠に合うと澪へ説明した。` | 308 | 333 | `c5c72be8b211cf673a8fcaa50159feaf810efcb5abca334756fe7a350359e70f` |
| `ev-000004` | `thread_state:thread-000001/thread_status` | `主灯が消えた原因は、灯室だけではなく地下修理庫まで調べなければ分からない` | 224 | 260 | `1afa078e121dfd04a61c90e168b2c5fb3a6b790ca6902782764e43132cccfc0a` |
| `ev-000005` | `story_clock:null/time_label` | `西窓の光は細く、日没まで一時間もなかった。` | 185 | 206 | `bab0523e7b23e24657c6bec37bbdd2b7e537f2999b7ea367af2f4adb6d2733d4` |

Every row satisfies:

```text
canonical_prose[start_offset:end_offset] = quote
prose_sha256 = 45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b
```

## 31. Adopted Scene manifest

```text
EXACT ARTIFACT
path = artifacts/scenes/v01/c001/s001/scene-manifest.json
example_id = EX-POS-COMMIT-005
```

```json
{
  "adopted_at": "2026-07-22T00:17:00Z",
  "adopted_generation_id": "00000001",
  "chapter_number": 1,
  "character_count": 549,
  "commit_id": "commit-00000001",
  "continuity_delta_path": "artifacts/scenes/v01/c001/s001/continuity-delta.json",
  "continuity_delta_sha256": "1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406",
  "evidence_ids": [
    "ev-000001",
    "ev-000002",
    "ev-000003",
    "ev-000004",
    "ev-000005"
  ],
  "input_plan_refs": [
    {
      "path": "plans/series-map.json",
      "role": "series_map",
      "sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294"
    },
    {
      "path": "plans/volumes/v01/volume-design.json",
      "role": "volume_design",
      "sha256": "c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e"
    },
    {
      "path": "plans/volumes/v01/chapters/c001/chapter-design.json",
      "role": "chapter_design",
      "sha256": "463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5"
    }
  ],
  "manifest_version": "1.0",
  "prose_path": "artifacts/scenes/v01/c001/s001/prose.md",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "scene_card_path": "artifacts/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "scene_number": 1,
  "source_generation_id": "00000000",
  "volume_number": 1
}
```

Canonical SHA-256:

```text
d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1
```

All Scene paths point to `artifacts/scenes/...`. No checkpoint or staging path is present.

## 32. Scene Commit manifest

```text
EXACT ARTIFACT
path = canon/generations/00000001/commit-manifest.json
example_id = EX-POS-COMMIT-003
```

```json
{
  "after_generation": "00000001",
  "before_generation": "00000000",
  "commit_id": "commit-00000001",
  "commit_type": "scene",
  "committed_at": "2026-07-22T00:17:00Z",
  "continuity_delta_sha256": "1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406",
  "created_at": "2026-07-22T00:16:00Z",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 1,
  "evidence_ids": [
    "ev-000001",
    "ev-000002",
    "ev-000003",
    "ev-000004",
    "ev-000005"
  ],
  "evidence_index_sha256": "b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "local_key_mappings": [],
  "manifest_version": "1.0",
  "parent_commit_id": "commit-00000000",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "scene_manifest_sha256": "d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1",
  "story_state_sha256": "cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7",
  "volume_handoff_path": null,
  "volume_handoff_sha256": null
}
```

Canonical SHA-256:

```text
7f323bcb617be6905d5d604bbe05a2585844b1611abd4e6631369ef21a598e23
```

## 33. Scene Generation manifest

```text
EXACT ARTIFACT
path = canon/generations/00000001/generation-manifest.json
example_id = EX-POS-COMMIT-004
```

```json
{
  "commit_id": "commit-00000001",
  "commit_manifest_path": "canon/generations/00000001/commit-manifest.json",
  "commit_manifest_sha256": "7f323bcb617be6905d5d604bbe05a2585844b1611abd4e6631369ef21a598e23",
  "created_at": "2026-07-22T00:17:00Z",
  "current_canon_path": "canon/generations/00000001/current-canon.json",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 1,
  "evidence_index_path": "canon/generations/00000001/evidence-index.json",
  "evidence_index_sha256": "b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a",
  "generation_id": "00000001",
  "knowledge_items_path": "canon/generations/00000001/knowledge-items.json",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "manifest_version": "1.0",
  "parent_generation_id": "00000000",
  "source_scene_id": "v01-c001-s001",
  "source_scene_manifest_path": "artifacts/scenes/v01/c001/s001/scene-manifest.json",
  "source_scene_manifest_sha256": "d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1",
  "source_volume_handoff_path": null,
  "source_volume_handoff_sha256": null,
  "story_state_path": "canon/generations/00000001/story-state.json",
  "story_state_sha256": "cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7"
}
```

Canonical SHA-256:

```text
2565c99ea0eaf638e81fef85f3dda6c69a1a0813784f0e94092ec879ff6991d0
```

# Part VII: Staged transaction validation and adoption
## 34. Transaction Validation

```text
EXACT ARTIFACT
path = .staging/scene-commits/v01-c001-s001/transaction-validation.json
example_id = EX-POS-SCENE-FIX-TXN-001
```

```json
{
  "after_generation": "00000001",
  "all_checks_pass": true,
  "before_generation": "00000000",
  "checks": [
    {
      "artifact_path": "artifacts/scenes/v01/c001/s001/scene-manifest.json",
      "artifact_sha256": "d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1",
      "check_id": "ADOPTED_PATHS",
      "message": "Scene manifest contains only final adopted Scene and plan paths.",
      "status": "pass"
    },
    {
      "artifact_path": "artifacts/scenes/v01/c001/s001/continuity-delta.json",
      "artifact_sha256": "1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406",
      "check_id": "DELTA_ROOT_DIFF",
      "message": "Committed delta and resulting root changes correspond in both directions.",
      "status": "pass"
    },
    {
      "artifact_path": "artifacts/scenes/v01/c001/s001/prose.md",
      "artifact_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "check_id": "EVIDENCE_OFFSETS",
      "message": "Every Evidence quote, offset, quote hash, and prose hash validates.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000001/generation-manifest.json",
      "artifact_sha256": "2565c99ea0eaf638e81fef85f3dda6c69a1a0813784f0e94092ec879ff6991d0",
      "check_id": "MANIFEST_GRAPH",
      "message": "Scene, Commit, and Generation manifest graph is complete and noncyclic.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000001/story-state.json",
      "artifact_sha256": "cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7",
      "check_id": "ROOT_SCHEMAS",
      "message": "All staged Canon, Knowledge, State, and Evidence roots validate.",
      "status": "pass"
    }
  ],
  "commit_id": "commit-00000001",
  "created_at": "2026-07-22T00:16:30Z",
  "scene_id": "v01-c001-s001",
  "schema_version": "1.0",
  "staged_refs": [
    {
      "path": "generation/00000001/current-canon.json",
      "role": "current_canon",
      "sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff"
    },
    {
      "path": "generation/00000001/knowledge-items.json",
      "role": "knowledge_items",
      "sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d"
    },
    {
      "path": "generation/00000001/story-state.json",
      "role": "story_state",
      "sha256": "cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7"
    },
    {
      "path": "generation/00000001/evidence-index.json",
      "role": "evidence_index",
      "sha256": "b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a"
    },
    {
      "path": "scene/scene-card.json",
      "role": "scene_card",
      "sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194"
    },
    {
      "path": "scene/prose.md",
      "role": "prose",
      "sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b"
    },
    {
      "path": "scene/continuity-delta.json",
      "role": "continuity_delta",
      "sha256": "1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406"
    },
    {
      "path": "scene/scene-manifest.json",
      "role": "scene_manifest",
      "sha256": "d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1"
    },
    {
      "path": "generation/00000001/commit-manifest.json",
      "role": "commit_manifest",
      "sha256": "7f323bcb617be6905d5d604bbe05a2585844b1611abd4e6631369ef21a598e23"
    },
    {
      "path": "generation/00000001/generation-manifest.json",
      "role": "generation_manifest",
      "sha256": "2565c99ea0eaf638e81fef85f3dda6c69a1a0813784f0e94092ec879ff6991d0"
    }
  ],
  "transaction_type": "scene_commit"
}
```

Canonical SHA-256:

```text
73b60222169242cde04d89eeda2057a205ec75606b8fdf455e683a835bbec8fa
```

## 35. Final Transaction manifest

```text
EXACT ARTIFACT
path = .staging/scene-commits/v01-c001-s001/transaction-manifest.json
example_id = EX-POS-SCENE-FIX-TXN-002
```

```json
{
  "after_generation": "00000001",
  "before_generation": "00000000",
  "commit_id": "commit-00000001",
  "commit_manifest_sha256": "7f323bcb617be6905d5d604bbe05a2585844b1611abd4e6631369ef21a598e23",
  "commit_plan_path": "runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json",
  "commit_plan_sha256": "501a9c35b6e049ecabbecbe8ca4e52fa42e83a9dc2a70665b3961a1171d51916",
  "created_at": "2026-07-22T00:16:00Z",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "evidence_index_sha256": "b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a",
  "evidence_source_mappings": [
    {
      "end_offset": 472,
      "evidence_id": "ev-000001",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "a34fa92bd168ec83ec657299850aee4ac958d9449d15104a8a2c97fdd584a560",
      "source_pointer": "/existing_item_updates/0/evidence/0",
      "start_offset": 445
    },
    {
      "end_offset": 308,
      "evidence_id": "ev-000002",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "073aefdfb8c95046751c19f046c1eaed3a8c09e933f4b8fe2cbaf5fa7ce9442d",
      "source_pointer": "/knowledge_updates/0/evidence/0",
      "start_offset": 285
    },
    {
      "end_offset": 333,
      "evidence_id": "ev-000003",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "c5c72be8b211cf673a8fcaa50159feaf810efcb5abca334756fe7a350359e70f",
      "source_pointer": "/knowledge_updates/1/evidence/0",
      "start_offset": 308
    },
    {
      "end_offset": 260,
      "evidence_id": "ev-000004",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "1afa078e121dfd04a61c90e168b2c5fb3a6b790ca6902782764e43132cccfc0a",
      "source_pointer": "/thread_updates/0/evidence/0",
      "start_offset": 224
    },
    {
      "end_offset": 206,
      "evidence_id": "ev-000005",
      "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
      "quote_sha256": "bab0523e7b23e24657c6bec37bbdd2b7e537f2999b7ea367af2f4adb6d2733d4",
      "source_pointer": "/time_update/evidence/0",
      "start_offset": 185
    }
  ],
  "generation_manifest_sha256": "2565c99ea0eaf638e81fef85f3dda6c69a1a0813784f0e94092ec879ff6991d0",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "local_key_mappings": [],
  "merge_plan_path": ".staging/scene-commits/v01-c001-s001/merge-plan.json",
  "merge_plan_sha256": "e4206d2b25ab46882dad28fbb1367824ded6e30e504dcee425100e2af99770ce",
  "scene_id": "v01-c001-s001",
  "scene_manifest_sha256": "d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1",
  "schema_version": "1.0",
  "staged_generation_path": ".staging/scene-commits/v01-c001-s001/generation/00000001",
  "staged_scene_path": ".staging/scene-commits/v01-c001-s001/scene",
  "story_state_sha256": "cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7",
  "transaction_status": "validated",
  "transaction_type": "scene_commit",
  "updated_at": "2026-07-22T00:16:30Z",
  "validation_path": ".staging/scene-commits/v01-c001-s001/transaction-validation.json",
  "validation_sha256": "73b60222169242cde04d89eeda2057a205ec75606b8fdf455e683a835bbec8fa"
}
```

Canonical SHA-256:

```text
e3114b9218c0b21933ac2d34c4e7279216a1869aa30828ef1751d0fa5250a538
```

## 36. COMMIT_PREPARED Checkpoint manifest

```text
EXACT ARTIFACT
path = runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json
example_id = EX-POS-SCENE-FIX-CHK-005
```

```json
{
  "commit_plan_path": "runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json",
  "commit_plan_sha256": "501a9c35b6e049ecabbecbe8ca4e52fa42e83a9dc2a70665b3961a1171d51916",
  "continuity_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/continuity/v0001/candidate-manifest.json",
  "continuity_delta_path": "runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json",
  "continuity_delta_sha256": "67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784",
  "created_at": "2026-07-22T00:10:02Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "manifest_version": "1.0",
  "phase": "COMMIT_PREPARED",
  "prose_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/prose/v0001/candidate-manifest.json",
  "prose_path": "runtime/checkpoints/scenes/v01/c001/s001/prose.md",
  "prose_sha256": "45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b",
  "scene_card_candidate_manifest_path": "runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json",
  "scene_card_path": "runtime/checkpoints/scenes/v01/c001/s001/scene-card.json",
  "scene_card_sha256": "74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194",
  "scene_id": "v01-c001-s001",
  "source_generation_id": "00000000",
  "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
  "staging_transaction_path": ".staging/scene-commits/v01-c001-s001/transaction-manifest.json",
  "updated_at": "2026-07-22T00:16:31Z"
}
```

Canonical SHA-256:

```text
2c3a88fc324e5cad91f779fb1dd3c595a7bbeaa436b2610560adf5478b8dddf1
```

## 37. COMMIT-04 adoption point

Exact final pointer bytes:

```text
canon/HEAD = 00000001\n
```

SHA-256:

```text
4f12fa9e685428bcf226169192fb132acdfe38da0785eda1a6bbb137c51d4976
```

Adoption order:

```text
canon/generations/00000001 rename
→ artifacts/scenes/v01/c001/s001 rename
→ both graphs revalidated
→ canon/HEAD replaced
→ Run state replaced
→ checkpoint and staging cleanup
```

Before HEAD changes, the final-looking Generation and Scene are unadopted.

# Part VIII: Runtime postcondition
## 38. Counters after Scene commit

```text
EXACT ARTIFACT
path = runtime/counters.json
example_id = EX-POS-SCENE-FIX-COUNTERS-001
```

```json
{
  "active_elapsed_seconds": 20,
  "completion_audit_attempts_used": 0,
  "estimated_cost_used": 0,
  "input_tokens_used": 17750,
  "llm_calls_used": 19,
  "next_call_id": 20,
  "next_character_id": 3,
  "next_commit_id": 2,
  "next_culture_id": 1,
  "next_ending_id": 2,
  "next_evidence_id": 6,
  "next_fact_id": 2,
  "next_history_id": 1,
  "next_item_id": 2,
  "next_location_id": 2,
  "next_organization_id": 1,
  "next_publication_id": 1,
  "next_relationship_id": 2,
  "next_rule_id": 2,
  "next_system_id": 1,
  "next_thread_id": 2,
  "output_tokens_used": 6920,
  "response_structure_retries_used": 0,
  "revision_rounds_used": 0,
  "successful_scene_commits": 1,
  "transport_retries_used": 0
}
```

Canonical SHA-256:

```text
4c362aac991d8a4617ec79ca7fbd85cb02a0e52e9fce9eb168eddb5969d09589
```

## 39. Run state after COMMIT-04

```text
EXACT ARTIFACT
path = runtime/run-state.json
example_id = EX-POS-SCENE-FIX-RUN-002
```

```json
{
  "active_candidate_manifest_path": null,
  "active_checkpoint_manifest_path": null,
  "adopted_brief_path": "input/brief.json",
  "adopted_brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
  "current_chapter_number": 1,
  "current_head_generation": "00000001",
  "current_publication_id": null,
  "current_scene_number": 2,
  "current_target_id": "v01-c001-s002",
  "current_volume_number": 1,
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "last_commit_id": "commit-00000001",
  "last_completed_stage": "COMMIT-04",
  "last_error_audit_path": null,
  "next_stage": "SC-01",
  "run_id": "run-000001",
  "run_status": "running",
  "scene_phase": "SCENE_NOT_STARTED",
  "state_revision": 39,
  "state_version": "1.0",
  "stop_reason_code": null,
  "stop_reason_detail": null,
  "updated_at": "2026-07-22T00:17:01Z"
}
```

Canonical SHA-256:

```text
693dc48011c0ea61e5a17eef2c75618e52685b58f5c34531e1e68211203c8750
```

## 40. Scene-stage provider usage

| Call ID | stage | processor role | input tokens | output tokens |
|---|---|---|---:|---:|
| `call-000014` | `SC-01` | `generate` | 1000 | 500 |
| `call-000015` | `SC-02` | `review` | 600 | 80 |
| `call-000016` | `PROSE-01` | `generate` | 900 | 700 |
| `call-000017` | `PROSE-02` | `review` | 700 | 80 |
| `call-000018` | `DELTA-01` | `extract` | 1200 | 600 |
| `call-000019` | `DELTA-02` | `review` | 700 | 80 |

Post-scene totals:

```text
llm_calls_used = 19
next_call_id = 20
next_commit_id = 2
next_evidence_id = 6
successful_scene_commits = 1
input_tokens_used = 17750
output_tokens_used = 6920
```

No persistent story-record counter changes because the Scene creates no new record.

---

# Part IX: Hash and inventory summary

## 41. Core hash chain

```text
SC Context:
  3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e

SC candidate:
  c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17

SC Review:
  0492efdf2feb3038382b61d67033e8bcd8cbd03dc04effa331b42ec1822820a6

SC Candidate manifest:
  ab18dbec13c898a4cda42f73c65f9b9517e2277b9ba2c376fe779a21d38d958b

frozen Scene card:
  74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194

Writer Context:
  49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda

canonical prose:
  45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b

Continuity Context:
  ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29

candidate delta:
  67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784

Commit plan:
  501a9c35b6e049ecabbecbe8ca4e52fa42e83a9dc2a70665b3961a1171d51916

merge plan:
  e4206d2b25ab46882dad28fbb1367824ded6e30e504dcee425100e2af99770ce

committed delta:
  1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406

Story state after Scene:
  cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7

Evidence index after Scene:
  b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a

Scene manifest:
  d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1

Commit manifest:
  7f323bcb617be6905d5d604bbe05a2585844b1611abd4e6631369ef21a598e23

Generation manifest:
  2565c99ea0eaf638e81fef85f3dda6c69a1a0813784f0e94092ec879ff6991d0
```

Manifest construction is noncyclic:

```text
Scene card/prose/committed delta
→ Scene manifest
→ Commit manifest
→ Generation manifest
```

## 42. Exact fixture inventory

| path | authority role | bytes | SHA-256 |
|---|---|---:|---|
| `.staging/scene-commits/v01-c001-s001/merge-plan.json` | `staging` | 3067 | `e4206d2b25ab46882dad28fbb1367824ded6e30e504dcee425100e2af99770ce` |
| `.staging/scene-commits/v01-c001-s001/transaction-manifest.json` | `staging` | 3011 | `e3114b9218c0b21933ac2d34c4e7279216a1869aa30828ef1751d0fa5250a538` |
| `.staging/scene-commits/v01-c001-s001/transaction-validation.json` | `staging` | 3088 | `73b60222169242cde04d89eeda2057a205ec75606b8fdf455e683a835bbec8fa` |
| `artifacts/scenes/v01/c001/s001/continuity-delta.json` | `adopted` | 1306 | `1a127b9d542f2a97544eee77dc3e962c6a2063dc8429f5b31367555db181a406` |
| `artifacts/scenes/v01/c001/s001/prose.md` | `adopted` | 1616 | `45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b` |
| `artifacts/scenes/v01/c001/s001/scene-card.json` | `adopted` | 6533 | `74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194` |
| `artifacts/scenes/v01/c001/s001/scene-manifest.json` | `adopted` | 1264 | `d586983139c20b587b3c4399f4f3fc66c170d3059084708f81ba1a0bef69e8d1` |
| `canon/HEAD` | `pointer` | 9 | `4f12fa9e685428bcf226169192fb132acdfe38da0785eda1a6bbb137c51d4976` |
| `canon/generations/00000001/commit-manifest.json` | `adopted` | 1167 | `7f323bcb617be6905d5d604bbe05a2585844b1611abd4e6631369ef21a598e23` |
| `canon/generations/00000001/current-canon.json` | `adopted` | 4184 | `080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff` |
| `canon/generations/00000001/evidence-index.json` | `adopted` | 3014 | `b21a16ab797f72efc32dc20057c7d15c58240ceefee112d183c2bc717154e88a` |
| `canon/generations/00000001/generation-manifest.json` | `adopted` | 1260 | `2565c99ea0eaf638e81fef85f3dda6c69a1a0813784f0e94092ec879ff6991d0` |
| `canon/generations/00000001/knowledge-items.json` | `adopted` | 488 | `3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d` |
| `canon/generations/00000001/story-state.json` | `adopted` | 2097 | `cbd51e52fef2a719f1c0ebf696928e1d8690ee845eabea67ce0563fe3dc1fdb7` |
| `runtime/candidates/scenes/v01/c001/s001/continuity/v0001/candidate-manifest.json` | `candidate_history` | 1357 | `f49bb05075e36c9e42f2729a496bc753a0d23319423411f1abc89e4f713baf3d` |
| `runtime/candidates/scenes/v01/c001/s001/continuity/v0001/continuity-delta.json` | `candidate_history` | 1810 | `67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784` |
| `runtime/candidates/scenes/v01/c001/s001/continuity/v0001/review.json` | `candidate_history` | 773 | `894d4f45cb424631a030a754307c3c0096b673af9001b36648487054ca29cc23` |
| `runtime/candidates/scenes/v01/c001/s001/prose/v0001/candidate-manifest.json` | `candidate_history` | 1319 | `53f5a620e41e7714f783a6f45b68f4adc3763c88c981a7379332cf0b9d7c789f` |
| `runtime/candidates/scenes/v01/c001/s001/prose/v0001/prose.md` | `candidate_history` | 1616 | `45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b` |
| `runtime/candidates/scenes/v01/c001/s001/prose/v0001/review.json` | `candidate_history` | 744 | `2307b5894dbce018c15d371fbd3f9739912bacfe9511585d891b31b52b0f0a47` |
| `runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/candidate-manifest.json` | `candidate_history` | 1339 | `ab18dbec13c898a4cda42f73c65f9b9517e2277b9ba2c376fe779a21d38d958b` |
| `runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/review.json` | `candidate_history` | 755 | `0492efdf2feb3038382b61d67033e8bcd8cbd03dc04effa331b42ec1822820a6` |
| `runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/scene-card.json` | `candidate_history` | 2334 | `c9edea94b2ef171f6a6be12c884c9ff5d071305a730f4764052e4f95f9c2ce17` |
| `runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json` | `checkpoint` | 3687 | `501a9c35b6e049ecabbecbe8ca4e52fa42e83a9dc2a70665b3961a1171d51916` |
| `runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json` | `checkpoint` | 1810 | `67f8a75c810594336957d414edf46e4c82c642976ec5950a6513aabf82ac9784` |
| `runtime/checkpoints/scenes/v01/c001/s001/prose.md` | `checkpoint` | 1616 | `45a671e2335e8cfe8c44bedeb16dfaeebeff1c00ec8d613223b872ba1e17160b` |
| `runtime/checkpoints/scenes/v01/c001/s001/scene-card.json` | `checkpoint` | 6533 | `74745e6927429007d77a2e5823b1947929d448ac02a26898f7e055c7fe342194` |
| `runtime/context-snapshots/delta-01/v01-c001-s001/ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29.json` | `candidate_history` | 20521 | `ef7436c3314ad5c4c6c85a224f72512e177bf6232efbe5b8b855f1fb8b096d29` |
| `runtime/context-snapshots/prose-01/v01-c001-s001/49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda.json` | `candidate_history` | 11277 | `49c87aa1ff416e8ffefe304242d6989decabb0e5e6d24fa0577cbff865460bda` |
| `runtime/context-snapshots/sc-01/v01-c001-s001/3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e.json` | `candidate_history` | 34243 | `3b6eae01f19f7dccb179b993182638789464407c5aa2192d34cf9e91f6420f3e` |
| `runtime/counters.json` | `runtime_resume` | 601 | `4c362aac991d8a4617ec79ca7fbd85cb02a0e52e9fce9eb168eddb5969d09589` |
| `runtime/effective-config.json` | `runtime_resume` | 3146 | `4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c` |
| `runtime/run-manifest.json` | `runtime_resume` | 922 | `2286207ba97cb075b3b94aa01ea1de0a50aa91d8bb12acdae3fb84d771cf2418` |
| `runtime/run-state.json` | `runtime_resume` | 810 | `693dc48011c0ea61e5a17eef2c75618e52685b58f5c34531e1e68211203c8750` |

Fixture inventory SHA-256:

```text
48ae77ce40964b14f67c07bffb44ca068b84a4e5b6793fd004a0ef44e930c03e
```

This inventory covers the representative Scene's exact Runtime history, checkpoint/staging records, adopted Scene/Generation, final counters, Run state, and HEAD pointer.

---

# Part X: Required negative mutations

## 43. Scene-card and Context mutations

```text
EX-NEG-FIX-SCENE-001
base:
  frozen Scene card
mutation:
  remove char-000002 from participant_ids
expected:
  Chapter-required Character validation failure

EX-NEG-FIX-SCENE-002
base:
  frozen Scene card
mutation:
  insert Thread author_truth into forbidden_disclosures.reason
expected:
  safe Scene-card disclosure failure

EX-NEG-FIX-SCENE-003
base:
  Writer Context
mutation:
  add fact-000001 author_truth
expected:
  Writer-view exact-Schema/security failure

EX-NEG-FIX-SCENE-004
base:
  Continuity Context
mutation:
  add persistent counter values
expected:
  Continuity-view exact-Schema/security failure
```

---

## 44. Prose and Delta mutations

```text
EX-NEG-FIX-DELTA-001
base:
  prose
mutation:
  duplicate the exact time Evidence quote
expected:
  Evidence unique-occurrence failure

EX-NEG-FIX-DELTA-002
base:
  DELTA response
mutation:
  add before = low
expected:
  code-owned before-value response failure

EX-NEG-FIX-DELTA-003
base:
  normalized candidate delta
mutation:
  relationship before = medium
expected:
  source HEAD before-value mismatch

EX-NEG-FIX-DELTA-004
base:
  normalized candidate delta
mutation:
  target /b_to_a/trust rather than /a_to_b/trust
expected:
  prose Evidence/semantic target mismatch

EX-NEG-FIX-DELTA-005
base:
  candidate delta
mutation:
  add evidence_id = ev-000001
expected:
  candidate code-ownership failure

EX-NEG-FIX-DELTA-006
base:
  committed delta
mutation:
  retain Evidence proposal instead of evidence_ids
expected:
  committed-delta Schema failure
```

---

## 45. Commit and manifest mutations

```text
EX-NEG-FIX-COMMIT-001
base:
  Commit plan
mutation:
  allocate ev-000001 inside COMMIT-01
expected:
  COMMIT-01 no-allocation failure

EX-NEG-FIX-COMMIT-002
base:
  Evidence record
mutation:
  use UTF-8 byte offset instead of code-point offset
expected:
  Evidence slice failure

EX-NEG-FIX-COMMIT-003
base:
  Scene manifest
mutation:
  prose_path = runtime/checkpoints/scenes/v01/c001/s001/prose.md
expected:
  adopted-path failure

EX-NEG-FIX-COMMIT-004
base:
  Scene Commit manifest
mutation:
  volume_handoff_path = artifacts/handoffs/v01.json
expected:
  commit-type conditional failure

EX-NEG-FIX-COMMIT-005
base:
  Scene Generation manifest
mutation:
  current_order = 0
expected:
  parent-plus-one failure

EX-NEG-FIX-COMMIT-006
base:
  post-commit Story state
mutation:
  omit ev-000004-supported Thread transition
expected:
  committed-delta/root bidirectional mismatch
```

---

## 46. Crash mutations

```text
EX-NEG-FIX-CRASH-001
durable state:
  final Generation exists
  final Scene directory absent
  HEAD = 00000000
expected:
  Generation quarantined; no adoption inference

EX-NEG-FIX-CRASH-002
durable state:
  final Generation and Scene exist
  HEAD = 00000000
expected:
  both quarantined; no HEAD rewrite

EX-NEG-FIX-CRASH-003
durable state:
  HEAD = 00000001
  Run state still points to COMMIT-04
expected:
  reconcile to v01-c001-s002 without LLM call or ID allocation

EX-NEG-FIX-CRASH-004
durable state:
  checkpoint prose exists
  Checkpoint phase = CARD_ACCEPTED
expected:
  unreferenced prose quarantined; resume PROSE-01
```

---

# Part XI: Mechanical validation

## 47. Required fixture checks

The fixture validator must demonstrate:

```text
baseline inventory identity
effective config fingerprint and complete-file hash
Run-manifest/config consistency

SC Context hash-named path
SC candidate exact response
SC Review and Candidate-manifest identity
frozen Scene-card code-owned fields
safe forbidden disclosures
allowed-update target derivation
CARD_ACCEPTED checkpoint

Writer Context secret exclusion
canonical prose format/hash/character count
PROSE Review and Candidate manifest
PROSE_FROZEN checkpoint

Continuity Context secret exclusion
target-baseline equality
DELTA response code-owned-field exclusion
normalized candidate before values
Delta Review and Candidate manifest
DELTA_ACCEPTED checkpoint

COMMIT-01 no allocation
deterministic Evidence request order
Unicode code-point offsets
five Evidence allocations
merge-plan complete resolution
current Canon/Knowledge byte identity
Story-state exact changes
Evidence-index exact records
committed-delta/root bidirectional correspondence

Scene-manifest adopted paths
Commit-type Scene branch
Generation source-Scene branch
noncyclic manifest hashes
transaction validation
COMMIT_PREPARED phase
HEAD-last adoption

post-commit counters
successful Scene count/current_order equality
Run route to v01-c001-s002
inventory hash
negative mutation classifications
```

---

## 48. Mechanical acceptance conditions

This document is acceptable only when:

```text
all JSON fences parse
all embedded hashes recompute
all relative links resolve
all exact Evidence quotes occur once
every Evidence code-point slice equals its quote
prose hash includes one final LF
prose character count excludes that LF

current Canon and Knowledge hashes equal Genesis
Story State changes only authorized values and Scene position
Evidence index contains exactly ev-000001..ev-000005
candidate delta contains no code-owned ID/hash/offset
committed delta contains no Evidence proposal or unresolved local key

Scene card/prose checkpoint and adopted bytes are equal
Scene manifest contains no runtime/checkpoint/staging path
Commit manifest hashes Scene manifest
Generation manifest hashes Commit and Scene manifests
HEAD bytes are exactly 00000001 plus LF

no story-record counter changes
Evidence and Commit counters advance without reuse
successful_scene_commits = current_order = 1
next target is v01-c001-s002
```
