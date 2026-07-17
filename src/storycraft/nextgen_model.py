"""次世代実行系のOpenAI互換JSONモデル。"""
from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient
from .nextgen import ContractError


_STAGE_CONTRACTS = {
    "plan": """出力スキーマ:
{
  "volumes": [
    {
      "number": "1から始まる連番の整数",
      "title": "その巻だけの内容を表す空でない巻題",
      "chapters": [{"number": "1から始まる連番の整数", "title": "空でない章題"}],
      "change": "この巻で読者が得る変化または独立した区切りを表す空でない説明",
      "leaves_question": "最終巻以外では次巻を読みたくなる未解決の問い。最終巻では空文字列でよい"
    }
  ]
}
制約:
- volumes は依頼された巻数と完全に一致させる。指定がない場合も4〜10巻にする。brief.chapters_per_volume がある場合、巻番号 n の chapters は配列の n 番目の数と完全に一致させる。
- 各巻に少なくとも1章を置き、number と chapters[].number は欠番・重複なしの連番にする。
- title と chapter title を他の巻・章と混同しない。
- change は出来事の羅列ではなく、その巻の読了後に成立する変化または区切りを書く。
- 最終巻以外の leaves_question は、まだ解決していない問いにする。最終巻で結末を先延ばしにしない。""",
    "scene_card": """出力スキーマ:
{
  "scene_id": "入力の scene_id と完全一致する文字列",
  "visible_thread_ids": ["この場面で参照してよい入力 available_thread_ids のID"],
  "allowed_update_ids": ["この場面で status 更新してよい visible_thread_ids のID"]
}
制約:
- scene_id は新規作成・変更・推測しない。
- 配列には入力で提示されたIDだけを入れ、未知IDを作らない。
- allowed_update_ids は visible_thread_ids の部分集合にする。
- 可視化は本文で扱う主要な問いに限り、更新許可はこの場面で実際に進展または回収する問いに限る。
- 入力 is_final_scene が true のとき、unresolved_thread_ids の全IDを visible_thread_ids と allowed_update_ids に含める。最終場面でないときは未回収の問いを一括回収する許可を広げない。""",
    "scene": """出力スキーマ:
{
  "content": "完成した日本語小説本文。約500〜5000字を目安とし、注釈・箇条書き・Markdown・執筆メモを混ぜない",
  "handoff_summary": "次の場面の執筆者が使う、実際に本文で起きた事実・終点・未解決点だけの空でない引継ぎ要約",
  "state_updates": [{"id": "card.allowed_update_ids にあるID", "status": "open | in_progress | resolved"}]
}
制約:
- content は入力の brief、plan、card、可視の台帳状態と矛盾させない。本文外の説明を出さない。
- handoff_summary は本文を切り捨てず、次場面に必要な変化と未解決点を具体的に記す。本文にない人物、設定、期間、出来事、次場面の予測、計画、解釈を足さない。各文は本文中の出来事・終点・未解決点だけに根拠を置く。
- state_updates は card.allowed_update_ids にあるIDだけを使い、各 status はその問いが本文で未着手・進展中・回収済みのどれかに対応させる。本文で直接答えや回収が描かれた時だけ resolved にし、本文に新しい進展がない既に resolved のIDを in_progress へ戻さない。
- 許可されていない問いを解決・更新したと主張しない。
- 入力 is_final_scene が true のとき、required_ending を本文で到達済みにし、required_resolved_ids の各IDを本文事実に基づいて resolved へ更新する。次場面への予告や未確定の結末を handoff_summary に残さない。""",
    "closure": """出力スキーマ:
{
  "resolved_ids": ["入力 threads にある全IDを一度ずつ"],
  "ending_reached": "初回企画の ending が実際に到達済みなら true、そうでなければ false"
}
制約:
- resolved_ids は入力 threads の全IDと完全一致させる。IDの追加、欠落、重複、別名は不可。
- ending_reached は希望や予定ではなく、採用済み場面の状態に基づいて判定する。
- 未回収の問いがあれば、それを resolved_ids に入れたり ending_reached を true にしたりしない。""",
}


