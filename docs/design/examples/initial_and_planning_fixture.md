# Initial and planning fixture

This document is the complete authoring fixture for:

```text
fixture_id = lighthouse-input-and-genesis-v3
planning_fixture_id = lighthouse-planning-v3
baseline_fixture_id = null
```

It covers:

```text
Keyword source
Brief generation and adoption
INIT-01 Concept
INIT-02 People
INIT-03 World
INIT-04 Arcs/Threads/Ending/Knowledge
INIT-05 integrated bundle
INIT-06 empty semantic Review
deterministic INIT-ID mapping
complete Genesis Canon/Knowledge/State/Evidence
Genesis Commit and Generation manifests
adopted initial-design snapshot
Series-map candidate and adoption
Volume-1 candidate and adoption
Chapter-1 candidate and adoption
post-CH-ID counters and next target
```

The data contracts are defined by:

- [`../contracts/data/brief_and_initial.md`](../contracts/data/brief_and_initial.md)
- [`../contracts/data/planning_artifacts.md`](../contracts/data/planning_artifacts.md)
- [`../contracts/ledger/canon_records.md`](../contracts/ledger/canon_records.md)
- [`../contracts/ledger/story_state.md`](../contracts/ledger/story_state.md)
- [`../contracts/ledger/runtime_records.md`](../contracts/ledger/runtime_records.md)
- [`../data_contract_examples.md`](../data_contract_examples.md)

Every JSON block in this document is a complete logical value. The SHA-256 values are calculated from the compact canonical JSON bytes defined by `data_contract_examples.md`, including exactly one final LF. Pretty indentation in this document is presentation-only.

---

## 1. Fixture constants

```text
fixture story:
  岬の灯

input mode:
  keywords

Volumes:
  4

Genesis Generation:
  00000000

Genesis Commit:
  commit-00000000

first planned Scene:
  v01-c001-s001

fake clock:
  2026-07-22 UTC

revision rounds:
  0

transport retries:
  0

response-structure retries:
  0
```

This baseline contains no adopted Scene, Handoff, Evidence record, Publication, or `output/CURRENT`.

---

# Part I: Input
## 2. Keyword source

```text
EXACT ARTIFACT
path = input/keywords.json
example_id = EX-POS-INPUT-001
```

```json
{
  "avoid": [
    "主人公だけが全責任を負う結末",
    "説明だけで謎を解決する場面"
  ],
  "ending_hint": "町が灯を守る意思を持つ",
  "genre_hint": "海洋幻想譚",
  "keywords": [
    "灯台",
    "海",
    "失われた鍵",
    "町の共同責任"
  ],
  "notes": "四巻構成。各巻で局所的な解決を置き、最終巻で灯台の再点灯と町の意思決定を完結させる。",
  "title_hint": "岬の灯",
  "volumes_hint": 4
}
```

Canonical SHA-256:

```text
cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f
```

Cross-contract condition:

```text
source hash for adopted Brief =
cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f
```

## 3. Brief content response

```text
EXACT RESPONSE
operation = INPUT-02
example_id = EX-POS-INPUT-002
```

```json
{
  "avoid": [
    "主人公だけが全責任を負う結末",
    "説明だけで謎を解決する場面"
  ],
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
  "target_reader": "成人読者",
  "title": "岬の灯",
  "volumes": 4,
  "want": "停止した灯台の原因を追い、町全体が灯を守る仕組みを作る"
}
```

Canonical SHA-256:

```text
db953c0f83fa420abfc618368f8531059c57af71112e70f3aeb21506dbfbe24e
```

The response contains no profile ID, source hash, timestamp, persistent ID, or Runtime field.

## 4. Adopted Brief

```text
EXACT ARTIFACT
path = input/brief.json
example_id = EX-POS-INPUT-003
```

```json
{
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
}
```

Canonical SHA-256:

```text
75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7
```

Required equality:

```text
brief.source_hash =
SHA-256(input/keywords.json) =
cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f
```

# Part II: Initial-design provider responses
## 5. INIT-01 Concept

```text
EXACT RESPONSE
operation = INIT-01
example_id = EX-POS-INIT-001
```

```json
{
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
}
```

Canonical SHA-256:

```text
7ea40f5b5e6c00b86a39814b681b39e0f831cb55d354fb06801742afd0d75f99
```

## 6. INIT-02 People

```text
EXACT RESPONSE
operation = INIT-02
example_id = EX-POS-INIT-002
```

