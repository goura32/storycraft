# Configuration contracts

> 設定、timeout、budgetの正本。秘密を除いた実効設定は`runtime/effective-config.json`へ保存する。

## LLMとretry

| field | 型 | 必須 | default | 規則 |
|---|---|---:|---|---|
| `provider` | string | はい | なし | provider名 |
| `base_url` | string | はい | なし | HTTPS又はlocal HTTP URL |
| `model` | string | はい | なし | run manifestへ固定 |
| `thinking` | boolean | はい | false | provider指定 |
| `stream` | boolean | はい | true | timeout監視対象 |
| `temperature` | number | はい | 0.7 | 0.0〜2.0 |
| `top_p` | number | はい | 1.0 | 0.0〜1.0 |
| `seed` | integer/null | はい | null | provider非対応時はnull |
| `structured_output_mode` | enum | はい | `json_schema` | `json_schema`のみ |
| `max_transport_retries` | integer | はい | 2 | 0〜10 |
| `max_response_structure_retries` | integer | はい | 2 | 0〜10 |
| `max_revision_rounds` | integer | はい | 1 | 0〜10 |
| `max_completion_audit_attempts` | integer | はい | 2 | 1〜10 |
| `backoff_initial_seconds` | number | はい | 1 | >0 |
| `backoff_multiplier` | number | はい | 2 | >=1 |
| `backoff_max_seconds` | number | はい | 30 | >0 |

## timeout・budget

| field | 型 | default | 契約 |
|---|---|---:|---|
| `connect_timeout_seconds` | integer | 30 | 接続待機上限 |
| `first_event_timeout_seconds` | integer | 120 | stream初イベント上限 |
| `idle_timeout_seconds` | integer | 120 | 最終イベント後の上限 |
| `total_call_timeout_seconds` | integer | 900 | 1 call全体上限 |
| `max_llm_calls` | integer/null | null | 枯渇で機械停止 |
| `max_total_input_tokens` | integer/null | null | 枯渇で機械停止 |
| `max_total_output_tokens` | integer/null | null | 枯渇で機械停止 |
| `max_elapsed_seconds` | integer/null | null | 枯渇で機械停止 |
| `max_estimated_cost` | number/null | null | 枯渇で機械停止 |

timeoutではstreamをcloseしworkerを終了してcall失敗へ分類し、transport retryへ渡す。watchdogがログだけ出して処理を継続することは禁止する。`null` budgetは無制限。

## 文字数とprofile

`scene_target_chars=3000`、`scene_guide_min_chars=500`、`scene_guide_max_chars=5000`、`chapter_target_chars=12000`、`volume_target_chars=60000`はSoft Targetである。空本文のみhard error。文字数だけでreject/revisionしない。NFC正規化後のUnicode code point数（改行含む、Markdown除去なし）をmetric記録する。

KDP既定publishing profileは`volume_count_min=4`、`volume_count_recommended=5`、`volume_count_max=10`、`first_volume_role=free_entry`、`later_volume_role=paid`、`each_volume_requires_local_resolution=true`、`nonfinal_volume_requires_reader_question=true`、`platform=kdp`、`auto_publish=false`。これはCore Engine固定条件でなくprofile値である。

resumeはprompt/schema bundle version、editorial/publishing profile、model、正本影響config、code state version変更時に拒否する。log level、timeout延長、audit retentionだけは変更可。拒否対象をoverrideした場合はaudit logへ記録する。
