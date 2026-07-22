# Completion and publication fixture

This document is the complete final-lifecycle fixture for:

```text
fixture_id = lighthouse-completion-publication-v3
baseline_fixture_id = lighthouse-scene-commit-v3
baseline_inventory_sha256 = 48ae77ce40964b14f67c07bffb44ca068b84a4e5b6793fd004a0ef44e930c03e

final Scene = v04-c003-s002
final Scene Generation = 00000050
final Handoff / HEAD Generation = 00000051
current_order = 47
Publication = pub-000001
```

It covers the final Scene, final Volume Handoff, Completion precondition and audit, deterministic Publication build, Validation, Manifest, rename-stable Gate, `output/CURRENT`, and completed Run state.

Owning contracts:

- [`../contracts/data/review_and_audit.md`](../contracts/data/review_and_audit.md)
- [`../contracts/ledger/runtime_records.md`](../contracts/ledger/runtime_records.md)
- [`../contracts/pipeline/commit_and_output.md`](../contracts/pipeline/commit_and_output.md)
- [`../context_contracts.md`](../context_contracts.md)
- [`../workspace_layout.md`](../workspace_layout.md)
- [`../data_contract_examples.md`](../data_contract_examples.md)
- [`scene_commit_fixture.md`](scene_commit_fixture.md)

Every JSON block is complete. Hashes use canonical JSON plus one LF.

---

## 1. Noncyclic Completion correction

The Completion-precondition report does **not** contain the Completion Context path/hash. The construction order is:

```text
Completion precondition
→ Completion Context containing that precondition
→ saved attempt carrying both hashes
```

This fixture is accompanied by corrected complete replacements of `review_and_audit.md` and `context_contracts.md`.

---

# Part I: Final corpus and plans
## 2. Scene corpus index

```text
EXACT VALUE
fixture = 47 adopted Scenes
example_id = EX-POS-COMP-FIX-CORPUS-001
```

```json
[
  {
    "adopted_generation_id": "00000001",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "cc45b7fcc71cf6feebd1c9bcb535102c64427cb675da464861f72ea1b0da6b84",
    "scene_id": "v01-c001-s001",
    "scene_manifest_sha256": "ed2067e1613ba4c9d899536b1ed4f7907382cc54a21759fdf3677ac7f42b838e",
    "scene_number": 1,
    "scene_order": 1,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000002",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "cc45b7fcc71cf6feebd1c9bcb535102c64427cb675da464861f72ea1b0da6b84",
    "scene_id": "v01-c001-s002",
    "scene_manifest_sha256": "94db180fb4a5197fe8ee559fed72b72e47a54ed0371ab9ffe0dc610574de4f70",
    "scene_number": 2,
    "scene_order": 2,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000003",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "cc45b7fcc71cf6feebd1c9bcb535102c64427cb675da464861f72ea1b0da6b84",
    "scene_id": "v01-c001-s003",
    "scene_manifest_sha256": "8fa70d02e0d6b1b59b5ac17870b772665f057cd3637eb1ff657a957b3449db22",
    "scene_number": 3,
    "scene_order": 3,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000004",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "8f9d69c99f179eeeadda1458b9b7592f56f97d1f59c2b35c014c997aca0f9900",
    "scene_id": "v01-c002-s001",
    "scene_manifest_sha256": "f2192ddd558c1eb327ad2f940bdcd28aabf295e174ee7ff6f764c27d1b0c5feb",
    "scene_number": 1,
    "scene_order": 4,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000005",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "8f9d69c99f179eeeadda1458b9b7592f56f97d1f59c2b35c014c997aca0f9900",
    "scene_id": "v01-c002-s002",
    "scene_manifest_sha256": "ba5db96ccc376ebef93b0b62b27d83d9259607100f2b0ca4bde8e66eae262281",
    "scene_number": 2,
    "scene_order": 5,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000006",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "8f9d69c99f179eeeadda1458b9b7592f56f97d1f59c2b35c014c997aca0f9900",
    "scene_id": "v01-c002-s003",
    "scene_manifest_sha256": "53ebac2a336975cb883cd9ee061c2557bb8c58883d3dbf923cf0237eee5af9a1",
    "scene_number": 3,
    "scene_order": 6,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000007",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "532a6dc4a0ab0679acb01cb53b4b8937b59ff0075b40078f51fd69cc1b2cd0b6",
    "scene_id": "v01-c003-s001",
    "scene_manifest_sha256": "3d7ca3f087e0cc213b17788f3bea0376201382f1dc440addc4cf6f04c2c47f6f",
    "scene_number": 1,
    "scene_order": 7,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000008",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "532a6dc4a0ab0679acb01cb53b4b8937b59ff0075b40078f51fd69cc1b2cd0b6",
    "scene_id": "v01-c003-s002",
    "scene_manifest_sha256": "26b7c34de3ec1926e090d5291451db4fea18d40897a9d36974bf07fb65cccb27",
    "scene_number": 2,
    "scene_order": 8,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000009",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "532a6dc4a0ab0679acb01cb53b4b8937b59ff0075b40078f51fd69cc1b2cd0b6",
    "scene_id": "v01-c003-s003",
    "scene_manifest_sha256": "017a1d1a632edcff24cdf5d2b15ce614113dbcab3754e5dfd29bd190fc3d2d10",
    "scene_number": 3,
    "scene_order": 9,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000010",
    "chapter_number": 4,
    "character_count": 70,
    "prose_sha256": "4ae03325048919863828a3c1d65b847045ccfffa393a2b56f68fd1d7b6aaca2b",
    "scene_id": "v01-c004-s001",
    "scene_manifest_sha256": "648a21fd12d6f04d89bf9aea640d22fdf0d0ad65d5fd4a10267aa0f1a8deaa04",
    "scene_number": 1,
    "scene_order": 10,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000011",
    "chapter_number": 4,
    "character_count": 70,
    "prose_sha256": "4ae03325048919863828a3c1d65b847045ccfffa393a2b56f68fd1d7b6aaca2b",
    "scene_id": "v01-c004-s002",
    "scene_manifest_sha256": "4e70b5230a8766e9116abcd7490173588320d8a8cb2f2b543fc8c7e582e35a1b",
    "scene_number": 2,
    "scene_order": 11,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000012",
    "chapter_number": 4,
    "character_count": 70,
    "prose_sha256": "4ae03325048919863828a3c1d65b847045ccfffa393a2b56f68fd1d7b6aaca2b",
    "scene_id": "v01-c004-s003",
    "scene_manifest_sha256": "6bceeda40a15cf81581af297e1c0a96d6f28521d233ea5539215a2fc40746f30",
    "scene_number": 3,
    "scene_order": 12,
    "volume_number": 1
  },
  {
    "adopted_generation_id": "00000014",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "c161d6308cf040679643280eb418d4b9c3cd6fdcb40bb52061e080fa47cd1a15",
    "scene_id": "v02-c001-s001",
    "scene_manifest_sha256": "eabd47c574f33e6efc5607dcaa76b9d135445f967908e182b8cf1e83bb8e28b5",
    "scene_number": 1,
    "scene_order": 13,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000015",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "c161d6308cf040679643280eb418d4b9c3cd6fdcb40bb52061e080fa47cd1a15",
    "scene_id": "v02-c001-s002",
    "scene_manifest_sha256": "8e34e5beba7d2da94cc432d1106341cc096c59403b4faf5537634d64ebb8a5c3",
    "scene_number": 2,
    "scene_order": 14,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000016",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "c161d6308cf040679643280eb418d4b9c3cd6fdcb40bb52061e080fa47cd1a15",
    "scene_id": "v02-c001-s003",
    "scene_manifest_sha256": "aaf079dd95e486f96ffc6c4ddbfcd988a1704b4cb86b70bf6397d5c57cde469e",
    "scene_number": 3,
    "scene_order": 15,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000017",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3a39b0a2a2b6d95bb5993628c5c0b1f2fee900aca97740479752fd44f3b42df1",
    "scene_id": "v02-c002-s001",
    "scene_manifest_sha256": "4db0284ac8cd1daefbfee60cfb9803aa70893625b645f3b1fa38353cb5bc0a4b",
    "scene_number": 1,
    "scene_order": 16,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000018",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3a39b0a2a2b6d95bb5993628c5c0b1f2fee900aca97740479752fd44f3b42df1",
    "scene_id": "v02-c002-s002",
    "scene_manifest_sha256": "1e9e12637f87d1c09aa332a9aa6bfe25896019216b7a5bdaa02eaa3665069b30",
    "scene_number": 2,
    "scene_order": 17,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000019",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3a39b0a2a2b6d95bb5993628c5c0b1f2fee900aca97740479752fd44f3b42df1",
    "scene_id": "v02-c002-s003",
    "scene_manifest_sha256": "5bdde3a2dfa8e64cb32e1f5dbaf5e7680fbea40f0ef067e6cd50f85106e6ffdb",
    "scene_number": 3,
    "scene_order": 18,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000020",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "7b6fc5d522c8d5ae6eb42a4a79eddf5d18dd449f8af6af3b23bbef944bb795af",
    "scene_id": "v02-c003-s001",
    "scene_manifest_sha256": "b005d92f5acb9edf1689f7d7d45f34babc9cb76c2bf44abf836c216928e43382",
    "scene_number": 1,
    "scene_order": 19,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000021",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "7b6fc5d522c8d5ae6eb42a4a79eddf5d18dd449f8af6af3b23bbef944bb795af",
    "scene_id": "v02-c003-s002",
    "scene_manifest_sha256": "81924d92bbe141ed40b9b050fe21c887c8223a89afcff0ee98ba8dbdca2a6b4c",
    "scene_number": 2,
    "scene_order": 20,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000022",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "7b6fc5d522c8d5ae6eb42a4a79eddf5d18dd449f8af6af3b23bbef944bb795af",
    "scene_id": "v02-c003-s003",
    "scene_manifest_sha256": "1ff92639786b8a103db4fe08d989635716c2d4fbfa5b644030c5236ec6758897",
    "scene_number": 3,
    "scene_order": 21,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000023",
    "chapter_number": 4,
    "character_count": 70,
    "prose_sha256": "f36c1e4152b33397017aa83e590fb17c23acfd43e8384f675bb737e6c8db90b8",
    "scene_id": "v02-c004-s001",
    "scene_manifest_sha256": "da15801d7e13b1af1436a2f5decbd87451f326610c0805561fdd53bc0b1f7b2d",
    "scene_number": 1,
    "scene_order": 22,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000024",
    "chapter_number": 4,
    "character_count": 70,
    "prose_sha256": "f36c1e4152b33397017aa83e590fb17c23acfd43e8384f675bb737e6c8db90b8",
    "scene_id": "v02-c004-s002",
    "scene_manifest_sha256": "6d612571faf468f7755ae895a31bc16da398541e67447a3e8a40b539be2a3f7c",
    "scene_number": 2,
    "scene_order": 23,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000025",
    "chapter_number": 4,
    "character_count": 79,
    "prose_sha256": "bfdeefa3b9d4401ded4af2ad1ae1d1a84520d05586dd1a5b65c0a4f30e056021",
    "scene_id": "v02-c004-s003",
    "scene_manifest_sha256": "f674becd29170c0de2e085a34ca7b07a2dfc82568e3987e86d6ab096ea380b80",
    "scene_number": 3,
    "scene_order": 24,
    "volume_number": 2
  },
  {
    "adopted_generation_id": "00000027",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "ad5e0350dc1152a89414c71529d75f6bf0428f158ca09e84111e5f039f9223b0",
    "scene_id": "v03-c001-s001",
    "scene_manifest_sha256": "daa78b784fab9cf6a67718ef6755e7a0e769f2c93377bb312e9e1b6c5c245951",
    "scene_number": 1,
    "scene_order": 25,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000028",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "ad5e0350dc1152a89414c71529d75f6bf0428f158ca09e84111e5f039f9223b0",
    "scene_id": "v03-c001-s002",
    "scene_manifest_sha256": "af5b3de8f6eac7bb9c0efcee8e80575761c8fc2f8c902a4e89545be785c10a84",
    "scene_number": 2,
    "scene_order": 26,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000029",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "ad5e0350dc1152a89414c71529d75f6bf0428f158ca09e84111e5f039f9223b0",
    "scene_id": "v03-c001-s003",
    "scene_manifest_sha256": "f6815201f603f12efb7b62ed620a20c3e631039099e0da2eca8add75201442a4",
    "scene_number": 3,
    "scene_order": 27,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000030",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "ad5e0350dc1152a89414c71529d75f6bf0428f158ca09e84111e5f039f9223b0",
    "scene_id": "v03-c001-s004",
    "scene_manifest_sha256": "b7f2cda69e11ad3ccbaf72f0af737b8847b3323654d4edfe80dd115488c7ac50",
    "scene_number": 4,
    "scene_order": 28,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000031",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3565fea569a0fce69e71d774925298d8306801c7a6550dd08bdfd0f0d057fc84",
    "scene_id": "v03-c002-s001",
    "scene_manifest_sha256": "c26a86ac2fcb4ff34e7c8662cff8099cee45da4bcf359c796e49894f74ce49e6",
    "scene_number": 1,
    "scene_order": 29,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000032",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3565fea569a0fce69e71d774925298d8306801c7a6550dd08bdfd0f0d057fc84",
    "scene_id": "v03-c002-s002",
    "scene_manifest_sha256": "acaa68215e25b26184acc3916321c6b4e8c9d21ad1c361b7120b54c2279f3e44",
    "scene_number": 2,
    "scene_order": 30,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000033",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3565fea569a0fce69e71d774925298d8306801c7a6550dd08bdfd0f0d057fc84",
    "scene_id": "v03-c002-s003",
    "scene_manifest_sha256": "f1b3b287dd6c16d5f3c8c0a7a6de5047320b6a736940e57ad523131273eb5ce0",
    "scene_number": 3,
    "scene_order": 31,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000034",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "3565fea569a0fce69e71d774925298d8306801c7a6550dd08bdfd0f0d057fc84",
    "scene_id": "v03-c002-s004",
    "scene_manifest_sha256": "f4023cc0353ad13a6a2e641f84116a80af78c1c193226a28befae7234c05e152",
    "scene_number": 4,
    "scene_order": 32,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000035",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "c00eb75e66586875ddd304876eda43f935bd02c6eb73f8b6b1766ec91b1b2a2e",
    "scene_id": "v03-c003-s001",
    "scene_manifest_sha256": "d144d52232528b96530907e23e4d1102b0e0ac0d58b02a7502a6113d43ad5eb0",
    "scene_number": 1,
    "scene_order": 33,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000036",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "c00eb75e66586875ddd304876eda43f935bd02c6eb73f8b6b1766ec91b1b2a2e",
    "scene_id": "v03-c003-s002",
    "scene_manifest_sha256": "d20e6ce520f3d605011c683f4247079f757b5828d8cf20ee6d011c8c6ecd81b7",
    "scene_number": 2,
    "scene_order": 34,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000037",
    "chapter_number": 3,
    "character_count": 81,
    "prose_sha256": "813841a282503ddd4f3e2d199f7b12466ceeb7dca7cbcbf8fa7e18e0051e530f",
    "scene_id": "v03-c003-s003",
    "scene_manifest_sha256": "1b2ef076db6f341b6f2cc9451f334d6e3a3b8aba7bf9e6a65f1b25be6d1e64f8",
    "scene_number": 3,
    "scene_order": 35,
    "volume_number": 3
  },
  {
    "adopted_generation_id": "00000039",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "fbaf490088435d5fe31aca72f06b1b9947560bb2bd3856b23f09d3c890c2c922",
    "scene_id": "v04-c001-s001",
    "scene_manifest_sha256": "43db362506ba2646d5b0deff9d4f0ce36dc925d6ebbe90dafa51db0440f32293",
    "scene_number": 1,
    "scene_order": 36,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000040",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "fbaf490088435d5fe31aca72f06b1b9947560bb2bd3856b23f09d3c890c2c922",
    "scene_id": "v04-c001-s002",
    "scene_manifest_sha256": "b0f893e988523272e252b98d9637be464c82b64fa5bbcdb02dfc1262c95271fb",
    "scene_number": 2,
    "scene_order": 37,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000041",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "fbaf490088435d5fe31aca72f06b1b9947560bb2bd3856b23f09d3c890c2c922",
    "scene_id": "v04-c001-s003",
    "scene_manifest_sha256": "45a8367df50d155c161f5e800714016763ddb7185d30657e70d0baa8add43ed0",
    "scene_number": 3,
    "scene_order": 38,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000042",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "fbaf490088435d5fe31aca72f06b1b9947560bb2bd3856b23f09d3c890c2c922",
    "scene_id": "v04-c001-s004",
    "scene_manifest_sha256": "917d8429c2273ef004901fa454f9fd0b04e8c111891b598259cc8dcd3b5a4615",
    "scene_number": 4,
    "scene_order": 39,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000043",
    "chapter_number": 1,
    "character_count": 70,
    "prose_sha256": "fbaf490088435d5fe31aca72f06b1b9947560bb2bd3856b23f09d3c890c2c922",
    "scene_id": "v04-c001-s005",
    "scene_manifest_sha256": "10f816b8368ca39b1987391c7e31a16bd989748c3872fb5bdaf023224ae1596c",
    "scene_number": 5,
    "scene_order": 40,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000044",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "5ad2459c3d7cc08a5e09c53320ab3167324899f742c80d8b88f68b012272c06e",
    "scene_id": "v04-c002-s001",
    "scene_manifest_sha256": "8648e93ad770ea0fd9084ef8d80d42805161c2a2c87686d6fd5d24bbd41c6666",
    "scene_number": 1,
    "scene_order": 41,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000045",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "5ad2459c3d7cc08a5e09c53320ab3167324899f742c80d8b88f68b012272c06e",
    "scene_id": "v04-c002-s002",
    "scene_manifest_sha256": "88877822c5dc006fd5a424a5d8b9dfa78517e924acd0e72414c801ddacec482d",
    "scene_number": 2,
    "scene_order": 42,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000046",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "5ad2459c3d7cc08a5e09c53320ab3167324899f742c80d8b88f68b012272c06e",
    "scene_id": "v04-c002-s003",
    "scene_manifest_sha256": "23a79cd13ef272d6cc404cb4ba8833f3ef85d81defc79dfe9a7d2e95ad6a65a3",
    "scene_number": 3,
    "scene_order": 43,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000047",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "5ad2459c3d7cc08a5e09c53320ab3167324899f742c80d8b88f68b012272c06e",
    "scene_id": "v04-c002-s004",
    "scene_manifest_sha256": "619062084de7cdd27a049f5cafdecb7bd3344fe79274b35f219e30691935bb3f",
    "scene_number": 4,
    "scene_order": 44,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000048",
    "chapter_number": 2,
    "character_count": 70,
    "prose_sha256": "5ad2459c3d7cc08a5e09c53320ab3167324899f742c80d8b88f68b012272c06e",
    "scene_id": "v04-c002-s005",
    "scene_manifest_sha256": "276340190c96175083f8e71238c30b5361483a7841fee587c26c00c84e11cf51",
    "scene_number": 5,
    "scene_order": 45,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000049",
    "chapter_number": 3,
    "character_count": 70,
    "prose_sha256": "4b3def5c63887b97edd05786f0b5d1f7a7e8a062deccc348582564baa6ed78ab",
    "scene_id": "v04-c003-s001",
    "scene_manifest_sha256": "bab9b89879e845ecaf89f6d9000f24404bd6f9bc0aa929091655400a1040977a",
    "scene_number": 1,
    "scene_order": 46,
    "volume_number": 4
  },
  {
    "adopted_generation_id": "00000050",
    "chapter_number": 3,
    "character_count": 332,
    "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
    "scene_id": "v04-c003-s002",
    "scene_manifest_sha256": "bf1e71ee6929d6fd52632e84e8c86bcec1b00cb67c89e7992901c25ce72f0b41",
    "scene_number": 2,
    "scene_order": 47,
    "volume_number": 4
  }
]
```

Canonical SHA-256:

```text
605ea9977f0fc85c1edac9d42e44fbbafba617c04fa09b550643fe2b22f5c717
```

The index proves the 47-Scene order and Generation arithmetic without embedding all prior private transaction records.

## 3. Plan inventory

```text
EXACT VALUE
fixture = all Volume and Chapter plans
example_id = EX-POS-COMP-FIX-PLAN-001
```

```json
[
  {
    "path": "plans/volumes/v01/chapters/c001/chapter-design.json",
    "role": "chapter_design",
    "sha256": "be04ace98724791a914bd1d7ce9edc9fc582d86620a82b8a2e4e771bf698e068"
  },
  {
    "path": "plans/volumes/v01/chapters/c002/chapter-design.json",
    "role": "chapter_design",
    "sha256": "876fd708a20595797bac566a32fb4705d1082885ebcdf42090e01165f69fb89f"
  },
  {
    "path": "plans/volumes/v01/chapters/c003/chapter-design.json",
    "role": "chapter_design",
    "sha256": "3c60f8ede191937059258bbcb9796ece582cf07a4fcc639ae4df1b996566fcea"
  },
  {
    "path": "plans/volumes/v01/chapters/c004/chapter-design.json",
    "role": "chapter_design",
    "sha256": "0c290271779a942a7463121b255c4386a436b12b3c8e63078db0e9e31d12ca75"
  },
  {
    "path": "plans/volumes/v01/volume-design.json",
    "role": "volume_design",
    "sha256": "09131a4c39bc4002d338b9de81341dce7d9905d5f3ec16f9ff6676b4b9698d8c"
  },
  {
    "path": "plans/volumes/v02/chapters/c001/chapter-design.json",
    "role": "chapter_design",
    "sha256": "ac581cd8033a743636d209f2d3fa42e7d10f8683ecef73b253768628b20d209f"
  },
  {
    "path": "plans/volumes/v02/chapters/c002/chapter-design.json",
    "role": "chapter_design",
    "sha256": "c133f39f1c8207d0c8a4d181b503a699d862e1cec81997dfcc5e1570bd8e1f97"
  },
  {
    "path": "plans/volumes/v02/chapters/c003/chapter-design.json",
    "role": "chapter_design",
    "sha256": "9c61abe2bc60b57127d0107bd2e931f72f4af196e37fce0c5b55a33db532c81e"
  },
  {
    "path": "plans/volumes/v02/chapters/c004/chapter-design.json",
    "role": "chapter_design",
    "sha256": "2973a918b1d5b3ca64947c8609f5580bd8ad9fa62e4bb7ccfa763959e213a6dd"
  },
  {
    "path": "plans/volumes/v02/volume-design.json",
    "role": "volume_design",
    "sha256": "023d8e425e32d125f245e3b792895737d3b19b5521b85920ba08d98f05a07f1c"
  },
  {
    "path": "plans/volumes/v03/chapters/c001/chapter-design.json",
    "role": "chapter_design",
    "sha256": "82c732c4e2256742fd3382efaffdfffafd4b0ba5a327507b185a08722d883b26"
  },
  {
    "path": "plans/volumes/v03/chapters/c002/chapter-design.json",
    "role": "chapter_design",
    "sha256": "e6a8cb4c2dc80d35f119284aedd5981d99222c6fe0499c9050822f4f7d92f7f6"
  },
  {
    "path": "plans/volumes/v03/chapters/c003/chapter-design.json",
    "role": "chapter_design",
    "sha256": "7d29f1c12c15095fea5f54acae90dd08a691b33b1a79de64e503cfeba26d12e5"
  },
  {
    "path": "plans/volumes/v03/volume-design.json",
    "role": "volume_design",
    "sha256": "b85836d7f04ce7be84a59ede2fe80516c2bb8f6b39ff8124c6d66fc5ec4beb27"
  },
  {
    "path": "plans/volumes/v04/chapters/c001/chapter-design.json",
    "role": "chapter_design",
    "sha256": "8a79873d5c9c2f3665fe275b655dc99e4e00192e2be4d0d43bf5e97ac4066ae4"
  },
  {
    "path": "plans/volumes/v04/chapters/c002/chapter-design.json",
    "role": "chapter_design",
    "sha256": "629a08f0793931f2d639e9f19bae216d2f6b3de7e2e9d4d4e10aa62d47da27a3"
  },
  {
    "path": "plans/volumes/v04/chapters/c003/chapter-design.json",
    "role": "chapter_design",
    "sha256": "4348b0fedfd19b0d2eabb356288110b0429a78666be8fd78396fc1496e548dbc"
  },
  {
    "path": "plans/volumes/v04/volume-design.json",
    "role": "volume_design",
    "sha256": "9a78283fc5dd4bf067f14315604273598e257051aa04a43c534917cc894cc52a"
  }
]
```