```json
{
  "characters": [
    {
      "aliases": [],
      "appearance_anchor": "潮に色褪せた青い外套と、腰の小さな工具袋。",
      "background": "岬の灯台守の家に生まれ、家業を継ぐことを当然とされてきた見習い。",
      "core_trait": "粘り強い",
      "immutable_facts": [
        "灯台の主灯と日誌の基本手順を知っている",
        "凪とは幼なじみである"
      ],
      "local_key": "mio",
      "name": "澪",
      "role": "protagonist",
      "scope": "series",
      "speech_anchor": "短く確かめるように話し、決めた後は言い切る。",
      "starting_emotional_state": "焦りを抑えて手順を守ろうとしている",
      "starting_goal": "日没までに灯台停止の原因を特定する",
      "starting_location_local_key": "cape-lighthouse",
      "starting_physical_condition": "疲労や負傷はない",
      "starting_pressure": "町が灯台守の家だけを責め始める前に結果を出す必要がある",
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
      "immutable_facts": [
        "港と灯台の旧式機構に詳しい",
        "澪とは幼なじみである"
      ],
      "local_key": "nagi",
      "name": "凪",
      "role": "ally",
      "scope": "series",
      "speech_anchor": "確認事項を順番に挙げ、断定の前に根拠を求める。",
      "starting_emotional_state": "澪への距離を測りながら設備を警戒している",
      "starting_goal": "灯台設備を安全に調べ、再故障を防ぐ",
      "starting_location_local_key": "cape-lighthouse",
      "starting_physical_condition": "右手首に古傷があるが作業可能",
      "starting_pressure": "無理な再点灯で港へ二次被害を出せない",
      "values": [
        "安全な整備",
        "共有できる記録"
      ]
    }
  ],
  "relationships": [
    {
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
      "local_key": "mio-nagi",
      "participant_a_local_key": "mio",
      "participant_b_local_key": "nagi",
      "relationship_origin": "幼なじみだったが、灯台管理をめぐる両家の対立で疎遠になった。",
      "relationship_type": "friendship",
      "scope": "series",
      "shared_state": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。",
      "starting_public_relation": "必要な作業のために再会した疎遠な幼なじみ",
      "structural_role": "primary"
    }
  ]
}
```

Canonical SHA-256:

```text
65c23c550b4b3a12c935423746d32ced587fd4a87ceaa47aa7abd250c4297fed
```

## 7. INIT-03 World

```text
EXACT RESPONSE
operation = INIT-03
example_id = EX-POS-INIT-003
```

```json
{
  "initial_story_time": {
    "parallel_group_id": null,
    "time_label": "初日の夕方"
  },
  "temporal_rules": [
    {
      "description": "主灯は日没後に必要となり、初日は日没までに停止原因を特定しなければならない。",
      "fixed_rule": "初日の夕方から日没までが最初の調査期限である。",
      "kind": "deadline",
      "local_key": "sunset-deadline",
      "related_local_keys": [
        "cape-lighthouse"
      ],
      "scope": "volume"
    }
  ],
  "world_entities": [
    {
      "description": "断崖の先に建つ石造灯台。主灯室、螺旋階段、地下の修理庫がある。",
      "immutable_rules": [
        "主灯は日没後に点灯する",
        "地下修理庫は専用鍵でのみ開く"
      ],
      "kind": "location",
      "local_key": "cape-lighthouse",
      "name": "岬の灯台",
      "scope": "series",
      "sensory_anchors": [
        "塩を含んだ冷たい風",
        "石壁を伝う低い振動",
        "消えた主灯の黒いレンズ"
      ]
    },
    {
      "description": "灯台の旧管理台帳に記録された小型の真鍮鍵。",
      "immutable_rules": [
        "地下修理庫の錠に対応する"
      ],
      "kind": "item",
      "local_key": "spare-key",
      "name": "真鍮の予備鍵",
      "scope": "series",
      "sensory_anchors": [
        "緑青の浮いた縁",
        "掌に残る冷たい重み"
      ]
    }
  ]
}
```

Canonical SHA-256:

```text
2c643cfb73f4b16b99de8940eab1cadee3eaf792e4f75cc2c70a135ddb07ac38
```

## 8. INIT-04 Arcs, Threads, Ending, and Knowledge

```text
EXACT RESPONSE
operation = INIT-04
example_id = EX-POS-INIT-004
```

```json
{
  "ending_criteria": [
    {
      "description": "町が灯台を共同で守る意思と具体的な役割分担を示す。",
      "local_key": "town-shared-light",
      "required": true,
      "scope": "series",
      "source_ending_text": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける"
    }
  ],
  "initial_knowledge_states": [
    {
      "audience_character_local_key": "nagi",
      "audience_type": "character",
      "fact_local_key": "spare-key-purpose",
      "status": "knows"
    },
    {
      "audience_character_local_key": null,
      "audience_type": "reader",
      "fact_local_key": "spare-key-purpose",
      "status": "hinted"
    }
  ],
  "knowledge_items": [
    {
      "author_truth": "予備鍵で地下修理庫を開けると、停止原因につながる旧式切替器と管理台帳を調べられる。",
      "canonical_fact": "真鍮の予備鍵は地下修理庫の錠に対応する。",
      "local_key": "spare-key-purpose",
      "scope": "series",
      "subject_local_key": "spare-key",
      "subject_type": "world_entity",
      "writer_visible_label": "予備鍵の役割"
    }
  ],
  "major_threads": [
    {
      "author_truth": "地下修理庫に残された旧式切替器と管理台帳が停止原因を示し、予備鍵がその調査を可能にする。",
      "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
      "local_key": "light-failure",
      "presentation_rule": "予備鍵、修理庫、台帳、切替器の順に根拠を開示し、説明だけで真相を確定しない。",
      "required": true,
      "resolution_condition": "旧式切替器の故障と管理記録の空白を公に確認し、安全な再点灯と共同管理を実現する。",
      "scope": "series"
    }
  ],
  "protagonist_arc": {
    "change_function": "孤立した義務感を、他者と選び直す責任へ変える。",
    "end_state": "町と責任を分け合いながら、自分の意思で灯台を守る。",
    "protagonist_local_key": "mio",
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
      "relationship_local_key": "mio-nagi",
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
  ]
}
```

Canonical SHA-256:

```text
a812c8dfb6095f4e520c4f6ac48b3a6ed8a267f481049b25caf020f4bd9aea4f
```

## 9. INIT-05 integrated bundle

