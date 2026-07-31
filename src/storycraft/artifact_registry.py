"""V2 成果物の種類、ID、保存先、selection slot を一箇所で対応付ける。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

from .series_contracts import ContractError


_COORDINATE_PATTERNS = {
    "volume": r"v(?P<volume>[0-9]{2})",
    "chapter": r"v(?P<volume>[0-9]{2})-c(?P<chapter>[0-9]{2})",
    "scene": r"v(?P<volume>[0-9]{2})-c(?P<chapter>[0-9]{2})-s(?P<scene>[0-9]{2})",
}
_COUNTER = r"(?P<counter>[0-9]{6})"


@dataclass(frozen=True)
class ArtifactSpec:
    """一つの採用済み V2 成果物の正規 ID・配置・slot 規則。"""

    id_pattern: str
    directory_root: str
    slot_pattern: str | None

    def match_id(self, artifact_id: object) -> re.Match[str]:
        if not isinstance(artifact_id, str):
            raise ContractError("artifact_idが文字列ではありません")
        match = re.fullmatch(self.id_pattern, artifact_id)
        if match is None:
            raise ContractError("artifact_kindとartifact_idが一致しません")
        for name in ("volume", "chapter", "scene", "counter"):
            raw = match.groupdict().get(name)
            if raw is not None and int(raw) < 1:
                raise ContractError("artifact_idの座標または通番は1以上でなければなりません")
        return match

    def directory_for(self, artifact_id: object) -> Path:
        self.match_id(artifact_id)
        assert isinstance(artifact_id, str)
        return Path(self.directory_root) / artifact_id

    def slot_for(self, artifact_id: object) -> str:
        match = self.match_id(artifact_id)
        values = match.groupdict()
        if self.slot_pattern is None:
            raise ContractError("このartifact_kindのslotはIDだけから決まりません")
        return self.slot_pattern.format(**values)


# `artifact_kind` を唯一の入口にして、ID、保存ディレクトリ、logical slot を同時に決める。
# coordinate IDs は仕様通りハイフンで各座標を分け、末尾に6桁通番を持つ。
ARTIFACT_SPECS: Mapping[str, ArtifactSpec] = MappingProxyType({
    "request": ArtifactSpec(rf"request-{_COUNTER}", "inputs", "request"),
    "keywords": ArtifactSpec(rf"keywords-{_COUNTER}", "inputs", "keywords"),
    "settings": ArtifactSpec(rf"settings-{_COUNTER}", "runtime/settings", "settings"),
    "initial-design": ArtifactSpec(rf"initial-design-{_COUNTER}", "design/initial", "initial_design"),
    "series-plan": ArtifactSpec(rf"series-plan-{_COUNTER}", "design/series-plans", "series_plan"),
    "volume-plan": ArtifactSpec(rf"volume-plan-{_COORDINATE_PATTERNS['volume']}-{_COUNTER}", "design/volume-plans", "volume_plan.v{volume}"),
    "chapter-plan": ArtifactSpec(rf"chapter-plan-{_COORDINATE_PATTERNS['chapter']}-{_COUNTER}", "design/chapter-plans", "chapter_plan.v{volume}.c{chapter}"),
    "scene-plan": ArtifactSpec(rf"scene-plan-{_COORDINATE_PATTERNS['scene']}-{_COUNTER}", "design/scene-plans", "scene_plan.v{volume}.c{chapter}.s{scene}"),
    "scene-card": ArtifactSpec(rf"scene-card-{_COORDINATE_PATTERNS['scene']}-{_COUNTER}", "design/scene-cards", "scene_card.v{volume}.c{chapter}.s{scene}"),
    "scene-prose": ArtifactSpec(rf"scene-{_COORDINATE_PATTERNS['scene']}-{_COUNTER}", "scenes", "scene_prose.v{volume}.c{chapter}.s{scene}"),
    "continuity-update": ArtifactSpec(rf"continuity-{_COORDINATE_PATTERNS['scene']}-{_COUNTER}", "scenes", "continuity_update.v{volume}.c{chapter}.s{scene}"),
    "generation": ArtifactSpec(rf"gen-{_COUNTER}", "generations", "current_state"),
    "scene": ArtifactSpec(rf"scene-artifact-{_COORDINATE_PATTERNS['scene']}-{_COUNTER}", "scenes", "scene.v{volume}.c{chapter}.s{scene}"),
    "scene-commit": ArtifactSpec(rf"scene-commit-{_COORDINATE_PATTERNS['scene']}-{_COUNTER}", "scenes", "scene_commit.v{volume}.c{chapter}.s{scene}"),
    "selection": ArtifactSpec(rf"selection-{_COUNTER}", "runtime/selections", None),
    "adoption": ArtifactSpec(rf"adoption-{_COUNTER}", "runtime/adoptions", None),
    "volume-publication": ArtifactSpec(rf"volume-pub-{_COORDINATE_PATTERNS['volume']}-{_COUNTER}", "publications", "volume_publication.v{volume}"),
    "quality-disposition": ArtifactSpec(rf"quality-{_COUNTER}", "quality", None),
})


def artifact_spec(artifact_kind: object) -> ArtifactSpec:
    """未知の kind を許さず、その V2 registry entry を返す。"""
    if not isinstance(artifact_kind, str) or artifact_kind not in ARTIFACT_SPECS:
        raise ContractError("未知のartifact_kindです")
    return ARTIFACT_SPECS[artifact_kind]


def artifact_directory(artifact_kind: object, artifact_id: object) -> Path:
    """成果物ディレクトリの workspace 相対パスを返す。"""
    return artifact_spec(artifact_kind).directory_for(artifact_id)



def canonical_slot(artifact_kind: object, artifact_id: object) -> str:
    """ID の座標・通番から一意な canonical logical slot を作る。"""
    return artifact_spec(artifact_kind).slot_for(artifact_id)


def validate_artifact_reference(artifact_kind: object, artifact_id: object, slot: object) -> None:
    """kind、ID、slot を同時に検証する。内容 payload はここでは扱わない。"""
    spec = artifact_spec(artifact_kind)
    if artifact_kind == "quality-disposition":
        spec.match_id(artifact_id)
        slot_str = str(slot) if isinstance(slot, str) else ""
        if not slot_str.startswith("scene_prose_disposition.") and not slot_str.startswith("continuity_disposition."):
            raise ContractError("quality-dispositionのslotが不正です")
        return
    if artifact_kind == "adoption":
        spec.match_id(artifact_id)
        if not isinstance(slot, str) or re.fullmatch(r"(?:initial_design|series_plan|volume_plan|chapter_plan|scene_plan|scene_card|scene_prose|continuity)_adoption(?:\.v[0-9]{2}(?:\.c[0-9]{2})?(?:\.s[0-9]{2})?)?", slot) is None:
            raise ContractError("adoptionのslotが不正です")
        return
    # Special sentinel slots that don't match the canonical pattern but are valid for this kind.
    special_sentinels: dict[str, set[str]] = {
        "volume-plan": {"prior_volume_plan"},
        "generation": {"current_state"},
    }
    expected = spec.slot_for(artifact_id)
    if not isinstance(slot, str):
        raise ContractError("artifact_kind、artifact_id、slotが一致しません")
    if slot != expected and slot not in special_sentinels.get(str(artifact_kind), set()):
        raise ContractError("artifact_kind、artifact_id、slotが一致しません")