Canonical SHA-256:

```text
baebdfc3484144e5297cbc5d30e822abaec7d7d9551f11b9f6b58ac88be91517
```

## 4. Final Volume design

```text
EXACT ARTIFACT
path = plans/volumes/v04/volume-design.json
example_id = EX-POS-COMP-FIX-PLAN-002
```

```json
{
  "accepted_candidate_sha256": "3da2dc4f10e109bb90d4d61b8e725bdc0fdc790165380e90a6791d4dfde6a1d0",
  "chapter_functions": [
    {
      "chapter_end_function": "decision",
      "chapter_number": 1,
      "function": "町の役割を具体化する。",
      "primary_change_target_id": "char-000001",
      "primary_change_target_type": "character",
      "required_thread_ids": [
        "thread-000001"
      ],
      "target_scene_count": 5
    },
    {
      "chapter_end_function": "preparation",
      "chapter_number": 2,
      "function": "再点灯手順を実行可能にする。",
      "primary_change_target_id": "rel-000001",
      "primary_change_target_type": "relationship",
      "required_thread_ids": [
        "thread-000001"
      ],
      "target_scene_count": 5
    },
    {
      "chapter_end_function": "resolution",
      "chapter_number": 3,
      "function": "停止原因を確定し、共同再点灯を完了する。",
      "primary_change_target_id": "char-000001",
      "primary_change_target_type": "character",
      "required_thread_ids": [
        "thread-000001"
      ],
      "target_scene_count": 2
    }
  ],
  "created_at": "2026-07-22T03:00:00Z",
  "ending_criterion_targets": [
    {
      "criterion_id": "ending-000001",
      "plan_action": "satisfy",
      "prohibited_disclosure": null,
      "purpose": "役割分担と再点灯を証拠化する。",
      "required": true
    }
  ],
  "ending_function": {
    "final_image_or_decision": "岬のレンズが海へ白い光を返す。",
    "local_resolution": "役割分担と再点灯を完了する。",
    "prohibited_outcomes": [
      "責任を澪一人へ戻す"
    ],
    "series_transition": "物語を完結する。"
  },
  "major_conflict": {
    "conflict_statement": "町が責任と作業を実際に分け合えるか。",
    "escalation_rule": "決定を実作業へ落とす。",
    "opposing_force_ids": [],
    "resolution_condition": "安全な再点灯と役割分担が成立する。",
    "stakes": "共同管理が成立しなければ灯台は再び個人へ押し戻される。"
  },
  "preceding_volume_handoff_path": "artifacts/handoffs/v03.json",
  "preceding_volume_handoff_sha256": "539a4a8cf5414534aabc7ff43d520486ad21931bf9bdc7b711b5e63ecd875c44",
  "protagonist_change": {
    "character_id": "char-000001",
    "purpose": "主人公arcを完結させる。",
    "required_turns": [],
    "start_state_summary": "共同解決を公に求めている。",
    "target_state_summary": "町と責任を分け合い、自分の意思で灯を守っている。"
  },
  "reader_question": null,
  "relationship_changes": [
    {
      "purpose": "主要Relationshipを確立する。",
      "relationship_id": "rel-000001",
      "required_change": "最終作業を互いに委ねる。",
      "required_turns": [],
      "start_state_summary": "町への説明を共同で引き受けている。",
      "target_state_summary": "再点灯を対等な共同作業として完了する。"
    }
  ],
  "schema_version": "1.0",
  "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
  "source_generation_id": "00000038",
  "source_generation_manifest_sha256": "76b52a9c0015fa143486a95cd9eb8420ee2969d9e010b7453fae9dd76061ab65",
  "starting_state_summary": "停止原因と管理責任は公になり、町は具体的な役割分担を決めなければならない。",
  "target_chapter_count": 3,
  "thread_actions": [
    {
      "purpose": "停止原因と共同管理を確定する。",
      "required": true,
      "required_action": "resolve",
      "start_progress": 3,
      "start_status": "in_progress",
      "target_progress": 4,
      "target_status": "resolved",
      "thread_id": "thread-000001"
    }
  ],
  "title": "灯を分ける夜",
  "volume_number": 4,
  "volume_promise": "町の役割分担を成立させ、灯台を安全に再点灯する。"
}
```

Canonical SHA-256:

```text
71c1888a6c3ad4a5a5f5a858646a3c7c66c1474312b4d37d806ddb828a2357cb
```

## 5. Final Chapter design

```text
EXACT ARTIFACT
path = plans/volumes/v04/chapters/c003/chapter-design.json
example_id = EX-POS-COMP-FIX-PLAN-003
```

```json
{
  "accepted_candidate_sha256": "2de67187d831bd52829b073c6742bfcd53d557260dbf808d8b62184213578f91",
  "chapter_end_function": "resolution",
  "chapter_number": 3,
  "created_at": "2026-07-22T03:10:00Z",
  "end_goal": {
    "handoff_to_next_chapter": "Volume HandoffとCompletionへ進む。",
    "reader_effect": "共同責任の結末を確認する。",
    "required_decision_or_event": "町が役割を宣言し、澪と凪が再点灯する。",
    "state_summary": "主要Threadはresolved/4となり、町の役割分担と再点灯が成立する。"
  },
  "ending_criterion_targets": [
    {
      "criterion_id": "ending-000001",
      "plan_action": "satisfy",
      "prohibited_disclosure": null,
      "purpose": "共同管理と再点灯を示す。",
      "required": true
    }
  ],
  "prior_chapter_handoff_path": null,
  "prior_chapter_handoff_sha256": null,
  "protagonist_or_relationship_change": {
    "purpose": "主人公arcを完結する。",
    "required_change": "義務を共同の選択へ変える。",
    "start_state_summary": "共同解決を求めている。",
    "target_id": "char-000001",
    "target_state_summary": "共同責任の中で灯を守ると選んでいる。",
    "target_type": "character"
  },
  "purpose": "停止原因を確定し、町の役割分担のもとで再点灯する。",
  "required_world_entity_ids": [
    "loc-000001"
  ],
  "scene_plan": [
    {
      "completion_role": "development",
      "emotional_change_target": "最終判断を町へ委ねる。",
      "ending_criterion_ids": [
        "ending-000001"
      ],
      "pov_character_id": "char-000001",
      "purpose": "修理と役割分担の最終確認を行う。",
      "required_beats": [
        "切替器を確認する",
        "班の配置を確認する"
      ],
      "required_character_ids": [
        "char-000001",
        "char-000002"
      ],
      "required_location_id": "loc-000001",
      "scene_number": 1,
      "thread_action_ids": [
        "thread-000001"
      ]
    },
    {
      "completion_role": "resolution",
      "emotional_change_target": "灯を共同の選択として受け入れる。",
      "ending_criterion_ids": [
        "ending-000001"
      ],
      "pov_character_id": "char-000001",
      "purpose": "停止原因を確定し、共同の再点灯を完了する。",
      "required_beats": [
        "停止原因を確定する",
        "町が役割を宣言する",
        "澪と凪が再点灯する"
      ],
      "required_character_ids": [
        "char-000001",
        "char-000002"
      ],
      "required_location_id": "loc-000001",
      "scene_number": 2,
      "thread_action_ids": [
        "thread-000001"
      ]
    }
  ],
  "schema_version": "1.0",
  "source_generation_id": "00000048",
  "source_generation_manifest_sha256": "f4c506fb77871678baf7966ffb5b8a3ea561a968146dd5bb50507f1d567cfab0",
  "start_state": {
    "active_character_ids": [
      "char-000001",
      "char-000002"
    ],
    "active_relationship_ids": [
      "rel-000001"
    ],
    "active_thread_ids": [
      "thread-000001"
    ],
    "location_ids": [
      "loc-000001"
    ],
    "summary": "最終日の夕方。役割分担案と修理は整い、最後の確認が残る。",
    "time_label": "最終日の夕方"
  },
  "target_scene_count": 2,
  "thread_actions": [
    {
      "purpose": "停止原因と共同管理を確定する。",
      "required": true,
      "required_action": "resolve",
      "start_progress": 3,
      "start_status": "in_progress",
      "target_progress": 4,
      "target_status": "resolved",
      "thread_id": "thread-000001"
    }
  ],
  "title": "岬の白い光",
  "volume_design_sha256": "e422de0dc71dcb4fe2905996f2fccb68b2f3cd0c32824441bdfbdef7c1088ca1",
  "volume_number": 4
}
```

Canonical SHA-256:

```text
e4c49e7eca0dbba898abf83613a01092ca66f813b6327cc3a07679af84e0f559
```

# Part II: Source Generation and final Scene
## 6. Generation-49 Story state

```text
EXACT ARTIFACT
path = canon/generations/00000049/story-state.json
example_id = EX-POS-COMP-FIX-STATE-049
```

```json
{
  "character_states": [
    {
      "character_id": "char-000001",
      "current_goal": "共同の手順で灯台を再点灯する",
      "current_pressure": "役割分担を実作業として成立させる必要がある",
      "emotional_state": "町の決定を受け止め、最後の確認へ集中している",
      "location_id": "loc-000001",
      "physical_condition": "長い作業による疲労はあるが作業可能"
    },
    {
      "character_id": "char-000002",
      "current_goal": "安全な再点灯と継続点検を成立させる",
      "current_pressure": "最後の切替で設備を再損傷させられない",
      "emotional_state": "澪と町を信頼し、最終手順を慎重に確認している",
      "location_id": "loc-000001",
      "physical_condition": "右手首を保護しながら作業可能"
    }
  ],
  "knowledge_states": [
    {
      "audience_id": "char-000001",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": "char-000002",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": null,
      "audience_type": "reader",
      "fact_id": "fact-000001",
      "status": "revealed"
    }
  ],
  "relationship_states": [
    {
      "a_to_b": {
        "current_intention": "最終操作を共同で行う",
        "emotional_stance": "感謝と安心",
        "perception": "判断を任せられる対等な技術者",
        "trust": "high"
      },
      "b_to_a": {
        "current_intention": "安全手順を最後まで支える",
        "emotional_stance": "信頼と静かな誇り",
        "perception": "責任を共有できる灯台守",
        "trust": "high"
      },
      "public_relation": "灯台の再点灯を共同で担う幼なじみ",
      "relationship_id": "rel-000001",
      "shared_state": "町への説明と修理を共同で進め、再点灯の直前にいる。"
    }
  ],
  "story_clock": {
    "current_chapter_number": 3,
    "current_order": 46,
    "current_scene_number": 1,
    "current_volume_number": 4,
    "last_scene_id": "v04-c003-s001",
    "parallel_group_id": null,
    "time_label": "最終日の夕方"
  },
  "thread_states": [
    {
      "progress": 3,
      "thread_id": "thread-000001",
      "thread_status": "in_progress",
      "volume_disposition": "carry_over"
    }
  ]
}
```

Canonical SHA-256:

```text
ab9dfca3985e1648b1697061ef2ceb0e582e011a6ebceec32c88a6a626fac661
```

## 7. Generation-49 Evidence index

```text
EXACT ARTIFACT
path = canon/generations/00000049/evidence-index.json
example_id = EX-POS-COMP-FIX-EVID-049
```

```json
{
  "records": [
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000025",
      "created_at": "2026-07-22T04:00:00Z",
      "end_offset": 59,
      "evidence_id": "ev-000090",
      "evidence_type": "thread_state_update",
      "prose_sha256": "bfdeefa3b9d4401ded4af2ad1ae1d1a84520d05586dd1a5b65c0a4f30e056021",
      "quote": "欠けた台帳は、設備の故障が町の管理記録と結びつくことを示した。",
      "quote_sha256": "b624426b5b0495cad06202e58b1e7f0cc8f0463b65e3664cfed6d49d48502087",
      "relation": "supports",
      "scene_id": "v02-c004-s003",
      "start_offset": 28,
      "target_field": "/progress",
      "target_id": "thread-000001",
      "target_type": "thread_state"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000037",
      "created_at": "2026-07-22T04:00:00Z",
      "end_offset": 59,
      "evidence_id": "ev-000095",
      "evidence_type": "thread_state_update",
      "prose_sha256": "813841a282503ddd4f3e2d199f7b12466ceeb7dca7cbcbf8fa7e18e0051e530f",
      "quote": "澪と凪は、停止原因を町の会議へ持ち込み、共同管理の判断を求めた。",
      "quote_sha256": "adc4301108a2dde335a2107979658c076602bf68cb2de9d5993377af4e1db8c3",
      "relation": "supports",
      "scene_id": "v03-c003-s003",
      "start_offset": 27,
      "target_field": "/progress",
      "target_id": "thread-000001",
      "target_type": "thread_state"
    }
  ]
}
```

Canonical SHA-256:

```text
63bb02004b1a826a07a4ba67d87fcb950810f1211580834a7883c4c7e53fcb8d
```

## 8. Generation-49 Commit manifest

```text
EXACT ARTIFACT
path = canon/generations/00000049/commit-manifest.json
example_id = EX-POS-COMP-FIX-COMMIT-049
```

```json
{
  "after_generation": "00000049",
  "before_generation": "00000048",
  "commit_id": "commit-00000049",
  "commit_type": "scene",
  "committed_at": "2026-07-22T04:10:00Z",
  "continuity_delta_sha256": "84bc0c0a27cd081b72230e79fe266368e93de18c3c0753998a97e07277ad4c26",
  "created_at": "2026-07-22T04:09:00Z",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 46,
  "evidence_ids": [],
  "evidence_index_sha256": "63bb02004b1a826a07a4ba67d87fcb950810f1211580834a7883c4c7e53fcb8d",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "local_key_mappings": [],
  "manifest_version": "1.0",
  "parent_commit_id": "commit-00000048",
  "prose_sha256": "4b3def5c63887b97edd05786f0b5d1f7a7e8a062deccc348582564baa6ed78ab",
  "scene_card_sha256": "7fbaaae41740b540979c797816e3dcaa76e888a1648f512a780b0dd974f881de",
  "scene_id": "v04-c003-s001",
  "scene_manifest_sha256": "ce7a394ef3315046386477493f33f8afbc2ed13e19efcb1268340b5b18017e02",
  "story_state_sha256": "ab9dfca3985e1648b1697061ef2ceb0e582e011a6ebceec32c88a6a626fac661",
  "volume_handoff_path": null,
  "volume_handoff_sha256": null
}
```

Canonical SHA-256:

```text
a6976ba40fdfed5dcfb7ea8e60eb246e1dd01b9703b9d90ca19e25295c49213b
```

## 9. Generation-49 manifest

```text
EXACT ARTIFACT
path = canon/generations/00000049/generation-manifest.json
example_id = EX-POS-COMP-FIX-GEN-049
```

```json
{
  "commit_id": "commit-00000049",
  "commit_manifest_path": "canon/generations/00000049/commit-manifest.json",
  "commit_manifest_sha256": "a6976ba40fdfed5dcfb7ea8e60eb246e1dd01b9703b9d90ca19e25295c49213b",
  "created_at": "2026-07-22T04:10:00Z",
  "current_canon_path": "canon/generations/00000049/current-canon.json",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 46,
  "evidence_index_path": "canon/generations/00000049/evidence-index.json",
  "evidence_index_sha256": "63bb02004b1a826a07a4ba67d87fcb950810f1211580834a7883c4c7e53fcb8d",
  "generation_id": "00000049",
  "knowledge_items_path": "canon/generations/00000049/knowledge-items.json",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "manifest_version": "1.0",
  "parent_generation_id": "00000048",
  "source_scene_id": "v04-c003-s001",
  "source_scene_manifest_path": "artifacts/scenes/v04/c003/s001/scene-manifest.json",
  "source_scene_manifest_sha256": "ce7a394ef3315046386477493f33f8afbc2ed13e19efcb1268340b5b18017e02",
  "source_volume_handoff_path": null,
  "source_volume_handoff_sha256": null,
  "story_state_path": "canon/generations/00000049/story-state.json",
  "story_state_sha256": "ab9dfca3985e1648b1697061ef2ceb0e582e011a6ebceec32c88a6a626fac661"
}
```

Canonical SHA-256:

```text
8a2ab173740626531e04bbf0398a88f8bcf0978605d5078301227cf28ca5b0ec
```

## 10. Final frozen Scene card

```text
EXACT ARTIFACT
path = artifacts/scenes/v04/c003/s002/scene-card.json
example_id = EX-POS-COMP-FIX-SCENE-050
```

```json
{
  "accepted_candidate_sha256": "88096fb1e1ef15958e865420b87947b7b3beaf13cbc6acc047190ef2ec47bd0c",
  "allowed_update_targets": [
    {
      "allowed_operations": [
        "resolve"
      ],
      "start_progress": 3,
      "start_status": "in_progress",
      "target_kind": "thread_state",
      "target_progress": 4,
      "target_status": "resolved",
      "thread_id": "thread-000001"
    },
    {
      "allowed_time_relations": [
        "later"
      ],
      "target_kind": "story_clock",
      "target_parallel_group_id": null,
      "target_time_label": "最終日の夜"
    }
  ],
  "canon_metadata_change_targets": [],
  "chapter_completion_role": "resolution",
  "chapter_design_path": "plans/volumes/v04/chapters/c003/chapter-design.json",
  "chapter_design_sha256": "e4c49e7eca0dbba898abf83613a01092ca66f813b6327cc3a07679af84e0f559",
  "chapter_number": 3,
  "character_knowledge_targets": [],
  "created_at": "2026-07-22T04:20:00Z",
  "emotional_change_target": "澪が灯を共同の選択として受け入れる。",
  "ending_criterion_targets": [
    {
      "criterion_id": "ending-000001",
      "plan_action": "satisfy",
      "prohibited_disclosure": null,
      "purpose": "町の役割分担と再点灯を証拠化する。",
      "required": true
    }
  ],
  "forbidden_disclosures": [
    {
      "constraint_id": "fd-final-0001",
      "label": "主人公だけが全責任を負う結末",
      "reason": "町の三班と凪の共同作業を欠かさない。",
      "release_hint": null,
      "source_id": null,
      "source_type": "brief_avoid"
    }
  ],
  "length_guidance": {
    "counting_rule": "unicode_code_points_excluding_final_lf",
    "guide_max_chars": 2200,
    "guide_min_chars": 500,
    "hard_limit": false,
    "target_chars": 1200
  },
  "location_id": "loc-000001",
  "new_item_policy": {
    "allow_knowledge_items": false,
    "allowed_types": [],
    "max_items": 0,
    "max_scope": null,
    "purpose": "最終Sceneは既存要素だけで完結する。"
  },
  "parallel_group_id": null,
  "participant_ids": [
    "char-000001",
    "char-000002"
  ],
  "pov_character_id": "char-000001",
  "reader_disclosures": [],
  "relationship_change_targets": [],
  "required_beats": [
    "停止原因を確定する",
    "町が三班の役割を宣言する",
    "澪と凪が共同で再点灯する",
    "岬の光が海へ戻る"
  ],
  "required_temporal_rule_ids": [
    "rule-000001"
  ],
  "required_world_entity_ids": [
    "loc-000001"
  ],
  "scene_id": "v04-c003-s002",
  "scene_number": 2,
  "scene_purpose": "停止原因を確定し、町の役割分担のもとで澪と凪が再点灯する。",
  "schema_version": "1.0",
  "source_generation_id": "00000049",
  "source_generation_manifest_sha256": "8a2ab173740626531e04bbf0398a88f8bcf0978605d5078301227cf28ca5b0ec",
  "thread_actions": [
    {
      "operation": "resolve",
      "purpose": "停止原因と共同管理を確定する。",
      "required": true,
      "start_progress": 3,
      "start_status": "in_progress",
      "target_progress": 4,
      "target_status": "resolved",
      "thread_id": "thread-000001"
    }
  ],
  "time_label": "最終日の夜",
  "time_relation": "later",
  "volume_number": 4
}
```

Canonical SHA-256:

```text
39f3fe751c15b7da5148c3a6cde1a9657ebe7e84c2a90a23caf3778536cc1a79
```

## 11. Final adopted prose

```text
EXACT ARTIFACT
path = artifacts/scenes/v04/c003/s002/prose.md
example_id = EX-POS-COMP-FIX-PROSE-050
```

```markdown
町の会議を終えた人々は、灯台の下へ三つの道具箱を運んだ。記録係、点検係、夜間監視係の札が、それぞれの箱に結ばれていた。

故障した旧式切替器と欠落した管理記録が、灯台停止の原因だった。澪は修理済みの接点を確かめ、凪は新しい点検表へ最後の値を書き込んだ。

町は、点検、記録、夜間監視を三つの班で分担すると宣言した。誰か一人の家へ灯の責任を戻さないための役割だった。

澪は凪を見た。凪は工具を置き、再点灯の手順を指で一つずつ示した。二人は声を合わせて確認し、澪と凪は同時に主灯の再点灯レバーを押した。

最終日の夜、岬のレンズは海へ白い光を返した。港から上がった歓声は風にほどけ、澪は灯を守ることが、自分だけの義務ではなく、町と選び続ける仕事になったのだと知った。
```

SHA-256:

```text
77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e
```

Character count excluding final LF:

```text
332
```

## 12. Final committed delta

```text
EXACT ARTIFACT
path = artifacts/scenes/v04/c003/s002/continuity-delta.json
example_id = EX-POS-COMP-FIX-DELTA-050
```

```json
{
  "delta_status": "committed",
  "ending_evidence": [
    {
      "criterion_id": "ending-000001",
      "evidence_ids": [
        "ev-000102",
        "ev-000103"
      ]
    }
  ],
  "existing_item_updates": [],
  "handoff_summary": "町は三班の役割分担を宣言し、停止原因を確定した。澪と凪は共同で再点灯し、岬の光が海へ戻った。",
  "knowledge_item_adoptions": [],
  "knowledge_updates": [],
  "new_item_adoptions": [],
  "scene_id": "v04-c003-s002",
  "schema_version": "1.0",
  "thread_updates": [
    {
      "after_progress": 4,
      "after_status": "resolved",
      "before_progress": 3,
      "before_status": "in_progress",
      "evidence_ids": [
        "ev-000101"
      ],
      "operation": "resolve",
      "thread_id": "thread-000001"
    }
  ],
  "time_update": {
    "after_parallel_group_id": null,
    "after_time_label": "最終日の夜",
    "before_parallel_group_id": null,
    "before_time_label": "最終日の夕方",
    "elapsed_hint": null,
    "evidence_ids": [
      "ev-000104"
    ],
    "time_relation": "later"
  }
}
```

Canonical SHA-256:

```text
3a6e9d22b173976210decc31937401137687838fb6220d298ab65e574971f3d5
```

## 13. Generation-50 Story state

```text
EXACT ARTIFACT
path = canon/generations/00000050/story-state.json
example_id = EX-POS-COMP-FIX-STATE-050
```

