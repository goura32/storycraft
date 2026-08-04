# 場面制作工程の契約

## 1. 共通規則

場面制作は `scene_card`、`scene_prose`、`scene_continuity`、`scene_commit` の順です。本文と継続性更新は別候補ですが、場面確定では一つの単位にします。本文の修正後に古い継続性更新を使うことは許可しません。

候補を採用する工程は、候補全体の生成、決定的検証、独立 LLM 確認を行います。重大な指摘があり、`quality_revision_limit` の上限前であれば候補全体を修正して再検証・再確認します。候補や呼出し記録は作品正本ではありません。

## 2. 場面カード

| 区分 | 内容 |
|---|---|
| 責務 | 本文執筆に許す局所制約を、場面計画から具体化する |
| 必須入力スロット | `settings`、`initial_design`、`current_state`、対象 `scene_plan` |
| 出力成果物 | `scene-card` payload。視点人物、許可された事実・知識・開示、禁止開示、許可された状態更新、本文上の達成条件を持つ。場面座標は成果物外枠と selection slot が束縛し、LLM payload には含めない |
| 次工程 | `scene_prose`、同一場面座標 |

コードは、場面カードの座標と場面計画の一致、視点人物の実在、許可更新と未解決事項割当の一致、知識・開示の参照実在を検証します。LLM は、局所制約が場面目的・人物動機・読者体験を実現できるかを確認します。

## 3. 場面本文

| 区分 | 内容 |
|---|---|
| 責務 | 固定した場面カードと基準作品状態に従う本文候補を作る |
| 必須入力スロット | `settings`、`current_state`、対象 `scene_plan`、対象 `scene_card` |
| 出力成果物 | `scene-prose` 候補。本文、対象場面座標。基準作品状態 ID と場面カード ID は固定入力束からシステムが候補記録へ束縛する |
| 次工程 | `scene_continuity`。本文が採用済みの場合だけ |

本文生成には、上表の4スロットと、工程共通規則で定めた system/user 指示文だけを渡します。本文のprovider応答はJSON Schemaを要求しないraw text（`response_format=None`）で、コードが対象座標と本文を `scene-prose` CandidateResponse payloadへ包んでから候補検証・品質ループへ渡します。カードにない追加の文脈、カードが許可しない作者用秘密、視点人物が知らない情報、読者未開示情報、固定パスから探索した過去本文は渡しません。コードは、入力束の座標・基準作品状態・場面カードと必須本文項目を検証します。LLM は、視点、開示、人物知識、場面目的、予定した未解決事項の進行、文体・日本語品質を確認します。

## 4. 継続性更新

| 区分 | 内容 |
|---|---|
| 責務 | 採用済み本文により生じた事実・知識・開示・未解決事項状態の変化を根拠付きで提案する |
| 必須入力スロット | `settings`、`current_state`、対象 `scene_plan`、対象 `scene_card`、採用済み `scene_prose` |
| 出力成果物 | `continuity-update` 候補。変更集合、各変更の本文根拠位置。基準作品状態 ID と本文 ID は固定入力束からシステムが候補記録へ束縛する |
| 次工程 | `scene_commit`。更新が採用済みの場合だけ |

コードは、各変更がカードの許可更新内にあること、入力束の本文と根拠位置が実在すること、未解決事項の状態変更が場面計画の予定と整合すること、同じ事実を矛盾する値へ更新しないことを検証します。LLM は、本文に根拠があるか、変更が本文の意味を過不足なく反映するか、知識・開示の帰属が正しいかを確認します。

## 5. 場面確定

| 区分 | 内容 |
|---|---|
| 責務 | 本文と検証済み更新から、採用済み場面と後続現在状態を原子的に確定する |
| 必須入力スロット | `current_state`、対象 `scene_plan`、対象 `scene_card`、採用済み `scene_prose`、採用済み `scene_prose_disposition`、採用済み `continuity_update`、採用済み `continuity_disposition` |
| 出力成果物 | 不変 `scene`、後続 `generation`、場面確定記録、後続選択スナップショット |
| 次工程 | 次場面 `scene_plan`、次章 `chapter_plan`、または `volume_publication` |

