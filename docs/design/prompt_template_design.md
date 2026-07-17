# プロンプトテンプレートと出力契約

> この文書は、次世代実装が実際に送信するJinjaテンプレートと、採用前の検証契約を対応付ける設計資料である。製品仕様は[製品仕様](../product/SPECIFICATION.md)を正本とする。

## 正本と記録

- 実送信プロンプトの正本は `templates/prompts/` である。
- `src/storycraft/nextgen_model.py` は工程名をテンプレート名へ対応付け、`PromptTemplate.render_system()` と `render_user()` でsystem/userメッセージを構築する。Python文字列に工程別契約を重複させない。
- 採用可否は `src/storycraft/nextgen.py` の工程別検証器が決める。JSON object モードだけを信用して採用してはならない。
- 生の要求と応答はシリーズ作業場所の `raw/` にJSONと同stemのMarkdownで残す。草稿・批評・修正版・失敗理由・採用済み状態は `state.json` に残す。

## 現行工程とテンプレート

| 次世代工程 | 生成 | 批評 | 修正 |
|---|---|---|---|
| `plan` | `user/generate_plan.j2` | `user/critique_plan.j2` | `user/fix_plan.j2` |
| `scene_card` | `user/generate_scene_cards.j2` | `user/critique_scene_cards.j2` | `user/fix_scene_cards.j2` |
| `scene` | `user/generate_scene_write.j2` | `user/critique_scene_write.j2` | `user/fix_scene_write.j2` |
| `closure` | `user/generate_closure_check.j2` | `user/critique_closure_check.j2` | `user/fix_closure_check.j2` |

共通systemメッセージは `system/common.j2` である。テンプレートにない工程は次世代モデルから呼び出せない。

## 全巻計画 `plan`

| 項目 | テンプレートが要求する内容 | 採用前の検証 |
|---|---|---|
| `volumes` | 依頼された巻数と一致する4〜10巻の配列 | 4〜10件、依頼巻数と完全一致 |
| `volumes[].number` | 1から始まる欠番・重複なしの連番 | 実行順と一致する連番 |
| `volumes[].title` | その巻だけを表す空でない巻題 | 空文字列を拒否 |
| `volumes[].chapters` | 少なくとも1章。指定時は`chapters_per_volume`と件数完全一致 | 空配列・件数不一致を拒否 |
| `chapters[].number` | 巻内で1から始まる欠番・重複なしの連番 | 実行順と一致する連番 |
| `change` | 出来事列挙でなく読了後に成立する変化または区切り | 空文字列を拒否 |
| `leaves_question` | 最終巻以外では未解決の問い、最終巻は空文字列 | 最終巻以外の空文字列を拒否 |

## 場面カード `scene_card`

`scene_id` は入力実行対象と完全一致する。`visible_thread_ids` は入力の既知IDだけ、`allowed_update_ids` はその部分集合だけを含める。最終場面では全未回収IDを両方へ含める。検証器は未知ID、重複ID、不可視ID、最終場面の未許可未回収IDを拒否する。

## 場面成果物 `scene`

- `content` は注釈、箇条書き、Markdown、執筆メモを含まない完成日本語本文である。空本文を拒否する。
- `handoff_summary` は本文で起きた事実、終点、未解決点だけを記す。本文外の人物、設定、期間、出来事、予測、計画、解釈を加えない。空文字列を拒否する。
- `state_updates` は `allowed_update_ids` だけを使い、`open`、`in_progress`、`resolved` のいずれかとする。未知ID、未許可ID、同一ID重複を拒否する。
- 最終場面は初回企画の結末へ到達し、未回収主要問いをすべて本文根拠で `resolved` にする。

## 完結確認 `closure`

`resolved_ids` は入力台帳の全IDを一度ずつ含める。`ending_reached` は採用済み場面で初回企画の結末に実際に到達したときだけtrueにする。検証器はID集合不一致、重複、未回収時のtrueを拒否する。

## 批評と修正

批評テンプレートは、確認できる契約違反だけを `severity`、`field`、`description`、`suggestion` の4キーを持つ `issues` に出す。問題がなければ空配列にする。称賛、点数、出版可否、候補に存在しない問題は出さない。自然な日本語以外、簡体字・中国語混入、明白な誤字、人称混乱も対象にする。

修正テンプレートは、候補、批評、元入力を受け、対象工程と同じ出力スキーマ・制約を再掲する。指摘されていない正しいID、順序、本文事実を失わず、修正版は草稿と同じ検証器で再検証する。

## 検証手順

1. 各工程の検証器から必須・列挙・相互整合・採用条件を抽出する。
2. `PromptTemplate.render_user()` に実行時コンテキストを渡し、未展開のJinjaトークンがないことを確認する。
3. rawの `sent_messages` と同stem Markdownに、対応テンプレートの内容と実データが記録されることを確認する。
4. 決定的モデルで、生成、批評、修正、状態保存、完結確認、Markdown出力を通す。