```json
{
  "character_states": [
    {
      "character_id": "char-000001",
      "current_goal": "共同の手順で灯台を再点灯する",
      "current_pressure": "役割分担を実作業として成立させる必要がある",
      "emotional_state": "町の決定を受け止め、最後の確認へ集中している",
      "location_id": "loc-000001",
      "physical_condition": "長い作業による疲労はあるが作業可能"
    },
    {
      "character_id": "char-000002",
      "current_goal": "安全な再点灯と継続点検を成立させる",
      "current_pressure": "最後の切替で設備を再損傷させられない",
      "emotional_state": "澪と町を信頼し、最終手順を慎重に確認している",
      "location_id": "loc-000001",
      "physical_condition": "右手首を保護しながら作業可能"
    }
  ],
  "knowledge_states": [
    {
      "audience_id": "char-000001",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": "char-000002",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": null,
      "audience_type": "reader",
      "fact_id": "fact-000001",
      "status": "revealed"
    }
  ],
  "relationship_states": [
    {
      "a_to_b": {
        "current_intention": "最終操作を共同で行う",
        "emotional_stance": "感謝と安心",
        "perception": "判断を任せられる対等な技術者",
        "trust": "high"
      },
      "b_to_a": {
        "current_intention": "安全手順を最後まで支える",
        "emotional_stance": "信頼と静かな誇り",
        "perception": "責任を共有できる灯台守",
        "trust": "high"
      },
      "public_relation": "灯台の再点灯を共同で担う幼なじみ",
      "relationship_id": "rel-000001",
      "shared_state": "町への説明と修理を共同で進め、再点灯の直前にいる。"
    }
  ],
  "story_clock": {
    "current_chapter_number": 3,
    "current_order": 47,
    "current_scene_number": 2,
    "current_volume_number": 4,
    "last_scene_id": "v04-c003-s002",
    "parallel_group_id": null,
    "time_label": "最終日の夜"
  },
  "thread_states": [
    {
      "progress": 4,
      "thread_id": "thread-000001",
      "thread_status": "resolved",
      "volume_disposition": "carry_over"
    }
  ]
}
```

Canonical SHA-256:

```text
3135b1a4ae531fe4c47508eebe08bb985ddced32d4aaf6bd87adf685568a61ed
```

## 14. Generation-50 Evidence index

```text
EXACT ARTIFACT
path = canon/generations/00000050/evidence-index.json
example_id = EX-POS-COMP-FIX-EVID-050
```

```json
{
  "records": [
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000025",
      "created_at": "2026-07-22T04:00:00Z",
      "end_offset": 59,
      "evidence_id": "ev-000090",
      "evidence_type": "thread_state_update",
      "prose_sha256": "bfdeefa3b9d4401ded4af2ad1ae1d1a84520d05586dd1a5b65c0a4f30e056021",
      "quote": "欠けた台帳は、設備の故障が町の管理記録と結びつくことを示した。",
      "quote_sha256": "b624426b5b0495cad06202e58b1e7f0cc8f0463b65e3664cfed6d49d48502087",
      "relation": "supports",
      "scene_id": "v02-c004-s003",
      "start_offset": 28,
      "target_field": "/progress",
      "target_id": "thread-000001",
      "target_type": "thread_state"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000037",
      "created_at": "2026-07-22T04:00:00Z",
      "end_offset": 59,
      "evidence_id": "ev-000095",
      "evidence_type": "thread_state_update",
      "prose_sha256": "813841a282503ddd4f3e2d199f7b12466ceeb7dca7cbcbf8fa7e18e0051e530f",
      "quote": "澪と凪は、停止原因を町の会議へ持ち込み、共同管理の判断を求めた。",
      "quote_sha256": "adc4301108a2dde335a2107979658c076602bf68cb2de9d5993377af4e1db8c3",
      "relation": "supports",
      "scene_id": "v03-c003-s003",
      "start_offset": 27,
      "target_field": "/progress",
      "target_id": "thread-000001",
      "target_type": "thread_state"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000050",
      "created_at": "2026-07-22T04:22:00Z",
      "end_offset": 92,
      "evidence_id": "ev-000101",
      "evidence_type": "thread_state_update",
      "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
      "quote": "故障した旧式切替器と欠落した管理記録が、灯台停止の原因だった。",
      "quote_sha256": "d26356866733fb6f7e7adad4641762f0fb6fe5e8e37fead4eb555b765e0533ea",
      "relation": "supports",
      "scene_id": "v04-c003-s002",
      "start_offset": 61,
      "target_field": "/thread_status",
      "target_id": "thread-000001",
      "target_type": "thread_state"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000050",
      "created_at": "2026-07-22T04:22:00Z",
      "end_offset": 157,
      "evidence_id": "ev-000102",
      "evidence_type": "ending_criterion",
      "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
      "quote": "町は、点検、記録、夜間監視を三つの班で分担すると宣言した。",
      "quote_sha256": "ac0c2514958bf11fd8dc2ab286c5267e609079e4dc7edfd5e7c1df9fd909322a",
      "relation": "supports",
      "scene_id": "v04-c003-s002",
      "start_offset": 128,
      "target_field": null,
      "target_id": "ending-000001",
      "target_type": "ending_criterion"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000050",
      "created_at": "2026-07-22T04:22:00Z",
      "end_offset": 250,
      "evidence_id": "ev-000103",
      "evidence_type": "ending_criterion",
      "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
      "quote": "澪と凪は同時に主灯の再点灯レバーを押した。",
      "quote_sha256": "6fee537ca1e4510c89d37218d88ae7424ad18fec5c7082d8f7503608f4e74ede",
      "relation": "supports",
      "scene_id": "v04-c003-s002",
      "start_offset": 229,
      "target_field": null,
      "target_id": "ending-000001",
      "target_type": "ending_criterion"
    },
    {
      "audience_id": null,
      "audience_type": null,
      "commit_id": "commit-00000050",
      "created_at": "2026-07-22T04:22:00Z",
      "end_offset": 274,
      "evidence_id": "ev-000104",
      "evidence_type": "time_update",
      "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
      "quote": "最終日の夜、岬のレンズは海へ白い光を返した。",
      "quote_sha256": "49909f343e658e33a9f2b5f0b8b5868904fee1b4164910e2c62d2ac83f50e234",
      "relation": "supports",
      "scene_id": "v04-c003-s002",
      "start_offset": 252,
      "target_field": "/time_label",
      "target_id": null,
      "target_type": "story_clock"
    }
  ]
}
```

Canonical SHA-256:

```text
0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601
```

## 15. Final Scene manifest

```text
EXACT ARTIFACT
path = artifacts/scenes/v04/c003/s002/scene-manifest.json
example_id = EX-POS-COMP-FIX-SCENE-MANIFEST-050
```

```json
{
  "adopted_at": "2026-07-22T04:22:00Z",
  "adopted_generation_id": "00000050",
  "chapter_number": 3,
  "character_count": 332,
  "commit_id": "commit-00000050",
  "continuity_delta_path": "artifacts/scenes/v04/c003/s002/continuity-delta.json",
  "continuity_delta_sha256": "3a6e9d22b173976210decc31937401137687838fb6220d298ab65e574971f3d5",
  "evidence_ids": [
    "ev-000101",
    "ev-000102",
    "ev-000103",
    "ev-000104"
  ],
  "input_plan_refs": [
    {
      "path": "plans/volumes/v04/volume-design.json",
      "role": "volume_design",
      "sha256": "e422de0dc71dcb4fe2905996f2fccb68b2f3cd0c32824441bdfbdef7c1088ca1"
    },
    {
      "path": "plans/volumes/v04/chapters/c003/chapter-design.json",
      "role": "chapter_design",
      "sha256": "e4c49e7eca0dbba898abf83613a01092ca66f813b6327cc3a07679af84e0f559"
    }
  ],
  "manifest_version": "1.0",
  "prose_path": "artifacts/scenes/v04/c003/s002/prose.md",
  "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
  "scene_card_path": "artifacts/scenes/v04/c003/s002/scene-card.json",
  "scene_card_sha256": "39f3fe751c15b7da5148c3a6cde1a9657ebe7e84c2a90a23caf3778536cc1a79",
  "scene_id": "v04-c003-s002",
  "scene_number": 2,
  "source_generation_id": "00000049",
  "volume_number": 4
}
```

Canonical SHA-256:

```text
7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174
```

## 16. Scene Commit-50 manifest

```text
EXACT ARTIFACT
path = canon/generations/00000050/commit-manifest.json
example_id = EX-POS-COMP-FIX-COMMIT-050
```

```json
{
  "after_generation": "00000050",
  "before_generation": "00000049",
  "commit_id": "commit-00000050",
  "commit_type": "scene",
  "committed_at": "2026-07-22T04:22:00Z",
  "continuity_delta_sha256": "3a6e9d22b173976210decc31937401137687838fb6220d298ab65e574971f3d5",
  "created_at": "2026-07-22T04:21:00Z",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 47,
  "evidence_ids": [
    "ev-000101",
    "ev-000102",
    "ev-000103",
    "ev-000104"
  ],
  "evidence_index_sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "local_key_mappings": [],
  "manifest_version": "1.0",
  "parent_commit_id": "commit-00000049",
  "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
  "scene_card_sha256": "39f3fe751c15b7da5148c3a6cde1a9657ebe7e84c2a90a23caf3778536cc1a79",
  "scene_id": "v04-c003-s002",
  "scene_manifest_sha256": "7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174",
  "story_state_sha256": "3135b1a4ae531fe4c47508eebe08bb985ddced32d4aaf6bd87adf685568a61ed",
  "volume_handoff_path": null,
  "volume_handoff_sha256": null
}
```

Canonical SHA-256:

```text
41d470d4fcee41b468a5bcb5543c23ff8009751b09e383e64ad9d2415a6f2c51
```

## 17. Generation-50 manifest

```text
EXACT ARTIFACT
path = canon/generations/00000050/generation-manifest.json
example_id = EX-POS-COMP-FIX-GEN-050
```

```json
{
  "commit_id": "commit-00000050",
  "commit_manifest_path": "canon/generations/00000050/commit-manifest.json",
  "commit_manifest_sha256": "41d470d4fcee41b468a5bcb5543c23ff8009751b09e383e64ad9d2415a6f2c51",
  "created_at": "2026-07-22T04:22:00Z",
  "current_canon_path": "canon/generations/00000050/current-canon.json",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 47,
  "evidence_index_path": "canon/generations/00000050/evidence-index.json",
  "evidence_index_sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601",
  "generation_id": "00000050",
  "knowledge_items_path": "canon/generations/00000050/knowledge-items.json",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "manifest_version": "1.0",
  "parent_generation_id": "00000049",
  "source_scene_id": "v04-c003-s002",
  "source_scene_manifest_path": "artifacts/scenes/v04/c003/s002/scene-manifest.json",
  "source_scene_manifest_sha256": "7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174",
  "source_volume_handoff_path": null,
  "source_volume_handoff_sha256": null,
  "story_state_path": "canon/generations/00000050/story-state.json",
  "story_state_sha256": "3135b1a4ae531fe4c47508eebe08bb985ddced32d4aaf6bd87adf685568a61ed"
}
```

Canonical SHA-256:

```text
fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614
```

## 18. Final Evidence offsets

| Evidence ID | target | start | end | quote SHA-256 |
|---|---|---:|---:|---|
| `ev-000101` | `thread_state:thread-000001` | 61 | 92 | `d26356866733fb6f7e7adad4641762f0fb6fe5e8e37fead4eb555b765e0533ea` |
| `ev-000102` | `ending_criterion:ending-000001` | 128 | 157 | `ac0c2514958bf11fd8dc2ab286c5267e609079e4dc7edfd5e7c1df9fd909322a` |
| `ev-000103` | `ending_criterion:ending-000001` | 229 | 250 | `6fee537ca1e4510c89d37218d88ae7424ad18fec5c7082d8f7503608f4e74ede` |
| `ev-000104` | `story_clock:None` | 252 | 274 | `49909f343e658e33a9f2b5f0b8b5868904fee1b4164910e2c62d2ac83f50e234` |

All four code-point slices equal their exact quote and use the final prose hash.

# Part III: Final Volume Handoff
## 19. VH-01 content response

```text
EXACT RESPONSE
operation = VH-01 / v04
example_id = EX-POS-VH-001
```

```json
{
  "character_carryovers": [
    {
      "character_id": "char-000001",
      "importance": "required",
      "knowledge_fact_ids": [
        "fact-000001"
      ],
      "next_volume_relevance": null,
      "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
      "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
    },
    {
      "character_id": "char-000002",
      "importance": "important",
      "knowledge_fact_ids": [
        "fact-000001"
      ],
      "next_volume_relevance": null,
      "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
      "public_state_summary": "凪は安全手順と共同記録を支えている。"
    }
  ],
  "ending_state_summary": "第4巻の局所目標を達成し、灯台停止の主要Threadは進行度4に到達した。",
  "knowledge_carryovers": [
    {
      "fact_id": "fact-000001",
      "importance": "important",
      "next_volume_constraint": null,
      "reader_status": "revealed",
      "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
      "relevant_character_ids": [
        "char-000001",
        "char-000002"
      ]
    }
  ],
  "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
  "next_volume_constraints": [],
  "relationship_carryovers": [
    {
      "importance": "required",
      "next_volume_relevance": null,
      "private_state_summary": "互いの専門性を信頼している。",
      "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
      "relationship_id": "rel-000001"
    }
  ],
  "residual_risks": [],
  "series_transition_summary": null,
  "thread_decisions": [
    {
      "disposition": "resolve",
      "evidence_ids": [
        "ev-000090",
        "ev-000095",
        "ev-000101"
      ],
      "importance": "required",
      "next_volume_constraint": null,
      "summary": "停止原因と共同責任の主要Threadは最終的に解決した。",
      "thread_id": "thread-000001"
    }
  ],
  "volume_number": 4,
  "world_carryovers": [
    {
      "importance": "required",
      "next_volume_constraint": null,
      "relevance_summary": "岬の灯台は主要舞台であり、最終巻で再点灯した。",
      "world_entity_id": "loc-000001"
    }
  ]
}
```

Canonical SHA-256:

```text
358279a1e1b96154ecd55fde09c09062c8e53d85a4e5013ed2f8be5319504030
```

## 20. Normalized final Handoff candidate

```text
EXACT ARTIFACT
path = runtime/candidates/handoffs/v04/v0001/volume-handoff.json
example_id = EX-POS-VH-002
```

```json
{
  "accepted_response_sha256": "358279a1e1b96154ecd55fde09c09062c8e53d85a4e5013ed2f8be5319504030",
  "character_carryovers": [
    {
      "character_id": "char-000001",
      "importance": "required",
      "knowledge_fact_ids": [
        "fact-000001"
      ],
      "next_volume_relevance": null,
      "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
      "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
    },
    {
      "character_id": "char-000002",
      "importance": "important",
      "knowledge_fact_ids": [
        "fact-000001"
      ],
      "next_volume_relevance": null,
      "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
      "public_state_summary": "凪は安全手順と共同記録を支えている。"
    }
  ],
  "created_at": "2026-07-22T04:30:00Z",
  "ending_state_summary": "第4巻の局所目標を達成し、灯台停止の主要Threadは進行度4に到達した。",
  "knowledge_carryovers": [
    {
      "fact_id": "fact-000001",
      "importance": "important",
      "next_volume_constraint": null,
      "reader_status": "revealed",
      "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
      "relevant_character_ids": [
        "char-000001",
        "char-000002"
      ]
    }
  ],
  "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
  "next_volume_constraints": [],
  "relationship_carryovers": [
    {
      "importance": "required",
      "next_volume_relevance": null,
      "private_state_summary": "互いの専門性を信頼している。",
      "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
      "relationship_id": "rel-000001"
    }
  ],
  "residual_risks": [],
  "schema_version": "1.0",
  "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
  "series_transition_summary": null,
  "source_generation_id": "00000050",
  "source_generation_manifest_sha256": "fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614",
  "story_clock": {
    "current_chapter_number": 3,
    "current_order": 47,
    "current_scene_number": 2,
    "current_volume_number": 4,
    "last_scene_id": "v04-c003-s002",
    "parallel_group_id": null,
    "time_label": "最終日の夜"
  },
  "thread_decisions": [
    {
      "disposition": "resolve",
      "evidence_ids": [
        "ev-000090",
        "ev-000095",
        "ev-000101"
      ],
      "importance": "required",
      "next_volume_constraint": null,
      "prior_volume_disposition": "carry_over",
      "progress": 4,
      "record_lifecycle": "active",
      "required": true,
      "scope": "series",
      "summary": "停止原因と共同責任の主要Threadは最終的に解決した。",
      "thread_id": "thread-000001",
      "thread_status": "resolved",
      "thread_type": "major"
    }
  ],
  "volume_design_path": "plans/volumes/v04/volume-design.json",
  "volume_design_sha256": "9a78283fc5dd4bf067f14315604273598e257051aa04a43c534917cc894cc52a",
  "volume_number": 4,
  "world_carryovers": [
    {
      "importance": "required",
      "next_volume_constraint": null,
      "relevance_summary": "岬の灯台は主要舞台であり、最終巻で再点灯した。",
      "world_entity_id": "loc-000001"
    }
  ]
}
```

Canonical SHA-256:

```text
a3c222245b75ccf794dff27a554cd61e9e297010a3a8b9cc20e1df1f2b1cf70e
```

## 21. Saved Handoff Review

```text
EXACT ARTIFACT
path = runtime/candidates/handoffs/v04/v0001/review.json
example_id = EX-POS-COMP-FIX-VH-REVIEW
```

```json
{
  "call_id": "call-000254",
  "candidate_path": "runtime/candidates/handoffs/v04/v0001/volume-handoff.json",
  "candidate_sha256": "a3c222245b75ccf794dff27a554cd61e9e297010a3a8b9cc20e1df1f2b1cf70e",
  "candidate_version": 1,
  "created_at": "2026-07-22T04:31:00Z",
  "input_snapshot_sha256": "4ab00fcf304392d780c5f9da81fc819bc575e9f20c94550175a8638d1830f7a0",
  "issue_counts": {
    "error": 0,
    "total": 0,
    "warning": 0
  },
  "issues": [],
  "operation_id": "VH-02",
  "review_prompt_version": "vh-02-v1",
  "review_round": 1,
  "review_schema_version": "review-v1",
  "review_status": "issues_empty",
  "reviewed_artifact_role": "volume_handoff",
  "schema_version": "1.0",
  "summary": "実際の終端Stateと次巻制約に重大な問題はありません。",
  "target_id": "v04"
}
```

Canonical SHA-256:

```text
58110ed53daaf485bc18b042320d332d54df83fa7d372ff0cc1d87c85186b482
```

## 22. Handoff Candidate manifest

```text
EXACT ARTIFACT
path = runtime/candidates/handoffs/v04/v0001/candidate-manifest.json
example_id = EX-POS-COMP-FIX-VH-CAND
```

```json
{
  "candidate_artifact_format": "json",
  "candidate_path": "runtime/candidates/handoffs/v04/v0001/volume-handoff.json",
  "candidate_sha256": "a3c222245b75ccf794dff27a554cd61e9e297010a3a8b9cc20e1df1f2b1cf70e",
  "candidate_status": "ready_for_adoption",
  "candidate_version": 1,
  "completion_audit_attempt": null,
  "created_at": "2026-07-22T04:30:00Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "input_snapshot_path": "runtime/context-snapshots/vh-01/v04/4ab00fcf304392d780c5f9da81fc819bc575e9f20c94550175a8638d1830f7a0.json",
  "input_snapshot_sha256": "4ab00fcf304392d780c5f9da81fc819bc575e9f20c94550175a8638d1830f7a0",
  "last_call_id": "call-000254",
  "last_structurally_valid": true,
  "manifest_version": "1.0",
  "next_stage": "VH-ID",
  "operation_id": "VH-01",
  "previous_candidate_manifest_path": null,
  "previous_candidate_manifest_sha256": null,
  "processor_type": "llm_generate",
  "prompt_version": "vh-01-v1",
  "residual_issues_path": null,
  "response_schema_version": "volume-handoff-content-v1",
  "response_structure_retries_used": 0,
  "review_path": "runtime/candidates/handoffs/v04/v0001/review.json",
  "review_sha256": "58110ed53daaf485bc18b042320d332d54df83fa7d372ff0cc1d87c85186b482",
  "revision_rounds_used": 0,
  "target_id": "v04",
  "transport_retries_used": 0,
  "updated_at": "2026-07-22T04:31:00Z"
}
```

Canonical SHA-256:

```text
fa743c5c358f472611285923eb9f329645b495ccf5491d3d13c7909f2868861c
```

## 23. Adopted final Handoff

```text
EXACT ARTIFACT
path = artifacts/handoffs/v04.json
example_id = EX-POS-VH-003
```

```json
{
  "accepted_candidate_path": "runtime/candidates/handoffs/v04/v0001/volume-handoff.json",
  "accepted_candidate_sha256": "a3c222245b75ccf794dff27a554cd61e9e297010a3a8b9cc20e1df1f2b1cf70e",
  "accepted_response_sha256": "358279a1e1b96154ecd55fde09c09062c8e53d85a4e5013ed2f8be5319504030",
  "adopted_at": "2026-07-22T04:32:00Z",
  "adopted_generation_id": "00000051",
  "character_carryovers": [
    {
      "character_id": "char-000001",
      "importance": "required",
      "knowledge_fact_ids": [
        "fact-000001"
      ],
      "next_volume_relevance": null,
      "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
      "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
    },
    {
      "character_id": "char-000002",
      "importance": "important",
      "knowledge_fact_ids": [
        "fact-000001"
      ],
      "next_volume_relevance": null,
      "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
      "public_state_summary": "凪は安全手順と共同記録を支えている。"
    }
  ],
  "commit_id": "commit-00000051",
  "created_at": "2026-07-22T04:30:00Z",
  "ending_state_summary": "第4巻の局所目標を達成し、灯台停止の主要Threadは進行度4に到達した。",
  "handoff_version": "1.0",
  "knowledge_carryovers": [
    {
      "fact_id": "fact-000001",
      "importance": "important",
      "next_volume_constraint": null,
      "reader_status": "revealed",
      "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
      "relevant_character_ids": [
        "char-000001",
        "char-000002"
      ]
    }
  ],
  "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
  "next_volume_constraints": [],
  "relationship_carryovers": [
    {
      "importance": "required",
      "next_volume_relevance": null,
      "private_state_summary": "互いの専門性を信頼している。",
      "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
      "relationship_id": "rel-000001"
    }
  ],
  "residual_risks": [],
  "review_path": "runtime/candidates/handoffs/v04/v0001/review.json",
  "review_sha256": "58110ed53daaf485bc18b042320d332d54df83fa7d372ff0cc1d87c85186b482",
  "schema_version": "1.0",
  "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
  "series_transition_summary": null,
  "source_generation_id": "00000050",
  "source_generation_manifest_sha256": "fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614",
  "story_clock": {
    "current_chapter_number": 3,
    "current_order": 47,
    "current_scene_number": 2,
    "current_volume_number": 4,
    "last_scene_id": "v04-c003-s002",
    "parallel_group_id": null,
    "time_label": "最終日の夜"
  },
  "thread_decisions": [
    {
      "disposition": "resolve",
      "evidence_ids": [
        "ev-000090",
        "ev-000095",
        "ev-000101"
      ],
      "importance": "required",
      "next_volume_constraint": null,
      "prior_volume_disposition": "carry_over",
      "progress": 4,
      "record_lifecycle": "active",
      "required": true,
      "scope": "series",
      "summary": "停止原因と共同責任の主要Threadは最終的に解決した。",
      "thread_id": "thread-000001",
      "thread_status": "resolved",
      "thread_type": "major"
    }
  ],
  "volume_design_path": "plans/volumes/v04/volume-design.json",
  "volume_design_sha256": "9a78283fc5dd4bf067f14315604273598e257051aa04a43c534917cc894cc52a",
  "volume_number": 4,
  "world_carryovers": [
    {
      "importance": "required",
      "next_volume_constraint": null,
      "relevance_summary": "岬の灯台は主要舞台であり、最終巻で再点灯した。",
      "world_entity_id": "loc-000001"
    }
  ]
}
```

Canonical SHA-256:

```text
a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b
```