_CRITIQUE_CONTRACT = """出力スキーマ:
{
  "issues": [
    {
      "severity": "critical | major | minor",
      "field": "問題のある出力フィールド名またはJSONパス",
      "description": "入力契約・ID・状態・結末条件に照らした具体的な問題",
      "suggestion": "次の修正工程がそのまま適用できる具体的な修正指示"
    }
  ]
}
制約:
- 問題がなければ issues は空配列にする。
- 称賛、点数、出版可否、曖昧な感想は出力しない。
- 候補に存在しない問題を作らず、入力と候補から確認できる契約違反だけを挙げる。
- 本文、要約、計画、issues の説明と提案は自然な日本語だけで書く。簡体字・中国語・不自然な外国語混じり、明白な誤字、人称の混乱を発見したら、対象フィールドの issue として報告する。
- issues の各要素は severity、field、description、suggestion の四つのキーを一度ずつ必ず持つ。severity にフィールド名を入れず、field に重大度を入れない。四つのキーを満たせない指摘は捨て、issues を空配列にする。"""


class OpenAIStoryModel:
    """既存の接続設定を使い、次世代の工程契約だけをLLMへ渡す。"""

    def __init__(self, settings, raw_dir) -> None:
        self.client = LLMClient(settings, raw_dir)
        self.attempt = 0

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        contract = _STAGE_CONTRACTS.get(stage)
        if contract is None:
            raise ContractError(f"未知の生成工程です: {stage}")
        return self._call("generate", stage, f"{self._goal(stage)}\n\n{contract}", context)

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        contract = _STAGE_CONTRACTS[stage]
        instruction = (
            f"{stage} の候補を批評する。候補の出力契約と入力状態を照合し、"
            "修正可能な契約違反だけを抽出する。\n\n"
            f"候補が満たすべき契約:\n{contract}\n\n{_CRITIQUE_CONTRACT}"
        )
        return self._call("critique", stage, instruction, {"candidate": candidate, "context": context})

    def revise(
        self,
        stage: str,
        candidate: dict[str, Any],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        contract = _STAGE_CONTRACTS[stage]
        instruction = (
            f"{stage} の候補を批評 issues に従って修正する。"
            "指摘されていない正しい値、ID、順序、本文事実を失わない。\n\n"
            f"修正版が満たすべき契約:\n{contract}"
        )
        return self._call("revise", stage, instruction, {"candidate": candidate, "critique": critique, "context": context})

    @staticmethod
    def _goal(stage: str) -> str:
        return {
            "plan": "初回企画を、各巻が役割を持つ全巻計画へ変換する。",
            "scene_card": "一つの場面で参照・更新を許可する主要な問いを最小集合で決める。",
            "scene": "許可済みの場面カードを小説本文、引継ぎ、状態更新という不可分な成果物へ変換する。",
            "closure": "採用済みの台帳状態だけから、主要な問いと結末の完結可否を判定する。",
        }[stage]

    def _call(self, kind: str, stage: str, instruction: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error = ""
        attempts = int(self.client.settings.retry.get("max_attempts", 1))
        for _ in range(max(attempts, 1)):
            self.attempt += 1
            messages = [
                {"role": "system", "content": "あなたはStorycraftの小説生成工程です。JSONオブジェクトだけを返してください。人間向けの文字列値は、固有名・引用・ID以外を自然な日本語で書き、簡体字や中国語を混ぜないでください。"},
                {"role": "user", "content": f"{instruction}\n\n入力:\n{json.dumps(payload, ensure_ascii=False)}"},
                {"__kind": kind, "__phase": stage, "__ref": stage, "__attempt": self.attempt},
            ]
            record = self.client.call_once(messages, {"type": "json_object"}, self.attempt)
            self.client.save_raw(record, messages)
            if record.error:
                last_error = record.error
                continue
            try:
                value = json.loads(record.content)
            except json.JSONDecodeError:
                last_error = "JSONを返しませんでした"
                continue
            if isinstance(value, dict):
                return value
            last_error = "JSONオブジェクトを返しませんでした"
        raise ContractError(f"{stage} の生成に失敗しました: {last_error}")
