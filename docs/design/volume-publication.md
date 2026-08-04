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
  "created_at": "..."
}
```

`record.json` は未知項目を拒否し、`schema_version`（整数 `1`）、`volume_publication_id`（ID表の `volume-pub-vNN-{通番6桁}`）、`volume_number`（1以上の整数）、`input_selection_id`、`created_at`（UTC RFC3339）を必須とする。`publication_notice_type` は省略、または文字列 `編集` だけを許可し、`null` を含む他の値を拒否する。設定、計画、状態、場面、本文・継続性品質判定は `input_selection_id` から導出し、record へ複写しない。`volume_number` は導出した採用済み volume plan の巻番号と一致し、同じ selection から導出する全対象 scene、scene prose、本文・継続性品質判定、状態、計画が一意かつ有効でなければならない。`manuscript.md` はその同じ導出集合だけを計画順に並べた決定的出力とし、`publication_notice_type="編集"` のときだけ先頭の定型文を持つ。

**公開注意集約規則（決定的）:**
- `scene_prose_disposition.vNN.cMM.sKK` の品質判定だけについて、`remaining_major_issues` が空でないかを確認する。これは本文の `critical` 指摘だけを巻全体へ集約する対象である
- `continuity_disposition.vNN.cMM.sKK` の品質判定だけは、欠落・重複・結果不正を公開拒否判定として検証する。`scene_plan` と `scene_card` は専用の品質 disposition slot を持たず、採用時に候補全体の形式・親計画・入力束を検証済みであることを前提に、公開時は選択された内容と lineage の決定的整合だけを再検証する。いずれも `publication_notice_type` へ集約しない
- いずれかの本文品質判定で `remaining_major_issues` が非空なら `publication_notice_type = "編集"` を保存する
- すべて空なら `publication_notice_type` キーを省略する（`null` を書かない）
- 対象本文ごとに品質判定が一件だけ存在し、`result` が `accepted | accepted_with_notice` のいずれかであることを確認する。欠落・重複・列挙外なら公開を拒否する（`publication_invalid` で `blocked`）
- 各場面の `continuity_disposition.{coordinate}` slot にも品質判定が一件だけ存在し、`result` が `accepted | accepted_with_notice` であることを確認する。継続性品質判定は本文品質判定と別に検証するが、巻全体の公開注意へ集約しない。
- `remaining_major_issues` の非空判定は `critical` 指摘だけを対象とし、`notice` 指摘は公開注意の集約対象にしない。

巻公開サービスは`validate_workspace()`を経由しない直接呼出しでも、各品質判定のcandidate・review recordをworkspaceから再読込し、record自身のschema、candidate ID一致、review ID一致、critical evidence bindingを再検証してから公開stagingを作成します。

コードは `input_selection_id` から対象の計画・状態・場面・本文・継続性品質判定・設定を導出し、欠落・重複・列挙外の参照がないことを検証します。本文・継続性品質判定の集合と `publication_notice_type` が決定的な集約規則に一致しない場合は公開を拒否します。その後、計画順、全場面の採用済み状態、決定的に構築した原稿、公開注意、作者用情報の不在を検証します。公開記録には導出可能な ID 群を再保存しません。

## 3. 結末必須事項の扱い

結末必須事項は公開直前に救済する対象ではありません。

1. 初期設計で、必須事項の`thread_name`と達成条件を確定する。
2. シリーズ・巻・章・場面計画で、各事項を進めるまたは解決する予定を明示する。
3. 場面確定で、本文根拠を持つ継続性更新として実際の進行・解決を記録する。
4. 各工程の通常の決定的検証と独立 LLM 確認で、計画・本文・更新の整合性を評価する。

この処理は全巻共通です。最終巻にだけ追加の達成条件照合、確認記録、本文再生成、注意付き公開による例外を設けません。公開工程は LLM を呼びません。未解決事項の本文上の進行・解決は通常の独立 LLM 確認で意味的に確認し、上限到達時は他の本文と同じく注意付き採用にします。公開前は、その場面で確定済みの状態・根拠位置・selection lineageの決定的検証だけを行います。

## 4. 確定と復旧

1. 巻の入力を決定的に検証する。
2. 一時保存に公開記録と原稿を作る。
3. 内容、参照、注意文を検証し、公開ディレクトリ一つを target とする `pending_commit` manifest を保存する。
4. 公開ディレクトリ全体を公開先へ原子的に名前変更する。
5. manifest target を再検証する。
6. `published_volumes` を更新し、次巻または `completed` へ収束する。

一時保存完全かつ最終配置不在なら確定を続行し、最終配置完全かつ一時保存不在なら状態だけを前進します。公開ディレクトリ target の staging と最終配置がともにある、または不正なら自動的に削除・再選択せず停止します。公開済み巻、公開原稿、構成元の採用参照は変更できません。