```text
EXACT RESPONSE
operation = INIT-05
example_id = EX-POS-INIT-005
```

```json
{
  "arcs": {
    "ending_criteria": [
      {
        "description": "町が灯台を共同で守る意思と具体的な役割分担を示す。",
        "local_key": "town-shared-light",
        "required": true,
        "scope": "series",
        "source_ending_text": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける"
      }
    ],
    "initial_knowledge_states": [
      {
        "audience_character_local_key": "nagi",
        "audience_type": "character",
        "fact_local_key": "spare-key-purpose",
        "status": "knows"
      },
      {
        "audience_character_local_key": null,
        "audience_type": "reader",
        "fact_local_key": "spare-key-purpose",
        "status": "hinted"
      }
    ],
    "knowledge_items": [
      {
        "author_truth": "予備鍵で地下修理庫を開けると、停止原因につながる旧式切替器と管理台帳を調べられる。",
        "canonical_fact": "真鍮の予備鍵は地下修理庫の錠に対応する。",
        "local_key": "spare-key-purpose",
        "scope": "series",
        "subject_local_key": "spare-key",
        "subject_type": "world_entity",
        "writer_visible_label": "予備鍵の役割"
      }
    ],
    "major_threads": [
      {
        "author_truth": "地下修理庫に残された旧式切替器と管理台帳が停止原因を示し、予備鍵がその調査を可能にする。",
        "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
        "local_key": "light-failure",
        "presentation_rule": "予備鍵、修理庫、台帳、切替器の順に根拠を開示し、説明だけで真相を確定しない。",
        "required": true,
        "resolution_condition": "旧式切替器の故障と管理記録の空白を公に確認し、安全な再点灯と共同管理を実現する。",
        "scope": "series"
      }
    ],
    "protagonist_arc": {
      "change_function": "孤立した義務感を、他者と選び直す責任へ変える。",
      "end_state": "町と責任を分け合いながら、自分の意思で灯台を守る。",
      "protagonist_local_key": "mio",
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
        "relationship_local_key": "mio-nagi",
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
    ]
  },
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
  "people": {
    "characters": [
      {
        "aliases": [],
        "appearance_anchor": "潮に色褪せた青い外套と、腰の小さな工具袋。",
        "background": "岬の灯台守の家に生まれ、家業を継ぐことを当然とされてきた見習い。",
        "core_trait": "粘り強い",
        "immutable_facts": [
          "灯台の主灯と日誌の基本手順を知っている",
          "凪とは幼なじみである"
        ],
        "local_key": "mio",
        "name": "澪",
        "role": "protagonist",
        "scope": "series",
        "speech_anchor": "短く確かめるように話し、決めた後は言い切る。",
        "starting_emotional_state": "焦りを抑えて手順を守ろうとしている",
        "starting_goal": "日没までに灯台停止の原因を特定する",
        "starting_location_local_key": "cape-lighthouse",
        "starting_physical_condition": "疲労や負傷はない",
        "starting_pressure": "町が灯台守の家だけを責め始める前に結果を出す必要がある",
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
        "immutable_facts": [
          "港と灯台の旧式機構に詳しい",
          "澪とは幼なじみである"
        ],
        "local_key": "nagi",
        "name": "凪",
        "role": "ally",
        "scope": "series",
        "speech_anchor": "確認事項を順番に挙げ、断定の前に根拠を求める。",
        "starting_emotional_state": "澪への距離を測りながら設備を警戒している",
        "starting_goal": "灯台設備を安全に調べ、再故障を防ぐ",
        "starting_location_local_key": "cape-lighthouse",
        "starting_physical_condition": "右手首に古傷があるが作業可能",
        "starting_pressure": "無理な再点灯で港へ二次被害を出せない",
        "values": [
          "安全な整備",
          "共有できる記録"
        ]
      }
    ],
    "relationships": [
      {
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
        "local_key": "mio-nagi",
        "participant_a_local_key": "mio",
        "participant_b_local_key": "nagi",
        "relationship_origin": "幼なじみだったが、灯台管理をめぐる両家の対立で疎遠になった。",
        "relationship_type": "friendship",
        "scope": "series",
        "shared_state": "過去の対立を話さないまま、停止した灯台の調査を共同で始める。",
        "starting_public_relation": "必要な作業のために再会した疎遠な幼なじみ",
        "structural_role": "primary"
      }
    ]
  },
  "world": {
    "initial_story_time": {
      "parallel_group_id": null,
      "time_label": "初日の夕方"
    },
    "temporal_rules": [
      {
        "description": "主灯は日没後に必要となり、初日は日没までに停止原因を特定しなければならない。",
        "fixed_rule": "初日の夕方から日没までが最初の調査期限である。",
        "kind": "deadline",
        "local_key": "sunset-deadline",
        "related_local_keys": [
          "cape-lighthouse"
        ],
        "scope": "volume"
      }
    ],
    "world_entities": [
      {
        "description": "断崖の先に建つ石造灯台。主灯室、螺旋階段、地下の修理庫がある。",
        "immutable_rules": [
          "主灯は日没後に点灯する",
          "地下修理庫は専用鍵でのみ開く"
        ],
        "kind": "location",
        "local_key": "cape-lighthouse",
        "name": "岬の灯台",
        "scope": "series",
        "sensory_anchors": [
          "塩を含んだ冷たい風",
          "石壁を伝う低い振動",
          "消えた主灯の黒いレンズ"
        ]
      },
      {
        "description": "灯台の旧管理台帳に記録された小型の真鍮鍵。",
        "immutable_rules": [
          "地下修理庫の錠に対応する"
        ],
        "kind": "item",
        "local_key": "spare-key",
        "name": "真鍮の予備鍵",
        "scope": "series",
        "sensory_anchors": [
          "緑青の浮いた縁",
          "掌に残る冷たい重み"
        ]
      }
    ]
  }
}
```

