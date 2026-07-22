# 現行実装の位置付け

> [製品仕様](SPECIFICATION.md)が次期実装の正本。この文書は現行コードとの差分であり、仕様を現行へ後退させない。

## 現行実装で確認できる基盤

`run`/`resume`/`step`、brief/keywords入力、排他lock、原子的state・出力、コードによるID採番、生成・批評・修正・最終批評、既知issueの記録がある。現行は`characters`、`relationships`、`world`、`timeline`、`threads`、`volume_map`、`closure`中心のstate v5である。

## 仕様済み・未実装

- `local_key`を使うINIT-01〜05、レビュー後の一括永続ID採番、参照変換、`initial_design_bundle`の唯一の正本化
- 初期設計・巻・章・場面・本文・差分・handoffの全体レビュー／一括修正と`max_revision_rounds`契約
- `temporal_rules`と`story_clock`分離、後続巻への現在Canon入力
- 場面カードの`new_item_policy`、局所Canonのscope/lifecycle、supporting threadのcarry-over
- 型付きupdate operation、汎用Canon merge、knowledge update、場面Outer Transaction
- `ending_evidence_proposals`、`ending_evidence_index`、完結監査でのindex利用
- `max_completion_audit_attempts`/`completion_audit_attempts_used`、response structure retry、COMP-PRE/COMP-AUDIT/COMP-PUBLISH分離、現行`closure`から独立した完結監査
- `story_state`/`runtime_state`分離、`knowledge_items`、完全pipeline/ledger/context/runtime/configuration/acceptance contract、新workspace構成とgeneration/HEAD原子的commit
- series map統合、完全field contract、thread progress 0..4、nested relationship state、knowledge projection、token-aware context budget、genesis generation、orphan recovery、publication pointer、budget accounting、runtime file schemas、evidence ID、semantic sample validation、scene state machine、resume recovery、ID allocator idempotency、timeout cancellation、audit gzip、output Markdown contract、acceptance tests

現行実装が上記を満たすとは主張しない。旧state migrationや互換shimは対象にしない。