## 24. Handoff validation

```text
EXACT ARTIFACT
path = .staging/handoffs/v04/run-000001/handoff-validation.json
example_id = EX-POS-COMP-FIX-VH-VALID
```

```json
{
  "after_generation": "00000051",
  "all_checks_pass": true,
  "before_generation": "00000050",
  "checks": [
    {
      "artifact_path": "artifacts/handoffs/v04.json",
      "artifact_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b",
      "check_id": "HANDOFF_SCHEMA",
      "message": "Final Handoff root validates.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/story-state.json",
      "artifact_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0",
      "check_id": "ONLY_DISPOSITION_CHANGED",
      "message": "Only thread volume_disposition changed.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/generation-manifest.json",
      "artifact_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
      "check_id": "ROOT_BYTES",
      "message": "Canon, Knowledge, Evidence, and Story clock remain valid.",
      "status": "pass"
    }
  ],
  "commit_id": "commit-00000051",
  "created_at": "2026-07-22T04:32:00Z",
  "schema_version": "1.0",
  "transaction_type": "volume_handoff",
  "volume_number": 4
}
```

Canonical SHA-256:

```text
d1103d74241672f6fcb5f9d090fca7727568c92edc53c18bec6ce6b28e8567fd
```

## 25. Generation-51 Story state

```text
EXACT ARTIFACT
path = canon/generations/00000051/story-state.json
example_id = EX-POS-COMP-FIX-STATE-051
```

```json
{
  "character_states": [
    {
      "character_id": "char-000001",
      "current_goal": "共同の手順で灯台を再点灯する",
      "current_pressure": "役割分担を実作業として成立させる必要がある",
      "emotional_state": "町の決定を受け止め、最後の確認へ集中している",
      "location_id": "loc-000001",
      "physical_condition": "長い作業による疲労はあるが作業可能"
    },
    {
      "character_id": "char-000002",
      "current_goal": "安全な再点灯と継続点検を成立させる",
      "current_pressure": "最後の切替で設備を再損傷させられない",
      "emotional_state": "澪と町を信頼し、最終手順を慎重に確認している",
      "location_id": "loc-000001",
      "physical_condition": "右手首を保護しながら作業可能"
    }
  ],
  "knowledge_states": [
    {
      "audience_id": "char-000001",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": "char-000002",
      "audience_type": "character",
      "fact_id": "fact-000001",
      "status": "knows"
    },
    {
      "audience_id": null,
      "audience_type": "reader",
      "fact_id": "fact-000001",
      "status": "revealed"
    }
  ],
  "relationship_states": [
    {
      "a_to_b": {
        "current_intention": "最終操作を共同で行う",
        "emotional_stance": "感謝と安心",
        "perception": "判断を任せられる対等な技術者",
        "trust": "high"
      },
      "b_to_a": {
        "current_intention": "安全手順を最後まで支える",
        "emotional_stance": "信頼と静かな誇り",
        "perception": "責任を共有できる灯台守",
        "trust": "high"
      },
      "public_relation": "灯台の再点灯を共同で担う幼なじみ",
      "relationship_id": "rel-000001",
      "shared_state": "町への説明と修理を共同で進め、再点灯の直前にいる。"
    }
  ],
  "story_clock": {
    "current_chapter_number": 3,
    "current_order": 47,
    "current_scene_number": 2,
    "current_volume_number": 4,
    "last_scene_id": "v04-c003-s002",
    "parallel_group_id": null,
    "time_label": "最終日の夜"
  },
  "thread_states": [
    {
      "progress": 4,
      "thread_id": "thread-000001",
      "thread_status": "resolved",
      "volume_disposition": "resolve"
    }
  ]
}
```

Canonical SHA-256:

```text
1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0
```

The only logical difference from Generation 50 is `thread_states[].volume_disposition: carry_over → resolve`. Story clock remains byte-identical.

## 26. Handoff Commit-51 manifest

```text
EXACT ARTIFACT
path = canon/generations/00000051/commit-manifest.json
example_id = EX-POS-VH-004
```

```json
{
  "after_generation": "00000051",
  "before_generation": "00000050",
  "commit_id": "commit-00000051",
  "commit_type": "volume_handoff",
  "committed_at": "2026-07-22T04:32:00Z",
  "continuity_delta_sha256": null,
  "created_at": "2026-07-22T04:32:00Z",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 47,
  "evidence_ids": [],
  "evidence_index_sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "local_key_mappings": [],
  "manifest_version": "1.0",
  "parent_commit_id": "commit-00000050",
  "prose_sha256": null,
  "scene_card_sha256": null,
  "scene_id": null,
  "scene_manifest_sha256": null,
  "story_state_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0",
  "volume_handoff_path": "artifacts/handoffs/v04.json",
  "volume_handoff_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b"
}
```

Canonical SHA-256:

```text
00f5028967d25add25c3766dfaa1fe9a7d4836efdfbc726e2227e3b985df7276
```

## 27. Generation-51 manifest

```text
EXACT ARTIFACT
path = canon/generations/00000051/generation-manifest.json
example_id = EX-POS-VH-005
```

```json
{
  "commit_id": "commit-00000051",
  "commit_manifest_path": "canon/generations/00000051/commit-manifest.json",
  "commit_manifest_sha256": "00f5028967d25add25c3766dfaa1fe9a7d4836efdfbc726e2227e3b985df7276",
  "created_at": "2026-07-22T04:32:00Z",
  "current_canon_path": "canon/generations/00000051/current-canon.json",
  "current_canon_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
  "current_order": 47,
  "evidence_index_path": "canon/generations/00000051/evidence-index.json",
  "evidence_index_sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601",
  "generation_id": "00000051",
  "knowledge_items_path": "canon/generations/00000051/knowledge-items.json",
  "knowledge_items_sha256": "3fd771cc7ed4bf3a27fa7d1e7a96278759dac4ad30adcea753b6677b9bd1cc4d",
  "manifest_version": "1.0",
  "parent_generation_id": "00000050",
  "source_scene_id": null,
  "source_scene_manifest_path": null,
  "source_scene_manifest_sha256": null,
  "source_volume_handoff_path": "artifacts/handoffs/v04.json",
  "source_volume_handoff_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b",
  "story_state_path": "canon/generations/00000051/story-state.json",
  "story_state_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0"
}
```

Canonical SHA-256:

```text
86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c
```

## 28. Final HEAD pointer

Exact bytes:

```text
00000051\n
```

SHA-256:

```text
d172d87ba813bf4a0525c167d4a7f7e13e10fb41ef285bfc2072b39e29ca1c8e
```

The final Handoff consumes a Commit/Generation ID but does not increment `current_order` or `successful_scene_commits`.

# Part IV: Completion
## 29. Completion precondition

```text
EXACT ARTIFACT
path = audit/completion/00000051/completion-precondition.json
example_id = EX-POS-COMP-001
```

```json
{
  "all_checks_pass": true,
  "brief_path": "input/brief.json",
  "brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
  "checks": [
    {
      "artifact_path": "artifacts/handoffs/v04.json",
      "artifact_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b",
      "check_id": "ALL_HANDOFFS",
      "message": "All four Volume Handoffs exist; the final Handoff is HEAD-reachable.",
      "status": "pass"
    },
    {
      "artifact_path": "plans/series-map.json",
      "artifact_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
      "check_id": "ALL_PLANS",
      "message": "Series map and every Volume/Chapter plan are present.",
      "status": "pass"
    },
    {
      "artifact_path": "artifacts/scenes/v04/c003/s002/scene-manifest.json",
      "artifact_sha256": "7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174",
      "check_id": "ALL_SCENES",
      "message": "All 47 planned Scenes are adopted in canonical order.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/current-canon.json",
      "artifact_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
      "check_id": "ENDING_CRITERIA",
      "message": "Every required Ending criterion exists.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/evidence-index.json",
      "artifact_sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601",
      "check_id": "EVIDENCE_INDEX",
      "message": "Evidence references, quotes, offsets, and hashes validate.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/generation-manifest.json",
      "artifact_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
      "check_id": "FINAL_HEAD",
      "message": "HEAD is the final Volume-handoff Generation.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/story-state.json",
      "artifact_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0",
      "check_id": "FINAL_POSITION",
      "message": "Final Scene is v04-c003-s002 and current_order is 47.",
      "status": "pass"
    },
    {
      "artifact_path": "canon/generations/00000051/story-state.json",
      "artifact_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0",
      "check_id": "MAJOR_THREADS",
      "message": "Every required Major Thread is resolved/4 with final disposition resolve.",
      "status": "pass"
    },
    {
      "artifact_path": null,
      "artifact_sha256": null,
      "check_id": "NO_ACTIVE_TRANSACTION",
      "message": "No active candidate, checkpoint, or staging transaction remains.",
      "status": "pass"
    },
    {
      "artifact_path": null,
      "artifact_sha256": null,
      "check_id": "OUTPUT_POINTER",
      "message": "No prior output/CURRENT exists.",
      "status": "pass"
    }
  ],
  "created_at": "2026-07-22T04:40:00Z",
  "current_order": 47,
  "final_scene_id": "v04-c003-s002",
  "final_volume_number": 4,
  "schema_version": "1.0",
  "series_map_path": "plans/series-map.json",
  "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c"
}
```

Canonical SHA-256:

```text
14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c
```

## 30. Completion Context snapshot

```text
EXACT ARTIFACT
path = runtime/context-snapshots/comp-audit/completion/5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc.json
example_id = EX-POS-COMP-FIX-CTX-001
```

