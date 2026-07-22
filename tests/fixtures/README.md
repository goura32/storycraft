# Storycraft Test Fixtures

このdirectoryには、Storycraft Version 1の自動試験で使用する最小fixtureを置く。

## 方針

- 実際のJSONまたはMarkdown fileを試験コードが読み込む。
- Markdown文書内へ巨大なJSON例を複製しない。
- 正常fixtureと不正fixtureをdirectoryで分ける。
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
| `publication/` | 4巻Publication |
| `workspace/` | run-state、counters、config |
| `recovery/` | Crash位置と期待するRecovery分類 |
| `provider/` | Provider Adapter応答 |
| `security/` | Prompt injectionとredaction |
| `invalid/` | 意図的に不正なfixture |

## 作品の前提

仮題は『潮騒の記憶』。

主人公の澪は、海辺の町へ戻り、失われた記憶と姉・凪の秘密を追う。
灯台火災の夜がシリーズ全体の中心Threadであり、4巻で姉妹が真相を受け止め、町を離れずに再出発する。

## 利用方法

試験コードは、このdirectoryをpackage source treeから直接参照せず、repository rootまたはtest resource helperから解決する。

不正fixtureは、file名または隣接する`expected.json`で期待errorを示す。