Canonical SHA-256:

```text
d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034
```

The bundle is independently valid. It is not a wrapper around four invalid partial objects and contains no planning fields.

## 10. INIT-06 Review response

```text
EXACT RESPONSE
operation = INIT-06
example_id = EX-POS-INIT-006
```

```json
{
  "issues": [],
  "summary": "Brief、Initial design、参照関係、開示境界に重大な問題はありません。"
}
```

Canonical SHA-256:

```text
88e246ec9dec5f1e46c60283cefe1d41c54d4a1c92ffbef6bb368b9aee2ddea2
```

Code derives `issues_empty` and routes directly to INIT-ID. No INIT-REV call occurs.

## 11. Candidate paths and hashes

| stage | canonical candidate path | candidate SHA-256 |
|---|---|---|
| `INPUT-02` | `runtime/candidates/input/brief/v0001/brief.json` | `db953c0f83fa420abfc618368f8531059c57af71112e70f3aeb21506dbfbe24e` |
| `INIT-01` | `runtime/candidates/initial-design/concept/v0001/concept.json` | `7ea40f5b5e6c00b86a39814b681b39e0f831cb55d354fb06801742afd0d75f99` |
| `INIT-02` | `runtime/candidates/initial-design/people/v0001/people.json` | `65c23c550b4b3a12c935423746d32ced587fd4a87ceaa47aa7abd250c4297fed` |
| `INIT-03` | `runtime/candidates/initial-design/world/v0001/world.json` | `2c643cfb73f4b16b99de8940eab1cadee3eaf792e4f75cc2c70a135ddb07ac38` |
| `INIT-04` | `runtime/candidates/initial-design/arcs/v0001/arcs.json` | `a812c8dfb6095f4e520c4f6ac48b3a6ed8a267f481049b25caf020f4bd9aea4f` |
| `INIT-05` | `runtime/candidates/initial-design/bundle/v0001/bundle.json` | `d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034` |

The accepted integrated-bundle hash used by `canon/initial-design.json` is:

```text
d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034
```

---

# Part III: INIT-ID allocation and Genesis
## 12. Deterministic local-key mapping

```text
EXACT VALUE
operation = INIT-ID
example_id = EX-POS-INIT-007
```

```json
[
  {
    "allocation_type": "character",
    "local_key": "mio",
    "persistent_id": "char-000001"
  },
  {
    "allocation_type": "character",
    "local_key": "nagi",
    "persistent_id": "char-000002"
  },
  {
    "allocation_type": "relationship",
    "local_key": "mio-nagi",
    "persistent_id": "rel-000001"
  },
  {
    "allocation_type": "location",
    "local_key": "cape-lighthouse",
    "persistent_id": "loc-000001"
  },
  {
    "allocation_type": "item",
    "local_key": "spare-key",
    "persistent_id": "item-000001"
  },
  {
    "allocation_type": "temporal_rule",
    "local_key": "sunset-deadline",
    "persistent_id": "rule-000001"
  },
  {
    "allocation_type": "thread",
    "local_key": "light-failure",
    "persistent_id": "thread-000001"
  },
  {
    "allocation_type": "ending_criterion",
    "local_key": "town-shared-light",
    "persistent_id": "ending-000001"
  },
  {
    "allocation_type": "knowledge_item",
    "local_key": "spare-key-purpose",
    "persistent_id": "fact-000001"
  }
]
```

Canonical SHA-256:

```text
b4d31e805bc71105953a89b4a1bca6306d8707f60c61a476d9563897ed57018f
```

Allocation is grouped by the Initial-design allocation registry. Within each group, local keys are sorted. Every counter is persisted before the ID is used.

## 13. Genesis current Canon

```text
EXACT ARTIFACT
path = canon/generations/00000000/current-canon.json
example_id = EX-POS-CANON-ROOT-001
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

Important corrections from the deprecated fixture:

```text
Relationship uses relationship_origin, not origin
Temporal rule ID is rule-000001, not time-000001
record_origin is explicit on every record
mutable Character/Relationship values are absent from Canon
```

## 14. Genesis Knowledge items

```text
EXACT ARTIFACT
path = canon/generations/00000000/knowledge-items.json
example_id = EX-POS-KNOWLEDGE-ROOT-001
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

Mio's implicit Character Knowledge state remains `unknown` and is therefore not stored as an explicit row.

## 15. Genesis Story state

```text
EXACT ARTIFACT
path = canon/generations/00000000/story-state.json
example_id = EX-POS-STATE-ROOT-001
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
  ],
  "relationship_states": [
    {
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
  ],
  "story_clock": {
    "current_chapter_number": null,
    "current_order": 0,
    "current_scene_number": null,
    "current_volume_number": null,
    "last_scene_id": null,
    "parallel_group_id": null,
    "time_label": "初日の夕方"
  },
  "thread_states": [
    {
      "progress": 0,
      "thread_id": "thread-000001",
      "thread_status": "open",
      "volume_disposition": null
    }
  ]
}
```

Canonical SHA-256:

```text
d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660
```

This root contains complete Character, Relationship, Thread, sparse Knowledge, and Story-clock data. It contains no `world_states`.

