# Implementation acceptance

> 次期実装の受入試験の唯一の正本。すべてdeterministic fakeで実行し、実LLMを必要としない。

## Pipeline and object contracts

- 全50 stage（INPUT-01からOUT-03）に目的、実行条件、input/output field、正本、LLM/code field、秘密境界、検証、review、retry、revision、採用、保存、失敗、次stageが存在する。
- 全保存objectはunknown fieldを拒否し、field-level enum/default/nullabilityを検証する。
- character fixed/state、relationship fixed/nested stateの全fieldを検証する。`b_to_a`全fieldは個別に検証する。
- world kindごとのprefix、`next_culture_id`、`next_history_id`、6桁、欠番、非再利用、LLM ID禁止を検証する。
- general lifecycleはactive/inactive/retiredだけであり、resolvedを拒否する。thread status/progress/disposition matrixを検証する。
- series mapのvolume numberはコードが1..brief.volumesを付与し、LLM outputにscene ID/volume/chapter/scene numbersがないことを検証する。

## Checkpoint, commit, and resume

- SC-CHK/PROSE-CHK/DELTA-CHKはそれぞれruntime checkpointのcard/prose/deltaだけを保存し、artifacts pathを作らない。
- COMMIT-04前にformal readerがcheckpointまたはartifactを正式成果物として読むことを拒否する。
- checkpoint manifest、scene manifest、commit manifestの全field、null pair、hash/path、phase enum、genesis固定値を検証する。
- crash at CARD_ACCEPTED, PROSE_FROZEN, DELTA_ACCEPTED, COMMIT_PREPARED, pre-HEAD, post-HEAD resumes at documented phase and never duplicates a commit.
- HEAD chain外generationとchain外commit artifactはorphanへ移し、adopted artifact/HEAD-reachable generationを消さない。

## Knowledge and Context

- initial_design knowledge requires non-null author truth; prose knowledge requires null author truth.
- prose knowledge proposal rejects author truth.
- knowledge state uses array row uniqueness `fact_id+audience_type+audience_id`; reader has null audience ID and character has known character ID.
- scene planner receives author truth, resolution condition, ending author information, and target-scene necessary future plan.
- writer never receives any prohibited secret, but receives reader_known_facts.
- forbidden disclosures contain only abstract labels, never secret prose.
- identical Context input/config yields same hash/order; deterministic overflow and mandatory overflow stop are tested.
- exact provider/tokenizer count is used when available; fallback is `ceil(code_points * 2.0)` only when unavailable.

## Retry, audit, configuration

- transport retry includes only connection/HTTP/stream/timeout; JSON parse failure is not transport retry.
- review and revision response structure failures consume `max_response_structure_retries`.
- timeout closes stream and worker; each attempt consumes budget.
- every named configuration field and operation-key entry is required; unknown-price model with cost ceiling rejects startup.
- audit payload has all contract fields, is JSON gzip, excludes credentials/headers/environment/secrets, and has retention warning/max tests.

## Samples, output, E2E

- every sample JSON parses, every fixture/baseline reference resolves, and no explanatory storage-only alias is accepted.
- sample complete before/after state, evidence substring/offset/hash, knowledge meaning, ending supports meaning, manifest, and HEAD transition are verified.
- output staging/publication pointer crash behavior, Markdown order/nonempty, and absence of prompt/raw/checkpoint/author truth/unadopted prose are verified.
- run minimum one-volume, multi-volume, interrupted-resume, residual-audit-issue, and no-valid-completion-audit fake cases.
