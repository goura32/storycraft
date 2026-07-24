# Storycraft Documentation

Storycraft Version 1の文書入口です。各概念は一つの文書だけが所有し、他の文書は再定義せず参照します。

## 読書順

全体を理解する場合:

1. [`product/SPECIFICATION.md`](product/SPECIFICATION.md)
2. [`product/REQUIREMENTS.md`](product/REQUIREMENTS.md)
3. [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md)
4. 必要な`design/`文書
5. [`testing/ACCEPTANCE.md`](testing/ACCEPTANCE.md)
6. [`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md)

利用者はrepository rootの[`README.md`](../README.md)と`SPECIFICATION.md`だけを読めば、V1の目的と利用者向け振る舞いを確認できます。

## 文書Registry

| 文書 | 所有する内容 | 所有しない内容 |
|---|---|---|
| [`product/SPECIFICATION.md`](product/SPECIFICATION.md) | 利用者から見える振る舞い、対象範囲、用語の製品上の意味 | JSON field、path、内部関数 |
| [`product/REQUIREMENTS.md`](product/REQUIREMENTS.md) | 実装が満たす76件の検証可能要件 | 実装状況、詳細手順 |
| [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | 全体構造、component境界、Authority原則 | 個別Schema、Crash手順 |
| [`design/DATA_MODEL.md`](design/DATA_MODEL.md) | Storyデータの意味、Authority、不変条件 | 保存path、Stage順 |
| [`design/WORKSPACE_AND_RECOVERY.md`](design/WORKSPACE_AND_RECOVERY.md) | Workspace、atomic確定、Lock、Crash Recovery | Prompt、Story上の意味 |
| [`design/PIPELINE.md`](design/PIPELINE.md) | Stage、operation、Review／Revision、遷移 | file確定手順、Provider request |
| [`design/LLM_INTEGRATION.md`](design/LLM_INTEGRATION.md) | Context、Prompt、Provider、Retry、timeout、Budget、Audit | Story Stateの意味、Release結果 |
| [`testing/ACCEPTANCE.md`](testing/ACCEPTANCE.md) | Release判定に必要な受入試験 | 新しい仕様や設計 |
| [`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md) | 現在の実装、試験、Release blocker | 仕様、設計の正本 |

Fixtureは[`../tests/fixtures/`](../tests/fixtures/)に置き、説明は[`../tests/fixtures/README.md`](../tests/fixtures/README.md)を正本とします。

## 競合時の判断

文書へ共通の優先順位は設けません。競合した内容を所有する文書を正本とします。

```text
利用者向け振る舞い      SPECIFICATION.md
必須条件                REQUIREMENTS.md
全体構造                ARCHITECTURE.md
Storyデータ             DATA_MODEL.md
保存・Recovery          WORKSPACE_AND_RECOVERY.md
Stage・遷移             PIPELINE.md
LLM連携                 LLM_INTEGRATION.md
Release試験             ACCEPTANCE.md
現在の進捗              IMPLEMENTATION_STATUS.md
```

`IMPLEMENTATION_STATUS.md`が正本文書と競合する場合は、正本文書を優先し、Statusを修正します。

## 変更先

| 変更内容 | 最初に更新する文書 |
|---|---|
| 利用者から見える振る舞い | `product/SPECIFICATION.md` |
| 必須要件 | `product/REQUIREMENTS.md` |
| componentやAuthority原則 | `architecture/ARCHITECTURE.md` |
| Storyデータ | `design/DATA_MODEL.md` |
| path、atomic確定、Recovery | `design/WORKSPACE_AND_RECOVERY.md` |
| Stage、Loop、遷移 | `design/PIPELINE.md` |
| Context、Prompt、Provider | `design/LLM_INTEGRATION.md` |
| Release試験 | `testing/ACCEPTANCE.md` |
| 現在の進捗 | `product/IMPLEMENTATION_STATUS.md` |

大きな変更は次の順で反映します。

```text
SPECIFICATION
→ REQUIREMENTS
→ ARCHITECTURE
→ 対応するdesign文書
→ ACCEPTANCE
→ production code
→ 自動試験
→ IMPLEMENTATION_STATUS
→ README
```

試験文書だけで新しい仕様を追加したり、既存実装へ合わせるために上位契約を弱めたりしません。

## SchemaとFixture

厳密なJSON Schemaまたは同等のvalidatorはproduction assetを正本とします。Markdownでは意味、関係、不変条件、短い代表例だけを扱います。

Fixtureには次を明記します。

```text
用途
正常入力または不正入力
期待結果
関連する受入試験ID
```

巨大なJSONをMarkdownへ複製しません。

## 文書Review

文書変更時に次を確認します。

```text
正本の責務が一意
別文書の契約を再定義していない
同じStateのAuthorityを複数作っていない
仕様と実装状況を混ぜていない
例を必須Schemaとして扱っていない
要件IDが一意で欠番がない
全要件が受入試験から参照される
相対linkが存在する
Markdown fenceと節番号が整合する
廃止した用語、field、Stage、pathが残っていない
文書以外の変更を文書PRへ混ぜていない
```

推奨機械検査:

```bash
git diff --check
python -m unittest discover -s tests -p "test_*.py"
```

Requirement trace、Markdown link、節番号は、文書変更時の補助scriptまたはtestでも検査します。

## 状況確認

現在の実装範囲とRelease blockerは次だけを参照します。

[`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md)

> 文書は、仕様、要件、設計、試験、実装状況を分離し、一つの概念に一つの正本を持ちます。
