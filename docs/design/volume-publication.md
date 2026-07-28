# 巻公開の設計

## 1. 公開単位

読者向け出力は巻だけです。各巻の公開可否は同じ基準で判断します。各巻は、その巻の全計画、全場面、継続性更新が確定した後に一度だけ公開します。

最終巻にも別の公開工程、確認記録、LLM 呼出し、シリーズ完結判定はありません。最終巻の巻公開済みが制作完了です。

```text
scene_commit
  → volume_publication(vN)
  → volume_plan(vN+1)  # N が最終巻でない
  → completed           # N が最終巻
```

全巻結合原稿、シリーズ公開、完結結果、巻引継ぎは作りません。

## 2. 巻公開成果物

```text
publications/
  volume-pub-v04-000004/
    record.json
    manuscript.md
```

- `record.json`: 巻公開の不変な記録
- `manuscript.md`: 読者向けの唯一の巻原稿

```json
{
  "schema_version": 1,
  "volume_publication_id": "volume-pub-v04-000004",
  "volume_number": 4,
  "input_selection_id": "selection-000077",
  "settings_id": "settings-000001",
  "series_plan_id": "series-plan-0001",
  "volume_plan_id": "volume-plan-v04",
  "current_state_id": "gen-000123",
  "chapter_plan_ids": ["chapter-plan-v04-c001"],
  "scene_ids": ["scene-v04-c001-s001"],
  "publication_notice_type": null,
  "quality_disposition_refs": ["quality-disposition-scene-v04-c001-s001"],
  "created_at": "..."
}
```

`publication_notice_type` は `null`、`表現`、`編集` だけを許可します。公開記録は入力選択の各場面に対応する不変 `quality_disposition` を `quality_disposition_refs` として固定します。残存重大指摘が一つでもあれば、許可された品質判定の注意種別を決定的に集約します。`表現` が一つでもあれば `表現`、なければ `編集` とし、残存重大指摘がなければ `null` です。非 `null` なら原稿先頭に仕様書の定型文を置きます。

コードは入力選択を読み、公開記録の計画・状態・場面 ID、各場面の品質判定 ID、公開注意を決める設定 ID が対応するスナップショットスロットと完全一致し、欠落・余剰参照がないことを検証します。品質判定の集合と `publication_notice_type` が決定的な集約規則に一致しない場合は公開を拒否します。その後、計画順、ID の集合と重複、全場面の採用済み状態、決定的に構築した原稿、公開注意、作者用情報の不在を検証します。

## 3. 結末必須事項の扱い

結末必須事項は公開直前に救済する対象ではありません。

1. 初期設計で、必須事項 ID と達成条件を確定する。
2. シリーズ・巻・章・場面計画で、各事項を進めるまたは解決する予定を明示する。
3. 場面確定で、本文根拠を持つ継続性更新として実際の進行・解決を記録する。
4. 各工程の通常の決定的検証と独立 LLM 確認で、計画・本文・更新の整合性を評価する。

この処理は全巻共通です。最終巻にだけ追加の達成条件照合、確認記録、本文再生成、注意付き公開による例外を設けません。

## 4. 確定と復旧

1. 巻の入力を決定的に検証する。
2. 一時保存に公開記録と原稿を作る。
3. 内容、参照、注意文を検証し `volume_publication/prepared` を保存する。
4. 一時保存を公開先へ原子的に名前変更する。
5. `publication_finalized` を保存する。
6. `published_volumes` を更新し、次巻または `completed` へ収束する。

一時保存完全かつ最終配置不在なら確定を続行し、最終配置完全かつ一時保存不在なら状態だけを前進します。双方がある、または不正なら自動的に削除・再選択せず停止します。公開済み巻、公開原稿、構成元の採用参照は変更できません。