## 16. Genesis Evidence index

```text
EXACT ARTIFACT
path = canon/generations/00000000/evidence-index.json
example_id = EX-POS-EVIDENCE-ROOT-001
```

```json
{
  "records": []
}
```

Canonical SHA-256:

```text
d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89
```

The file is JSON, not JSON Lines. Initial-design assertions do not create prose Evidence.

## 17. Genesis Commit manifest

```text
EXACT ARTIFACT
path = canon/generations/00000000/commit-manifest.json
example_id = EX-POS-INIT-008
```

```json
{
  "after_generation": "00000000",
  "before_generation": null,
  "commit_id": "commit-00000000",
  "commit_type": "initial_design",
  "committed_at": "2026-07-22T00:05:01Z",
  "continuity_delta_sha256": null,
  "created_at": "2026-07-22T00:05:00Z",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 0,
  "evidence_ids": [],
  "evidence_index_sha256": "d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "local_key_mappings": [
    {
      "allocation_type": "character",
      "local_key": "mio",
      "persistent_id": "char-000001"
    },
    {
      "allocation_type": "character",
      "local_key": "nagi",
      "persistent_id": "char-000002"
    },
    {
      "allocation_type": "relationship",
      "local_key": "mio-nagi",
      "persistent_id": "rel-000001"
    },
    {
      "allocation_type": "location",
      "local_key": "cape-lighthouse",
      "persistent_id": "loc-000001"
    },
    {
      "allocation_type": "item",
      "local_key": "spare-key",
      "persistent_id": "item-000001"
    },
    {
      "allocation_type": "temporal_rule",
      "local_key": "sunset-deadline",
      "persistent_id": "rule-000001"
    },
    {
      "allocation_type": "thread",
      "local_key": "light-failure",
      "persistent_id": "thread-000001"
    },
    {
      "allocation_type": "ending_criterion",
      "local_key": "town-shared-light",
      "persistent_id": "ending-000001"
    },
    {
      "allocation_type": "knowledge_item",
      "local_key": "spare-key-purpose",
      "persistent_id": "fact-000001"
    }
  ],
  "manifest_version": "1.0",
  "parent_commit_id": null,
  "prose_sha256": null,
  "scene_card_sha256": null,
  "scene_id": null,
  "scene_manifest_sha256": null,
  "story_state_sha256": "d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660",
  "volume_handoff_path": null,
  "volume_handoff_sha256": null
}
```

Canonical SHA-256:

```text
0dd625924fd5cef951ba2aceb3547c91bbef8ba0a0814642fd643cff67d3ac05
```

The Commit uses the `initial_design` conditional branch. All Scene and Handoff fields are null.

## 18. Genesis Generation manifest

```text
EXACT ARTIFACT
path = canon/generations/00000000/generation-manifest.json
example_id = EX-POS-INIT-009
```

```json
{
  "commit_id": "commit-00000000",
  "commit_manifest_path": "canon/generations/00000000/commit-manifest.json",
  "commit_manifest_sha256": "0dd625924fd5cef951ba2aceb3547c91bbef8ba0a0814642fd643cff67d3ac05",
  "created_at": "2026-07-22T00:05:01Z",
  "current_canon_path": "canon/generations/00000000/current-canon.json",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 0,
  "evidence_index_path": "canon/generations/00000000/evidence-index.json",
  "evidence_index_sha256": "d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89",
  "generation_id": "00000000",
  "knowledge_items_path": "canon/generations/00000000/knowledge-items.json",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "manifest_version": "1.0",
  "parent_generation_id": null,
  "source_scene_id": null,
  "source_scene_manifest_path": null,
  "source_scene_manifest_sha256": null,
  "source_volume_handoff_path": null,
  "source_volume_handoff_sha256": null,
  "story_state_path": "canon/generations/00000000/story-state.json",
  "story_state_sha256": "d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660"
}
```

Canonical SHA-256:

```text
df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40
```

The Generation manifest hashes the Commit manifest but does not hash itself.

## 19. Adopted initial-design snapshot

```text
EXACT ARTIFACT
path = canon/initial-design.json
example_id = EX-POS-INIT-010
```

```json
{
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
}
```

Canonical SHA-256:

```text
e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce
```

Required relationships:

```text
brief_sha256 =
75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7

accepted_bundle_sha256 =
d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034

created_at =
Genesis committed_at =
2026-07-22T00:05:01Z
```

## 20. Genesis pointer

```text
EXACT ARTIFACT
path = canon/HEAD
```

Exact bytes:

```text
00000000\n
```

SHA-256:

```text
22dbe6b7b70a64966e31813e597db3e863492d341bee2fb05c0e8864773387af
```

The pointer is written only after the Genesis Generation and `canon/initial-design.json` are durable.

---

# Part IV: Series planning
## 21. SERIES-01 candidate

```text
EXACT RESPONSE
operation = SERIES-01
example_id = EX-POS-PLAN-001
```

```json
{
  "final_required_criterion_ids": [
    "ending-000001"
  ],
  "protagonist_end_state": "町と責任を分け合いながら、自分の意思で灯台を守っている。",
  "protagonist_start_state": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
  "series_question": "灯台停止の原因を明らかにし、町は灯を誰の責任として守るのか。",
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
}
```

Canonical SHA-256:

```text
450a883f030353874d490cbecd699d7f71ed9fa8d32a535e0edbd4a3217367eb
```

The required Major Thread chain is:

