# Storycraft テスト fixture

このdirectoryには、Storycraft Version 1の自動試験で使用する最小fixtureを置く。ここにある入力、原稿、設定、作品前提はテストデータであり、製品仕様・要件・作品 Canon の正本ではない。現行契約は[`../../docs/SPECIFICATION.md`](../../docs/SPECIFICATION.md)に従う。

## 方針

- 実際のJSONまたはMarkdown fileを試験コードが読み込む。
- Markdown文書内へ巨大なJSON例を複製しない。
- 入力・成果物の不正fixtureは`invalid/`に置き、Providerの失敗応答は`provider/`に置く。
- fixture内のIDと参照は、同じscenario内で一貫させる。
- Credential、実Provider名、実API keyを含めない。
- Hash、Manifest graph、Publication Gateを前提にしない。

## 主なscenario

| Directory | 用途 |
|---|---|
| `brief/` | Brief入力 |
| `keywords/` | Keywords入力 |
| `initial-design/` | Initial Design |
| `plans/` | Series／Volume／Chapter／Scene Plan |
| `scene/` | Scene Card、本文、Continuity、Review |
| `generation/` | Initial GenerationとScene後Generation |
| `handoff/` | Volume Handoff |
| `completion/` | 完結判定3状態 |
| `publication/` | 独立した最小Publication組立scenario |
| `workspace/` | run-state、counters、config |
| `recovery/` | Crash位置と期待するRecovery分類 |
| `provider/` | Provider Adapter応答 |
| `security/` | Prompt injectionとredaction |
| `invalid/` | 意図的に不正なfixture |

## 作品の前提

仮題は『潮騒の記憶』。

主人公の澪は、海辺の町へ戻り、失われた記憶と姉・凪の秘密を追う。
灯台火災の夜がシリーズ全体の中心Threadであり、4巻で姉妹が真相を受け止め、町を離れずに再出発する。

`provider/prose-success.txt`と`scene/prose.md`は、Provider成功応答とScene本文という別の検証目的で同じ本文を使う。片方を変更する場合は、同一本文である必要が残るかを確認する。

`publication/`はScene fixtureとは独立した最小scenarioである。同じ題名・章名は説明用の再利用であり、`scene/prose.md`を要約・変換して作る出力例ではない。

## 利用方法

試験コードは、このdirectoryをpackage source treeから直接参照せず、repository rootまたはtest resource helperから解決する。

不正fixtureは、file名または隣接する`expected.json`で期待errorを示す。

`provider/malformed-json.txt`は、コードフェンスや補足文を含むため応答全体が生JSONではない形式不正を表す。Recoveryの`tree.txt`はcrash時の配置だけを表し、期待する`resume`、`regenerate`、`manual`分類は同じscenarioの`expected.json`で判定する。