```json
{
  "builder_id": "completion_builder",
  "builder_version": "context-builders-v1",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "exclusions": [],
  "operation_id": "COMP-AUDIT",
  "payload": {
    "brief": {
      "avoid": [
        "主人公だけが全責任を負う結末",
        "説明だけで謎を解決する場面"
      ],
      "brief_version": "1.0",
      "created_at": "2026-07-22T00:00:00Z",
      "editorial_profile_id": "default-ja",
      "ending": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける",
      "genre": "海洋幻想譚",
      "key_people": [
        {
          "initial_relation_to_protagonist": "疎遠になった幼なじみ",
          "name": "凪",
          "present_position": "港の修理工"
        }
      ],
      "protagonist": {
        "core_trait": "粘り強い",
        "current_pressure": "日没までに停止原因を特定する必要がある",
        "initial_wish": "家業としてではなく自分の意思で灯を守りたい",
        "name": "澪",
        "present_position": "岬の灯台守見習い"
      },
      "publishing_profile_id": "kdp-ja-v1",
      "source_hash": "cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f",
      "source_type": "keywords",
      "target_reader": "成人読者",
      "title": "岬の灯",
      "volumes": 4,
      "want": "停止した灯台の原因を追い、町全体が灯を守る仕組みを作る"
    },
    "completion_rules": [
      {
        "applies_to": [
          "completion_audit"
        ],
        "description": "Every required Ending criterion must be satisfied.",
        "rule_id": "COMP_CRITERIA_REQUIRED",
        "severity": "error",
        "source_contract": "contracts/data/review_and_audit.md#criterion-assessment-candidate"
      },
      {
        "applies_to": [
          "completion_audit"
        ],
        "description": "A material contradiction forces incomplete.",
        "rule_id": "COMP_NO_MATERIAL_CONTRADICTION",
        "severity": "error",
        "source_contract": "contracts/data/review_and_audit.md#completion-contradiction-and-residual-assessment"
      },
      {
        "applies_to": [
          "completion_audit"
        ],
        "description": "Every required Major Thread must be resolved with progress 4.",
        "rule_id": "COMP_THREAD_RESOLVED",
        "severity": "error",
        "source_contract": "contracts/data/review_and_audit.md#thread-assessment-candidate"
      }
    ],
    "final_generation_id": "00000051",
    "final_story_clock": {
      "current_chapter_number": 3,
      "current_order": 47,
      "current_scene_number": 2,
      "current_volume_number": 4,
      "last_scene_id": "v04-c003-s002",
      "parallel_group_id": null,
      "time_label": "最終日の夜"
    },
    "generation_chain": [
      {
        "commit_id": "commit-00000000",
        "current_order": 0,
        "generation_id": "00000000",
        "generation_manifest_sha256": "0ba1ee20a1e8914878cd582a5c7c94fdcf338cb9c687074aaf368b39d31343b2",
        "parent_generation_id": null,
        "scene_manifest_sha256": null,
        "source_scene_id": null
      },
      {
        "commit_id": "commit-00000001",
        "current_order": 1,
        "generation_id": "00000001",
        "generation_manifest_sha256": "2a5d19cf0c0d85d25736f3d1e3fc854fee1d00d589ba7bf04106ebd55e7a1df3",
        "parent_generation_id": "00000000",
        "scene_manifest_sha256": "ed2067e1613ba4c9d899536b1ed4f7907382cc54a21759fdf3677ac7f42b838e",
        "source_scene_id": "v01-c001-s001"
      },
      {
        "commit_id": "commit-00000002",
        "current_order": 2,
        "generation_id": "00000002",
        "generation_manifest_sha256": "7d353dae505fa82f53a4dd23912f0107ecc84d36aceaf596d6e7931492815258",
        "parent_generation_id": "00000001",
        "scene_manifest_sha256": "94db180fb4a5197fe8ee559fed72b72e47a54ed0371ab9ffe0dc610574de4f70",
        "source_scene_id": "v01-c001-s002"
      },
      {
        "commit_id": "commit-00000003",
        "current_order": 3,
        "generation_id": "00000003",
        "generation_manifest_sha256": "f2af47abbe39e2e6e2eaa02fd1382b60bde6d1f39faf3341ea51c17b0df98bd2",
        "parent_generation_id": "00000002",
        "scene_manifest_sha256": "8fa70d02e0d6b1b59b5ac17870b772665f057cd3637eb1ff657a957b3449db22",
        "source_scene_id": "v01-c001-s003"
      },
      {
        "commit_id": "commit-00000004",
        "current_order": 4,
        "generation_id": "00000004",
        "generation_manifest_sha256": "f831eed925e23358fa288c201f331f09696190eb207f155d4b65ac6e9a2faa49",
        "parent_generation_id": "00000003",
        "scene_manifest_sha256": "f2192ddd558c1eb327ad2f940bdcd28aabf295e174ee7ff6f764c27d1b0c5feb",
        "source_scene_id": "v01-c002-s001"
      },
      {
        "commit_id": "commit-00000005",
        "current_order": 5,
        "generation_id": "00000005",
        "generation_manifest_sha256": "2a7afc3195c71770e573b7592fc01623b6de018fcfcc0e2c5cbf763c4f800fb5",
        "parent_generation_id": "00000004",
        "scene_manifest_sha256": "ba5db96ccc376ebef93b0b62b27d83d9259607100f2b0ca4bde8e66eae262281",
        "source_scene_id": "v01-c002-s002"
      },
      {
        "commit_id": "commit-00000006",
        "current_order": 6,
        "generation_id": "00000006",
        "generation_manifest_sha256": "b59d5a1c31e0590cbc8c5517eaac4c88bb0e81ddb735f75718834d64e4141dd7",
        "parent_generation_id": "00000005",
        "scene_manifest_sha256": "53ebac2a336975cb883cd9ee061c2557bb8c58883d3dbf923cf0237eee5af9a1",
        "source_scene_id": "v01-c002-s003"
      },
      {
        "commit_id": "commit-00000007",
        "current_order": 7,
        "generation_id": "00000007",
        "generation_manifest_sha256": "163f68dc82e8f13ea7c184bd03665efd8e5e5fd0c3431462777e29c76e362845",
        "parent_generation_id": "00000006",
        "scene_manifest_sha256": "3d7ca3f087e0cc213b17788f3bea0376201382f1dc440addc4cf6f04c2c47f6f",
        "source_scene_id": "v01-c003-s001"
      },
      {
        "commit_id": "commit-00000008",
        "current_order": 8,
        "generation_id": "00000008",
        "generation_manifest_sha256": "8827c7a3789f79562b54e3afdb3af8483530fbee937944182cad71b5532f6312",
        "parent_generation_id": "00000007",
        "scene_manifest_sha256": "26b7c34de3ec1926e090d5291451db4fea18d40897a9d36974bf07fb65cccb27",
        "source_scene_id": "v01-c003-s002"
      },
      {
        "commit_id": "commit-00000009",
        "current_order": 9,
        "generation_id": "00000009",
        "generation_manifest_sha256": "2bf813af6b9fe850c1f3e9f4a820faaabae5950021002f49cefec36038c49236",
        "parent_generation_id": "00000008",
        "scene_manifest_sha256": "017a1d1a632edcff24cdf5d2b15ce614113dbcab3754e5dfd29bd190fc3d2d10",
        "source_scene_id": "v01-c003-s003"
      },
      {
        "commit_id": "commit-00000010",
        "current_order": 10,
        "generation_id": "00000010",
        "generation_manifest_sha256": "6a17e931646c77cfb86ae1299b53e3eb759261654626bb384362c4f31b4c571b",
        "parent_generation_id": "00000009",
        "scene_manifest_sha256": "648a21fd12d6f04d89bf9aea640d22fdf0d0ad65d5fd4a10267aa0f1a8deaa04",
        "source_scene_id": "v01-c004-s001"
      },
      {
        "commit_id": "commit-00000011",
        "current_order": 11,
        "generation_id": "00000011",
        "generation_manifest_sha256": "470ccad6f5ec62a3c290fb35783ca738daa658614bcb9babd1b28729539dcb03",
        "parent_generation_id": "00000010",
        "scene_manifest_sha256": "4e70b5230a8766e9116abcd7490173588320d8a8cb2f2b543fc8c7e582e35a1b",
        "source_scene_id": "v01-c004-s002"
      },
      {
        "commit_id": "commit-00000012",
        "current_order": 12,
        "generation_id": "00000012",
        "generation_manifest_sha256": "34bafae4150a83cf2a0675dc1410d2ae2b4b48784a8982c40231be930fe3a2d8",
        "parent_generation_id": "00000011",
        "scene_manifest_sha256": "6bceeda40a15cf81581af297e1c0a96d6f28521d233ea5539215a2fc40746f30",
        "source_scene_id": "v01-c004-s003"
      },
      {
        "commit_id": "commit-00000013",
        "current_order": 12,
        "generation_id": "00000013",
        "generation_manifest_sha256": "de7211619ccdfb28050c480be3a8544509fc728a5517d6949c8f219a493aa364",
        "parent_generation_id": "00000012",
        "scene_manifest_sha256": null,
        "source_scene_id": null
      },
      {
        "commit_id": "commit-00000014",
        "current_order": 13,
        "generation_id": "00000014",
        "generation_manifest_sha256": "47d129903d6e22eaa411244f473298e3c9d9e847c81c984bce4bfe8a7ba3cc7a",
        "parent_generation_id": "00000013",
        "scene_manifest_sha256": "eabd47c574f33e6efc5607dcaa76b9d135445f967908e182b8cf1e83bb8e28b5",
        "source_scene_id": "v02-c001-s001"
      },
      {
        "commit_id": "commit-00000015",
        "current_order": 14,
        "generation_id": "00000015",
        "generation_manifest_sha256": "758d64770f25af3b1fbdf9565c5d8e8bea99c167d748f7c61feda04e511fb8eb",
        "parent_generation_id": "00000014",
        "scene_manifest_sha256": "8e34e5beba7d2da94cc432d1106341cc096c59403b4faf5537634d64ebb8a5c3",
        "source_scene_id": "v02-c001-s002"
      },
      {
        "commit_id": "commit-00000016",
        "current_order": 15,
        "generation_id": "00000016",
        "generation_manifest_sha256": "1fe7ebd99d9b8e111235f0d7d9779e0445f7cb2d8be1276b7dc88f12e51884ba",
        "parent_generation_id": "00000015",
        "scene_manifest_sha256": "aaf079dd95e486f96ffc6c4ddbfcd988a1704b4cb86b70bf6397d5c57cde469e",
        "source_scene_id": "v02-c001-s003"
      },
      {
        "commit_id": "commit-00000017",
        "current_order": 16,
        "generation_id": "00000017",
        "generation_manifest_sha256": "5a2807afa41eee1fe0fbe2202b9738319eddf2fbcac3dbe342cf4e07eec5d010",
        "parent_generation_id": "00000016",
        "scene_manifest_sha256": "4db0284ac8cd1daefbfee60cfb9803aa70893625b645f3b1fa38353cb5bc0a4b",
        "source_scene_id": "v02-c002-s001"
      },
      {
        "commit_id": "commit-00000018",
        "current_order": 17,
        "generation_id": "00000018",
        "generation_manifest_sha256": "98c943947531ce1a29b2b4b42d8a8967c0259cef41fb8b795c61821061c9a94a",
        "parent_generation_id": "00000017",
        "scene_manifest_sha256": "1e9e12637f87d1c09aa332a9aa6bfe25896019216b7a5bdaa02eaa3665069b30",
        "source_scene_id": "v02-c002-s002"
      },
      {
        "commit_id": "commit-00000019",
        "current_order": 18,
        "generation_id": "00000019",
        "generation_manifest_sha256": "1a23ea15d92cc389e4d2811551ebae1eec254a6eb59fb94f5971c06f56dfa571",
        "parent_generation_id": "00000018",
        "scene_manifest_sha256": "5bdde3a2dfa8e64cb32e1f5dbaf5e7680fbea40f0ef067e6cd50f85106e6ffdb",
        "source_scene_id": "v02-c002-s003"
      },
      {
        "commit_id": "commit-00000020",
        "current_order": 19,
        "generation_id": "00000020",
        "generation_manifest_sha256": "00c8657d9b2e3ffa8dff95db404b9b02b078a4779eb9a71da49445ab6b5a9693",
        "parent_generation_id": "00000019",
        "scene_manifest_sha256": "b005d92f5acb9edf1689f7d7d45f34babc9cb76c2bf44abf836c216928e43382",
        "source_scene_id": "v02-c003-s001"
      },
      {
        "commit_id": "commit-00000021",
        "current_order": 20,
        "generation_id": "00000021",
        "generation_manifest_sha256": "6397ef18d88c5ad89fc639afaee7abf822eee01fb493350c0a8a172dc8133b8f",
        "parent_generation_id": "00000020",
        "scene_manifest_sha256": "81924d92bbe141ed40b9b050fe21c887c8223a89afcff0ee98ba8dbdca2a6b4c",
        "source_scene_id": "v02-c003-s002"
      },
      {
        "commit_id": "commit-00000022",
        "current_order": 21,
        "generation_id": "00000022",
        "generation_manifest_sha256": "4806c9e4e303ee4b02a2aea9acd217440655b6d36f2819d1c7ad13f7d4811bfc",
        "parent_generation_id": "00000021",
        "scene_manifest_sha256": "1ff92639786b8a103db4fe08d989635716c2d4fbfa5b644030c5236ec6758897",
        "source_scene_id": "v02-c003-s003"
      },
      {
        "commit_id": "commit-00000023",
        "current_order": 22,
        "generation_id": "00000023",
        "generation_manifest_sha256": "9a962b4237f1bdf1112b1c15c71348f23d1646f5a4878b9a74b4041e7651ac1d",
        "parent_generation_id": "00000022",
        "scene_manifest_sha256": "da15801d7e13b1af1436a2f5decbd87451f326610c0805561fdd53bc0b1f7b2d",
        "source_scene_id": "v02-c004-s001"
      },
      {
        "commit_id": "commit-00000024",
        "current_order": 23,
        "generation_id": "00000024",
        "generation_manifest_sha256": "5242096d66267bd1dd75e5cd1799502fcc7475e782a202849ab1aee05bbab7d8",
        "parent_generation_id": "00000023",
        "scene_manifest_sha256": "6d612571faf468f7755ae895a31bc16da398541e67447a3e8a40b539be2a3f7c",
        "source_scene_id": "v02-c004-s002"
      },
      {
        "commit_id": "commit-00000025",
        "current_order": 24,
        "generation_id": "00000025",
        "generation_manifest_sha256": "354c60477c895a74b18431c3fe4a73f9e7aa738de5d33488e752aee587520b01",
        "parent_generation_id": "00000024",
        "scene_manifest_sha256": "f674becd29170c0de2e085a34ca7b07a2dfc82568e3987e86d6ab096ea380b80",
        "source_scene_id": "v02-c004-s003"
      },
      {
        "commit_id": "commit-00000026",
        "current_order": 24,
        "generation_id": "00000026",
        "generation_manifest_sha256": "b80fc6859449665728e9b61a27d7c36846407944f580e7574e43c6d5bf123c94",
        "parent_generation_id": "00000025",
        "scene_manifest_sha256": null,
        "source_scene_id": null
      },
      {
        "commit_id": "commit-00000027",
        "current_order": 25,
        "generation_id": "00000027",
        "generation_manifest_sha256": "79bcbb3b69f50270dcaa9b7a6f17fb6a101abc331a4f41b1ec952c2c4e1ce7c4",
        "parent_generation_id": "00000026",
        "scene_manifest_sha256": "daa78b784fab9cf6a67718ef6755e7a0e769f2c93377bb312e9e1b6c5c245951",
        "source_scene_id": "v03-c001-s001"
      },
      {
        "commit_id": "commit-00000028",
        "current_order": 26,
        "generation_id": "00000028",
        "generation_manifest_sha256": "38dba42956bff87d4fbea1c154e431764d5ed8988e9cd034a12f917a98330cfc",
        "parent_generation_id": "00000027",
        "scene_manifest_sha256": "af5b3de8f6eac7bb9c0efcee8e80575761c8fc2f8c902a4e89545be785c10a84",
        "source_scene_id": "v03-c001-s002"
      },
      {
        "commit_id": "commit-00000029",
        "current_order": 27,
        "generation_id": "00000029",
        "generation_manifest_sha256": "7d9a364f215937caa67c1b2b7b052053992ada09749cfd27904c26600dee001f",
        "parent_generation_id": "00000028",
        "scene_manifest_sha256": "f6815201f603f12efb7b62ed620a20c3e631039099e0da2eca8add75201442a4",
        "source_scene_id": "v03-c001-s003"
      },
      {
        "commit_id": "commit-00000030",
        "current_order": 28,
        "generation_id": "00000030",
        "generation_manifest_sha256": "0e89930cc0eea4b85b6081b9fde9322e034de16309b789e24ba9c2c8da21f05e",
        "parent_generation_id": "00000029",
        "scene_manifest_sha256": "b7f2cda69e11ad3ccbaf72f0af737b8847b3323654d4edfe80dd115488c7ac50",
        "source_scene_id": "v03-c001-s004"
      },
      {
        "commit_id": "commit-00000031",
        "current_order": 29,
        "generation_id": "00000031",
        "generation_manifest_sha256": "2e2c13d1401e98bcdbf64398dcf3fd40dac790cb00f89ed8211e1ac6c2167289",
        "parent_generation_id": "00000030",
        "scene_manifest_sha256": "c26a86ac2fcb4ff34e7c8662cff8099cee45da4bcf359c796e49894f74ce49e6",
        "source_scene_id": "v03-c002-s001"
      },
      {
        "commit_id": "commit-00000032",
        "current_order": 30,
        "generation_id": "00000032",
        "generation_manifest_sha256": "e6b638beb80bf91a87f1839cd96750d988f1cdfafb90b577052a832a7b7c8316",
        "parent_generation_id": "00000031",
        "scene_manifest_sha256": "acaa68215e25b26184acc3916321c6b4e8c9d21ad1c361b7120b54c2279f3e44",
        "source_scene_id": "v03-c002-s002"
      },
      {
        "commit_id": "commit-00000033",
        "current_order": 31,
        "generation_id": "00000033",
        "generation_manifest_sha256": "3a5a996149916982d4ceee705a0137c72a048949d1608e0ab1b2697df8c926e9",
        "parent_generation_id": "00000032",
        "scene_manifest_sha256": "f1b3b287dd6c16d5f3c8c0a7a6de5047320b6a736940e57ad523131273eb5ce0",
        "source_scene_id": "v03-c002-s003"
      },
      {
        "commit_id": "commit-00000034",
        "current_order": 32,
        "generation_id": "00000034",
        "generation_manifest_sha256": "2838acd2bc75abf8dda3cf2ba42245065b5821bbf99a38c8b1f175285af00984",
        "parent_generation_id": "00000033",
        "scene_manifest_sha256": "f4023cc0353ad13a6a2e641f84116a80af78c1c193226a28befae7234c05e152",
        "source_scene_id": "v03-c002-s004"
      },
      {
        "commit_id": "commit-00000035",
        "current_order": 33,
        "generation_id": "00000035",
        "generation_manifest_sha256": "aec824ecd8b8c165c86fb32aac1b20c5e3d36b552f48004a885f1ed91bd58e1a",
        "parent_generation_id": "00000034",
        "scene_manifest_sha256": "d144d52232528b96530907e23e4d1102b0e0ac0d58b02a7502a6113d43ad5eb0",
        "source_scene_id": "v03-c003-s001"
      },
      {
        "commit_id": "commit-00000036",
        "current_order": 34,
        "generation_id": "00000036",
        "generation_manifest_sha256": "6475331268e431aff54dc0839df22d69b59e75c25116fe10d80923e9d8454a85",
        "parent_generation_id": "00000035",
        "scene_manifest_sha256": "d20e6ce520f3d605011c683f4247079f757b5828d8cf20ee6d011c8c6ecd81b7",
        "source_scene_id": "v03-c003-s002"
      },
      {
        "commit_id": "commit-00000037",
        "current_order": 35,
        "generation_id": "00000037",
        "generation_manifest_sha256": "5f806be1155d7dbae6a3be875445af20d16e93425ace66f902f743a973fdfcd2",
        "parent_generation_id": "00000036",
        "scene_manifest_sha256": "1b2ef076db6f341b6f2cc9451f334d6e3a3b8aba7bf9e6a65f1b25be6d1e64f8",
        "source_scene_id": "v03-c003-s003"
      },
      {
        "commit_id": "commit-00000038",
        "current_order": 35,
        "generation_id": "00000038",
        "generation_manifest_sha256": "b7558c63b721dc49f3fa9b59b0e3fe3c7bb12596da6aca92652326990c13de94",
        "parent_generation_id": "00000037",
        "scene_manifest_sha256": null,
        "source_scene_id": null
      },
      {
        "commit_id": "commit-00000039",
        "current_order": 36,
        "generation_id": "00000039",
        "generation_manifest_sha256": "db08d2eeeb45d2364331b03ca63b92b286209bc328ad09273a32c2cc5c195471",
        "parent_generation_id": "00000038",
        "scene_manifest_sha256": "43db362506ba2646d5b0deff9d4f0ce36dc925d6ebbe90dafa51db0440f32293",
        "source_scene_id": "v04-c001-s001"
      },
      {
        "commit_id": "commit-00000040",
        "current_order": 37,
        "generation_id": "00000040",
        "generation_manifest_sha256": "6bb676710ee2e30e801c153e1b81cc5f26209fdef22996b65e729faf0d486e65",
        "parent_generation_id": "00000039",
        "scene_manifest_sha256": "b0f893e988523272e252b98d9637be464c82b64fa5bbcdb02dfc1262c95271fb",
        "source_scene_id": "v04-c001-s002"
      },
      {
        "commit_id": "commit-00000041",
        "current_order": 38,
        "generation_id": "00000041",
        "generation_manifest_sha256": "a9e3820112df3b330ad810f2a607c999d9da685cf7309fc1de86096b35cda1c5",
        "parent_generation_id": "00000040",
        "scene_manifest_sha256": "45a8367df50d155c161f5e800714016763ddb7185d30657e70d0baa8add43ed0",
        "source_scene_id": "v04-c001-s003"
      },
      {
        "commit_id": "commit-00000042",
        "current_order": 39,
        "generation_id": "00000042",
        "generation_manifest_sha256": "6374da7a9ec667b631d53452f2f5ce4ce0b816a739d9f44475dae12434d6a61d",
        "parent_generation_id": "00000041",
        "scene_manifest_sha256": "917d8429c2273ef004901fa454f9fd0b04e8c111891b598259cc8dcd3b5a4615",
        "source_scene_id": "v04-c001-s004"
      },
      {
        "commit_id": "commit-00000043",
        "current_order": 40,
        "generation_id": "00000043",
        "generation_manifest_sha256": "927369d0aca9e0a1b92486d1236d8fefd6182ba9d077084182a4c1f3b255e8c7",
        "parent_generation_id": "00000042",
        "scene_manifest_sha256": "10f816b8368ca39b1987391c7e31a16bd989748c3872fb5bdaf023224ae1596c",
        "source_scene_id": "v04-c001-s005"
      },
      {
        "commit_id": "commit-00000044",
        "current_order": 41,
        "generation_id": "00000044",
        "generation_manifest_sha256": "89f1e5a47c2257e9859ff6c9ec7529c99cf73ca4177a95cbd01a0bc2208c5e2e",
        "parent_generation_id": "00000043",
        "scene_manifest_sha256": "8648e93ad770ea0fd9084ef8d80d42805161c2a2c87686d6fd5d24bbd41c6666",
        "source_scene_id": "v04-c002-s001"
      },
      {
        "commit_id": "commit-00000045",
        "current_order": 42,
        "generation_id": "00000045",
        "generation_manifest_sha256": "ee32ee4eceb874e0d51eb7c071979f0dcd99e6c1639f21383db84f1fc0ed004e",
        "parent_generation_id": "00000044",
        "scene_manifest_sha256": "88877822c5dc006fd5a424a5d8b9dfa78517e924acd0e72414c801ddacec482d",
        "source_scene_id": "v04-c002-s002"
      },
      {
        "commit_id": "commit-00000046",
        "current_order": 43,
        "generation_id": "00000046",
        "generation_manifest_sha256": "6c1047391676bfff295066ae6446d6bed5fa6753d0b6853f2e0e5fe9fd5c4eca",
        "parent_generation_id": "00000045",
        "scene_manifest_sha256": "23a79cd13ef272d6cc404cb4ba8833f3ef85d81defc79dfe9a7d2e95ad6a65a3",
        "source_scene_id": "v04-c002-s003"
      },
      {
        "commit_id": "commit-00000047",
        "current_order": 44,
        "generation_id": "00000047",
        "generation_manifest_sha256": "3e6eb855f4957859822ff416cf29bac601a612d55d8cf1c7ae2d8cecf2f79303",
        "parent_generation_id": "00000046",
        "scene_manifest_sha256": "619062084de7cdd27a049f5cafdecb7bd3344fe79274b35f219e30691935bb3f",
        "source_scene_id": "v04-c002-s004"
      },
      {
        "commit_id": "commit-00000048",
        "current_order": 45,
        "generation_id": "00000048",
        "generation_manifest_sha256": "0f34c21a09a29744247939b54b15499574232a7ff8171e6ae561f1ec906c6caf",
        "parent_generation_id": "00000047",
        "scene_manifest_sha256": "276340190c96175083f8e71238c30b5361483a7841fee587c26c00c84e11cf51",
        "source_scene_id": "v04-c002-s005"
      },
      {
        "commit_id": "commit-00000049",
        "current_order": 46,
        "generation_id": "00000049",
        "generation_manifest_sha256": "8a2ab173740626531e04bbf0398a88f8bcf0978605d5078301227cf28ca5b0ec",
        "parent_generation_id": "00000048",
        "scene_manifest_sha256": "ce7a394ef3315046386477493f33f8afbc2ed13e19efcb1268340b5b18017e02",
        "source_scene_id": "v04-c003-s001"
      },
      {
        "commit_id": "commit-00000050",
        "current_order": 47,
        "generation_id": "00000050",
        "generation_manifest_sha256": "fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614",
        "parent_generation_id": "00000049",
        "scene_manifest_sha256": "7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174",
        "source_scene_id": "v04-c003-s002"
      },
      {
        "commit_id": "commit-00000051",
        "current_order": 47,
        "generation_id": "00000051",
        "generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
        "parent_generation_id": "00000050",
        "scene_manifest_sha256": null,
        "source_scene_id": null
      }
    ],
    "initial_design": {
      "accepted_bundle_sha256": "d171b0e5109fc9a46abac7b1ac3da84f2f0a97ce6c0cc458edcc55b0777bb034",
      "brief_path": "input/brief.json",
      "brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
      "character_ids": [
        "char-000001",
        "char-000002"
      ],
      "concept": {
        "central_conflict": "灯台を家の責任として背負おうとする澪と、設備と記録を共同管理すべきだという現実の間で、日没までに停止原因を追う必要がある。",
        "core_concept": "停止した岬の灯台を調べる見習い灯台守の澪が、疎遠な幼なじみの凪と協力し、隠されてきた予備鍵と町の責任の関係を明らかにする。",
        "ending_direction": "町が灯台を共同で守る意思を表明し、澪と凪が再点灯を見届けることで、個人の義務を共同の選択へ変える。",
        "genre_promise": "潮風と灯火の感覚的な描写を軸に、手掛かりを段階的に積み上げる海洋幻想ミステリを提供する。",
        "reader_experience": "各巻で一つの実務的な問題が解ける達成感と、町全体の選択へ近づく連続的な謎を両立させる。",
        "themes": [
          "責任の共有",
          "継承と選択",
          "信頼の再構築"
        ],
        "tone_constraints": [
          "説明だけで真相を処理しない",
          "危機の中にも静かな海辺の余韻を残す",
          "主人公一人へ責任を集中させない"
        ]
      },
      "created_at": "2026-07-22T00:05:01Z",
      "ending_criterion_ids": [
        "ending-000001"
      ],
      "genesis_commit_id": "commit-00000000",
      "knowledge_item_ids": [
        "fact-000001"
      ],
      "major_thread_ids": [
        "thread-000001"
      ],
      "protagonist_arc": {
        "change_function": "孤立した義務感を、他者と選び直す責任へ変える。",
        "end_state": "町と責任を分け合いながら、自分の意思で灯台を守る。",
        "protagonist_id": "char-000001",
        "start_state": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
        "turning_points": [
          {
            "description": "凪と修理庫の手掛かりを共有し、単独調査では進めないと認める。",
            "purpose": "協力を選ぶ最初の変化",
            "sequence": 1
          },
          {
            "description": "灯台停止が個人の失敗ではなく、町の管理の空白と結びつくと知る。",
            "purpose": "責任の範囲を広げる",
            "sequence": 2
          },
          {
            "description": "原因を公にし、町へ共同の判断を求める。",
            "purpose": "共同責任を要求する",
            "sequence": 3
          },
          {
            "description": "町と役割を分け合ったうえで、自分の意思で灯を守る。",
            "purpose": "継承を選択へ変える",
            "sequence": 4
          }
        ]
      },
      "relationship_arcs": [
        {
          "change_function": "疎遠な幼なじみを、責任を分け合う主要な協力者へ戻す。",
          "end_state": "互いの専門性と選択を信頼し、灯台を共同で支える。",
          "relationship_id": "rel-000001",
          "start_state": "互いの能力は認めるが、過去の対立を避けて必要最低限しか話さない。",
          "turning_points": [
            {
              "description": "修理庫の調査で互いの判断根拠を共有する。",
              "purpose": "実務上の信頼を回復する",
              "sequence": 1
            },
            {
              "description": "両家の対立と隠された記録を互いに説明する。",
              "purpose": "過去の誤解を解く",
              "sequence": 2
            },
            {
              "description": "町への説明を二人で引き受ける。",
              "purpose": "協力関係を公にする",
              "sequence": 3
            },
            {
              "description": "再点灯を対等な共同作業として完了する。",
              "purpose": "主要な信頼関係を確立する",
              "sequence": 4
            }
          ]
        }
      ],
      "relationship_ids": [
        "rel-000001"
      ],
      "schema_version": "1.0",
      "temporal_rule_ids": [
        "rule-000001"
      ],
      "world_entity_ids": [
        "item-000001",
        "loc-000001"
      ]
    },
    "optional_criteria": [],
    "precondition": {
      "all_checks_pass": true,
      "brief_path": "input/brief.json",
      "brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
      "checks": [
        {
          "artifact_path": "artifacts/handoffs/v04.json",
          "artifact_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b",
          "check_id": "ALL_HANDOFFS",
          "message": "All four Volume Handoffs exist; the final Handoff is HEAD-reachable.",
          "status": "pass"
        },
        {
          "artifact_path": "plans/series-map.json",
          "artifact_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
          "check_id": "ALL_PLANS",
          "message": "Series map and every Volume/Chapter plan are present.",
          "status": "pass"
        },
        {
          "artifact_path": "artifacts/scenes/v04/c003/s002/scene-manifest.json",
          "artifact_sha256": "7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174",
          "check_id": "ALL_SCENES",
          "message": "All 47 planned Scenes are adopted in canonical order.",
          "status": "pass"
        },
        {
          "artifact_path": "canon/generations/00000051/current-canon.json",
          "artifact_sha256": "080c1aeb07a5b39c22dd7a763b13797cf910e2034aca4c1c09464ac49bdcefff",
          "check_id": "ENDING_CRITERIA",
          "message": "Every required Ending criterion exists.",
          "status": "pass"
        },
        {
          "artifact_path": "canon/generations/00000051/evidence-index.json",
          "artifact_sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601",
          "check_id": "EVIDENCE_INDEX",
          "message": "Evidence references, quotes, offsets, and hashes validate.",
          "status": "pass"
        },
        {
          "artifact_path": "canon/generations/00000051/generation-manifest.json",
          "artifact_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
          "check_id": "FINAL_HEAD",
          "message": "HEAD is the final Volume-handoff Generation.",
          "status": "pass"
        },
        {
          "artifact_path": "canon/generations/00000051/story-state.json",
          "artifact_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0",
          "check_id": "FINAL_POSITION",
          "message": "Final Scene is v04-c003-s002 and current_order is 47.",
          "status": "pass"
        },
        {
          "artifact_path": "canon/generations/00000051/story-state.json",
          "artifact_sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0",
          "check_id": "MAJOR_THREADS",
          "message": "Every required Major Thread is resolved/4 with final disposition resolve.",
          "status": "pass"
        },
        {
          "artifact_path": null,
          "artifact_sha256": null,
          "check_id": "NO_ACTIVE_TRANSACTION",
          "message": "No active candidate, checkpoint, or staging transaction remains.",
          "status": "pass"
        },
        {
          "artifact_path": null,
          "artifact_sha256": null,
          "check_id": "OUTPUT_POINTER",
          "message": "No prior output/CURRENT exists.",
          "status": "pass"
        }
      ],
      "created_at": "2026-07-22T04:40:00Z",
      "current_order": 47,
      "final_scene_id": "v04-c003-s002",
      "final_volume_number": 4,
      "schema_version": "1.0",
      "series_map_path": "plans/series-map.json",
      "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
      "source_generation_id": "00000051",
      "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c"
    },
    "required_criteria": [
      {
        "contradicting_evidence": [],
        "record": {
          "created_scene_id": null,
          "description": "町が灯台を共同で守る意思と具体的な役割分担を示す。",
          "id": "ending-000001",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "ending_criterion",
          "required": true,
          "scope": "series",
          "source_ending_text": "町が灯を守る意思を持ち、澪と凪が再点灯を見届ける"
        },
        "supporting_evidence": [
          {
            "audience_id": null,
            "audience_type": null,
            "commit_id": "commit-00000050",
            "created_at": "2026-07-22T04:22:00Z",
            "end_offset": 157,
            "evidence_id": "ev-000102",
            "evidence_type": "ending_criterion",
            "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
            "quote": "町は、点検、記録、夜間監視を三つの班で分担すると宣言した。",
            "quote_sha256": "ac0c2514958bf11fd8dc2ab286c5267e609079e4dc7edfd5e7c1df9fd909322a",
            "relation": "supports",
            "scene_id": "v04-c003-s002",
            "start_offset": 128,
            "target_field": null,
            "target_id": "ending-000001",
            "target_type": "ending_criterion"
          },
          {
            "audience_id": null,
            "audience_type": null,
            "commit_id": "commit-00000050",
            "created_at": "2026-07-22T04:22:00Z",
            "end_offset": 250,
            "evidence_id": "ev-000103",
            "evidence_type": "ending_criterion",
            "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
            "quote": "澪と凪は同時に主灯の再点灯レバーを押した。",
            "quote_sha256": "6fee537ca1e4510c89d37218d88ae7424ad18fec5c7082d8f7503608f4e74ede",
            "relation": "supports",
            "scene_id": "v04-c003-s002",
            "start_offset": 229,
            "target_field": null,
            "target_id": "ending-000001",
            "target_type": "ending_criterion"
          }
        ]
      }
    ],
    "required_major_threads": [
      {
        "evidence": [
          {
            "audience_id": null,
            "audience_type": null,
            "commit_id": "commit-00000025",
            "created_at": "2026-07-22T04:00:00Z",
            "end_offset": 59,
            "evidence_id": "ev-000090",
            "evidence_type": "thread_state_update",
            "prose_sha256": "bfdeefa3b9d4401ded4af2ad1ae1d1a84520d05586dd1a5b65c0a4f30e056021",
            "quote": "欠けた台帳は、設備の故障が町の管理記録と結びつくことを示した。",
            "quote_sha256": "b624426b5b0495cad06202e58b1e7f0cc8f0463b65e3664cfed6d49d48502087",
            "relation": "supports",
            "scene_id": "v02-c004-s003",
            "start_offset": 28,
            "target_field": "/progress",
            "target_id": "thread-000001",
            "target_type": "thread_state"
          },
          {
            "audience_id": null,
            "audience_type": null,
            "commit_id": "commit-00000037",
            "created_at": "2026-07-22T04:00:00Z",
            "end_offset": 59,
            "evidence_id": "ev-000095",
            "evidence_type": "thread_state_update",
            "prose_sha256": "813841a282503ddd4f3e2d199f7b12466ceeb7dca7cbcbf8fa7e18e0051e530f",
            "quote": "澪と凪は、停止原因を町の会議へ持ち込み、共同管理の判断を求めた。",
            "quote_sha256": "adc4301108a2dde335a2107979658c076602bf68cb2de9d5993377af4e1db8c3",
            "relation": "supports",
            "scene_id": "v03-c003-s003",
            "start_offset": 27,
            "target_field": "/progress",
            "target_id": "thread-000001",
            "target_type": "thread_state"
          },
          {
            "audience_id": null,
            "audience_type": null,
            "commit_id": "commit-00000050",
            "created_at": "2026-07-22T04:22:00Z",
            "end_offset": 92,
            "evidence_id": "ev-000101",
            "evidence_type": "thread_state_update",
            "prose_sha256": "77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e",
            "quote": "故障した旧式切替器と欠落した管理記録が、灯台停止の原因だった。",
            "quote_sha256": "d26356866733fb6f7e7adad4641762f0fb6fe5e8e37fead4eb555b765e0533ea",
            "relation": "supports",
            "scene_id": "v04-c003-s002",
            "start_offset": 61,
            "target_field": "/thread_status",
            "target_id": "thread-000001",
            "target_type": "thread_state"
          }
        ],
        "final_state": {
          "progress": 4,
          "thread_id": "thread-000001",
          "thread_status": "resolved",
          "volume_disposition": "resolve"
        },
        "handoff_mentions": [
          {
            "handoff_sha256": "737c35f0d17e19b4439009ab7bd9422057305e359337ced27832009aba962495",
            "safe_summary": "主要Threadは進行度1で次巻へ継続する。",
            "volume_disposition": "carry_over",
            "volume_number": 1
          },
          {
            "handoff_sha256": "e3e6e72fa02260ee0f66fd01ebb9a21cc403cb16a7e8121bf608ec942f939c73",
            "safe_summary": "主要Threadは進行度2で次巻へ継続する。",
            "volume_disposition": "carry_over",
            "volume_number": 2
          },
          {
            "handoff_sha256": "539a4a8cf5414534aabc7ff43d520486ad21931bf9bdc7b711b5e63ecd875c44",
            "safe_summary": "主要Threadは進行度3で次巻へ継続する。",
            "volume_disposition": "carry_over",
            "volume_number": 3
          },
          {
            "handoff_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b",
            "safe_summary": "停止原因と共同責任の主要Threadは最終的に解決した。",
            "volume_disposition": "resolve",
            "volume_number": 4
          }
        ],
        "record": {
          "author_truth": "地下修理庫に残された旧式切替器と管理台帳が停止原因を示し、予備鍵がその調査を可能にする。",
          "created_scene_id": null,
          "description": "灯台停止の原因と、隠されてきた管理責任を明らかにできるか。",
          "id": "thread-000001",
          "presentation_rule": "予備鍵、修理庫、台帳、切替器の順に根拠を開示し、説明だけで真相を確定しない。",
          "record_lifecycle": "active",
          "record_origin": "initial_design",
          "record_type": "thread",
          "required": true,
          "resolution_condition": "旧式切替器の故障と管理記録の空白を公に確認し、安全な再点灯と共同管理を実現する。",
          "scope": "series",
          "thread_type": "major"
        }
      }
    ],
    "residual_issues": [],
    "series_map": {
      "accepted_candidate_sha256": "450a883f030353874d490cbecd699d7f71ed9fa8d32a535e0edbd4a3217367eb",
      "brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
      "created_at": "2026-07-22T00:06:00Z",
      "final_required_criterion_ids": [
        "ending-000001"
      ],
      "initial_design_sha256": "e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce",
      "protagonist_end_state": "町と責任を分け合いながら、自分の意思で灯台を守っている。",
      "protagonist_start_state": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
      "schema_version": "1.0",
      "series_question": "灯台停止の原因を明らかにし、町は灯を誰の責任として守るのか。",
      "source_generation_id": "00000000",
      "source_generation_manifest_sha256": "df47c3a32cfd19ecbdb08aa39c843810850974d9f0331be7f71b7b3208732e40",
      "volumes": [
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "withhold",
              "prohibited_disclosure": "町の最終的な役割分担を断定しない",
              "purpose": "共同責任という結末条件をまだ確定せず、個人責任の限界だけを示す",
              "required": true
            }
          ],
          "ending_function": "局所的な調査成功を与えつつ、町の管理記録へ疑問を広げる。",
          "estimated_chapter_count": 4,
          "local_resolution": "地下修理庫への進入経路を確保し、最初の設備調査を完了する。",
          "major_thread_targets": [
            {
              "purpose": "停止原因の問いと予備鍵の手掛かりを導入する",
              "required_action": "introduce",
              "start_progress": 0,
              "start_status": "open",
              "target_progress": 1,
              "target_status": "in_progress",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "孤立した義務感から協力へ動かす",
            "required_change": "単独で抱えず凪と調査根拠を共有する",
            "start_state_summary": "家の責任を自分だけで背負い、町や凪へ弱みを見せまいとしている。",
            "target_state_summary": "凪と調査根拠を共有し、自分の意思で原因を追い始めている。"
          },
          "reader_question": "予備鍵の先に、誰が隠した停止原因の記録があるのか。",
          "relationship_change_targets": [
            {
              "purpose": "主要Relationshipの再始動",
              "relationship_id": "rel-000001",
              "required_change": "実務上の判断根拠を共有する",
              "start_state_summary": "能力は認めるが過去の対立を避け、必要最低限しか話さない。",
              "target_state_summary": "調査手順と根拠を共有し、実務上の信頼を取り戻し始める。"
            }
          ],
          "structural_role": "opening",
          "volume_function": "澪と凪を再会させ、予備鍵と修理庫という最初の実物手掛かりへ到達させる。",
          "volume_number": 1
        },
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "prepare",
              "prohibited_disclosure": "最終合意が成立したとは書かない",
              "purpose": "町の複数の担い手が必要だと読者に理解させる",
              "required": true
            }
          ],
          "ending_function": "原因を設備から制度へ拡大し、町の関係者を巻き込む。",
          "estimated_chapter_count": 4,
          "local_resolution": "故障箇所と記録欠落の時期を特定する。",
          "major_thread_targets": [
            {
              "purpose": "旧式切替器と欠落した台帳記録を結びつける",
              "required_action": "advance",
              "start_progress": 1,
              "start_status": "in_progress",
              "target_progress": 2,
              "target_status": "in_progress",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "個人対設備の問題を町の問題へ広げる",
            "required_change": "町の複数の立場を聞き、責任を共有する可能性を認める",
            "start_state_summary": "凪と調査根拠を共有し、自分の意思で原因を追い始めている。",
            "target_state_summary": "町の利害を聞き、自分だけで責任を背負わない選択肢を認めている。"
          },
          "reader_question": "管理記録の空白は事故なのか、意図的な隠蔽なのか。",
          "relationship_change_targets": [
            {
              "purpose": "誤解を解き信頼を深める",
              "relationship_id": "rel-000001",
              "required_change": "過去の両家の対立を互いに説明する",
              "start_state_summary": "調査手順と根拠を共有し、実務上の信頼を取り戻し始める。",
              "target_state_summary": "両家の対立を話し、互いの判断を相談できる。"
            }
          ],
          "structural_role": "midpoint",
          "volume_function": "修理庫と台帳を調べ、設備故障と町の管理空白が結びつく証拠を集める。",
          "volume_number": 2
        },
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "support",
              "prohibited_disclosure": "最終的な全町合意と再点灯を先取りしない",
              "purpose": "共同管理へ賛同する町の行動を積み上げる",
              "required": true
            }
          ],
          "ending_function": "真相開示を終え、最終巻の共同決断と再点灯へ移る。",
          "estimated_chapter_count": 3,
          "local_resolution": "停止原因と管理上の空白を町へ説明し、再点灯計画を合意可能な形にする。",
          "major_thread_targets": [
            {
              "purpose": "停止原因と管理責任を公の判断材料にする",
              "required_action": "advance",
              "start_progress": 2,
              "start_status": "in_progress",
              "target_progress": 3,
              "target_status": "in_progress",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "最終決断を町全体へ渡す",
            "required_change": "原因と責任の関係を公にし共同解決を要求する",
            "start_state_summary": "町の利害を聞き、自分だけで責任を背負わない選択肢を認めている。",
            "target_state_summary": "停止原因と町の管理責任を結びつけ、共同解決を公に求めている。"
          },
          "reader_question": "町は責任と作業を実際に分け合えるのか。",
          "relationship_change_targets": [
            {
              "purpose": "私的な信頼を公的な協力へ変える",
              "relationship_id": "rel-000001",
              "required_change": "町への説明を二人で引き受ける",
              "start_state_summary": "両家の対立を話し、互いの判断を相談できる。",
              "target_state_summary": "町への説明を共同で引き受け、対等な協力関係を公にする。"
            }
          ],
          "structural_role": "pre_final",
          "volume_function": "隠された判断と責任の所在を公にし、町へ共同管理の選択を迫る。",
          "volume_number": 3
        },
        {
          "ending_criterion_targets": [
            {
              "criterion_id": "ending-000001",
              "plan_action": "satisfy",
              "prohibited_disclosure": null,
              "purpose": "町の具体的な役割分担と再点灯を証拠化する",
              "required": true
            }
          ],
          "ending_function": "主要ThreadとEnding criterionを満たし、灯が共同の意思で維持される未来を示す。",
          "estimated_chapter_count": 3,
          "local_resolution": "町の役割分担が決まり、澪と凪が再点灯を見届ける。",
          "major_thread_targets": [
            {
              "purpose": "停止原因を確定し、安全な再点灯と共同管理を実現する",
              "required_action": "resolve",
              "start_progress": 3,
              "start_status": "in_progress",
              "target_progress": 4,
              "target_status": "resolved",
              "thread_id": "thread-000001"
            }
          ],
          "protagonist_change_target": {
            "character_id": "char-000001",
            "purpose": "主人公arcを完結させる",
            "required_change": "共同の役割を受け入れたうえで自分の意思で灯を守る",
            "start_state_summary": "停止原因と町の管理責任を結びつけ、共同解決を公に求めている。",
            "target_state_summary": "町と責任を分け合いながら、自分の意思で灯台を守っている。"
          },
          "reader_question": null,
          "relationship_change_targets": [
            {
              "purpose": "主要Relationshipを確立する",
              "relationship_id": "rel-000001",
              "required_change": "対等な共同作業として再点灯を完了する",
              "start_state_summary": "町への説明を共同で引き受け、対等な協力関係を公にする。",
              "target_state_summary": "互いの専門性と選択を信頼し、灯台を共同で支える。"
            }
          ],
          "structural_role": "final",
          "volume_function": "町の役割分担を成立させ、灯台を安全に再点灯して全ての主要条件を完結させる。",
          "volume_number": 4
        }
      ]
    },
    "volume_handoffs": [
      {
        "accepted_candidate_path": "runtime/candidates/handoffs/v01/v0001/volume-handoff.json",
        "accepted_candidate_sha256": "434fd9b02f9546ed31b24dd781a862ba25eb2138a105dbf31c45e99634afdf7e",
        "accepted_response_sha256": "04465eeadb802041d8ef11d9eecd6d27d03e144895164f587b1a9df8c8143248",
        "adopted_at": "2026-07-22T01:32:00Z",
        "adopted_generation_id": "00000013",
        "character_carryovers": [
          {
            "character_id": "char-000001",
            "importance": "required",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": "次巻でも町と凪へ判断根拠を共有する。",
            "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
            "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
          },
          {
            "character_id": "char-000002",
            "importance": "important",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": "次巻の設備調査と記録照合を支える。",
            "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
            "public_state_summary": "凪は安全手順と共同記録を支えている。"
          }
        ],
        "commit_id": "commit-00000013",
        "created_at": "2026-07-22T01:30:00Z",
        "ending_state_summary": "第1巻の局所目標を達成し、灯台停止の主要Threadは進行度1に到達した。",
        "handoff_version": "1.0",
        "knowledge_carryovers": [
          {
            "fact_id": "fact-000001",
            "importance": "important",
            "next_volume_constraint": "既知情報として扱い、再び謎へ戻さない。",
            "reader_status": "revealed",
            "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
            "relevant_character_ids": [
              "char-000001",
              "char-000002"
            ]
          }
        ],
        "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
        "next_volume_constraints": [
          {
            "category": "thread",
            "code": "NEXT_VOLUME_2_THREAD",
            "description": "主要Threadの計画遷移を次の進行度へ進める。",
            "related_ids": [
              "thread-000001"
            ],
            "required": true
          }
        ],
        "relationship_carryovers": [
          {
            "importance": "required",
            "next_volume_relevance": "次巻で共同説明と作業を継続する。",
            "private_state_summary": "互いの専門性を信頼している。",
            "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
            "relationship_id": "rel-000001"
          }
        ],
        "residual_risks": [],
        "review_path": "runtime/candidates/handoffs/v01/v0001/review.json",
        "review_sha256": "aa58517947bfa428ba8fe334683f117da984fc0d6ec42af01526fd01d485dae8",
        "schema_version": "1.0",
        "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
        "series_transition_summary": "第2巻で主要Threadを継続する。",
        "source_generation_id": "00000012",
        "source_generation_manifest_sha256": "2361471005740159e7d95c944148112e9c0bd10dc3445a369d5c68d206eb9b6d",
        "story_clock": {
          "current_chapter_number": 4,
          "current_order": 12,
          "current_scene_number": 3,
          "current_volume_number": 1,
          "last_scene_id": "v01-c004-s003",
          "parallel_group_id": null,
          "time_label": "第1巻終盤"
        },
        "thread_decisions": [
          {
            "disposition": "carry_over",
            "evidence_ids": [],
            "importance": "required",
            "next_volume_constraint": "次巻で停止原因と町の管理責任を一段進める。",
            "prior_volume_disposition": null,
            "progress": 1,
            "record_lifecycle": "active",
            "required": true,
            "scope": "series",
            "summary": "主要Threadは進行度1で次巻へ継続する。",
            "thread_id": "thread-000001",
            "thread_status": "in_progress",
            "thread_type": "major"
          }
        ],
        "volume_design_path": "plans/volumes/v01/volume-design.json",
        "volume_design_sha256": "09131a4c39bc4002d338b9de81341dce7d9905d5f3ec16f9ff6676b4b9698d8c",
        "volume_number": 1,
        "world_carryovers": [
          {
            "importance": "required",
            "next_volume_constraint": "既存の構造と安全規則を維持する。",
            "relevance_summary": "岬の灯台は次巻も主要舞台である。",
            "world_entity_id": "loc-000001"
          }
        ]
      },
      {
        "accepted_candidate_path": "runtime/candidates/handoffs/v02/v0001/volume-handoff.json",
        "accepted_candidate_sha256": "d00c197b983af38c24e4a6c34b96238dbcb29cd73efb8968cf403ca710f79bd7",
        "accepted_response_sha256": "9f4aad7e35793496ce560a302d6458dae4507ae109686432648316d793a38fe8",
        "adopted_at": "2026-07-22T02:32:00Z",
        "adopted_generation_id": "00000026",
        "character_carryovers": [
          {
            "character_id": "char-000001",
            "importance": "required",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": "次巻でも町と凪へ判断根拠を共有する。",
            "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
            "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
          },
          {
            "character_id": "char-000002",
            "importance": "important",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": "次巻の設備調査と記録照合を支える。",
            "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
            "public_state_summary": "凪は安全手順と共同記録を支えている。"
          }
        ],
        "commit_id": "commit-00000026",
        "created_at": "2026-07-22T02:30:00Z",
        "ending_state_summary": "第2巻の局所目標を達成し、灯台停止の主要Threadは進行度2に到達した。",
        "handoff_version": "1.0",
        "knowledge_carryovers": [
          {
            "fact_id": "fact-000001",
            "importance": "important",
            "next_volume_constraint": "既知情報として扱い、再び謎へ戻さない。",
            "reader_status": "revealed",
            "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
            "relevant_character_ids": [
              "char-000001",
              "char-000002"
            ]
          }
        ],
        "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
        "next_volume_constraints": [
          {
            "category": "thread",
            "code": "NEXT_VOLUME_3_THREAD",
            "description": "主要Threadの計画遷移を次の進行度へ進める。",
            "related_ids": [
              "thread-000001"
            ],
            "required": true
          }
        ],
        "relationship_carryovers": [
          {
            "importance": "required",
            "next_volume_relevance": "次巻で共同説明と作業を継続する。",
            "private_state_summary": "互いの専門性を信頼している。",
            "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
            "relationship_id": "rel-000001"
          }
        ],
        "residual_risks": [],
        "review_path": "runtime/candidates/handoffs/v02/v0001/review.json",
        "review_sha256": "cb2dd55378b36f2f97758db89e8893ca3511b27654ab868c8c3839205a4c3e65",
        "schema_version": "1.0",
        "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
        "series_transition_summary": "第3巻で主要Threadを継続する。",
        "source_generation_id": "00000025",
        "source_generation_manifest_sha256": "8d31f69e4540280420c31329f6fa77db9fe5ce050f52aead93a60c5f1d678f1f",
        "story_clock": {
          "current_chapter_number": 4,
          "current_order": 24,
          "current_scene_number": 3,
          "current_volume_number": 2,
          "last_scene_id": "v02-c004-s003",
          "parallel_group_id": null,
          "time_label": "第2巻終盤"
        },
        "thread_decisions": [
          {
            "disposition": "carry_over",
            "evidence_ids": [],
            "importance": "required",
            "next_volume_constraint": "次巻で停止原因と町の管理責任を一段進める。",
            "prior_volume_disposition": "carry_over",
            "progress": 2,
            "record_lifecycle": "active",
            "required": true,
            "scope": "series",
            "summary": "主要Threadは進行度2で次巻へ継続する。",
            "thread_id": "thread-000001",
            "thread_status": "in_progress",
            "thread_type": "major"
          }
        ],
        "volume_design_path": "plans/volumes/v02/volume-design.json",
        "volume_design_sha256": "023d8e425e32d125f245e3b792895737d3b19b5521b85920ba08d98f05a07f1c",
        "volume_number": 2,
        "world_carryovers": [
          {
            "importance": "required",
            "next_volume_constraint": "既存の構造と安全規則を維持する。",
            "relevance_summary": "岬の灯台は次巻も主要舞台である。",
            "world_entity_id": "loc-000001"
          }
        ]
      },
      {
        "accepted_candidate_path": "runtime/candidates/handoffs/v03/v0001/volume-handoff.json",
        "accepted_candidate_sha256": "64851ced4f2a7e1b9e2ff7d2a90a8340553fdfe19bc328416349d29a836fbfd1",
        "accepted_response_sha256": "02afcd99b395595fba58b4f241ac61d1a3b057a9aa3b0acfa59b2dffc2cc59b0",
        "adopted_at": "2026-07-22T03:32:00Z",
        "adopted_generation_id": "00000038",
        "character_carryovers": [
          {
            "character_id": "char-000001",
            "importance": "required",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": "次巻でも町と凪へ判断根拠を共有する。",
            "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
            "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
          },
          {
            "character_id": "char-000002",
            "importance": "important",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": "次巻の設備調査と記録照合を支える。",
            "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
            "public_state_summary": "凪は安全手順と共同記録を支えている。"
          }
        ],
        "commit_id": "commit-00000038",
        "created_at": "2026-07-22T03:30:00Z",
        "ending_state_summary": "第3巻の局所目標を達成し、灯台停止の主要Threadは進行度3に到達した。",
        "handoff_version": "1.0",
        "knowledge_carryovers": [
          {
            "fact_id": "fact-000001",
            "importance": "important",
            "next_volume_constraint": "既知情報として扱い、再び謎へ戻さない。",
            "reader_status": "revealed",
            "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
            "relevant_character_ids": [
              "char-000001",
              "char-000002"
            ]
          }
        ],
        "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
        "next_volume_constraints": [
          {
            "category": "thread",
            "code": "NEXT_VOLUME_4_THREAD",
            "description": "主要Threadの計画遷移を次の進行度へ進める。",
            "related_ids": [
              "thread-000001"
            ],
            "required": true
          }
        ],
        "relationship_carryovers": [
          {
            "importance": "required",
            "next_volume_relevance": "次巻で共同説明と作業を継続する。",
            "private_state_summary": "互いの専門性を信頼している。",
            "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
            "relationship_id": "rel-000001"
          }
        ],
        "residual_risks": [],
        "review_path": "runtime/candidates/handoffs/v03/v0001/review.json",
        "review_sha256": "db24d4f4bdd4a0e6d70c79ab1f0c5a6a405597796d6799af720fe431ea04ee42",
        "schema_version": "1.0",
        "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
        "series_transition_summary": "第4巻で主要Threadを継続する。",
        "source_generation_id": "00000037",
        "source_generation_manifest_sha256": "b271250de13d0cc5d3cc3d611610eda75284ace0ac9416a24cf0c9c802075f74",
        "story_clock": {
          "current_chapter_number": 3,
          "current_order": 35,
          "current_scene_number": 3,
          "current_volume_number": 3,
          "last_scene_id": "v03-c003-s003",
          "parallel_group_id": null,
          "time_label": "第3巻終盤"
        },
        "thread_decisions": [
          {
            "disposition": "carry_over",
            "evidence_ids": [],
            "importance": "required",
            "next_volume_constraint": "次巻で停止原因と町の管理責任を一段進める。",
            "prior_volume_disposition": "carry_over",
            "progress": 3,
            "record_lifecycle": "active",
            "required": true,
            "scope": "series",
            "summary": "主要Threadは進行度3で次巻へ継続する。",
            "thread_id": "thread-000001",
            "thread_status": "in_progress",
            "thread_type": "major"
          }
        ],
        "volume_design_path": "plans/volumes/v03/volume-design.json",
        "volume_design_sha256": "b85836d7f04ce7be84a59ede2fe80516c2bb8f6b39ff8124c6d66fc5ec4beb27",
        "volume_number": 3,
        "world_carryovers": [
          {
            "importance": "required",
            "next_volume_constraint": "既存の構造と安全規則を維持する。",
            "relevance_summary": "岬の灯台は次巻も主要舞台である。",
            "world_entity_id": "loc-000001"
          }
        ]
      },
      {
        "accepted_candidate_path": "runtime/candidates/handoffs/v04/v0001/volume-handoff.json",
        "accepted_candidate_sha256": "a3c222245b75ccf794dff27a554cd61e9e297010a3a8b9cc20e1df1f2b1cf70e",
        "accepted_response_sha256": "358279a1e1b96154ecd55fde09c09062c8e53d85a4e5013ed2f8be5319504030",
        "adopted_at": "2026-07-22T04:32:00Z",
        "adopted_generation_id": "00000051",
        "character_carryovers": [
          {
            "character_id": "char-000001",
            "importance": "required",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": null,
            "private_state_summary": "責任を一人で抱え込む必要がないと理解している。",
            "public_state_summary": "澪は凪と根拠を共有し、共同で灯を守る行動を選んでいる。"
          },
          {
            "character_id": "char-000002",
            "importance": "important",
            "knowledge_fact_ids": [
              "fact-000001"
            ],
            "next_volume_relevance": null,
            "private_state_summary": "澪へ判断を委ねられる信頼を持つ。",
            "public_state_summary": "凪は安全手順と共同記録を支えている。"
          }
        ],
        "commit_id": "commit-00000051",
        "created_at": "2026-07-22T04:30:00Z",
        "ending_state_summary": "第4巻の局所目標を達成し、灯台停止の主要Threadは進行度4に到達した。",
        "handoff_version": "1.0",
        "knowledge_carryovers": [
          {
            "fact_id": "fact-000001",
            "importance": "important",
            "next_volume_constraint": null,
            "reader_status": "revealed",
            "relevance_summary": "予備鍵と地下修理庫の関係は登場人物と読者に共有済みである。",
            "relevant_character_ids": [
              "char-000001",
              "char-000002"
            ]
          }
        ],
        "local_resolution_summary": "巻内の調査・判断・共同作業を完了した。",
        "next_volume_constraints": [],
        "relationship_carryovers": [
          {
            "importance": "required",
            "next_volume_relevance": null,
            "private_state_summary": "互いの専門性を信頼している。",
            "public_state_summary": "二人は灯台調査と再点灯を共同で担う。",
            "relationship_id": "rel-000001"
          }
        ],
        "residual_risks": [],
        "review_path": "runtime/candidates/handoffs/v04/v0001/review.json",
        "review_sha256": "58110ed53daaf485bc18b042320d332d54df83fa7d372ff0cc1d87c85186b482",
        "schema_version": "1.0",
        "series_map_sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294",
        "series_transition_summary": null,
        "source_generation_id": "00000050",
        "source_generation_manifest_sha256": "fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614",
        "story_clock": {
          "current_chapter_number": 3,
          "current_order": 47,
          "current_scene_number": 2,
          "current_volume_number": 4,
          "last_scene_id": "v04-c003-s002",
          "parallel_group_id": null,
          "time_label": "最終日の夜"
        },
        "thread_decisions": [
          {
            "disposition": "resolve",
            "evidence_ids": [
              "ev-000090",
              "ev-000095",
              "ev-000101"
            ],
            "importance": "required",
            "next_volume_constraint": null,
            "prior_volume_disposition": "carry_over",
            "progress": 4,
            "record_lifecycle": "active",
            "required": true,
            "scope": "series",
            "summary": "停止原因と共同責任の主要Threadは最終的に解決した。",
            "thread_id": "thread-000001",
            "thread_status": "resolved",
            "thread_type": "major"
          }
        ],
        "volume_design_path": "plans/volumes/v04/volume-design.json",
        "volume_design_sha256": "9a78283fc5dd4bf067f14315604273598e257051aa04a43c534917cc894cc52a",
        "volume_number": 4,
        "world_carryovers": [
          {
            "importance": "required",
            "next_volume_constraint": null,
            "relevance_summary": "岬の灯台は主要舞台であり、最終巻で再点灯した。",
            "world_entity_id": "loc-000001"
          }
        ]
      }
    ]
  },
  "prompt_version": "comp-audit-v1",
  "response_schema_version": "completion-audit-v1",
  "schema_version": "1.0",
  "sensitivity": "private_audit",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
  "source_refs": [
    {
      "generation_id": null,
      "path": "input/brief.json",
      "required": true,
      "role": "brief",
      "sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7"
    },
    {
      "generation_id": "00000000",
      "path": "canon/initial-design.json",
      "required": true,
      "role": "initial_design",
      "sha256": "e1b00b6c009510fbe6144d1ab9950c46666f94873b9fd949d50c56fa34b285ce"
    },
    {
      "generation_id": null,
      "path": "plans/series-map.json",
      "required": true,
      "role": "series_map",
      "sha256": "5ceb4d1738c9b46beaeb88ef8d20df2c324ffcf619771cdcc2651cec45c17294"
    },
    {
      "generation_id": "00000051",
      "path": "canon/generations/00000051/generation-manifest.json",
      "required": true,
      "role": "generation_manifest",
      "sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c"
    },
    {
      "generation_id": "00000051",
      "path": "canon/generations/00000051/story-state.json",
      "required": true,
      "role": "story_state",
      "sha256": "1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0"
    },
    {
      "generation_id": "00000051",
      "path": "canon/generations/00000051/evidence-index.json",
      "required": true,
      "role": "evidence_index",
      "sha256": "0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601"
    },
    {
      "generation_id": "00000051",
      "path": "audit/completion/00000051/completion-precondition.json",
      "required": true,
      "role": "completion_precondition",
      "sha256": "14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c"
    },
    {
      "generation_id": "00000013",
      "path": "artifacts/handoffs/v01.json",
      "required": true,
      "role": "volume_handoff",
      "sha256": "737c35f0d17e19b4439009ab7bd9422057305e359337ced27832009aba962495"
    },
    {
      "generation_id": "00000026",
      "path": "artifacts/handoffs/v02.json",
      "required": true,
      "role": "volume_handoff",
      "sha256": "e3e6e72fa02260ee0f66fd01ebb9a21cc403cb16a7e8121bf608ec942f939c73"
    },
    {
      "generation_id": "00000038",
      "path": "artifacts/handoffs/v03.json",
      "required": true,
      "role": "volume_handoff",
      "sha256": "539a4a8cf5414534aabc7ff43d520486ad21931bf9bdc7b711b5e63ecd875c44"
    },
    {
      "generation_id": "00000051",
      "path": "artifacts/handoffs/v04.json",
      "required": true,
      "role": "volume_handoff",
      "sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b"
    }
  ],
  "target_id": "completion",
  "token_budget": {
    "context_payload_limit": 22652,
    "final_input_tokens": 12100,
    "hard_input_limit": 23552,
    "max_operation_input_tokens": 32768,
    "model_context_window_tokens": 32768,
    "operation_key": "completion_audit",
    "overflowed": false,
    "payload_tokens": 11200,
    "protocol_overhead_tokens": 1024,
    "reserved_output_tokens": 8192,
    "static_prompt_tokens": 900,
    "token_count_method": "provider_tokenizer",
    "tokenizer_id": "fixture-tokenizer-v1"
  },
  "view_type": "completion"
}
```

