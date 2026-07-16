# Storycraft

利用者が最初に決めた題材と結末から、個人出版向けの日本語小説シリーズを最後まで書き切るための道具。

## 文書

- [要件](docs/product/REQUIREMENTS.md): 製品として変えてはいけない約束
- [製品仕様](docs/product/SPECIFICATION.md): 次の正式リリースで守る振る舞い
- [現行実装の位置付け](docs/product/IMPLEMENTATION_STATUS.md): 参照実装と次世代仕様の関係
- [次世代実装の設計方針](docs/design/next_generation_design.md): 正本状態、工程共通契約、受け入れテスト

## 現在の位置付け

現行コードは、次世代仕様に基づく互換なしの実装である。`run`、`resume`、`step` で一つの保存済みシリーズを扱う。

実LLMによる作品内容・販売原稿としての品質は、実行監査が終わるまで主張しない。
