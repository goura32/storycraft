# 依頼入口と thread 解決の契約

## 1. 依頼入口

新規作品は、採用済み依頼文またはキーワード入力のどちらか一方から始めます。

| 入口 | 必須入力 | 出力 | 次工程 |
|---|---|---|---|
| 依頼文 | request payload | 不変 `request` | `initial_design` |
| キーワード | 1個以上の短い keyword | request 候補、確認、採用済み `request` | `initial_design` |

キーワード起点は `request_intake` stage です。生成、確認、修正は共通品質ループを使います。`generation_context` は keyword、固定 settings、言語です。確認入力はこれと request 候補、修正入力はこれと直前候補と今回確認です。

採用済み request は次を満たします。

- `title` と `genre`: 空でない文字列
- `premise`: 空でない文字列
- `required_elements` と `forbidden_elements`: 文字列配列。重複なし
- `ending_preference`: 空でない文字列
- `volume_count`: 4〜10 の整数
- `language`: `ja`

必須要素と避ける条件が同じ意味内容で明示衝突すると形式不正です。request 採用時に、`request`、request adoption、`request` と `settings` を slot に持つ最初の selection snapshot、`current_stage=initial_design` を原子的に確定します。初期設計採用は、この最初の snapshot の successor を作ります。

## 2. thread の正本

初期設計は、各未解決事項を thread として作ります。canonical thread はコード採番 ID、名称、種別、結末必須性、説明を持ちます。結末必須 thread は達成条件を一つ持ちます。

`generation.unresolved_thread_states` は各 thread ID に次を持ちます。

```json
{
  "status": "open | progressed | resolved",
  "evidence_scene_ids": [],
  "resolved_condition_refs": []
}
```

`resolved` は結末必須 thread の達成条件をすべて満たす本文根拠があるときだけ許可します。

## 3. 予定の連鎖

シリーズ、巻、章、場面計画は thread allocation を持ちます。

```json
{
  "thread_id": "入力 catalog から選んだ既存 ID",
  "action": "introduce | progress | resolve",
  "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
  "required_conditions": ["達成条件の選択または説明"]
}
```

- series plan: 結末必須 thread ごとに `resolve` を一つだけ予定する。
- volume / chapter plan: 親 plan の予定を狭める。新しい `resolve` を作らない。
- scene plan: 親 plan と同じ座標・action・条件を持つ。
- scene card: その action に必要な状態更新だけを許可する。

親 plan にない thread、action、条件、座標は形式不正です。

## 4. 本文から解決まで

`resolve` を予定した場面は、次をすべて満たす必要があります。

1. scene prose に達成条件を満たす本文根拠がある。
2. continuity update が thread を `resolved` に変更する。
3. update が本文位置と達成条件を `resolved_condition_refs` に記録する。
4. scene commit がその update を successor generation へ一度だけ適用する。

`progress` は同じ手順で `progressed` にできますが、達成条件の全充足は要求しません。`introduce` は `open` のままでもよいです。

コードは本文根拠位置、scene plan の action、card の許可更新、thread state の遷移を検証します。LLM は本文が条件を意味的に満たすかを確認します。

## 5. 巻公開の検証

巻公開は、当該巻で `resolve` を予定した thread が canonical current state で `resolved` であることを検証します。未解決なら `volume_publication_invalid` で停止します。

最終巻の公開では、すべての結末必須 thread が `resolved` であり、各達成条件に本文根拠があることを決定的に検証します。これは最終巻だけの追加 LLM 確認ではありません。通常の plan、scene、continuity、公開 validator が持つ参照検証です。

## 6. 復旧

未公開の `resolve` 場面が不整合なら、保護された解決記録は、その場面計画から依存末端までを選び直しまたは除外できます。公開済み巻の本文、scene、generation、公開 record は変更できません。
