# Storycraft Documentation

Storycraft Version 1の文書入口。

このdirectoryには、製品仕様、要件、アーキテクチャ、詳細設計、受入試験、実装状況を置く。

同じ内容を複数文書へ重複させず、各文書の責務を分ける。

---

## 1. 最初に読む文書

Storycraft全体を理解する場合は、次の順で読む。

1. [`product/SPECIFICATION.md`](product/SPECIFICATION.md)
2. [`product/REQUIREMENTS.md`](product/REQUIREMENTS.md)
3. [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md)
4. 必要な`design/`文書
5. [`testing/ACCEPTANCE.md`](testing/ACCEPTANCE.md)
6. [`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md)

---

## 2. 文書一覧

### 製品

| 文書 | 責務 |
|---|---|
| [`product/SPECIFICATION.md`](product/SPECIFICATION.md) | 利用者から見える製品の振る舞い |
| [`product/REQUIREMENTS.md`](product/REQUIREMENTS.md) | 実装が満たすべき検証可能な要件 |
| [`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md) | 現在の実装・試験・移行状況 |

`IMPLEMENTATION_STATUS.md`は正本ではない。

仕様や設計を変更する場合は、対応する正本文書を先に更新する。

---

### アーキテクチャ

| 文書 | 責務 |
|---|---|
| [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | 全体構造、設計原則、Authority、主要component、用語、文書責務 |

Architectureの原則や用語を、別の補助文書へ分散させない。

---

### 詳細設計

| 文書 | 責務 |
|---|---|
| [`design/DATA_MODEL.md`](design/DATA_MODEL.md) | Storyデータの意味、関係、不変条件 |
| [`design/WORKSPACE_AND_RECOVERY.md`](design/WORKSPACE_AND_RECOVERY.md) | Workspace、保存、排他、確定処理、Crash Recovery |
| [`design/PIPELINE.md`](design/PIPELINE.md) | Stage、Loop、Review／Revision、Stage遷移 |
| [`design/LLM_INTEGRATION.md`](design/LLM_INTEGRATION.md) | Provider、Prompt、Context、秘密情報、Retry、timeout、Budget、Audit |

---

### 試験

| 文書 | 責務 |
|---|---|
| [`testing/ACCEPTANCE.md`](testing/ACCEPTANCE.md) | Release判定に必要な受入試験 |

実際のfixtureはrepository rootの次に置く。

```text
tests/fixtures/
```

Fixtureの説明は[`../tests/fixtures/README.md`](../tests/fixtures/README.md)を参照する。

---

## 3. 読者別の推奨順

### 製品利用者

```text
repository rootのREADME.md
↓
product/SPECIFICATION.md
```

内部実装を理解する必要がなければ、設計文書を読む必要はない。

---

### Product owner

```text
product/SPECIFICATION.md
↓
product/REQUIREMENTS.md
↓
product/IMPLEMENTATION_STATUS.md
```

---

### 実装担当者

```text
product/REQUIREMENTS.md
↓
architecture/ARCHITECTURE.md
↓
design/DATA_MODEL.md
↓
design/WORKSPACE_AND_RECOVERY.md
↓
design/PIPELINE.md
↓
design/LLM_INTEGRATION.md
↓
testing/ACCEPTANCE.md
```

---

### Test担当者

```text
product/REQUIREMENTS.md
↓
testing/ACCEPTANCE.md
↓
対応するdesign文書
↓
tests/fixtures/
```

---

### Reviewer

全体設計を確認する場合:

```text
architecture/ARCHITECTURE.md
↓
design/DATA_MODEL.md
↓
design/WORKSPACE_AND_RECOVERY.md
↓
design/PIPELINE.md
↓
design/LLM_INTEGRATION.md
```

Release可否を確認する場合:

```text
product/IMPLEMENTATION_STATUS.md
↓
testing/ACCEPTANCE.md
↓
test実行結果
```

---

## 4. Authorityの順序

文書間で内容が競合した場合は、次の役割を確認する。

```text
利用者向け振る舞い:
  product/SPECIFICATION.md

検証可能な必須条件:
  product/REQUIREMENTS.md

全体設計原則:
  architecture/ARCHITECTURE.md

データの意味:
  design/DATA_MODEL.md

保存と復旧:
  design/WORKSPACE_AND_RECOVERY.md

処理順:
  design/PIPELINE.md

LLM連携:
  design/LLM_INTEGRATION.md

Release試験:
  testing/ACCEPTANCE.md

現在状況:
  product/IMPLEMENTATION_STATUS.md
```

`IMPLEMENTATION_STATUS.md`が仕様や設計と競合する場合は、正本文書を優先する。

---

## 5. どこへ書くか

### 利用者から見える振る舞いを変更する

更新先:

```text
product/SPECIFICATION.md
```

その後、必要に応じて:

```text
product/REQUIREMENTS.md
architecture/ARCHITECTURE.md
design/*
testing/ACCEPTANCE.md
product/IMPLEMENTATION_STATUS.md
```

---

### 必須要件を追加する

更新先:

```text
product/REQUIREMENTS.md
```

条件:

```text
上位の製品仕様に根拠がある
自動試験で確認可能
既存要件と重複しない
```

---

### Storyデータを変更する

更新先:

```text
design/DATA_MODEL.md
```

具体的な保存pathやCrash処理は書かない。

---

### 保存構造やRecoveryを変更する

更新先:

```text
design/WORKSPACE_AND_RECOVERY.md
```

Stage意味やLLM Promptを再定義しない。

---

### StageやLoopを変更する

更新先:

```text
design/PIPELINE.md
```

保存のatomic処理は`WORKSPACE_AND_RECOVERY.md`へ置く。

---

### PromptやProvider連携を変更する

更新先:

```text
design/LLM_INTEGRATION.md
```

Storyデータの意味は`DATA_MODEL.md`へ置く。

---

### Release試験を変更する

更新先:

```text
testing/ACCEPTANCE.md
```

試験文書だけで新しい仕様を追加しない。

---

### 現在の進捗を変更する

更新先:

```text
product/IMPLEMENTATION_STATUS.md
```

根拠なしに`実装済み`へ変更しない。

---

## 6. 文書の基本原則

```text
一つの概念に一つの正本
仕様と実装状況を分離
Markdownとproduction Schemaを重複実装しない
巨大なfixtureをMarkdownへ埋め込まない
旧設計を参照し続けない
Hash、Manifest、Gateを根拠なく追加しない
```

---

## 7. Schema

厳密なJSON Schemaまたは同等の構造定義は、production code内の一つのasset rootへ置く。

Markdown文書では次を扱う。

```text
意味
関係
不変条件
代表例
```

Markdown文書を、productionとは別の完全Schema実装にしない。

---

## 8. Fixture

実際の試験入力は次へ置く。

```text
tests/fixtures/
```

Markdownへ巨大なJSON例を追加しない。

新しいfixtureには次を明示する。

```text
用途
正常または不正
期待する結果
関連する試験ID
```

---

## 9. Link

文書linkはrepository内の相対pathを使う。

旧文書を削除する前に、repository全体で参照を検索する。

推奨確認対象:

```text
Markdown link
source code内の文書path
test内のfixture path
CI設定
package metadata
```

---

## 10. 旧文書

旧文書は、新しい正本文書へ内容と参照を移した後に削除する。

主な統合先:

| 旧領域 | 新しい統合先 |
|---|---|
| Engine設計・flow | `ARCHITECTURE.md`、`PIPELINE.md` |
| Workspace・runtime・recovery | `WORKSPACE_AND_RECOVERY.md` |
| Ledger・data contract | `DATA_MODEL.md` |
| Context・Prompt・configuration | `LLM_INTEGRATION.md` |
| Acceptance | `testing/ACCEPTANCE.md` |
| Markdown example | `tests/fixtures/` |

詳細な移行状況は[`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md)を参照する。

---

## 11. 文書変更の順序

大きな変更は、原則として次の順で反映する。

```text
1. product/SPECIFICATION.md
2. product/REQUIREMENTS.md
3. architecture/ARCHITECTURE.md
4. 対応するdesign文書
5. testing/ACCEPTANCE.md
6. production code
7. 自動試験
8. product/IMPLEMENTATION_STATUS.md
9. README
```

内部実装だけの変更では、上位文書の更新が不要な場合もある。

---

## 12. Review checklist

文書変更時に確認する。

```text
既存正本と重複していない
別文書の責務を侵食していない
古いpathを追加していない
同じ状態を複数の正本へ書いていない
実装状況と仕様を混ぜていない
具体例を仕様として誤解させない
相対linkが正しい
```

---

## 13. 現在の状況

主要正本文書の完成版は作成済みで、repositoryへの配置と旧文書参照の切替を進めている。

現在の詳細:

[`product/IMPLEMENTATION_STATUS.md`](product/IMPLEMENTATION_STATUS.md)

---

## 14. 最終原則

> Storycraftの文書は、利用者向け仕様、検証可能要件、全体アーキテクチャ、詳細設計、受入試験、実装状況を分離し、一つの概念に一つの正本を持つ。
