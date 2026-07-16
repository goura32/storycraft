"""各依頼単位のプロンプト構築。§5 の LLM への依頼単位に従う。

各関数は (system_prompt, user_prompt, response_format, json_schema_str) を返す。
response_format は {"type": "json_object"} 固定。json_schema_str は依頼文末尾に含める。
"""
from __future__ import annotations

import json
from typing import Any

from .diversity import build_diversity_note


def _fmt(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


RESPONSE_FORMAT = {"type": "json_object"}


# §5 単位1: 全巻計画
def plan_series(brief: dict, diversity_note: str | None) -> tuple[str, str, dict, str]:
    sys_p = (
        "あなたは小説シリーズの構成作家です。与えられた企画から、"
        "読者が最後まで読み進められる完結小説シリーズの全巻計画を作ります。"
        "JSONオブジェクトだけを返してください。説明文は書かないでください。"
    )
    div = f"\n\n{diversity_note}" if diversity_note else ""
    user_p = (
        "次の企画から全巻計画を作ってください。\n\n"
        f"企画:\n{_fmt(brief)}\n"
        "巻数は5巻を第一候補に、4〜10巻から題材と物語の広がりで選んでください。"
        "各巻の章数は6〜10章、各章の場面数は2〜4場面、1場面の本文量は1,800〜2,600字の範囲で、"
        "物語の役割に合わせて選んでください。\n"
        "各巻は少なくとも18場面を持つようにしてください。\n"
        "計画はシリーズの方向、各巻の章数、視点規則だけを決め、章内の場面や本文の細部は決めないでください。"
        f"{div}\n\n"
        "返すJSONの構造:\n"
        "{\n"
        '  "volume_count": 5,\n'
        '  "volumes": [{"number":1,"title":"","role":"","character_changes":"","resolves":"","leaves":"","chapter_count":8,"viewpoint_rule":""}],\n'
        '  "final_resolution": "最終巻で回収する結末",\n'
        '  "series_viewpoint_rule": "語りの形式、視点変更を許す単位、視点人物候補"\n'
        "}"
    )
    schema = (
        "必須: volume_count(int 4-10), volumes(list), final_resolution(str), series_viewpoint_rule(str)\n"
        "volumes 各要素: number(int), title(str), role(str), character_changes(str), "
        "resolves(str), leaves(str), chapter_count(int 6-10), viewpoint_rule(str)"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位2: 登場人物・関係カード
def characters(series_plan: dict, diversity_note: str | None) -> tuple[str, str, dict, str]:
    sys_p = (
        "あなたは小説の登場人物設計者です。与えられた全巻計画から、"
        "主要人物と繰り返し登場する人物のカードと、人物同士の関係カードを作ります。"
        "JSONオブジェクトだけを返してください。"
    )
    div = f"\n\n{diversity_note}" if diversity_note else ""
    user_p = (
        "次の全巻計画から、人物カードと関係カードを作ってください。\n\n"
        f"全巻計画:\n{_fmt(series_plan)}\n"
        "人物カードは、主要・準主要な人物について作ってください（一時登場は除く）。"
        "各カードの id は仮の連番（char-01 等）で返しても構いません。プログラムが正式IDを割り当てます。\n"
        "人物カードには正体・秘密・犯行の真実・恋心の最終告白・回収が必要な約束を直接書かず、"
        "それらは後で伏線台帳へ置きます。\n"
        "関係カードは一組につき一枚、relationship_thread_id は後で付けます（この時点は null でよい）。"
        f"{div}\n\n"
        "返すJSONの構造:\n"
        "{\n"
        '  "characters": [{"id":"char-01","name":"","aliases":[],"role":"","narrative_function":"",'
        '"voice_note":"","behavior_note":"","appearance_cues":"","initial_goal":"","initial_constraint":"",'
        '"current_goal":"","current_pressure":"","current_location":"","current_condition":"","current_knowledge":""}],\n'
        '  "relationships": [{"id":"rel-01","character_a_id":"char-01","character_b_id":"char-02",'
        '"current_state":"","reader_knowledge":"","relationship_thread_id":null}]\n'
        "}"
    )
    schema = (
        "必須: characters(list), relationships(list)\n"
        "characters: id(str), name(str), role(str), narrative_function(str) ほか任意\n"
        "relationships: id(str), character_a_id(str), character_b_id(str), current_state(str)"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位3-5: 各台帳 (world / timeline / threads)
def world_ledger(brief: dict, series_plan: dict, characters: dict) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の世界設計者です。複数場面にまたがるか状態が変わる世界要素を台帳に登録します。JSONオブジェクトだけを返してください。"
    user_p = (
        "次の情報から、世界・場所・組織・重要物の台帳を作ってください。\n\n"
        f"企画: {_fmt(brief)}\n全巻計画: {_fmt(series_plan)}\n人物: {_fmt(characters)}\n"
        "登録対象: 繰り返し登場する場所、組織、重要物、世界の規則、専門用語。"
        "一度だけの背景や秘密の由来（伏線台帳へ回す）は除く。\n"
        "id は仮連番（entity-01 等）で返す。\n"
        "返すJSON: {\"entities\":[{\"id\":\"entity-01\",\"kind\":\"\",\"name\":\"\",\"aliases\":[],"
        "\"stable_fact\":\"\",\"use_or_access_rule\":\"\",\"current_state\":\"\"}]}"
    )
    schema = "必須: entities(list). 各要素: id(str), kind(str), name(str), stable_fact(str)"
    return sys_p, user_p, RESPONSE_FORMAT, schema


def timeline_ledger(brief: dict, series_plan: dict) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の時間軸設計者です。順序や経過時間を誤ると物語が壊れる時点・期限・移動を台帳に登録します。JSONオブジェクトだけを返してください。"
    user_p = (
        "次の情報から、時間・期限台帳を作ってください。\n\n"
        f"企画: {_fmt(brief)}\n全巻計画: {_fmt(series_plan)}\n"
        "登録対象: 移動、締切、回復期間、同時進行する重要出来事。すべての会話や食事は除く。\n"
        "id は仮連番（time-01 等）で返す。\n"
        "返すJSON: {\"timelines\":[{\"id\":\"time-01\",\"kind\":\"\",\"description\":\"\","
        "\"starts_at\":\"\",\"ends_at\":\"\",\"status\":\"\"}]}"
    )
    schema = "必須: timelines(list). 各要素: id(str), kind(str), description(str), status(str)"
    return sys_p, user_p, RESPONSE_FORMAT, schema


def threads_ledger(brief: dict, series_plan: dict, characters: dict,
                   world: dict, timeline: dict) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の伏線設計者です。回収が必要な伏線・重要イベントを先に決めます。JSONオブジェクトだけを返してください。"
    user_p = (
        "次の情報から、伏線・重要イベント台帳を作ってください。\n\n"
        f"企画: {_fmt(brief)}\n全巻計画: {_fmt(series_plan)}\n人物: {_fmt(characters)}\n"
        f"世界台帳: {_fmt(world)}\n時間台帳: {_fmt(timeline)}\n"
        "入れるのは最終的な説明・発見・対決・約束の実現など回収が必要なものだけ。"
        "各項目に導入先（introduce_by）と回収先（resolve_by）を必ず決める。"
        "id は仮連番（thread-01 等）、involved_characters は人物の id（char-01 等）で書く。\n"
        "返すJSON: {\"threads\":[{\"id\":\"thread-01\",\"kind\":\"\",\"importance\":\"主要|補助\","
        "\"description\":\"\",\"core_fact\":\"\",\"involved_characters\":[\"char-01\"],"
        "\"reader_knowledge\":\"\",\"character_knowledge\":\"\",\"presentation_rule\":\"\","
        "\"clue_plan\":\"\",\"must_not_reveal_before\":\"\",\"introduce_by\":\"\",\"resolve_by\":\"\","
        "\"resolution_condition\":\"\",\"status\":\"未導入\"}]}"
    )
    schema = (
        "必須: threads(list). 各要素: id(str), kind(str), importance('主要'|'補助'), "
        "description(str), core_fact(str), involved_characters(list), status('未導入'|'進行中'|'回収済み')"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位6: 巻の章一覧
def volume_chapters(vol_plan: dict, brief: dict, prior_summaries: list,
                    threads: dict, is_final: bool) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の章構成作家です。一巻の章一覧を作ります。JSONオブジェクトだけを返してください。"
    final_note = "最終巻です。台帳で未回収の項目を、まだ書いていない章へ回収先として配置してください。" if is_final else ""
    user_p = (
        f"次の巻計画から、章一覧を作ってください。\n\n巻計画: {_fmt(vol_plan)}\n企画: {_fmt(brief)}\n"
        f"これまでの巻の要約: {_fmt(prior_summaries)}\n未回収台帳: {_fmt(threads)}\n"
        f"{final_note}\n"
        "各章は章の役割、開始状態、終了状態、場面数（2〜4）だけを含める。本文や場面の詳細は含めない。\n"
        "返すJSON: {\"chapters\":[{\"chapter_number\":1,\"title\":\"\",\"purpose\":\"\","
        "\"start_state\":\"\",\"end_state\":\"\",\"scene_count\":3}]}"
    )
    schema = "必須: chapters(list). 各要素: chapter_number(int), title(str), purpose(str), start_state(str), end_state(str), scene_count(int 2-4)"
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位7: 章の場面カード
def scene_cards(chapter: dict, brief: dict, handoff: str, vol_changes: str,
                chapter_threads: dict, is_final_chapter: bool,
                final_condition: str) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の場面設計者です。一章を執筆可能な場面カードに分けます。JSONオブジェクトだけを返してください。"
    final_note = f"最終章です。初回企画の結末条件を必ず反映してください: {final_condition}" if is_final_chapter else ""
    user_p = (
        f"次の章から、場面カードを作ってください。\n\n章: {_fmt(chapter)}\n企画: {_fmt(brief)}\n"
        f"前章の引継ぎ要約: {handoff}\nこの巻で既に起きた変化: {vol_changes}\n"
        f"この章で扱う台帳項目: {_fmt(chapter_threads)}\n{final_note}\n"
        "場面カードは2〜4件。各カードに viewpoint_character（役名）、start_time、end_time、location_id（entity-01 等）、"
        "entity_ids（IDのリスト）、purpose、opening、required_events、characters（役名リスト）、thread_actions"
        "（[{id, action:'導入'|'進展'|'回収'}]）、reader_disclosure、presentation_rules、end_change を含める。\n"
        "返すJSON: {\"scene_cards\":[ ... ]}"
    )
    schema = (
        "必須: scene_cards(list). 各要素: scene_number(int), viewpoint_character(str), "
        "start_time(str), end_time(str), location_id(str), entity_ids(list), purpose(str), "
        "opening(str), required_events(list), characters(list), thread_actions(list), "
        "reader_disclosure(str), presentation_rules(list), end_change(str)"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位8: 場面執筆
def scene_write(card: dict, context: dict) -> tuple[str, str, dict, str]:
    sys_p = (
        "あなたは小説家です。与えられた場面カードと文脈から、自然な日本語で場面本文を書きます。"
        "中国語的な表現や不必要な外来語を避けてください。JSONオブジェクトだけを返してください。"
    )
    # 許可されたIDを文脈から収集して例示に使用
    allowed_threads = [t["id"] for t in context.get("related_threads", [])]
    allowed_entities = [e["id"] for e in context.get("related_entities", [])]
    allowed_timelines = [t["id"] for t in context.get("related_timelines", [])]
    char_ids = [c["id"] for c in context.get("characters", {}).get("characters", [])]
    rel_ids = [r["id"] for r in context.get("characters", {}).get("relationships", [])]
    # カードが参照するIDも追加
    for t in card.get("thread_actions", []):
        if t.get("id") not in allowed_threads:
            allowed_threads.append(t["id"])
    for e in card.get("entity_ids", []):
        if e not in allowed_entities:
            allowed_entities.append(e)
    if card.get("location_id") and card["location_id"] not in allowed_entities:
        allowed_entities.append(card["location_id"])
    # 例示用に最初の1つずつ使用（空ならプレースホルダ）
    ex_thread = allowed_threads[0] if allowed_threads else "thread-XX"
    ex_char = char_ids[0] if char_ids else "char-XX"
    ex_entity = allowed_entities[0] if allowed_entities else "entity-XX"
    ex_timeline = allowed_timelines[0] if allowed_timelines else "time-XX"
    ex_rel = rel_ids[0] if rel_ids else "rel-XX"
    thread_action_enum = "導入|進展|回収"
    char_field_enum = "current_goal|current_pressure|current_location|current_condition|current_knowledge|current_state"
    entity_field_enum = "current_state"
    timeline_status_enum = "進行中|完了|予定|失効"
    user_p = (
        f"次の場面カードから場面本文を書いてください。\n\n場面カード: {_fmt(card)}\n\n"
        f"文脈（視点人物の知識・読者の知識・許可された台帳情報・時刻・場所・人物情報・前場面の引継ぎ要約）:\n{_fmt(context)}\n\n"
        "本文は1,800〜2,600字程度で書いてください。視点人物以外の内心や秘密は、その人物の知識範囲を超えて書かないでください。"
        "情報は行動・対立・会話・観察を通じて示し、地の文だけで説明し続けないでください。\n"
        "返すJSON:\n"
        "{\n"
        f'  "content": "場面本文",\n'
        f'  "handoff_summary": "次の場面に渡す要約",\n'
        f'  "thread_updates": [{{"id":"{ex_thread}","action":"{thread_action_enum}"}}],\n'
        f'  "character_updates": [{{"character_id":"{ex_char}","field":"{char_field_enum}","value":""}}],\n'
        f'  "relationship_updates": [{{"relationship_id":"{ex_rel}","new_state":""}}],\n'
        f'  "entity_updates": [{{"entity_id":"{ex_entity}","field":"{entity_field_enum}","value":""}}],\n'
        f'  "timeline_updates": [{{"timeline_id":"{ex_timeline}","status":"{timeline_status_enum}","actual_scene":"volume-01/chapter-01/scene-01"}}]\n'
        "}\n"
        "※ 上記のIDは例示です。必ず文脈で許可された実在IDのみを使用してください。\n"
    )
    schema = (
        "必須: content(str), handoff_summary(str), thread_updates(list), character_updates(list), "
        "relationship_updates(list), entity_updates(list), timeline_updates(list)\n"
        f"thread_updates: id(str), action('{thread_action_enum}')\n"
        f"character_updates: character_id(str), field('{char_field_enum}'), value(str)\n"
        f"entity_updates: entity_id(str), field('{entity_field_enum}'), value(str)\n"
        f"timeline_updates: timeline_id(str), status('{timeline_status_enum}'), actual_scene(str)\n"
        "※ 許可されていないID、不正なenum値は検証で拒否されます。"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位8b / 単位9: 改善パス / 巻要約
def improve(current: dict, card: dict, directions: list) -> tuple[str, str, dict, str]:
    sys_p = "あなたは文章の改善者です。与えられた場面本文を、同じJSON構造で改善します。JSONオブジェクトだけを返してください。"
    user_p = (
        f"次の場面本文（草稿）を改善してください。\n\n草稿: {_fmt(current)}\n場面カード: {_fmt(card)}\n"
        f"改善の方向: {_fmt(directions)}\n"
        "草稿を床として、計測可能な軸で悪化しない範囲で改善してください。"
        "本文・handoff_summary・各更新のJSON構造はそのまま維持してください。\n"
        "返すJSONは草稿と同じ構造で返してください。"
    )
    schema = (
        "必須: content(str), handoff_summary(str), thread_updates(list), character_updates(list), "
        "relationship_updates(list), entity_updates(list), timeline_updates(list)"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


def volume_summary(chapters_handoffs: list, series_plan: dict) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の要約者です。一巻の短い要約を作ります。JSONオブジェクトだけを返してください。"
    user_p = (
        f"次の各章の最後の引継ぎ要約から、一巻の短い要約を作ってください。\n\n"
        f"引継ぎ要約: {_fmt(chapters_handoffs)}\n全巻計画: {_fmt(series_plan)}\n"
        "次巻へ渡すため、人物関係の現在地、未解決の問い、重要な事実だけを含めてください。\n"
        "返すJSON: {\"volume_summary\":\"\", \"unresolved_questions\":[], \"character_relations\":\"\"}"
    )
    schema = "必須: volume_summary(str), unresolved_questions(list), character_relations(str)"
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §5 単位10: 完結前確認
def closure_check(threads: dict, scene_updates: list, handoffs: list) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の監査者です。主要伏線がすべて回収されたか確認します。JSONオブジェクトだけを返してください。"
    user_p = (
        f"次の台帳の主要項目が、対応する場面で回収されたか確認してください。\n\n"
        f"台帳: {_fmt(threads)}\n場面ごとの台帳更新: {_fmt(scene_updates)}\n引継ぎ要約: {_fmt(handoffs)}\n"
        "主要項目（importance='主要'）ごとに、回収した場面番号、または未回収を返してください。\n"
        "返すJSON: {\"results\":[{\"thread_id\":\"thread-01\",\"status\":\"回収済み|未回収\",\"scene\":\"\"}]}"
    )
    schema = "必須: results(list). 各要素: thread_id(str), status('回収済み'|'未回収'), scene(str)"
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §3.13 二段階改善: 批評
def critique(current: dict, card: dict, directions: list) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説の批評家です。与えられた場面本文の問題点を抽出し、改善提案を出します。JSONオブジェクトだけを返してください。"
    user_p = (
        f"次の場面本文（草稿）を批評してください。\n\n草稿: {_fmt(current)}\n場面カード: {_fmt(card)}\n"
        f"改善の方向: {_fmt(directions)}\n"
        "以下の観点で問題点を列挙してください:\n"
        "- 日本語として自然か（中国語的表現・不要な外来語の混入・用語の揺れ）\n"
        "- 視点人物・読者への開示範囲・秘密の隠し方を守っているか\n"
        "- 人物の話し方と一貫した行動を保っているか\n"
        "- 情報は行動・対立・会話・観察を通じて示され、地の文だけで説明していないか\n"
        "- 必須イベントが含まれているか\n"
        "- 文字数は目安帯（1,800〜2,600字）に収まっているか\n"
        "返すJSON:\n"
        "{\n"
        '  "issues": [{"severity": "致命的|重要|軽微", "category": "台詞|地文|構成|情報制御|その他", '
        '"location": "該当箇所の目安", "problem": "何が問題か", "suggestion": "どう直すべきか"}],\n'
        '  "overall_assessment": "全体的な所見（良い点・悪い点の要約")}\n'
    )
    schema = (
        "必須: issues(list), overall_assessment(str)\n"
        "issues 各要素: severity('致命的'|'重要'|'軽微'), category(str), location(str), problem(str), suggestion(str)\n"
        "issues は空配列可"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema


# §3.13 二段階改善: 修正
def fix(current: dict, critique_result: dict, card: dict, directions: list) -> tuple[str, str, dict, str]:
    sys_p = "あなたは小説家です。批評結果に従って場面本文を修正します。同じJSON構造で返してください。JSONオブジェクトだけを返してください。"
    user_p = (
        f"次の場面本文（草稿）を、批評結果に従って修正してください。\n\n草稿: {_fmt(current)}\n批評結果: {_fmt(critique_result)}\n"
        f"場面カード: {_fmt(card)}\n改善の方向: {_fmt(directions)}\n"
        "草稿を床として、計測可能な軸で悪化しない範囲で修正してください。\n"
        "本文・handoff_summary・各更新のJSON構造はそのまま維持してください。\n"
        "批評で指摘された問題点を優先的に解決し、構造項目（ID・enum・必須項目）は絶対に変更しないでください。\n"
        "返すJSONは草稿と同じ構造で返してください。"
    )
    schema = (
        "必須: content(str), handoff_summary(str), thread_updates(list), character_updates(list), "
        "relationship_updates(list), entity_updates(list), timeline_updates(list)\n"
        "※ 批評で指摘された問題を解消し、構造・ID・enumは変更しないこと"
    )
    return sys_p, user_p, RESPONSE_FORMAT, schema
