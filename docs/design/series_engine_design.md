# シリーズエンジン設計方針

> 製品契約は[製品仕様](../product/SPECIFICATION.md)、呼び出し順は[生成フロー](series_engine_flow.md)を正本とする。

## 正本と初期設計

INIT-01〜04は**内部確定成果物**であり、初期設計フェーズ内だけで次の呼び出しへ渡す。INIT-05は永続IDを持たない`initial_design_bundle`候補を統合する。候補はレビュー・修正・構造検証の対象であり、外部フェーズの入力ではない。

候補全体が最終検証を通過した後にだけ、コードが`local_key`から永続IDを一度だけ採番し、bundle内参照を変換する。その後、`initial_design_bundle`を原子的に採用する。採番後に意味修正をせず、構造エラーなら採用せず停止する。後続工程はこのbundleだけを参照する。

## revisionとretry

正常レビューでissueがある場合のみ`max_revision_rounds`を消費する。transport retryはconnection failure、HTTP failure、stream interruption、timeoutだけであり、JSON不正を含めない。JSON parse、Schema、required field missing、enum violationはresponse structure retryであり、review/revision双方が`max_response_structure_retries`を使う。正常候補は常に保持し、枯渇時だけ停止する。

## 場面Outer Transaction

`scene_card_checkpoint`、`frozen_prose_checkpoint`、`continuity_delta_checkpoint`は再開用の未採用状態であり、対応する次stageだけが入力として読む。正式artifact readerはcheckpointを読まず、COMMIT-04採用後のartifactだけを読む。

1. 場面カード、凍結本文、差分候補
2. 型付き更新、新規局所Canon提案、knowledge/thread/clock更新、ending evidence候補
3. コードのID、field、operation、before、本文完全一致evidence、重複、scope/lifecycle検証
4. Canon・現在State・evidence index・handoffの一括適用

失敗時は部分採用しない。

## 局所Canonとevidence index

局所項目は`scope`=`scene|chapter|volume|series`、`record_lifecycle`=`active|inactive|retired`を持つ。threadだけが`thread_status`=`open|in_progress|resolved|retired`を持つ。`volume_disposition`は`resolve|carry_over|retire`であり、carry_overはactive・series scope・次巻handoff追加を意味する。supporting threadの既定はvolume・非必須である。更新は自由patchでなく`set|append|remove|transition`の型付きoperationであり、target type/fieldごとの許可表を必要とする。

`ending_evidence_index`はcriterion IDごとに、scene ID・完全一致引用・`supports|contradicts`を保存する。コードが参照、引用、重複を検証する。完結監査は全本文を再投入せずindexを読む。

## 完結

完結監査は共通revision loop外である。機械的前提検証→意味監査attempt→監査JSON検証を`max_completion_audit_attempts`まで行い、最後の構造正常結果を保存する。監査JSONを修正せず、監査自身が本文・Canonを変更しない。
