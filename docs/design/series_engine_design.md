# シリーズエンジン設計方針

> 製品契約は[製品仕様](../product/SPECIFICATION.md)、呼び出し順は[生成フロー](series_engine_flow.md)を正本とする。

## 正本と初期設計

INIT-01〜04は**内部確定成果物**であり、初期設計フェーズ内だけで次の呼び出しへ渡す。INIT-05は永続IDを持たない`initial_design_bundle`候補を統合する。候補はレビュー・修正・構造検証の対象であり、外部フェーズの入力ではない。

候補全体が最終検証を通過した後にだけ、コードが`local_key`から永続IDを一度だけ採番し、bundle内参照を変換する。その後、`initial_design_bundle`を原子的に採用する。採番後に意味修正をせず、構造エラーなら採用せず停止する。後続工程はこのbundleだけを参照する。

## revisionとretry

正常レビューでissueがある場合のみ`max_revision_rounds`を消費する。通信・JSONの`transport retry`は別カウンタである。レビューJSONの構造不正は同一review retry、修正構造不正は同一revision round内の有限再生成とする。正常候補は常に保持し、枯渇時だけ停止する。

## 場面Outer Transaction

`scene_card_checkpoint`、`frozen_prose_checkpoint`、`continuity_delta_checkpoint`は再開用で、後続入力ではない。場面採用は次を一つのトランザクションとして検証・保存する。

1. 場面カード、凍結本文、差分候補
2. 型付き更新、新規局所Canon提案、knowledge/thread/clock更新、ending evidence候補
3. コードのID、field、operation、before、本文完全一致evidence、重複、scope/lifecycle検証
4. Canon・現在State・evidence index・handoffの一括適用

失敗時は部分採用しない。

## 局所Canonとevidence index

局所項目は`scope`=`scene|chapter|volume|series`、`status`=`active|inactive|resolved|retired`を持つ。supporting threadの既定は`volume`・非必須で、巻末にresolved/carry_over/retiredへ移す。更新は自由patchでなく`set|append|remove|transition`の型付きoperationであり、target type/fieldごとの許可表を必要とする。

`ending_evidence_index`はcriterion IDごとに、scene ID・完全一致引用・`supports|contradicts`を保存する。コードが参照、引用、重複を検証する。完結監査は全本文を再投入せずindexを読む。

## 完結

完結監査は共通revision loop外である。機械的前提検証→意味監査attempt→監査JSON検証を`max_completion_audit_attempts`まで行い、最後の構造正常結果を保存する。監査JSONを修正せず、監査自身が本文・Canonを変更しない。
