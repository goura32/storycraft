# Storycraft

LLMが、利用者が最初に決めた題材と結末を基に、KDP個人出版向けの小説シリーズを**最後まで書き切る**ための道具。

## 正本

- [要件](docs/product/REQUIREMENTS.md): 製品として必ず守る約束
- [仕様](docs/product/SPECIFICATION.md): 現在の実装方針

## 今の段階

要件と仕様の初版を定義済み。first-release の実装も完了（§10.8 の範囲）。
`storycraft run/resume/step` で動作する。

### 実装状況 (first-release)

- `src/storycraft/`: 全ステージの実行・状態保存・再開・生データ保存
- 検証（§4 ID/enum）は場面応答に適用、不正IDを検出して再試行で修正
- 多様性目標注入（§3.0, promptモード）
- 確認済み: plan/characters/world/timeline/threads/volplan/cards/scenes が通る
- 全文完走（数時間）は未検証。ステージ単位の `step` で確認運用

### 次の課題

- 文字数目安は機械的強制せず目安（qwen が短く書く傾向あり、人間が後調整）
- 全文一括実行の所要時間と安定性の検証