```text
Volume 1: open/0 → introduce → in_progress/1
Volume 2: in_progress/1 → advance → in_progress/2
Volume 3: in_progress/2 → advance → in_progress/3
Volume 4: in_progress/3 → resolve → resolved/4
```

The final required Ending criterion uses `satisfy`, and the final `reader_question` is null.

## 22. Adopted Series map

```text
EXACT ARTIFACT
path = plans/series-map.json
example_id = EX-POS-PLAN-ADOPTED-001
```

```json
{
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
}
```

Canonical SHA-256:

```text
5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294
```

Source relationships:

```text
source_generation_id = 00000000
source_generation_manifest_sha256 = df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40
brief_sha256 = 75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7
initial_design_sha256 = e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce
accepted_candidate_sha256 = 450a883f030353874d490cbecd699d7f71ed9fa8d32a535e0edbd4a3217367eb
```

# Part V: Volume-1 planning
## 23. VOL-01 candidate

```text
EXACT RESPONSE
operation = VOL-01
example_id = EX-POS-PLAN-003
```

```json
{
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
}
```

Canonical SHA-256:

```text
24f1e841f8c898db93d94cb4d8fcc2b8b498a1e567159b70f7b1cfb83a4288dc
```

Volume 1 has four Chapters and twelve planned Scenes:

```text
c001 = 3
c002 = 3
c003 = 3
c004 = 3
total = 12
```

The Volume-level Thread action is one `introduce` operation. Later Chapter and Scene plans preserve that required action rather than inventing multiple sequential operations.

## 24. Adopted Volume-1 design

```text
EXACT ARTIFACT
path = plans/volumes/v01/volume-design.json
example_id = EX-POS-PLAN-ADOPTED-002
```

```json
{
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
}
```

Canonical SHA-256:

```text
c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e
```

Volume 1 starts from Genesis and therefore has no preceding Handoff:

```text
preceding_volume_handoff_path = null
preceding_volume_handoff_sha256 = null
series_map_sha256 = 5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294
```

# Part VI: Chapter-1 planning
## 25. CH-01 candidate

```text
EXACT RESPONSE
operation = CH-01
example_id = EX-POS-PLAN-005
```

```json
{
  "chapter_end_function": "hook",
  "chapter_number": 1,
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
  "volume_number": 1
}
```

Canonical SHA-256:

```text
bd613bc160693488b0139be9782bf30fc1e5655982efbaa456470bc6eef8ca71
```

The Scene-function sequence is:

```text
s001 opening
s002 development
s003 resolution
```

The first downstream target is `v01-c001-s001`.

## 26. Adopted Chapter-1 design

```text
EXACT ARTIFACT
path = plans/volumes/v01/chapters/c001/chapter-design.json
example_id = EX-POS-PLAN-ADOPTED-003
```

```json
{
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
}
```

Canonical SHA-256:

```text
463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5
```

Chapter 1 starts from Genesis and has no preceding Chapter Handoff artifact:

```text
prior_chapter_handoff_path = null
prior_chapter_handoff_sha256 = null
volume_design_sha256 = c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e
```

## 27. Planning Review behavior

SERIES-02, VOL-02, and CH-02 each use the same valid empty semantic response shape:

```json
{
  "issues": [],
  "summary": "Brief、Initial design、参照関係、開示境界に重大な問題はありません。"
}
```

Canonical response SHA-256:

```text
88e246ec9dec5f1e46c60283cefe1d41c54d4a1c92ffbef6bb368b9aee2ddea2
```

For each candidate, code saves a distinct normalized `review.json` containing that candidate's operation, role, target, path, hash, Context hash, Call ID, and timestamp.

No Review artifact is reused across Series, Volume, and Chapter candidates even though the provider response content is identical.

---

## 28. Planning candidate paths and hashes

| stage | canonical candidate path | candidate SHA-256 |
|---|---|---|
| `SERIES-01` | `runtime/candidates/planning/series-map/v0001/series-map.json` | `450a883f030353874d490cbecd699d7f71ed9fa8d32a535e0edbd4a3217367eb` |
| `VOL-01` | `runtime/candidates/planning/volumes/v01/v0001/volume-design.json` | `24f1e841f8c898db93d94cb4d8fcc2b8b498a1e567159b70f7b1cfb83a4288dc` |
| `CH-01` | `runtime/candidates/planning/volumes/v01/chapters/c001/v0001/chapter-design.json` | `bd613bc160693488b0139be9782bf30fc1e5655982efbaa456470bc6eef8ca71` |

Each path uses `v0001`. A later semantic revision would create `v0002`; it would not overwrite these files.

---

# Part VII: Runtime postcondition
## 29. Counters after CH-ID

```text
EXACT ARTIFACT
path = runtime/counters.json
example_id = EX-POS-RUNTIME-COUNTERS-001
```

```json
{
  "active_elapsed_seconds": 13,
  "completion_audit_attempts_used": 0,
  "estimated_cost_used": 0,
  "input_tokens_used": 12650,
  "llm_calls_used": 13,
  "next_call_id": 14,
  "next_character_id": 3,
  "next_commit_id": 1,
  "next_culture_id": 1,
  "next_ending_id": 2,
  "next_evidence_id": 1,
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
  "output_tokens_used": 4880,
  "response_structure_retries_used": 0,
  "revision_rounds_used": 0,
  "successful_scene_commits": 0,
  "transport_retries_used": 0
}
```

Canonical SHA-256:

```text
176bfff1d8f7ca378fc1a68a98febf765c498a36541dd4d40e9628e49c99cfa5
```

