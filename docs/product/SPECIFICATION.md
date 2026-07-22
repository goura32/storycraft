# Storycraft 製品仕様

> 次期正式リリースの振る舞いの正本。現行実装との差分は[実装状況](IMPLEMENTATION_STATUS.md)を参照する。

## 1. 用語

| 用語 | 意味 |
|---|---|
| 内部確定成果物 | 初期設計フェーズ内で次のINIT呼び出しへ渡せる成果物。外部フェーズの正本ではない。 |
| `initial_design_bundle`候補 | INIT-01〜05を統合した、レビュー・修正・検証対象。永続ID採番前。 |
| `initial_design_bundle` | 検証、ID採番、参照変換、原子的採用を終えた唯一の初期設計正本。 |
| `local_key` | 初期設計bundle内だけで参照する一意キー。LLMが永続IDの代わりに用いる。 |
| 正本候補 | 構造検証済み、未採用の成果物。 |
| 採用済み正本 | 後続工程の正式入力となる成果物。 |
| 場面内部checkpoint | 場面内の再開用保存物。後続場面の正式入力ではない。 |
| 場面採用 | 場面成果物全体とCanon・State更新を一体で原子的に確定すること。 |
| revision round | 正常なレビューがissueを返した後に実行できる修正呼び出し回数。初回レビューは含めない。 |
| transport retry | 一つのLLM呼び出しを成立させる通信・JSON処理の再試行。revision roundとは別。 |

Canonは採用済み固定事実・管理対象項目、現在Stateは場面採用で変化する現在値である。`temporal_rules`は長期規則、`story_clock`は場面進行である。

## 2. 入力と範囲

利用者は開始時にbriefまたはkeywordsを一度だけ渡す。通常実行中の巻・章・場面確認は要求しない。4〜10巻（推奨5巻）の日本語シリーズを生成し、巻別・全巻Markdownを出力する。KDP自動公開、Web UI、RAG、複数モデル自動選択、人間承認UI、旧state migrationは範囲外である。

## 3. 製品フェーズ

| # | フェーズ | フェーズ成果物 | 正式な採用済み正本 |
|---:|---|---|---|
| 1 | 入力確定 | brief | brief |
| 2 | シリーズ初期設計 | INIT成果物、bundle候補 | `initial_design_bundle` |
| 3 | series map | series map候補 | 不変のseries map |
| 4 | 巻設計 | 巻設計候補 | 対象巻設計 |
| 5 | 章設計 | 章設計候補 | 対象巻の章設計 |
| 6 | 場面設計 | 場面カードcheckpoint | なし |
| 7 | 本文生成 | 凍結本文checkpoint | なし |
| 8 | 差分抽出 | 継続性差分checkpoint | なし |
| 9 | 場面採用 | 場面成果物 | 更新済みCanon・Stateを含む場面 |
| 10 | 巻境界 | 巻handoff | 巻handoff |
| 11 | 完結監査 | audit attempt | 最後の構造正常な監査記録 |
| 12 | 出力 | Markdown・監査記録 | 公開出力 |

全巻を一括作成しない。`SERIES-ID`は全巻の不変series mapを採用する。後続巻の巻設計入力は、採用済み`initial_design_bundle`、採用済みseries map、**現在時点のHEADが指すCanon**、Story State、前巻handoff、対象巻番号、残り巻数、編集プロファイルである。詳細stage契約は[pipeline contracts](../design/pipeline_contracts.md)を正本とする。

## 4. シリーズ初期設計

INIT-01〜04は内部確定成果物、INIT-05はbundle候補の組立である。

| 呼び出し | 出力 |
|---|---|
| INIT-01 `initial_concept` | 作品コンセプト |
| INIT-02 `initial_characters_relationships` | 人物・関係。`local_key`で相互参照 |
| INIT-03 `initial_world_temporal_rules` | 世界・`temporal_rules` |
| INIT-04 `initial_series_arcs` | 長期変化、major thread、ending criteria |
| INIT-05 `initial_canon_assembly` | `initial_design_bundle`候補、開始State、知識状態 |
| INIT-06 `initial_design_review` | bundle候補全体のissue |

確定順序は、INIT-01〜05 → INIT-06 → bundle候補全体の一括修正 → 全体再レビュー → 上限まで反復 → 機械的検証 → コードの永続ID一括採番 → `local_key`参照を永続IDへ変換 → `initial_design_bundle`の原子的採用、である。

LLMは永続IDを生成しない。レビュー・修正中の追加・削除・統合も`local_key`で扱う。採番後には初期設計の意味修正を行わない。採番後に構造エラーが見つかれば採用せず停止し、採番済みIDは別recordへ再利用しない。INIT個別応答は来歴として保存できるが、巻・章・場面は採用済み`initial_design_bundle`だけを参照する。