Canonical SHA-256:

```text
5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc
```

## 31. Completion response

```text
EXACT RESPONSE
operation = COMP-AUDIT
example_id = EX-POS-COMP-002
```

```json
{
  "contradictions": [],
  "criteria_assessments": [
    {
      "assessment": "satisfied",
      "contradicts_evidence_ids": [],
      "criterion_id": "ending-000001",
      "explanation": "町の三班による役割分担と、澪・凪の共同再点灯がEvidenceで確認できる。",
      "required": true,
      "supports_evidence_ids": [
        "ev-000102",
        "ev-000103"
      ]
    }
  ],
  "overall_assessment": "complete",
  "residual_issues": [],
  "summary": "必要なEnding criterionとMajor ThreadはEvidenceにより完結しており、material contradictionやblocking residual issueはない。",
  "thread_assessments": [
    {
      "assessment": "resolved",
      "evidence_ids": [
        "ev-000090",
        "ev-000095",
        "ev-000101"
      ],
      "explanation": "設備故障と管理記録の空白が段階的に示され、最終Sceneで停止原因が確定している。",
      "progress": 4,
      "required": true,
      "thread_id": "thread-000001",
      "thread_status": "resolved"
    }
  ]
}
```

Canonical SHA-256:

```text
a687343eb880cfbb35f154aad28207ede6f39910392e5c3b924f112fa1ccec94
```