The scripted fake made thirteen successful LLM calls and no retry or revision.

Token totals:

```text
input_tokens_used = 12650
output_tokens_used = 4880
```

Genesis uses reserved Commit/Generation suffix `0`, so:

```text
next_commit_id = 1
```

No Scene or Evidence has been committed:

```text
successful_scene_commits = 0
next_evidence_id = 1
```

## 30. Expected Run-state postcondition

The complete Run-state artifact is produced by the shared Runtime fixture builder because it also embeds the full Effective-config hash and Run-manifest identity.

After CH-ID, these fields are required:

```text
run_status = running
last_completed_stage = CH-ID
next_stage = SC-01

current_target_id = v01-c001-s001
current_volume_number = 1
current_chapter_number = 1
current_scene_number = 1
scene_phase = SCENE_NOT_STARTED

active_candidate_manifest_path = null
active_checkpoint_manifest_path = null

adopted_brief_path = input/brief.json
current_head_generation = 00000000
last_commit_id = commit-00000000
current_publication_id = null

stop_reason_code = null
stop_reason_detail = null
```

The builder must validate:

```text
Run-state adopted_brief_sha256 =
SHA-256(input/brief.json)

Run-state current_head_generation =
canon/HEAD
```

---

## 31. Provider usage script

| Call ID | stage | input tokens | output tokens |
|---|---|---:|---:|
| `call-000001` | `INPUT-02` | 800 | 180 |
| `call-000002` | `INIT-01` | 900 | 300 |
| `call-000003` | `INIT-02` | 1100 | 400 |
| `call-000004` | `INIT-03` | 900 | 300 |
| `call-000005` | `INIT-04` | 1200 | 450 |
| `call-000006` | `INIT-05` | 1300 | 700 |
| `call-000007` | `INIT-06` | 700 | 100 |
| `call-000008` | `SERIES-01` | 1200 | 800 |
| `call-000009` | `SERIES-02` | 650 | 100 |
| `call-000010` | `VOL-01` | 1300 | 650 |
| `call-000011` | `VOL-02` | 700 | 100 |
| `call-000012` | `CH-01` | 1250 | 700 |
| `call-000013` | `CH-02` | 650 | 100 |

Totals:

```text
llm_calls_used = 13
input_tokens_used = 12650
output_tokens_used = 4880
estimated_cost_used = 0
active_elapsed_seconds = 13
```

The fixture fake has zero pricing. Production pricing tests use separate configuration fixtures.

---

# Part VIII: Hash and inventory summary

## 32. Exact artifact inventory

| path | authority role | bytes | SHA-256 |
|---|---|---:|---|
| `canon/HEAD` | `pointer` | 9 | `22dbe6b7b70a64966e31813e597db3e863492d341bee2fb05c0e8864773387af` |
| `canon/generations/00000000/commit-manifest.json` | `adopted` | 1644 | `0dd625924fd5cef951ba2aceb3547c91bbef8ba0a0814642fd643cff67d3ac05` |
| `canon/generations/00000000/current-canon.json` | `adopted` | 4184 | `080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff` |
| `canon/generations/00000000/evidence-index.json` | `adopted` | 15 | `d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89` |
| `canon/generations/00000000/generation-manifest.json` | `adopted` | 1133 | `df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40` |
| `canon/generations/00000000/knowledge-items.json` | `adopted` | 488 | `3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d` |
| `canon/generations/00000000/story-state.json` | `adopted` | 1981 | `d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660` |
| `canon/initial-design.json` | `adopted` | 3571 | `e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce` |
| `input/brief.json` | `input` | 996 | `75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7` |
| `input/keywords.json` | `input` | 426 | `cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f` |
| `plans/series-map.json` | `adopted` | 8030 | `5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294` |
| `plans/volumes/v01/chapters/c001/chapter-design.json` | `adopted` | 4168 | `463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5` |
| `plans/volumes/v01/volume-design.json` | `adopted` | 5228 | `c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e` |
| `runtime/counters.json` | `runtime_resume` | 601 | `176bfff1d8f7ca378fc1a68a98febf765c498a36541dd4d40e9628e49c99cfa5` |

Inventory SHA-256:

```text
d76edaa75abeee5b133c207007f973b049b3199bffba5d50f6711b93f62f7811
```

The inventory hash is calculated from the canonical sorted array of:

```text
path
role
media_type
size_bytes
sha256
```

It does not include filesystem timestamps, permissions, inode values, or the absolute temporary workspace root.

---

## 33. Cross-artifact hash chain

```text
input/keywords.json
  cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f
    ↓ brief.source_hash

input/brief.json
  75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7
    ↓ initial-design.brief_sha256
    ↓ series-map.brief_sha256

INIT-05 bundle
  d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034
    ↓ initial-design.accepted_bundle_sha256

Genesis roots
  current Canon:   080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff
  Knowledge items: 3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d
  Story state:     d268ffad4c2b7609c0eca8bd94cf32c5dcfe84fc15beb308363281f77d5ee660
  Evidence index:  d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89
    ↓ Genesis Commit

Genesis Commit
  0dd625924fd5cef951ba2aceb3547c91bbef8ba0a0814642fd643cff67d3ac05
    ↓ Genesis Generation

Genesis Generation
  df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40
    ↓ Series / Volume / Chapter source_generation_manifest_sha256

initial-design.json
  e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce
    ↓ Series-map initial_design_sha256

Series candidate
  450a883f030353874d490cbecd699d7f71ed9fa8d32a535e0edbd4a3217367eb
    ↓ adopted Series map

adopted Series map
  5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294
    ↓ Volume-design series_map_sha256

Volume candidate
  24f1e841f8c898db93d94cb4d8fcc2b8b498a1e567159b70f7b1cfb83a4288dc
    ↓ adopted Volume design

adopted Volume design
  c1b062c1a7561d067c5af1f262379ad2ea649ed606c6e8760a07ef00c481689e
    ↓ Chapter-design volume_design_sha256

Chapter candidate
  bd613bc160693488b0139be9782bf30fc1e5655982efbaa456470bc6eef8ca71
    ↓ adopted Chapter design

adopted Chapter design
  463fc694a31f7eca17bb41a957876bb856790264924c2b681fe0df0a8e5932b5
    ↓ SC-01 planning source
```

