# Context contracts

> Context投影の正本。元データは[ledger contracts](ledger_contracts.md)、工程I/Oは[pipeline contracts](pipeline_contracts.md)を参照する。Builderは純粋関数で、同一の正本snapshotと設定から同一JSON・同一`context_hash`を返す。

## 共通規則

| 項目 | 契約 |
|---|---|
| 並び順 | type → volume_number → chapter_number → scene_number → persistent ID。配列はこの順、object keyはUTF-8 codepoint順。 |
| hash | NFC正規化・key sort・compact JSONをUTF-8化したSHA-256。 |
| overflow | JSONを途中切断しない。低優先recordを決定的に除外し、既存handoff/summaryを優先する。必須情報が上限内に収まらなければ機械的停止。 |
| 要約 | Builder内部でLLM要約をしない。採用済みhandoff/summaryだけを利用する。 |
| secret | `author_truth`、`resolution_condition`、未採用候補はwriter系contextに入れない。 |

## Builder契約

| builder | 入力正本 | 選択・秘密投影 | 上限 / overflow優先順 |
|---|---|---|---|
| `build_initial_design_context` | brief | brief全量のみ | 20,000文字 / 入力超過は停止 |
| `build_series_map_context` | initial bundle | author truth・ending criteriaを含むauthor context | 30,000文字 / sensory anchor→supporting recordを除外 |
| `build_volume_design_context` | initial bundle, series map, current canon, story state, prior handoff | 対象巻、未完了major thread、前巻handoffを優先。author context | 36,000文字 / 完了supporting→遠いworld recordを除外 |
| `build_chapter_design_context` | 採用volume design, current canon, story state | 対象巻のみ。author context | 30,000文字 / 非対象scope recordを除外 |
| `build_scene_card_context` | 採用chapter design, current canon, story state, required thread assignment | 対象章・場面、直接参照recordだけ。author context | 24,000文字 / supporting recordを除外。必須assignmentが残らなければ停止 |
| `build_writer_context` | scene card, story state, current canon, knowledge state, prior handoff, style profile | POV、participant、visible world、POVが`knows`のfact、reader status、直前handoffだけ。author truth、resolution condition、他人物private knowledge、future scene/volume、ending秘密、未採用候補を除外 | 28,000文字 / sensory anchor→非participant visible recordを除外 |
| `build_continuity_context` | frozen prose, story state開始snapshot, allowed targets, knowledge items, new_item_policy, ID index | frozen prose全文、開始state、既知IDを必須。author truthはproposal検証にだけコードが使いLLMへ出さない | 32,000文字 / 本文または必須stateが収まらなければ停止 |
| `build_volume_handoff_context` | 採用済み当該巻artifact, current canon, story state | 採用本文・state・未完了threadだけ。未採用候補除外 | 30,000文字 / completed supporting recordを除外 |
| `build_completion_audit_context` | initial bundle, series map, current canon, story state, evidence index, published artifacts | author context。全criterion、全major thread、supports/contradicts evidenceを必須 | 48,000文字 / scene proseを含めずvolume handoffとevidence引用を優先。必須監査情報不足は停止 |

## writer projection

`writer_view`のfieldは`scene_card,pov_character,visible_characters,visible_relationship_state,visible_world,known_facts,reader_known_facts,previous_handoff,style_profile,forbidden_disclosures`に固定する。`known_facts`はPOV characterの`knowledge_status=knows`だけ、`reader_known_facts`は`revealed|partially_revealed|hinted`だけを含む。POV以外のcharacter knowledge、`author_truth`、解決条件、将来設計を含めない。

## 選択ログ

各builderは`context_hash`、入力正本hash、除外したrecord ID、文字数、上限、overflow有無をcall auditへ記録する。除外の再試行や恣意的な並び替えはしない。
