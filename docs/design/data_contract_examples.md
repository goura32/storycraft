# Data contract examples index

## 目的

完全保存Schemaへ接続するfixture関係と検証方針への案内です。長大なJSONは分割fixtureへだけ置きます。

## 対象範囲

```text
lighthouse-initial-v1
  → lighthouse-scene-commit-v1
  → lighthouse-pre-completion-v1
  → lighthouse-completion-publication-v1
```

## 正本関係

| Fixture | 詳細文書 |
|---|---|
| brief / initial design / genesis / planning | [initial and planning](examples/initial_and_planning_fixture.md) |
| complete scene commit | [scene commit](examples/scene_commit_fixture.md) |
| pre-completion / final commit / publication | [completion and publication](examples/completion_publication_fixture.md) |
| field schema | [data contracts index](contracts/data/brief_and_initial.md) と [ledger index](ledger_contracts.md) |

## 用語

- **baseline**: 直前fixtureの完全保存state。
- **canonical hash**: UTF-8、NFC、LF、JSON sort keys、compact separator、trailing LFによるSHA-256。
- **before/after**: commit前後の別正本object。参照aliasではない。

## 検証方針

JSON parse、fixture/baseline参照、ID参照、participant差異、before/after、evidence quote/Unicode offset/hash、manifest hash、HEAD chain、public audit sanitizationを検証します。

## 読み順

1. [initial and planning](examples/initial_and_planning_fixture.md)
2. [scene commit](examples/scene_commit_fixture.md)
3. [completion and publication](examples/completion_publication_fixture.md)