No hash is a placeholder and no artifact contains its own file hash.

---

# Part IX: Required negative mutations

## 34. Initial-design mutations

```text
EX-NEG-FIX-INIT-001
base:
  INIT-02 Relationship
mutation:
  rename relationship_origin to origin
expected:
  unknown-field failure

EX-NEG-FIX-INIT-002
base:
  INIT-03 Temporal rule mapping
mutation:
  allocate time-000001
expected:
  persistent-ID registry failure

EX-NEG-FIX-INIT-003
base:
  Genesis Story state
mutation:
  remove char-000002 Character State
expected:
  Genesis completeness failure

EX-NEG-FIX-INIT-004
base:
  Genesis Knowledge State
mutation:
  add explicit char-000001 status=unknown
expected:
  sparse-default-row failure

EX-NEG-FIX-INIT-005
base:
  Genesis Evidence index
mutation:
  replace root with []
expected:
  root-Schema failure
```

---

## 35. Planning mutations

```text
EX-NEG-FIX-PLAN-001
base:
  Series Volume 2 Thread target
mutation:
  start_progress = 0
expected:
  adjacent planned Thread-chain failure

EX-NEG-FIX-PLAN-002
base:
  final Series Volume
mutation:
  plan_action = support
expected:
  required final criterion must satisfy

EX-NEG-FIX-PLAN-003
base:
  Volume design
mutation:
  target_chapter_count = 3
expected:
  Chapter-function length mismatch

EX-NEG-FIX-PLAN-004
base:
  Chapter design
mutation:
  omit final resolution Scene
expected:
  completion-role sequence and target count failure

EX-NEG-FIX-PLAN-005
base:
  adopted Chapter design
mutation:
  source_generation_id = 00000001
expected:
  source-generation/HEAD mismatch

EX-NEG-FIX-PLAN-006
base:
  adopted Volume design
mutation:
  preceding_volume_handoff_path = artifacts/handoffs/v00.json
expected:
  Volume-1 nullable-field and path failure
```

---

# Part X: Fixture validation

## 36. Validation order

The fixture validator must:

1. parse every JSON block;
2. recompute every listed canonical hash;
3. validate Keyword/Brief source linkage;
4. validate INIT stage-specific roots;
5. validate the integrated bundle independently;
6. validate deterministic local-key mapping and counter results;
7. validate Canon and Knowledge record Schemas;
8. validate complete Genesis Story state;
9. validate the Genesis Commit type branch;
10. validate the Generation hash graph;
11. validate `canon/HEAD`;
12. validate Initial-design IDs and hashes;
13. validate Series continuity across all four Volumes;
14. validate required final Thread and Ending conditions;
15. validate Volume-1 Chapter-function coverage;
16. validate Chapter-1 Scene-function coverage;
17. validate adopted plan metadata and source hashes;
18. validate counters and call sequence;
19. validate the exact artifact inventory hash;
20. derive the first Scene target `v01-c001-s001`.

---

## 37. Deprecated values rejected by this fixture

```text
fixture_id = lighthouse-initial-v2
one generic combined INIT object repeated for INIT-01..04
brief_version as integer
publishing_profile_id = default-md
Relationship.origin
time-000001
evidence_index = []
story_state with only relationships/story_clock
flat plans/volumes/v01.json
flat plans/chapters/v01/c001.json
Series role entry/development/escalation/resolution
chapter_count/objective-only Volume design
scene_count/objective-only Chapter design
placeholder hashes
```

---

## 38. Mechanical acceptance conditions

This fixture is valid only when tests demonstrate:

```text
all JSON blocks parse
all exact SHA-256 values recompute
all relative links resolve
Keyword-source and Brief constraints
stage-distinct INIT roots
complete integrated bundle
Review response exactness
deterministic local-key allocation
current Canon exact root and ordering
Knowledge exact root and sparse State
complete Character/Relationship/Thread State
Genesis Story clock
Genesis Commit conditional fields
Genesis Generation hash graph
HEAD exact bytes
initial-design snapshot hashes and IDs

four-volume Series continuity
required Major Thread open/0 through resolved/4 plan
required Ending criterion withhold/prepare/support/satisfy
Volume-1 four-Chapter/twelve-Scene design
Chapter-1 three-Scene role sequence
adopted plan source and parent hashes
no preceding Handoff for Volume 1
no preceding Chapter Handoff for Chapter 1

thirteen-call fake usage sequence
counter non-reuse values
zero Scene/Evidence commits
artifact inventory and inventory hash
first Scene target v01-c001-s001

negative mutation classifications
no deprecated field/path/ID
no placeholder or self hash
```
