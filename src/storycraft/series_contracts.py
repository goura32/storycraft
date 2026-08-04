"""現行V1の共通例外。"""
from __future__ import annotations


class ContractError(ValueError):
    """利用者入力または生成結果が現行V1契約を満たさない。"""


class LLMCallError(ContractError):
    """設定済みretry後もLLM呼び出しに成功しなかった。"""
