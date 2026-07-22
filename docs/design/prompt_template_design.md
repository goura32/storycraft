# プロンプトテンプレートと出力契約

> 製品仕様は[製品仕様](../product/SPECIFICATION.md)、順番は[生成フロー](series_engine_flow.md)を正本とする。現行template・Schemaは変更しない。

## 基本方針

工程項目は[pipeline contracts](pipeline_contracts.md)、台帳投影は[ledger contracts](ledger_contracts.md)、workspace保存は[workspace layout](workspace_layout.md)を正本とする。

stage名と製品フェーズは同義ではない。LLMは候補とissueを返し、コードが構造・ID・evidence・採用を決める。修正templateは対象全体、全issue、変更範囲を一回で受け、成果物全体を返す。LLMは永続IDを決めない。

## stage責務

- `initial_concept`〜`initial_series_arcs`は`local_key`を使う内部確定成果物を返す。
- `initial_canon_assembly`はIDなしの`initial_design_bundle`候補を統合する。
- `initial_design_review`はbundle候補全体を監査し、`initial_design_revision`は全issueを反映したbundle全体を返す。
- `series_map`は初期bundleから全巻の不変計画を返す。`volume_design`は採用済みseries map、HEAD current canon、story state、前巻handoffを入力にする。
- `scene_card`は`new_item_policy`を返し、`scene`は本文だけを返す。
`continuity_delta`は型付きupdates、origin別knowledge proposal、knowledge/thread/time、`ending_evidence_proposals`、handoffを出力する。retryはtransportとresponse structureを分離し、JSON/Schema不正は`max_response_structure_retries`だけを消費する。
- `volume_handoff`は全本文を再入力せず事実handoffを返す。

## 完結監査

`completion_audit`はgenerate/revision stageではなくaudit attemptである。同一入力から有限回再監査できるが、前回issueを直すために監査JSONをrevisionしない。本文・Canonを変更せず、正直な意味監査結果を返す。コードが最後の構造正常結果を保存し、機械的完成条件だけで出力可否を決める。

## retry

`max_revision_rounds`は正常レビュー後の修正回数である。transport retryはconnection、HTTP、stream interruption、timeoutに限り、JSON parse・Schema・required field・enumはresponse structure retryとして別に数える。修正候補の構造不正は同一round内のresponse structure retryでありroundを消費しない。
