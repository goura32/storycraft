# 場面制作工程の契約

## 1. 共通規則

場面制作は `scene_card`、`scene_prose`、`scene_continuity`、`scene_commit` の順です。本文と継続性更新は別候補ですが、場面確定では一つの単位にします。本文の修正後に古い継続性更新を使うことは許可しません。

候補を採用する工程は、候補全体の生成、決定的検証、独立 LLM 確認、必要なら候補全体の修正、再検証・再確認を行います。候補や呼出し記録は作品正本ではありません。

## 2. 場面カード

| 区分 | 内容 |
|---|---|
| 責務 | 本文執筆に許す局所制約を、場面計画から具体化する |
| 必須入力 slot | `settings`、`initial_design`、`current_state`、対象 `scene_plan` |
| 出力 artifact | `scene-card`。場面座標、視点人物、許可された事実・知識・開示、禁止開示、許可された状態更新、本文上の達成条件 |
| 次工程 | `scene_prose`、同一場面座標 |

コードは、scene card の座標と scene plan の一致、視点人物の実在、許可更新と thread allocation の一致、知識・開示の参照実在を検証します。LLM は、局所制約が場面目的・人物動機・読者体験を実現できるかを確認します。

## 3. 場面本文

| 区分 | 内容 |
|---|---|
| 責務 | 固定した場面カードと基準作品状態に従う本文候補を作る |
| 必須入力 slot | `settings`、`current_state`、対象 `scene_plan`、対象 `scene_card`、カードが明示する許可済み context refs |
| 出力 artifact | `scene-prose` 候補。本文、対象場面座標、基準 generation ID、scene card ID |
| 次工程 | `scene_continuity`。本文が採用済みの場合だけ |

本文生成に、カードが許可しない作者用秘密、視点人物が知らない情報、読者未開示情報、固定パスから探索した過去本文を渡しません。コードは、座標、基準 generation、scene card ID、必須本文 field を検証します。LLM は、視点、開示、人物知識、場面目的、予定した thread の進行、文体・日本語品質を確認します。

## 4. 継続性更新

| 区分 | 内容 |
|---|---|
| 責務 | 採用済み本文により生じた事実・知識・開示・thread 状態の変化を根拠付きで提案する |
| 必須入力 slot | `settings`、`current_state`、対象 `scene_plan`、対象 `scene_card`、採用済み `scene_prose` |
| 出力 artifact | `continuity-update` 候補。基準 generation ID、本文 ID、変更集合、各変更の本文根拠位置 |
| 次工程 | `scene_commit`。更新が採用済みの場合だけ |

コードは、各変更が card の許可更新内にあること、本文 ID・根拠位置が実在すること、thread の `progress|resolve` が scene plan の allocation と一致すること、同じ事実を矛盾する値へ更新しないことを検証します。LLM は、本文に根拠があるか、変更が本文の意味を過不足なく反映するか、知識・開示の帰属が正しいかを確認します。

## 5. 場面確定

| 区分 | 内容 |
|---|---|
| 責務 | 本文と検証済み更新から、採用済み場面と successor current state を原子的に確定する |
| 必須入力 slot | `current_state`、対象 `scene_plan`、対象 `scene_card`、採用済み `scene_prose`、採用済み `continuity_update` |
| 出力 artifact | 不変 `scene`、successor `generation`、scene commit 記録、successor selection snapshot |
| 次工程 | 次場面 `scene_plan`、次章 `chapter_plan`、または `volume_publication` |

`scene` は本文、場面座標、基準 generation ID、scene card ID、continuity update ID を参照します。successor generation は更新を一度だけ適用した新しい作品状態です。コードは、入力が同一 scene 座標・同一基準 generation を指すこと、更新が検証済みであること、更新適用後の state schema・ID・知識・thread 状態が整合することを検証します。

staging、scene、successor generation、scene commit 記録、successor selection snapshot、次の `current_target` を一つの原子的確定で更新します。途中停止時は共通の `pending_commit=scene_commit` 収束規則を使い、二重適用・二重確定・新規 LLM 呼出しを行いません。

## 6. 採用と selection snapshot

各候補の採用では、入力 snapshot を複写して次の slot を追加または置換します。

| 工程 | 追加・置換する slot | 次工程 |
|---|---|---|
| `scene_card` | `scene_card.vNN.cMM.sKK`、`scene_card_adoption.vNN.cMM.sKK` | `scene_prose.vNN.cMM.sKK` |
| `scene_prose` | `scene_prose.vNN.cMM.sKK`、`scene_prose_adoption.vNN.cMM.sKK`、`scene_prose_disposition.vNN.cMM.sKK` | `scene_continuity.vNN.cMM.sKK` |
| `scene_continuity` | `continuity_update.vNN.cMM.sKK`、`continuity_adoption.vNN.cMM.sKK`、`continuity_disposition.vNN.cMM.sKK` | `scene_commit.vNN.cMM.sKK` |
| `scene_commit` | `scene.vNN.cMM.sKK`、`current_state`、`scene_commit.vNN.cMM.sKK` | 次場面・次章・巻公開 |

本文採用を置換するときは、同じ場面の continuity update、continuity adoption、continuity disposition slot を successor snapshot から除外し、新本文から再作成します。次工程は候補の固定パスや active candidate を読まず、この slot を読むだけです。

## 7. 修正・失敗

本文候補の修正は本文全体を置き換えます。本文の採用候補が変わったら、以前の continuity update 候補・確認・採用は再利用せず、採用済み新本文から継続性更新を新たに作ります。継続性更新の修正は更新候補全体を置き換えます。

生成、確認、修正の形式不正は各論理 operation ごとに初回を含め固定5回、別 seed で再呼出しします。重大指摘が上限前なら同一候補単位を修正し、上限到達なら最後の形式有効候補を注意付き採用します。形式不正・通信失敗・設定不正・内部エラーは、場面・successor generation・selection snapshot を確定せず、共通の停止・復旧契約に従います。
