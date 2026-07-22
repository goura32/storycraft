# Data contracts: planning artifacts

All planning records reject unknown fields and are immutable after the named `-ID` adoption stage. Code assigns `volume_number`, `chapter_number`, and all path coordinates.

## Series map

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `volumes` | array of volume-map record | yes | no | none | LLM, validated by code | immutable | count equals `brief.volumes` | `plans/series-map.json` |
| `volumes[].volume_number` | integer | yes | no | none | code | immutable | unique 1..brief.volumes | `plans/series-map.json` |
| `volumes[].volume_role` | enum `entry|development|escalation|turning_point|climax|resolution` | yes | no | none | LLM, validated by code | immutable | exact enum | `plans/series-map.json` |
| `volumes[].volume_promise` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].protagonist_change_target` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].relationship_change_targets` | array of relationship target record | yes | no | none | LLM, validated by code | immutable | each relationship resolves | `plans/series-map.json` |
| `volumes[].relationship_change_targets[].relationship_id` | relationship ID | yes | no | none | LLM, validated by code | immutable | adopted relationship | `plans/series-map.json` |
| `volumes[].relationship_change_targets[].start_state` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].relationship_change_targets[].target_state` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].relationship_change_targets[].change_function` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].major_thread_targets` | array of thread target record | yes | no | none | LLM, validated by code | immutable | each thread resolves | `plans/series-map.json` |
| `volumes[].major_thread_targets[].thread_id` | thread ID | yes | no | none | LLM, validated by code | immutable | adopted thread | `plans/series-map.json` |
| `volumes[].major_thread_targets[].start_progress` | integer | yes | no | none | LLM, validated by code | immutable | 0..4 | `plans/series-map.json` |
| `volumes[].major_thread_targets[].target_progress` | integer | yes | no | none | LLM, validated by code | immutable | 0..4 and not lower | `plans/series-map.json` |
| `volumes[].major_thread_targets[].required_action` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].reader_question` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/series-map.json` |
| `volumes[].ending_function` | enum `open|advance|turn|climax|resolve` | yes | no | none | LLM, validated by code | immutable | exact enum | `plans/series-map.json` |

## Volume design

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `volume_number` | integer | yes | no | none | code | immutable | adopted series map target | `plans/volumes/v01.json` |
| `title` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/volumes/v01.json` |
| `volume_promise` | string | yes | no | none | LLM, validated by code | immutable | matches map promise | `plans/volumes/v01.json` |
| `starting_state_summary` | string | yes | no | none | LLM, validated by code | immutable | adopted sources only | `plans/volumes/v01.json` |
| `protagonist_change` | string | yes | no | none | LLM, validated by code | immutable | map compatible | `plans/volumes/v01.json` |
| `relationship_changes` | array of relationship target record | yes | no | none | LLM, validated by code | immutable | IDs resolve | `plans/volumes/v01.json` |
| `thread_actions` | array of thread target record | yes | no | none | LLM, validated by code | immutable | IDs resolve | `plans/volumes/v01.json` |
| `major_conflict` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/volumes/v01.json` |
| `reader_question` | string | yes | no | none | LLM, validated by code | immutable | map compatible | `plans/volumes/v01.json` |
| `ending_function` | enum `open|advance|turn|climax|resolve` | yes | no | none | LLM, validated by code | immutable | exact enum | `plans/volumes/v01.json` |
| `target_chapter_count` | integer | yes | no | none | LLM, validated by code | immutable | positive | `plans/volumes/v01.json` |

## Chapter design

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `volume_number` | integer | yes | no | none | code | immutable | target volume | `plans/chapters/v01/c001.json` |
| `chapter_number` | integer | yes | no | none | code | immutable | target chapter | `plans/chapters/v01/c001.json` |
| `title` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/chapters/v01/c001.json` |
| `purpose` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/chapters/v01/c001.json` |
| `start_state` | string | yes | no | none | LLM, validated by code | immutable | adopted state only | `plans/chapters/v01/c001.json` |
| `end_goal` | string | yes | no | none | LLM, validated by code | immutable | NFC nonempty | `plans/chapters/v01/c001.json` |
| `protagonist_or_relationship_change` | string | yes | no | none | LLM, validated by code | immutable | map compatible | `plans/chapters/v01/c001.json` |
| `thread_actions` | array of thread target record | yes | no | none | LLM, validated by code | immutable | IDs resolve | `plans/chapters/v01/c001.json` |
| `scene_count` | integer | yes | no | none | LLM, validated by code | immutable | positive adopted structural contract | `plans/chapters/v01/c001.json` |
| `chapter_end_function` | enum `opening|development|turn|climax|resolution` | yes | no | none | LLM, validated by code | immutable | exact enum | `plans/chapters/v01/c001.json` |