## 32. Saved Completion attempt

```text
EXACT ARTIFACT
path = runtime/candidates/completion/attempt-01.json
example_id = EX-POS-COMP-FIX-ATTEMPT-001
```

```json
{
  "audit_attempt": 1,
  "call_id": "call-000299",
  "context_snapshot_path": "runtime/context-snapshots/comp-audit/completion/5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc.json",
  "context_snapshot_sha256": "5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc",
  "contradictions": [],
  "created_at": "2026-07-22T04:41:00Z",
  "criteria_assessments": [
    {
      "assessment": "satisfied",
      "contradicts_evidence_ids": [],
      "criterion_id": "ending-000001",
      "explanation": "町の三班による役割分担と、澪・凪の共同再点灯がEvidenceで確認できる。",
      "required": true,
      "supports_evidence_ids": [
        "ev-000102",
        "ev-000103"
      ]
    }
  ],
  "overall_assessment": "complete",
  "precondition_path": "audit/completion/00000051/completion-precondition.json",
  "precondition_sha256": "14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c",
  "prompt_version": "comp-audit-v1",
  "residual_issues": [],
  "response_schema_version": "completion-audit-v1",
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
  "summary": "必要なEnding criterionとMajor ThreadはEvidenceにより完結しており、material contradictionやblocking residual issueはない。",
  "thread_assessments": [
    {
      "assessment": "resolved",
      "evidence_ids": [
        "ev-000090",
        "ev-000095",
        "ev-000101"
      ],
      "explanation": "設備故障と管理記録の空白が段階的に示され、最終Sceneで停止原因が確定している。",
      "progress": 4,
      "required": true,
      "thread_id": "thread-000001",
      "thread_status": "resolved"
    }
  ]
}
```

Canonical SHA-256:

```text
f3ff4b09df9284e3aac6a11cd937728fa157d4c74507d2099902cdc73c42513a
```

## 33. Completion Candidate manifest

```text
EXACT ARTIFACT
path = runtime/candidates/completion/candidate-manifest.json
example_id = EX-POS-COMP-FIX-CAND-001
```

```json
{
  "candidate_artifact_format": "json",
  "candidate_path": "runtime/candidates/completion/attempt-01.json",
  "candidate_sha256": "f3ff4b09df9284e3aac6a11cd937728fa157d4c74507d2099902cdc73c42513a",
  "candidate_status": "ready_for_adoption",
  "candidate_version": 1,
  "completion_audit_attempt": 1,
  "created_at": "2026-07-22T04:41:00Z",
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "input_snapshot_path": "runtime/context-snapshots/comp-audit/completion/5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc.json",
  "input_snapshot_sha256": "5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc",
  "last_call_id": "call-000299",
  "last_structurally_valid": true,
  "manifest_version": "1.0",
  "next_stage": "COMP-SAVE",
  "operation_id": "COMP-AUDIT",
  "previous_candidate_manifest_path": null,
  "previous_candidate_manifest_sha256": null,
  "processor_type": "llm_generate",
  "prompt_version": "comp-audit-v1",
  "residual_issues_path": null,
  "response_schema_version": "completion-audit-v1",
  "response_structure_retries_used": 0,
  "review_path": null,
  "review_sha256": null,
  "revision_rounds_used": 0,
  "target_id": "completion",
  "transport_retries_used": 0,
  "updated_at": "2026-07-22T04:41:00Z"
}
```

Canonical SHA-256:

```text
788df355a47d428f2e32ade22383d7f924a6abd612828bba10e8d9955cbcdb7d
```

## 34. Accepted private Completion audit

```text
EXACT ARTIFACT
path = audit/completion/00000051/completion-audit.json
example_id = EX-POS-COMP-003
```

```json
{
  "accepted_attempt_path": "runtime/candidates/completion/attempt-01.json",
  "accepted_attempt_sha256": "f3ff4b09df9284e3aac6a11cd937728fa157d4c74507d2099902cdc73c42513a",
  "audit_attempt": 1,
  "call_id": "call-000299",
  "context_snapshot_path": "runtime/context-snapshots/comp-audit/completion/5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc.json",
  "context_snapshot_sha256": "5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc",
  "contradictions": [],
  "created_at": "2026-07-22T04:41:00Z",
  "criteria_assessments": [
    {
      "assessment": "satisfied",
      "contradicts_evidence_ids": [],
      "criterion_id": "ending-000001",
      "explanation": "町の三班による役割分担と、澪・凪の共同再点灯がEvidenceで確認できる。",
      "required": true,
      "supports_evidence_ids": [
        "ev-000102",
        "ev-000103"
      ]
    }
  ],
  "overall_assessment": "complete",
  "precondition_path": "audit/completion/00000051/completion-precondition.json",
  "precondition_sha256": "14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c",
  "prompt_version": "comp-audit-v1",
  "residual_issues": [],
  "response_schema_version": "completion-audit-v1",
  "saved_at": "2026-07-22T04:42:00Z",
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
  "summary": "必要なEnding criterionとMajor ThreadはEvidenceにより完結しており、material contradictionやblocking residual issueはない。",
  "thread_assessments": [
    {
      "assessment": "resolved",
      "evidence_ids": [
        "ev-000090",
        "ev-000095",
        "ev-000101"
      ],
      "explanation": "設備故障と管理記録の空白が段階的に示され、最終Sceneで停止原因が確定している。",
      "progress": 4,
      "required": true,
      "thread_id": "thread-000001",
      "thread_status": "resolved"
    }
  ]
}
```

Canonical SHA-256:

```text
d1fc155cdd6ae8b4efef122478f26232110febde9969c8063ec64f08e2aa947a
```

## 35. Publication-safe Completion report

```text
EXACT ARTIFACT
path = publications/pub-000001/reports/completion-audit.json
example_id = EX-POS-COMP-004
```

```json
{
  "contradiction_count": 0,
  "created_at": "2026-07-22T04:45:00Z",
  "criteria": [
    {
      "assessment": "satisfied",
      "contradiction_count": 0,
      "criterion_id": "ending-000001",
      "required": true,
      "safe_explanation": "町の役割分担と共同再点灯が確認されている。",
      "support_count": 2
    }
  ],
  "overall_assessment": "complete",
  "private_audit_sha256": "d1fc155cdd6ae8b4efef122478f26232110febde9969c8063ec64f08e2aa947a",
  "residual_issues": [],
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "summary": "物語の必須条件はすべて完結している。",
  "threads": [
    {
      "assessment": "resolved",
      "evidence_count": 3,
      "progress": 4,
      "safe_explanation": "停止原因が確定し、安全な再点灯と共同管理が成立している。",
      "status": "resolved",
      "thread_id": "thread-000001"
    }
  ]
}
```

Canonical SHA-256:

```text
3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f
```

# Part V: Publication payload
## 36. Deterministic manuscript hashes

| file | bytes | SHA-256 |
|---|---:|---|
| `manuscript/series.md` | 11168 | `93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9` |
| `manuscript/v01.md` | 2651 | `f8a695a0a0f3e99ec6d057038c507e4f168ff90ca3b81aeca78a3ae192ccb835` |
| `manuscript/v02.md` | 2666 | `b22c5a2cd080ef1d6e12d4274ffdcf16662c007893da284ae455ecba1457be57` |
| `manuscript/v03.md` | 2434 | `4e04e68f044e9e7ed3879a781fd262e8f5fdaf462e224bbcbde18ea742202c06` |
| `manuscript/v04.md` | 3401 | `9c47815fb581012818190fa463709a4fff7d7006f79d479733be4d1a51c624c9` |

Manuscript ordering follows Series → Volume → Chapter → Scene. Generated headings are excluded from Volume character counts.

## 37. Series metadata

```text
EXACT ARTIFACT
path = publications/pub-000001/metadata/series.json
example_id = EX-POS-COMP-FIX-META-SERIES
```

```json
{
  "completion_overall_assessment": "complete",
  "created_at": "2026-07-22T04:45:00Z",
  "editorial_profile_id": "default-ja",
  "genre": "海洋幻想譚",
  "publishing_profile_id": "kdp-ja-v1",
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
  "target_reader": "成人読者",
  "title": "岬の灯",
  "volume_count": 4
}
```

Canonical SHA-256:

```text
a40deb49c3e48b5330744a7fc2f448bd89ace3df4748806a510ed4c3c3bb29d2
```

## 38. Volume-1 metadata

```text
EXACT ARTIFACT
path = publications/pub-000001/metadata/volumes/v01.json
example_id = EX-POS-COMP-FIX-META-V01
```

```json
{
  "chapter_count": 4,
  "character_count": 840,
  "created_at": "2026-07-22T04:45:00Z",
  "manuscript_relative_path": "manuscript/v01.md",
  "manuscript_sha256": "f8a695a0a0f3e99ec6d057038c507e4f168ff90ca3b81aeca78a3ae192ccb835",
  "scene_count": 12,
  "schema_version": "1.0",
  "source_handoff_sha256": "737c35f0d17e19b4439009ab7bd9422057305e359337ced27832009aba962495",
  "source_volume_design_sha256": "09131a4c39bc4002d338b9de81341dce7d9905d5f3ec16f9ff6676b4b9698d8c",
  "title": "閉ざされた修理庫",
  "volume_number": 1
}
```

Canonical SHA-256:

```text
d4d63ded19cec7e4b7fd2d159214e31b7ef7039d882b105b09466c3ae6a5fe50
```

## 39. Volume-2 metadata

```text
EXACT ARTIFACT
path = publications/pub-000001/metadata/volumes/v02.json
example_id = EX-POS-COMP-FIX-META-V02
```

```json
{
  "chapter_count": 4,
  "character_count": 849,
  "created_at": "2026-07-22T04:45:00Z",
  "manuscript_relative_path": "manuscript/v02.md",
  "manuscript_sha256": "b22c5a2cd080ef1d6e12d4274ffdcf16662c007893da284ae455ecba1457be57",
  "scene_count": 12,
  "schema_version": "1.0",
  "source_handoff_sha256": "e3e6e72fa02260ee0f66fd01ebb9a21cc403cb16a7e8121bf608ec942f939c73",
  "source_volume_design_sha256": "023d8e425e32d125f245e3b792895737d3b19b5521b85920ba08d98f05a07f1c",
  "title": "欠けた台帳",
  "volume_number": 2
}
```

Canonical SHA-256:

```text
3a3938c3078ac526d3d96c284833ac30d9723b2f8175974499a227909960b1d7
```

## 40. Volume-3 metadata

```text
EXACT ARTIFACT
path = publications/pub-000001/metadata/volumes/v03.json
example_id = EX-POS-COMP-FIX-META-V03
```

```json
{
  "chapter_count": 3,
  "character_count": 781,
  "created_at": "2026-07-22T04:45:00Z",
  "manuscript_relative_path": "manuscript/v03.md",
  "manuscript_sha256": "4e04e68f044e9e7ed3879a781fd262e8f5fdaf462e224bbcbde18ea742202c06",
  "scene_count": 11,
  "schema_version": "1.0",
  "source_handoff_sha256": "539a4a8cf5414534aabc7ff43d520486ad21931bf9bdc7b711b5e63ecd875c44",
  "source_volume_design_sha256": "b85836d7f04ce7be84a59ede2fe80516c2bb8f6b39ff8124c6d66fc5ec4beb27",
  "title": "町の沈黙",
  "volume_number": 3
}
```

Canonical SHA-256:

```text
ffd4ee14cb2152ebe937fb8bd5f493ddcb6661603354f022bd5611c6b50640fb
```

## 41. Volume-4 metadata

```text
EXACT ARTIFACT
path = publications/pub-000001/metadata/volumes/v04.json
example_id = EX-POS-COMP-FIX-META-V04
```

```json
{
  "chapter_count": 3,
  "character_count": 1102,
  "created_at": "2026-07-22T04:45:00Z",
  "manuscript_relative_path": "manuscript/v04.md",
  "manuscript_sha256": "9c47815fb581012818190fa463709a4fff7d7006f79d479733be4d1a51c624c9",
  "scene_count": 12,
  "schema_version": "1.0",
  "source_handoff_sha256": "a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b",
  "source_volume_design_sha256": "71c1888a6c3ad4a5a5f5a858646a3c7c66c1474312b4d37d806ddb828a2357cb",
  "title": "灯を分ける夜",
  "volume_number": 4
}
```

Canonical SHA-256:

```text
41f434587f108d042e80091e1a11ed23877061a638ed52402b5e633b89137ab0
```

## 42. Payload file-reference set

```text
EXACT VALUE
publication = payload records
example_id = EX-POS-PUB-001
```

```json
[
  {
    "media_type": "text/markdown; charset=utf-8",
    "relative_path": "manuscript/series.md",
    "role": "manuscript",
    "sha256": "93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9",
    "size_bytes": 11168
  },
  {
    "media_type": "text/markdown; charset=utf-8",
    "relative_path": "manuscript/v01.md",
    "role": "manuscript",
    "sha256": "f8a695a0a0f3e99ec6d057038c507e4f168ff90ca3b81aeca78a3ae192ccb835",
    "size_bytes": 2651
  },
  {
    "media_type": "text/markdown; charset=utf-8",
    "relative_path": "manuscript/v02.md",
    "role": "manuscript",
    "sha256": "b22c5a2cd080ef1d6e12d4274ffdcf16662c007893da284ae455ecba1457be57",
    "size_bytes": 2666
  },
  {
    "media_type": "text/markdown; charset=utf-8",
    "relative_path": "manuscript/v03.md",
    "role": "manuscript",
    "sha256": "4e04e68f044e9e7ed3879a781fd262e8f5fdaf462e224bbcbde18ea742202c06",
    "size_bytes": 2434
  },
  {
    "media_type": "text/markdown; charset=utf-8",
    "relative_path": "manuscript/v04.md",
    "role": "manuscript",
    "sha256": "9c47815fb581012818190fa463709a4fff7d7006f79d479733be4d1a51c624c9",
    "size_bytes": 3401
  },
  {
    "media_type": "application/json",
    "relative_path": "metadata/series.json",
    "role": "metadata",
    "sha256": "a40deb49c3e48b5330744a7fc2f448bd89ace3df4748806a510ed4c3c3bb29d2",
    "size_bytes": 407
  },
  {
    "media_type": "application/json",
    "relative_path": "metadata/volumes/v01.json",
    "role": "metadata",
    "sha256": "d4d63ded19cec7e4b7fd2d159214e31b7ef7039d882b105b09466c3ae6a5fe50",
    "size_bytes": 493
  },
  {
    "media_type": "application/json",
    "relative_path": "metadata/volumes/v02.json",
    "role": "metadata",
    "sha256": "3a3938c3078ac526d3d96c284833ac30d9723b2f8175974499a227909960b1d7",
    "size_bytes": 484
  },
  {
    "media_type": "application/json",
    "relative_path": "metadata/volumes/v03.json",
    "role": "metadata",
    "sha256": "ffd4ee14cb2152ebe937fb8bd5f493ddcb6661603354f022bd5611c6b50640fb",
    "size_bytes": 481
  },
  {
    "media_type": "application/json",
    "relative_path": "metadata/volumes/v04.json",
    "role": "metadata",
    "sha256": "41f434587f108d042e80091e1a11ed23877061a638ed52402b5e633b89137ab0",
    "size_bytes": 488
  },
  {
    "media_type": "application/json",
    "relative_path": "reports/completion-audit.json",
    "role": "report",
    "sha256": "3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f",
    "size_bytes": 767
  }
]
```

Canonical SHA-256:

```text
cf8db431f7c75e6faa6cb8f8e771435e4de3021cc46713fc83f12ce4aac3db91
```

## 43. Provisional build manifest

```text
EXACT ARTIFACT
path = .staging/publication/pub-000001/publication-build-manifest.json
example_id = EX-POS-COMP-FIX-PUB-BUILD
```

```json
{
  "completion_precondition_path": "audit/completion/00000051/completion-precondition.json",
  "completion_precondition_sha256": "14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c",
  "created_at": "2026-07-22T04:45:00Z",
  "current_pointer_before": null,
  "expected_payload_file_refs": [
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/series.md",
      "role": "manuscript",
      "sha256": "93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9",
      "size_bytes": 11168
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v01.md",
      "role": "manuscript",
      "sha256": "f8a695a0a0f3e99ec6d057038c507e4f168ff90ca3b81aeca78a3ae192ccb835",
      "size_bytes": 2651
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v02.md",
      "role": "manuscript",
      "sha256": "b22c5a2cd080ef1d6e12d4274ffdcf16662c007893da284ae455ecba1457be57",
      "size_bytes": 2666
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v03.md",
      "role": "manuscript",
      "sha256": "4e04e68f044e9e7ed3879a781fd262e8f5fdaf462e224bbcbde18ea742202c06",
      "size_bytes": 2434
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v04.md",
      "role": "manuscript",
      "sha256": "9c47815fb581012818190fa463709a4fff7d7006f79d479733be4d1a51c624c9",
      "size_bytes": 3401
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/series.json",
      "role": "metadata",
      "sha256": "a40deb49c3e48b5330744a7fc2f448bd89ace3df4748806a510ed4c3c3bb29d2",
      "size_bytes": 407
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v01.json",
      "role": "metadata",
      "sha256": "d4d63ded19cec7e4b7fd2d159214e31b7ef7039d882b105b09466c3ae6a5fe50",
      "size_bytes": 493
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v02.json",
      "role": "metadata",
      "sha256": "3a3938c3078ac526d3d96c284833ac30d9723b2f8175974499a227909960b1d7",
      "size_bytes": 484
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v03.json",
      "role": "metadata",
      "sha256": "ffd4ee14cb2152ebe937fb8bd5f493ddcb6661603354f022bd5611c6b50640fb",
      "size_bytes": 481
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v04.json",
      "role": "metadata",
      "sha256": "41f434587f108d042e80091e1a11ed23877061a638ed52402b5e633b89137ab0",
      "size_bytes": 488
    },
    {
      "media_type": "application/json",
      "relative_path": "reports/completion-audit.json",
      "role": "report",
      "sha256": "3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f",
      "size_bytes": 767
    }
  ],
  "payload_set_sha256": "cf8db431f7c75e6faa6cb8f8e771435e4de3021cc46713fc83f12ce4aac3db91",
  "private_completion_audit_path": "audit/completion/00000051/completion-audit.json",
  "private_completion_audit_sha256": "d1fc155cdd6ae8b4efef122478f26232110febde9969c8063ec64f08e2aa947a",
  "publication_id": "pub-000001",
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c"
}
```

Canonical SHA-256:

```text
1c8ff2a0d460b77d0088e116767e2c751be59ad6d8a36b5d6cd32f209b77672d
```

This file is removed before the Publication Gate and is absent from the adopted directory.

## 44. Publication Validation

```text
EXACT ARTIFACT
path = publications/pub-000001/publication-validation.json
example_id = EX-POS-PUB-002
```

