# 依頼入口と未解決事項の解決の契約

## 1. 依頼入口

新規作品は、採用済み依頼文またはキーワード入力のどちらか一方から始めます。

| 入口 | 必須入力 | 出力 | 次工程 |
|---|---|---|---|
| 依頼文 | 依頼内容 | 不変 `request` | `initial_design` |
| キーワード | 1個以上の短いキーワード | 依頼候補、確認、採用済み `request` | `initial_design` |

キーワード起点は `request_intake` 工程です。`init` は入力 keywords を `inputs/keywords-{通番6桁}/record.json` として不変確定し、`run` がその入力記録と不変 settings を読んで生成、確認、修正を行います。入力記録は `keywords_id`、正規化したキーワード配列、言語、created_at を持ち、selection 前の候補・確認・呼出し記録は `keywords_id` と `settings_id` を必ず参照します。採用時だけ、採用済み `request` を唯一の初期化時成果物として `input_selection_id=null` で不変確定し、直後に最初の選択スナップショットを確定します。

採用済み依頼は次を満たします。

- `title`: 空でない文字列
- `genre`: 1件以上の重複しない空でない文字列配列
- `premise`: 空でない文字列
- `required_elements` と `avoid`: 文字列配列。重複なし
- `ending_preference`: 空でない文字列
- `volume_count`: 4〜10 の整数
- `language`: `ja`

直接依頼でもキーワード起点でも、依頼採用時に、採用済み `request`、依頼採用記録、`request` と `settings` をスロットに持つ最初の選択スナップショット、`current_stage=initial_design` を原子的に確定します。採用済み `request` は唯一の初期化時成果物として `input_selection_id=null` を持ちます。初期設計採用は、この最初のスナップショットの後続を作ります。

## 2. 未解決事項の正本

初期設計は、各未解決事項を未解決事項として作ります。正規形未解決事項はコード採番 ID、名称、種別、結末必須性、説明を持ちます。結末必須未解決事項は達成条件を一つ持ちます。

`generation.unresolved_thread_states` は各未解決事項 ID に次を持ちます。

```json
{
  "status": "open | progressed | resolved",
  "evidence_scene_ids": [],
  "resolved_condition_refs": []
}
```

`resolved` は結末必須未解決事項の達成条件をすべて満たす本文根拠があるときだけ許可します。

## 3. 予定の連鎖

シリーズ計画、巻計画、章計画、場面計画は、段階ごとに次の未解決事項割当を持ちます。

- series-plan: `thread_id`、`action`、`volume_number`、`required_conditions`。結末必須事項の `resolve` 対象巻は一意。
- volume-plan: `thread_id`、`action`、`chapter_number`、`required_conditions`。親 series-plan と同じ巻・操作・条件に限る。
- chapter-plan: `thread_id`、`action`、`scene_number`、`required_conditions`。親 volume-plan と同じ巻・章・操作・条件に限る。
- scene-plan: `thread_id`、`action`、完全座標 `{volume_number, chapter_number, scene_number}`、`required_conditions`。親 chapter-plan と同じ操作・条件に限る。

`required_conditions` と `resolved_condition_refs` は、初期設計でコード採番した `ending_condition_id` だけを参照します。説明文を代用しません。

- シリーズ計画: 結末必須未解決事項ごとに `resolve` の対象巻を一つだけ予定する。
- 巻 / 章計画: 親計画の割当を次の座標粒度まで具体化する。新しい `resolve` を作らない。
- 場面計画: 親章計画の割当を完全座標に具体化する。
- 場面カード: その操作に必要な状態更新だけを許可する。

親計画の各 allocation は、その `thread_id`、`action`、`required_conditions`、親座標を持つ一つ以上の子 allocation に漏れなく具体化し、子 allocation は親の座標範囲を狭めるだけです。`resolve` はシリーズ計画から場面計画まで一つの連鎖で完全具体化し、場面計画では完全座標を一意に持ちます。親計画にない未解決事項、操作、条件、または親の対象外の座標は形式不正です。

## 4. 本文から解決まで

`resolve` を予定した場面は、次をすべて満たす必要があります。

1. 場面本文に達成条件を満たす本文根拠がある。
2. 継続性更新が未解決事項を `resolved` に変更する。
3. 更新が本文位置と `ending_condition_id` を `resolved_condition_refs` に記録する。
4. 場面確定がその更新を後続の作品状態へ一度だけ適用する。

`progress` は同じ手順で `progressed` にできますが、達成条件の全充足は要求しません。`introduce` は `open` のままでもよいです。

コードは本文根拠位置、場面計画の操作、カードの許可更新、未解決事項状態の遷移を検証します。LLM は本文が条件を意味的に満たすかを確認します。

## 5. 巻公開の検証

巻公開は、当該巻で `resolve` を予定した未解決事項が正規形現在状態で `resolved` であり、`resolved_condition_refs` と本文根拠位置が全 `ending_condition_id` を漏れなく参照することを決定的に検証します。いずれかが不合格なら `publication_invalid` を `last_error.code` に保存して停止します。本文が達成条件を意味的に満たすかは、`resolve` 場面の通常の独立 LLM 確認で判定し、上限到達時は他の本文と同じく最後の形式有効版を注意付き採用します。

最終巻でも追加の達成条件照合、確認記録、本文再生成、注意付き公開による例外を設けません。シリーズ計画が結末必須未解決事項ごとに `resolve` の対象巻を一意に定め、巻・章・場面計画がその巻の中で具体座標を定め、各巻共通の公開検証が当該巻に予定された `resolve` の解決と本文根拠を検証するため、最終巻の通常公開が完了すれば全結末必須未解決事項も通常経路で検証済みになります。

## 6. 復旧

`resolve` 場面の計画・本文・継続性更新・根拠が不整合なら停止し、その作業場所を再開しません。公開済み巻の本文、場面、作品状態、公開記録は変更できません。
