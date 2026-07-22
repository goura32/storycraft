# Data contracts: planning artifacts

All planning artifacts reject unknown fields and are immutable after the named `-ID` adoption stage.

## Series map, volume design, chapter design

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `series_map.volumes` | array of volume target | yes | no | none | code | immutable | length equals brief.volumes | plans/series-map.json |
| `series_map.volumes[].volume_number` | integer | yes | no | none | code | immutable | 1..brief.volumes unique | plans/series-map.json |
| `series_map.volumes[].volume_role` | string | yes | no | none | LLM→code | immutable | nonempty | plans/series-map.json |
| `series_map.volumes[].volume_promise` | string | yes | no | none | LLM→code | immutable | nonempty | plans/series-map.json |
| `series_map.volumes[].protagonist_change_target` | string | yes | no | none | LLM→code | immutable | nonempty | plans/series-map.json |
| `series_map.volumes[].relationship_change_targets` | array<string> | yes | no | [] | LLM→code | immutable | known IDs/local mapping | plans/series-map.json |
| `series_map.volumes[].major_thread_targets` | array<string> | yes | no | [] | LLM→code | immutable | known IDs/local mapping | plans/series-map.json |
| `series_map.volumes[].reader_question` | string | yes | no | none | LLM→code | immutable | nonempty | plans/series-map.json |
| `series_map.volumes[].ending_position` | string | yes | no | none | LLM→code | immutable | nonempty | plans/series-map.json |
| `volume_design.volume_number` | integer | yes | no | none | code | immutable | target volume | plans/volumes/v01.json |
| `volume_design.objective` | string | yes | no | none | LLM→code | immutable | map compatibility | plans/volumes/v01.json |
| `volume_design.chapter_count` | integer | yes | no | none | LLM→code | immutable | >=1 | plans/volumes/v01.json |
| `volume_design.required_thread_ids` | array<string> | yes | no | [] | code | immutable | known threads | plans/volumes/v01.json |
| `chapter_design.volume_number` | integer | yes | no | none | code | immutable | target volume | plans/chapters/v01/c001.json |
| `chapter_design.chapter_number` | integer | yes | no | none | code | immutable | target chapter | plans/chapters/v01/c001.json |
| `chapter_design.objective` | string | yes | no | none | LLM→code | immutable | volume compatible | plans/chapters/v01/c001.json |
| `chapter_design.scene_count` | integer | yes | no | none | LLM→code | immutable | >=1 | plans/chapters/v01/c001.json |
| `chapter_design.required_thread_actions` | array<string> | yes | no | [] | LLM→code | immutable | known thread IDs | plans/chapters/v01/c001.json |