```json
{
  "checks": [
    {
      "check_id": "ALL_VOLUMES",
      "message": "All four Volumes are present in canonical order.",
      "relative_path": "manuscript/series.md",
      "sha256": "93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9",
      "status": "pass"
    },
    {
      "check_id": "COMPLETION_REPORT",
      "message": "Publication-safe Completion report validates.",
      "relative_path": "reports/completion-audit.json",
      "sha256": "3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f",
      "status": "pass"
    },
    {
      "check_id": "INTERNAL_ID_SCAN",
      "message": "Reader-facing manuscript contains no allocated internal identifier token.",
      "relative_path": "manuscript/series.md",
      "sha256": "93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9",
      "status": "pass"
    },
    {
      "check_id": "METADATA",
      "message": "Series and all Volume metadata are complete.",
      "relative_path": "metadata/series.json",
      "sha256": "a40deb49c3e48b5330744a7fc2f448bd89ace3df4748806a510ed4c3c3bb29d2",
      "status": "pass"
    },
    {
      "check_id": "PAYLOAD_HASHES",
      "message": "Every payload hash, size, media type, and role matches.",
      "relative_path": null,
      "sha256": null,
      "status": "pass"
    },
    {
      "check_id": "PRIVATE_LEAK_SCAN",
      "message": "No credential, prompt, raw response, workspace path, or author-only truth is present.",
      "relative_path": "reports/completion-audit.json",
      "sha256": "3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f",
      "status": "pass"
    },
    {
      "check_id": "PROFILE",
      "message": "The kdp-ja-v1 four-Volume profile constraints pass.",
      "relative_path": null,
      "sha256": null,
      "status": "pass"
    }
  ],
  "created_at": "2026-07-22T04:46:00Z",
  "payload_set_sha256": "cf8db431f7c75e6faa6cb8f8e771435e4de3021cc46713fc83f12ce4aac3db91",
  "publication_id": "pub-000001",
  "publishing_profile_id": "kdp-ja-v1",
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
  "validated_payload_file_count": 11,
  "validation_status": "pass"
}
```

Canonical SHA-256:

```text
cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea
```

## 45. Final Publication manifest

```text
EXACT ARTIFACT
path = publications/pub-000001/publication-manifest.json
example_id = EX-POS-PUB-003
```

```json
{
  "completion_audit_relative_path": "reports/completion-audit.json",
  "completion_audit_sha256": "3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f",
  "content_set_sha256": "017062328e652d76b5a608edc7f8a7449bbc5da8b1f2ac17fff18ac87c0f297c",
  "created_at": "2026-07-22T04:46:01Z",
  "current_pointer_after": "pub-000001",
  "current_pointer_before": null,
  "files": [
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/series.md",
      "role": "manuscript",
      "sha256": "93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9",
      "size_bytes": 11168
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v01.md",
      "role": "manuscript",
      "sha256": "f8a695a0a0f3e99ec6d057038c507e4f168ff90ca3b81aeca78a3ae192ccb835",
      "size_bytes": 2651
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v02.md",
      "role": "manuscript",
      "sha256": "b22c5a2cd080ef1d6e12d4274ffdcf16662c007893da284ae455ecba1457be57",
      "size_bytes": 2666
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v03.md",
      "role": "manuscript",
      "sha256": "4e04e68f044e9e7ed3879a781fd262e8f5fdaf462e224bbcbde18ea742202c06",
      "size_bytes": 2434
    },
    {
      "media_type": "text/markdown; charset=utf-8",
      "relative_path": "manuscript/v04.md",
      "role": "manuscript",
      "sha256": "9c47815fb581012818190fa463709a4fff7d7006f79d479733be4d1a51c624c9",
      "size_bytes": 3401
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/series.json",
      "role": "metadata",
      "sha256": "a40deb49c3e48b5330744a7fc2f448bd89ace3df4748806a510ed4c3c3bb29d2",
      "size_bytes": 407
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v01.json",
      "role": "metadata",
      "sha256": "d4d63ded19cec7e4b7fd2d159214e31b7ef7039d882b105b09466c3ae6a5fe50",
      "size_bytes": 493
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v02.json",
      "role": "metadata",
      "sha256": "3a3938c3078ac526d3d96c284833ac30d9723b2f8175974499a227909960b1d7",
      "size_bytes": 484
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v03.json",
      "role": "metadata",
      "sha256": "ffd4ee14cb2152ebe937fb8bd5f493ddcb6661603354f022bd5611c6b50640fb",
      "size_bytes": 481
    },
    {
      "media_type": "application/json",
      "relative_path": "metadata/volumes/v04.json",
      "role": "metadata",
      "sha256": "41f434587f108d042e80091e1a11ed23877061a638ed52402b5e633b89137ab0",
      "size_bytes": 488
    },
    {
      "media_type": "application/json",
      "relative_path": "publication-validation.json",
      "role": "validation",
      "sha256": "cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea",
      "size_bytes": 1893
    },
    {
      "media_type": "application/json",
      "relative_path": "reports/completion-audit.json",
      "role": "report",
      "sha256": "3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f",
      "size_bytes": 767
    }
  ],
  "manifest_version": "1.0",
  "publication_id": "pub-000001",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c",
  "validation_relative_path": "publication-validation.json",
  "validation_sha256": "cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea"
}
```

Canonical SHA-256:

```text
6c29719088bff3d4bba85bd23239a2b082b32233da0cfe38d7a226c95633d30a
```

## 46. Rename-stable snapshot value

```text
EXACT VALUE
publication = Gate snapshot input
example_id = EX-POS-COMP-FIX-PUB-SNAPSHOT
```

```json
{
  "content_set_sha256": "017062328e652d76b5a608edc7f8a7449bbc5da8b1f2ac17fff18ac87c0f297c",
  "payload_set_sha256": "cf8db431f7c75e6faa6cb8f8e771435e4de3021cc46713fc83f12ce4aac3db91",
  "publication_id": "pub-000001",
  "publication_manifest_relative_path": "publication-manifest.json",
  "publication_manifest_sha256": "6c29719088bff3d4bba85bd23239a2b082b32233da0cfe38d7a226c95633d30a",
  "publication_validation_relative_path": "publication-validation.json",
  "publication_validation_sha256": "cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c"
}
```

Canonical SHA-256:

```text
82cb1e6948c93c278b946f3edd3380a949c02f76b41735c9dcdb012d918e6067
```

## 47. Passing Publication Gate

```text
EXACT ARTIFACT
path = audit/publication-gates/pub-000001.json
example_id = EX-POS-PUB-004
```

```json
{
  "completion_audit_path": "audit/completion/00000051/completion-audit.json",
  "completion_audit_sha256": "d1fc155cdd6ae8b4efef122478f26232110febde9969c8063ec64f08e2aa947a",
  "completion_overall_assessment": "complete",
  "completion_precondition_path": "audit/completion/00000051/completion-precondition.json",
  "completion_precondition_sha256": "14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c",
  "content_set_sha256": "017062328e652d76b5a608edc7f8a7449bbc5da8b1f2ac17fff18ac87c0f297c",
  "created_at": "2026-07-22T04:47:00Z",
  "failures": [],
  "gate_status": "pass",
  "payload_set_sha256": "cf8db431f7c75e6faa6cb8f8e771435e4de3021cc46713fc83f12ce4aac3db91",
  "publication_id": "pub-000001",
  "publication_manifest_relative_path": "publication-manifest.json",
  "publication_manifest_sha256": "6c29719088bff3d4bba85bd23239a2b082b32233da0cfe38d7a226c95633d30a",
  "publication_snapshot_sha256": "82cb1e6948c93c278b946f3edd3380a949c02f76b41735c9dcdb012d918e6067",
  "publication_validation_relative_path": "publication-validation.json",
  "publication_validation_sha256": "cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea",
  "schema_version": "1.0",
  "source_generation_id": "00000051",
  "source_generation_manifest_sha256": "86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c"
}
```

Canonical SHA-256:

```text
389718c6e9c495532c4be72afa5fcdc53c132f0f58b6cbb73ce28d36a06cc2d1
```

## 48. Publication adoption

```text
.staging/publication/pub-000001
→ publications/pub-000001
→ output/CURRENT = pub-000001\n
```

CURRENT SHA-256:

```text
a10eef3a401d11ada9065c2c4c8b862964108feea7e2fb6139e8dfceb37adff8
```

The Gate snapshot SHA-256 is unchanged across the directory rename because every internal path is publication-root-relative.

# Part VI: Final Runtime state
## 49. Final counters

```text
EXACT ARTIFACT
path = runtime/counters.json
example_id = EX-POS-COMP-FIX-COUNTERS
```

```json
{
  "active_elapsed_seconds": 300,
  "completion_audit_attempts_used": 1,
  "estimated_cost_used": 0,
  "input_tokens_used": 420000,
  "llm_calls_used": 300,
  "next_call_id": 301,
  "next_character_id": 3,
  "next_commit_id": 52,
  "next_culture_id": 1,
  "next_ending_id": 2,
  "next_evidence_id": 105,
  "next_fact_id": 2,
  "next_history_id": 1,
  "next_item_id": 2,
  "next_location_id": 2,
  "next_organization_id": 1,
  "next_publication_id": 2,
  "next_relationship_id": 2,
  "next_rule_id": 2,
  "next_system_id": 1,
  "next_thread_id": 2,
  "output_tokens_used": 180000,
  "response_structure_retries_used": 0,
  "revision_rounds_used": 0,
  "successful_scene_commits": 47,
  "transport_retries_used": 0
}
```

Canonical SHA-256:

```text
0c7f8d278a6ef82bb3a89da3ae52ce20844370fe22a3956d1fbdacfeec4b7007
```

## 50. Completed Run state

```text
EXACT ARTIFACT
path = runtime/run-state.json
example_id = EX-POS-COMP-FIX-RUN
```

```json
{
  "active_candidate_manifest_path": null,
  "active_checkpoint_manifest_path": null,
  "adopted_brief_path": "input/brief.json",
  "adopted_brief_sha256": "75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7",
  "current_chapter_number": null,
  "current_head_generation": "00000051",
  "current_publication_id": "pub-000001",
  "current_scene_number": null,
  "current_target_id": "completion",
  "current_volume_number": 4,
  "effective_config_sha256": "4b2c4e60cfefaa7a153afd1967daf3d1d85039b0ca453606006f38ef9475101c",
  "last_commit_id": "commit-00000051",
  "last_completed_stage": "OUT-03",
  "last_error_audit_path": null,
  "next_stage": null,
  "run_id": "run-000001",
  "run_status": "completed",
  "scene_phase": null,
  "state_revision": 610,
  "state_version": "1.0",
  "stop_reason_code": "completed",
  "stop_reason_detail": null,
  "updated_at": "2026-07-22T04:48:00Z"
}
```

Canonical SHA-256:

```text
3d110c7f7138508ac2c0c78af89ec3f886fdac0275d560146de044c942bf8050
```

## 51. Generation arithmetic

```text
47 Scene commits
+ 4 Volume Handoff commits
= Generation suffix 51

final Scene Generation = 00000050
final Handoff / HEAD = 00000051
final current_order = 47
```

A Volume Handoff changes Generation identity without changing Scene order.

# Part VII: Hash and inventory summary
## 52. Core hash chain

```text
Generation 49 manifest: 8a2ab173740626531e04bbf0398a88f8bcf0978605d5078301227cf28ca5b0ec
final Scene card:      39f3fe751c15b7da5148c3a6cde1a9657ebe7e84c2a90a23caf3778536cc1a79
final prose:           77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e
final committed delta: 3a6e9d22b173976210decc31937401137687838fb6220d298ab65e574971f3d5
final Scene manifest:  7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174
Commit 50:             41d470d4fcee41b468a5bcb5543c23ff8009751b09e383e64ad9d2415a6f2c51
Generation 50:         fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614
final Handoff:         a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b
Commit 51:             00f5028967d25add25c3766dfaa1fe9a7d4836efdfbc726e2227e3b985df7276
Generation 51:         86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c
Completion precondition:14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c
Completion Context:    5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc
private audit:         d1fc155cdd6ae8b4efef122478f26232110febde9969c8063ec64f08e2aa947a
payload set:           cf8db431f7c75e6faa6cb8f8e771435e4de3021cc46713fc83f12ce4aac3db91
Validation:            cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea
content set:           017062328e652d76b5a608edc7f8a7449bbc5da8b1f2ac17fff18ac87c0f297c
Publication manifest:  6c29719088bff3d4bba85bd23239a2b082b32233da0cfe38d7a226c95633d30a
Gate snapshot:         82cb1e6948c93c278b946f3edd3380a949c02f76b41735c9dcdb012d918e6067
Gate:                  389718c6e9c495532c4be72afa5fcdc53c132f0f58b6cbb73ce28d36a06cc2d1
```

## 53. Exact fixture inventory

| path | authority role | bytes | SHA-256 |
|---|---|---:|---|
| `.staging/publication/pub-000001/publication-build-manifest.json` | `staging` | 2863 | `1c8ff2a0d460b77d0088e116767e2c751be59ad6d8a36b5d6cd32f209b77672d` |
| `artifacts/handoffs/v04.json` | `adopted` | 3310 | `a75b9d231cc1cdadd02157e67d3b64c703f00807c74cc8bf3dff4b8f4d89939b` |
| `artifacts/scenes/v04/c003/s002/continuity-delta.json` | `adopted` | 861 | `3a6e9d22b173976210decc31937401137687838fb6220d298ab65e574971f3d5` |
| `artifacts/scenes/v04/c003/s002/prose.md` | `adopted` | 981 | `77b7b414f485c788016a57bfcc839d50ddc6a0e2168c494cc52920f5793cc76e` |
| `artifacts/scenes/v04/c003/s002/scene-card.json` | `adopted` | 2676 | `39f3fe751c15b7da5148c3a6cde1a9657ebe7e84c2a90a23caf3778536cc1a79` |
| `artifacts/scenes/v04/c003/s002/scene-manifest.json` | `adopted` | 1123 | `7741fb1cb257d7ff60f72be6b16fa1fb0d8ee94859c293a12e1393fedbbd0174` |
| `audit/completion/00000051/completion-audit.json` | `audit` | 1760 | `d1fc155cdd6ae8b4efef122478f26232110febde9969c8063ec64f08e2aa947a` |
| `audit/completion/00000051/completion-precondition.json` | `audit` | 2915 | `14e34e2925954464dfd578cb98f6735fd82094722287924070448254f539377c` |
| `audit/publication-gates/pub-000001.json` | `audit` | 1264 | `389718c6e9c495532c4be72afa5fcdc53c132f0f58b6cbb73ce28d36a06cc2d1` |
| `canon/HEAD` | `pointer` | 9 | `d172d87ba813bf4a0525c167d4a7f7e13e10fb41ef285bfc2072b39e29ca1c8e` |
| `canon/generations/00000049/commit-manifest.json` | `adopted` | 1109 | `a6976ba40fdfed5dcfb7ea8e60eb246e1dd01b9703b9d90ca19e25295c49213b` |
| `canon/generations/00000049/evidence-index.json` | `adopted` | 1231 | `63bb02004b1a826a07a4ba67d87fcb950810f1211580834a7883c4c7e53fcb8d` |
| `canon/generations/00000049/generation-manifest.json` | `adopted` | 1261 | `8a2ab173740626531e04bbf0398a88f8bcf0978605d5078301227cf28ca5b0ec` |
| `canon/generations/00000049/story-state.json` | `adopted` | 1955 | `ab9dfca3985e1648b1697061ef2ceb0e582e011a6ebceec32c88a6a626fac661` |
| `canon/generations/00000050/commit-manifest.json` | `adopted` | 1156 | `41d470d4fcee41b468a5bcb5543c23ff8009751b09e383e64ad9d2415a6f2c51` |
| `canon/generations/00000050/evidence-index.json` | `adopted` | 3577 | `0fff74274d9f607e5e2ad13cbcbf0aa87b4ed050f39d46370a2d574f838ca601` |
| `canon/generations/00000050/generation-manifest.json` | `adopted` | 1261 | `fb26c79593bcb669421606cca28287d514d0e2d56477cd3f3d9f68ce01dab614` |
| `canon/generations/00000050/story-state.json` | `adopted` | 1949 | `3135b1a4ae531fe4c47508eebe08bb985ddced32d4aaf6bd87adf685568a61ed` |
| `canon/generations/00000051/commit-manifest.json` | `adopted` | 946 | `00f5028967d25add25c3766dfaa1fe9a7d4836efdfbc726e2227e3b985df7276` |
| `canon/generations/00000051/generation-manifest.json` | `adopted` | 1227 | `86f8e880fe25c9795db84922815af2f0d7d5716fdc0404587e41eb95d17a623c` |
| `canon/generations/00000051/story-state.json` | `adopted` | 1946 | `1800a83ac1e79ecba664622931d50d220ea3ee908c06dbd564d32b9fa3d35ed0` |
| `output/CURRENT` | `pointer` | 11 | `a10eef3a401d11ada9065c2c4c8b862964108feea7e2fb6139e8dfceb37adff8` |
| `plans/volumes/v04/chapters/c003/chapter-design.json` | `adopted` | 3088 | `e4c49e7eca0dbba898abf83613a01092ca66f813b6327cc3a07679af84e0f559` |
| `plans/volumes/v04/volume-design.json` | `adopted` | 3337 | `71c1888a6c3ad4a5a5f5a858646a3c7c66c1474312b4d37d806ddb828a2357cb` |
| `publications/pub-000001/manuscript/series.md` | `adopted` | 11168 | `93848551d0e17c6337ec3631f0a79b3bdf7c9aa6ec0408ce4a0c3ebdc2c9d3d9` |
| `publications/pub-000001/manuscript/v01.md` | `adopted` | 2651 | `f8a695a0a0f3e99ec6d057038c507e4f168ff90ca3b81aeca78a3ae192ccb835` |
| `publications/pub-000001/manuscript/v02.md` | `adopted` | 2666 | `b22c5a2cd080ef1d6e12d4274ffdcf16662c007893da284ae455ecba1457be57` |
| `publications/pub-000001/manuscript/v03.md` | `adopted` | 2434 | `4e04e68f044e9e7ed3879a781fd262e8f5fdaf462e224bbcbde18ea742202c06` |
| `publications/pub-000001/manuscript/v04.md` | `adopted` | 3401 | `9c47815fb581012818190fa463709a4fff7d7006f79d479733be4d1a51c624c9` |
| `publications/pub-000001/publication-manifest.json` | `adopted` | 3006 | `6c29719088bff3d4bba85bd23239a2b082b32233da0cfe38d7a226c95633d30a` |
| `publications/pub-000001/publication-validation.json` | `adopted` | 1893 | `cf151faa6f4dcb656f15d24cbc4111907bfd4f69a7cb49e61529e5f69ce949ea` |
| `publications/pub-000001/reports/completion-audit.json` | `adopted` | 767 | `3b5bdec5edeeb9f3ac1f599a810f571cec0d766898768430a5e4567c2410831f` |
| `runtime/candidates/completion/attempt-01.json` | `candidate_history` | 1561 | `f3ff4b09df9284e3aac6a11cd937728fa157d4c74507d2099902cdc73c42513a` |
| `runtime/candidates/completion/candidate-manifest.json` | `candidate_history` | 1191 | `788df355a47d428f2e32ade22383d7f924a6abd612828bba10e8d9955cbcdb7d` |
| `runtime/candidates/handoffs/v04/v0001/candidate-manifest.json` | `candidate_history` | 1288 | `fa743c5c358f472611285923eb9f329645b495ccf5491d3d13c7909f2868861c` |
| `runtime/candidates/handoffs/v04/v0001/review.json` | `candidate_history` | 711 | `58110ed53daaf485bc18b042320d332d54df83fa7d372ff0cc1d87c85186b482` |
| `runtime/candidates/handoffs/v04/v0001/volume-handoff.json` | `candidate_history` | 2855 | `a3c222245b75ccf794dff27a554cd61e9e297010a3a8b9cc20e1df1f2b1cf70e` |
| `runtime/context-snapshots/comp-audit/completion/5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc.json` | `candidate_history` | 56423 | `5b606fe5ef2aef46c8e640b2fd0e895683db55f798dd1fd389cd9878d99cffcc` |
| `runtime/counters.json` | `runtime_resume` | 611 | `0c7f8d278a6ef82bb3a89da3ae52ce20844370fe22a3956d1fbdacfeec4b7007` |
| `runtime/run-state.json` | `runtime_resume` | 810 | `3d110c7f7138508ac2c0c78af89ec3f886fdac0275d560146de044c942bf8050` |

Fixture inventory SHA-256:

```text
6b22703f77ec89ce49ee12ee95288378b3512a5e905b316de8895363b1c74355
```

# Part VIII: Required negative mutations

## 54. Final Scene and Handoff mutations

```text
EX-NEG-COMP-FIX-001
base: Generation-50 Story state
mutation: leave Thread in_progress/3
expected: Completion precondition or Thread assessment failure

EX-NEG-COMP-FIX-002
base: final Handoff
mutation: disposition = carry_over
expected: final-Volume disposition-matrix failure

EX-NEG-COMP-FIX-003
base: Generation-51 Story state
mutation: increment current_order to 48
expected: Handoff order-preservation failure

EX-NEG-COMP-FIX-004
base: final Handoff Generation
mutation: source_scene_id = v04-c003-s002
expected: volume_handoff conditional-field failure
```

## 55. Completion mutations

```text
EX-NEG-COMP-FIX-005
base: precondition
mutation: add context_snapshot_sha256
expected: noncyclic corrected-Schema unknown-field failure

EX-NEG-COMP-FIX-006
base: Completion response
mutation: criterion assessment = partially_supported while overall = complete
expected: overall-assessment consistency failure

EX-NEG-COMP-FIX-007
base: Completion response
mutation: Thread progress = 3
expected: exact-final-State and assessment failure

EX-NEG-COMP-FIX-008
base: structurally valid overall_assessment = incomplete
mutation: make another Completion attempt
expected: attempt-control failure; no retry permitted
```

## 56. Publication mutations

```text
EX-NEG-COMP-FIX-009
base: payload set
mutation: include publication-validation.json
expected: payload_set_sha256 definition failure

EX-NEG-COMP-FIX-010
base: Publication manifest files
mutation: include publication-manifest.json
expected: self-reference/content-set failure

EX-NEG-COMP-FIX-011
base: finalized Publication
mutation: retain publication-build-manifest.json
expected: exact final-file-set failure

EX-NEG-COMP-FIX-012
base: Gate
mutation: store .staging/publication/pub-000001/publication-manifest.json
expected: rename-stability/path failure

EX-NEG-COMP-FIX-013
base: final Publication directory before CURRENT
mutation: set run_status = completed
expected: adoption/status failure
```

# Part IX: Mechanical validation

## 57. Required checks

```text
47 Scene corpus records and final Scene coordinate
Generation arithmetic 50/51 versus order 47
final Scene Evidence quote uniqueness and code-point offsets
Thread resolved/4 before Handoff
only volume_disposition changes in Handoff Generation
final Handoff HEAD adoption
noncyclic Completion precondition/Context construction
required criterion and Thread assessment coverage
valid complete assessment
private-to-safe Completion report transformation
deterministic manuscript and metadata hashes
payload_set_sha256 excludes Validation/Manifest/build manifest
content_set_sha256 includes Validation and excludes Manifest itself
Gate snapshot rename stability
CURRENT-last adoption
completed Run-state invariants
private sentinel and internal-ID publication scan
```

## 58. Mechanical acceptance conditions

This document is acceptable only when:

```text
all JSON fences parse
all embedded hashes recompute
all relative links resolve
all Evidence slices equal exact quotes
all 47 Scene IDs are unique and ordered
final Scene Generation is 00000050
final Handoff/HEAD Generation is 00000051
current_order and successful_scene_commits are 47

final Handoff changes only volume_disposition
Completion precondition contains no Context hash
Completion Context contains the exact precondition
saved attempt links both hashes
overall complete follows criterion/Thread rules

Publication payload count is exact
Validation payload hash recomputes
Manifest content-set hash recomputes
Manifest lists Validation and not itself
provisional build manifest is absent from final publication
Gate snapshot recomputes before and after rename
output/CURRENT bytes are exact
Run last_completed_stage is OUT-03
```
