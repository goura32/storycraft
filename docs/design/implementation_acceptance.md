# Implementation acceptance

> 次期実装の受入条件の正本。各試験はdeterministic fakeで実行し、実LLMを必須にしない。

## Schema・台帳

- 全example JSONが対応Schemaを通る。
- 保存objectは`additionalProperties: false`で未知fieldを拒否する。
- enum違反、未知ID、未知local_key、禁止operationを拒否する。
- IDが`char|rel|loc|org|item|sys|rule|thread|ending|fact-000001`形式、欠番許容、再利用禁止であることを確認する。
- same commitの再実行が同一local key mappingを返し、before不一致・許可外field・evidence不一致を拒否する。

## Context

- writer contextにauthor truth、他人物private knowledge、future detail、未採用候補が漏れない。
- 同一snapshotは同一context hashを返す。
- overflowで低優先recordを決定的に除外し、必須情報不足は停止する。

## crash / resume

| crash注入点 | 期待resume位置 |
|---|---|
| `CARD_ACCEPTED` | PROSE-01 |
| `PROSE_FROZEN` | DELTA-01 |
| `DELTA_ACCEPTED` | COMMIT-01 |
| `COMMIT_PREPARED` | 同一commit IDのcommit検証 |
| HEAD更新直前 | 同一commit IDのcommit検証 |
| HEAD更新直後 | 次scene、二重commitなし |

## timeout / budget

first event、idle、total timeoutでstream closeとworker終了を検証する。transport retry枯渇、response structure retry枯渇、call/token/time/cost budget枯渇はいずれも機械停止である。

## output / E2E

- volume/series Markdownが巻・章順、非空本文、内部JSON・prompt・author truth・未採用本文なしである。
- 重複本文を検出し、staging失敗時に既存outputが不変である。
- 最小1巻、複数巻、途中停止resumeを実行する。
- completion audit issueが残っても正常JSONがあれば公開し、正常audit JSONが一件もなければ停止する。
