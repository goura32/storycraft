# Runtime and recovery

> Runtime/resume/manifestの概要。完全fieldは[run and manifest records](contracts/ledger/runtime_records.md)、保存pathは[workspace layout](workspace_layout.md)、stage別resumeは[pipeline index](pipeline_contracts.md)を正本とする。

## Resume

`runtime/run-state.json`はcurrent stage/target、scene phase、last valid candidate/review/checkpoint、next stage、HEAD、publicationを持つ。各stageはcandidate manifestの`last_structurally_valid=true`なら`next_stage`から再開する。candidate破損時は前stageの採用済み正本から再生成する。audit raw logはresume入力ではない。

## Scene transaction

```text
SCENE_NOT_STARTED
→ CARD_ACCEPTED
→ PROSE_FROZEN
→ DELTA_ACCEPTED
→ COMMIT_PREPARED
→ SCENE_COMMITTED
```

SC-CHK、PROSE-CHK、DELTA-CHKはcheckpointだけを保存する。COMMIT-01からCOMMIT-04はstagingを検証し、generation/artifactをrename後、HEADを最後にatomic replaceする。

## Recovery

HEAD chain外generationまたはchain外commit artifactは`runtime/orphans/<timestamp>/`へ隔離する。HEAD到達generationと採用済みartifactは削除しない。POSIX単一process lockは`.storycraft.lock`で管理し、network filesystemはv1範囲外である。