`scene` の `current_state_id` は、場面本文・継続性更新を生成した時点の入力 selection にある基準 `generation` ID（入力状態）です。場面確定記録の `current_state_id` は、同じ場面の継続性更新を適用した後に出力された後続 `generation` ID（出力状態）です。同じフィールド名でも record kind が異なる別scopeであり、入力状態と出力状態を相互に取り違えて比較してはなりません。場面確定記録は `scenes/<scene-commit-id>/record.json` にだけ保存する未知項目拒否の不変記録で、`schema_version: 1`、`scene_commit_id`、`scene_id`、`scene_card_id`、`scene_prose_id`、`continuity_update_id`、`current_state_id`、`quality_disposition_id`、座標、`created_at` を必須とする。`quality_disposition_id` は同じ座標の `scene_prose_disposition.vNN.cMM.sKK` slot の品質判定 ID に完全一致し、継続性更新の品質判定は、継続性候補の採用前検証には使うが場面確定記録のこのslotには指定しない。継続性品質判定は後続選択スナップショットに保持し、継続性採用が完了していることを検証する。各 ID と座標は同じ scene の入力・出力成果物と一致し、本文・カード・更新の内容を複写しない。後続の作品状態は更新を一度だけ適用した新しい作品状態です。コードは、入力が同一場面座標・同一基準作品状態を指すこと、更新が検証済みであること、更新適用後の状態スキーマ・ID・知識・未解決事項状態が整合することを検証します。`scene` が内容と参照の正本であり、場面確定記録は同じIDを監査・復旧用に重ねて持つ非正本manifestです。両者の重複は本文や設定の複写ではなく、同一原子的確定を再検証するための参照束です。

`scene` は `scenes/<scene-id>/record.json` に、場面確定記録は `scenes/<scene-commit-id>/record.json` に別々に保存し、同じ `scene_commit` manifest の target として原子的に確定します。一時保存、場面、後続の作品状態、場面確定記録、後続選択スナップショット、次の `current_target` を一つの原子的確定で更新します。途中停止時は共通の `pending_commit=scene_commit` 収束規則を使い、二重適用・二重確定・新規 LLM 呼出しを行いません。継続性品質判定は `continuity_disposition.vNN.cMM.sKK` slot に一件だけ存在し、`accepted` または `accepted_with_notice` でなければ場面確定を拒否します。これは本文品質判定と別の監査記録であり、巻公開時の公開注意には集約しません。

## 6. 採用と選択スナップショット

各候補の採用では、入力スナップショットを複写して次のスロットを追加または置換します。

| 工程 | 追加・置換するスロット | 次工程 |
|---|---|---|
| `scene_card` | `scene_card.vNN.cMM.sKK`、`scene_card_adoption.vNN.cMM.sKK` | `scene_prose.vNN.cMM.sKK` |
| `scene_prose` | `scene_prose.vNN.cMM.sKK`、`scene_prose_adoption.vNN.cMM.sKK`、`scene_prose_disposition.vNN.cMM.sKK` | `scene_continuity.vNN.cMM.sKK` |
| `scene_continuity` | `continuity_update.vNN.cMM.sKK`、`continuity_adoption.vNN.cMM.sKK`、`continuity_disposition.vNN.cMM.sKK` | `scene_commit.vNN.cMM.sKK` |
| `scene_commit` | `scene.vNN.cMM.sKK`、`current_state`、`scene_commit.vNN.cMM.sKK` | 次場面・次章・巻公開 |

本文採用を置換するときは、同じ場面の継続性更新、継続性採用記録、継続性品質判定スロットを後続スナップショットから除外し、新本文から再作成します。次工程は候補の固定パスや有効候補を読まず、このスロットを読むだけです。

## 7. 修正・失敗

本文候補の修正は本文全体を置き換えます。本文の採用候補が変わったら、以前の継続性更新候補・確認・採用は再利用せず、採用済み新本文から継続性更新を新たに作ります。継続性更新の修正は更新候補全体を置き換えます。

生成、確認、修正の形式不正は各論理処理ごとに初回を含め `invalid_response_limit` 回まで、別シードで再呼出しします。重大指摘が上限前なら同一候補単位を修正し、品質修正上限に達した場合は最後の形式有効候補を注意付き採用します。残存重大指摘と根拠はquality recordに保存し、adoption/selectionに複写しません。修正応答が形式不正上限に達した場合は、`quality_revision_limit=0` で直前に形式有効な候補があるときだけ同候補を注意付き採用し、それ以外は `blocked` とします。生成または確認で有効候補がないまま形式不正上限に達した場合も、場面・後続の作品状態・選択スナップショットを確定せず `blocked` とします。通信失敗・設定不正・内部エラーは共通の停止・復旧契約に従います。