## 5. 設計と新規Canon項目

巻設計は人物・関係の変化、thread、対立、巻末問いを定める。章設計は順序付き章、目的、開始・終了目標、thread action、場面数を定める。場面カードはPOV、開示制約、更新許可に加え、次の`new_item_policy`を持つ。

```json
{"allowed_types":["character","location","organization","item","supporting_thread"],"max_items":2,"purpose":"場面に必要な局所項目だけを許可する"}
```

`allowed_types`外、`max_items`超過、major thread、ending criterion、固定世界規則は提案不可である。許可しない場面は`max_items: 0`とする。上限は機械的な暴走防止である。

新規局所Canon項目のlifecycleは、`scope`を`scene`/`chapter`/`volume`/`series`、`status`を`active`/`inactive`/`resolved`/`retired`で表す。巻境界の`volume_disposition`は別enumの`resolve`/`carry_over`/`retire`である。carry_overはstatusではなく、`status: active`、`scope: series`、次巻handoff追加を意味する。supporting threadは既定で`scope: volume`、`required: false`であり、完結の機械的必須条件ではない。

## 6. 共通revision loop

対象はシリーズ初期設計、巻設計、章設計、場面設計、本文、継続性差分、巻handoffだけである。

1. 生成し、構造正常な候補を保持する。
2. 対象全体をレビューする。
3. issueがあれば、全成果物と全issueを一回で一括修正する。
4. 構造正常な修正版を候補にし、全体を再レビューする。
5. `max_revision_rounds`後、最新の構造正常候補を採用し、残存issueを保存する。

レビューseverityは停止条件ではない。レビューJSON構造不正は同じレビュー呼び出しのretry、修正結果の構造不正は同じrevision round内の有限再生成として扱い、roundを追加消費しない。transport retry・構造再生成を使い切れば停止する。以前の正常候補は保持する。

## 7. 本文、差分、場面採用

本文は本文だけを返す。差分抽出は凍結本文から、次を返す。

```json
{
  "existing_item_updates": [{"operation":"set","target_type":"relationship","target_id":"rel-0001","field":"current_distance","before":"警戒","after":"限定的な信頼","scene_id":"v01-c03-s02","evidence":"本文の完全一致引用"}],
  "new_item_proposals": [],
  "knowledge_updates": [], "thread_updates": [], "time_update": {},
  "ending_evidence_proposals": [{"criterion_id":"ending-0001","scene_id":"v05-c20-s02","evidence":"本文の完全一致引用","relation":"supports"}],
  "handoff_summary":""
}
```

更新operationは`set`/`append`/`remove`/`transition`だけである。target typeごとに更新可能field・fieldごとの許可operation・`before`必須性・evidence必須性を定義し、固定情報、自由path、任意JSON Patchは許可しない。

`ending_evidence_proposals`は既存criterionのみを参照し、現在場面ID、本文完全一致evidence、`supports`/`contradicts`だけを許可する。criterion本体や新criterionは変更しない。コードはcriterion/scene ID、全文一致、重複を検証し、`ending_evidence_index`へ保存する。major threadの根拠も同じindex設計を利用できる。

場面カード、凍結本文、差分は内部checkpointである。コード検証・新規ID採番・Canon/State/knowledge/thread/clock/evidence index更新・handoffがそろった場面成果物だけを一回の原子的保存で採用する。

## 8. 完結Gate・workspace・出力

完結は三段階で判定する。詳細項目は[pipeline contracts](../design/pipeline_contracts.md)、workspace・公開物は[workspace layout](../design/workspace_layout.md)を正本とする。

1. **COMP-PRE（監査前Gate）**: コードが予定巻・章・必要場面、非空本文、artifact欠落/重複/hash、required major thread、各required criterionの検証済み`supports` evidence 1件以上、全ID、current canon/story state/artifact/evidence indexを検証する。監査結果は要求しない。
2. **COMP-AUDIT（意味監査）**: COMP-PRE成功後だけLLMが監査する。監査JSONが構造正常なら最後の正常結果として保存する。意味issueは保存し、機械的完成条件を満たせば続行できる。構造不正でattempt残ありなら同一入力で再監査し、正常結果が一件もなく枯渇すれば停止する。
3. **COMP-PUBLISH（公開前Gate）**: COMP-PRE成功、構造正常audit 1件以上、staging出力検証成功を要求する。

監査issueで監査JSONを修正しない。監査工程自身は本文・Canonを変更しない。`contradicts`だけではcriterionを満たさない。supportsとcontradictsの両方は監査へ渡す。出力は一時領域で検証後、原子的に公開する。
