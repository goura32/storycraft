# 依頼入口と未解決事項の解決の契約

## 1. 依頼入口

新規作品は、採用済み依頼文またはキーワード入力のどちらか一方から始めます。

| 入口 | 必須入力 | 出力 | 次工程 |
|---|---|---|---|
| 依頼文 | 依頼内容 | 不変 `request` | `initial_design` |
| キーワード | 1個以上の短いキーワード | 依頼候補、確認、採用済み `request` | `initial_design` |

キーワード起点は `request_intake` 工程です。生成、確認、修正は共通品質ループを使います。`generation_context` はキーワード、固定設定、言語です。確認入力はこれと依頼候補、修正入力はこれと直前候補と今回確認です。候補・確認・修正の記録は最初の選択スナップショットの前に保存する監査記録であり、`input_selection_id` を持ちません。採用時だけ、採用済み `request` を唯一の初期化時成果物として `input_selection_id=null` で不変確定し、直後に最初の選択スナップショットを確定します。

採用済み依頼は次を満たします。

- `title` と `genre`: 空でない文字列
- `premise`: 空でない文字列
- `required_elements` と `forbidden_elements`: 文字列配列。重複なし
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

シリーズ、巻、章、場面計画は未解決事項割当を持ちます。

```json
{
  "thread_id": "入力 catalog から選んだ既存 ID",
  "action": "introduce | progress | resolve",
  "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
  "required_conditions": ["ending-condition-000001"]
}
```

`required_conditions` と `resolved_condition_refs` は、初期設計でコード採番した `ending_condition_id` だけを参照します。説明文を代用しません。

- シリーズ計画: 結末必須未解決事項ごとに `resolve` を一つだけ予定する。
- 巻 / 章計画: 親計画の予定を狭める。新しい `resolve` を作らない。
- 場面計画: 親計画と同じ座標・操作・条件を持つ。
- 場面カード: その操作に必要な状態更新だけを許可する。

親計画にない未解決事項、操作、条件、座標は形式不正です。

## 4. 本文から解決まで

`resolve` を予定した場面は、次をすべて満たす必要があります。

1. 場面本文に達成条件を満たす本文根拠がある。
2. 継続性更新が未解決事項を `resolved` に変更する。
3. 更新が本文位置と `ending_condition_id` を `resolved_condition_refs` に記録する。
4. 場面確定がその更新を後続の作品状態へ一度だけ適用する。

`progress` は同じ手順で `progressed` にできますが、達成条件の全充足は要求しません。`introduce` は `open` のままでもよいです。

コードは本文根拠位置、場面計画の操作、カードの許可更新、未解決事項状態の遷移を検証します。LLM は本文が条件を意味的に満たすかを確認します。

## 5. 巻公開の検証

巻公開は、当該巻で `resolve` を予定した未解決事項が正規形現在状態で `resolved` であることを検証します。未解決なら `volume_publication_invalid` で停止します。

最終巻でも追加の達成条件照合、確認記録、本文再生成、注意付き公開による例外を設けません。シリーズ計画が結末必須未解決事項ごとに最終的な `resolve` 座標を一意に定め、各巻共通の公開検証が当該巻に予定された `resolve` の解決と本文根拠を検証するため、最終巻の通常公開が完了すれば全結末必須未解決事項も通常経路で検証済みになります。

## 6. 復旧

`resolve` 場面の計画・本文・継続性更新・根拠の不整合は、`authority_reference_inconsistency` として停止する。この原因の保護された解決記録だけが、その場面計画から未公開依存末端までを選び直しまたは除外できる。公開済み巻の本文、場面、作品状態、公開記録は変更できません。
