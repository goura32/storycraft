"""各依頼単位のプロンプト構築。テンプレートファイルから構築する版。"""

from __future__ import annotations

from .prompt_template import get_template_loader

RESPONSE_FORMAT = {"type": "json_object"}


def _loader():
    return get_template_loader()


# §5 単位1: 全巻計画
def plan_series(brief: dict, diversity_note: str | None) -> tuple[str, str, dict, str]:
    loader = _loader()
    div = diversity_note or ""
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "plan", brief=brief, diversity_note=div)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "plan")


# §5 単位2: 登場人物・関係カード
def characters(series_plan: dict, diversity_note: str | None) -> tuple[str, str, dict, str]:
    loader = _loader()
    div = diversity_note or ""
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "characters", series_plan=series_plan, diversity_note=div)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "characters")


# §5 単位3: 世界台帳
def world_ledger(brief: dict, series_plan: dict, characters: dict) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "world", brief=brief, series_plan=series_plan, characters=characters)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "world")


# §5 単位4: 時間・期限台帳
def timeline_ledger(brief: dict, series_plan: dict) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "timeline", brief=brief, series_plan=series_plan)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "timeline")


# §5 単位5: 伏線・重要イベント台帳
def threads_ledger(brief: dict, series_plan: dict, characters: dict,
                   world: dict, timeline: dict) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "threads", brief=brief, series_plan=series_plan,
                                characters=characters, world=world, timeline=timeline)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "threads")


# §5 単位6: 巻の章一覧
def volume_chapters(vol_plan: dict, brief: dict, prior_summaries: list,
                    threads: dict, is_final: bool) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "volume_chapters", vol_plan=vol_plan, brief=brief,
                                prior_summaries=prior_summaries, threads=threads, is_final=is_final)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "volume_chapters")


# §5 単位7: 章の場面カード
def scene_cards(chapter: dict, brief: dict, handoff: str, vol_changes: str,
                chapter_threads: dict, is_final_chapter: bool,
                final_condition: str) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "scene_cards", chapter=chapter, brief=brief,
                                handoff=handoff, vol_changes=vol_changes,
                                chapter_threads=chapter_threads, is_final_chapter=is_final_chapter,
                                final_condition=final_condition)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "scene_cards")


# §5 単位8: 場面執筆
def scene_write(card: dict, context: dict) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "scene_write", card=card, context=context)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "scene_write")


# §5 単位9: 巻要約
def volume_summary(chapters_handoffs: list, series_plan: dict) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "volume_summary", chapters_handoffs=chapters_handoffs,
                                series_plan=series_plan)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "volume_summary")


# §5 単位10: 完結前確認
def closure_check(threads: dict, scene_updates: list, handoffs: list) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "closure_check", threads=threads,
                                scene_updates=scene_updates, handoffs=handoffs)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", "closure_check")


# §3.13 二段階改善: 批評（汎用版・全ステージ対応）
def critique(current: dict, card: dict, directions: list, stage: str) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("critique", stage, current=current, card=card, improvement_directions=directions)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("critique", stage)


# §3.13 二段階改善: 修正（汎用版・全ステージ対応）
def fix(current: dict, critique_result: dict, card: dict, directions: list, stage: str) -> tuple[str, str, dict, str]:
    loader = _loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("fix", stage, current=current, critique_result=critique_result,
                                card=card, improvement_directions=directions)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema_text("generate", stage)