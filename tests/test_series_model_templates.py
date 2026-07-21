"""実送信promptがbrief/Canon/volume_map契約を使うことを確認する。"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import unittest
from unittest.mock import patch

from storycraft import cli
from storycraft.llm import CallRecord, LLMClient
from storycraft.prompt_template import get_template_loader
from storycraft.series_contracts import LLMCallError
from storycraft.series_model import OpenAIStoryModel


STAGES = [
    "brief", "characters", "relationships", "world", "timeline", "threads", "volume_map",
    "volume_chapters", "scene_card", "scene", "continuity", "volume_summary", "closure",
]


class _CapturingClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(retry={"max_attempts": 1})
        self.messages: list[dict] | None = None

    def call_once(self, messages: list[dict], _response_format: dict, _seed: int) -> CallRecord:
        self.messages = messages
        return CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content='{}')

    def save_raw(self, _record: CallRecord, _messages: list[dict]) -> None:
        pass


class _SequenceClient:
    def __init__(self, records: list[CallRecord]) -> None:
        self.settings = SimpleNamespace(retry={"max_attempts": len(records)})
        self.records = records
        self.calls = 0
        self.raw_saves = 0
        self.messages: list[list[dict]] = []

    def call_once(self, _messages: list[dict], _response_format: dict, _seed: int) -> CallRecord:
        self.messages.append(_messages)
        record = self.records[self.calls]
        self.calls += 1
        return record

    def save_raw(self, _record: CallRecord, _messages: list[dict]) -> None:
        self.raw_saves += 1


class _TemplateLoader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def render_system(self) -> str:
        return "JINJAでレンダリングされたsystemプロンプト"

    def load_schema_text(self, category: str, stage: str) -> str:
        return f"外部スキーマ:{category}/{stage}"

    def render_user(self, kind: str, template_stage: str, **kwargs: object) -> str:
        self.calls.append((kind, template_stage, kwargs))
        return "JINJAでレンダリングされたbriefプロンプト"


class SeriesEngineModelTemplateTests(unittest.TestCase):
    def test_generate_brief_renders_stage_template_as_sent_user_prompt(self) -> None:
        client = _CapturingClient()
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = client
        model.attempt = 0
        loader = _TemplateLoader()

        with patch("storycraft.series_model.get_template_loader", return_value=loader):
            model.generate("brief", {"keywords": ["霧の島"]})

        self.assertEqual(
            loader.calls,
            [("generate", "brief", {"stage": "brief", "context": {"keywords": ["霧の島"]}, "output_schema": "外部スキーマ:generate/brief"})],
        )
        self.assertEqual(client.messages[1]["content"], "JINJAでレンダリングされたbriefプロンプト")

    def test_continuity_evidence_contract_requires_verbatim_scene_substrings(self) -> None:
        prompt = (Path("templates/prompts/user/continuity/generate_continuity.j2").read_text(encoding="utf-8"))
        schema = (Path("templates/prompts/schemas/continuity.json").read_text(encoding="utf-8"))
        self.assertIn("evidence in scene.content", prompt)
        self.assertNotIn("引用または要約", prompt)
        self.assertIn("scene.content からそのままコピーした連続文字列", schema)

    def test_brief_critique_prompt_requires_one_complete_issue_object(self) -> None:
        prompt = Path("templates/prompts/user/brief/critique_brief.j2").read_text(encoding="utf-8")
        self.assertIn("issueごとに必ず4キーを同じobject内に置く", prompt)
        self.assertIn("閉じる前に各issue objectの4キー", prompt)

    def test_scene_card_prompt_requires_the_context_time_floor(self) -> None:
        prompt = Path("templates/prompts/user/scene_card/generate_scene_card.j2").read_text(encoding="utf-8")
        self.assertIn("same_volume_time_floor", prompt)
        self.assertIn("allowed_start_time_ids", prompt)

    def test_scene_card_templates_bind_events_to_input_facts_and_prior_scene(self) -> None:
        generate = Path("templates/prompts/user/scene_card/generate_scene_card.j2").read_text(encoding="utf-8")
        critique = Path("templates/prompts/user/scene_card/critique_scene_card.j2").read_text(encoding="utf-8")
        revision = Path("templates/prompts/user/scene_card/revision_scene_card.j2").read_text(encoding="utf-8")
        for prompt in (generate, critique, revision):
            self.assertIn("previous_scene_content", prompt)
            self.assertIn("入力に根拠のない", prompt)
        self.assertIn("required_thread_actions", critique)

    def test_continuity_templates_prohibit_future_handoff_forecasts(self) -> None:
        for path in (
            "templates/prompts/user/continuity/generate_continuity.j2",
            "templates/prompts/user/continuity/critique_continuity.j2",
        ):
            prompt = Path(path).read_text(encoding="utf-8")
            self.assertIn("将来の出来事の予告", prompt)
            self.assertIn("そのままコピー", prompt)

    def test_scene_templates_forbid_unrooted_details_and_require_candidate_grounding(self) -> None:
        generate = Path("templates/prompts/user/scene/generate_scene.j2").read_text(encoding="utf-8")
        critique = Path("templates/prompts/user/scene/critique_scene.j2").read_text(encoding="utf-8")
        self.assertIn("入力に根拠のない固有の制度", generate)
        self.assertIn("候補本文に実在する文字列", critique)

    def test_initial_ledger_prompts_prohibit_unsupported_state_expansion_and_require_detection(self) -> None:
        brief_critique = Path("templates/prompts/user/brief/critique_brief.j2").read_text(encoding="utf-8")
        characters_generate = Path("templates/prompts/user/characters/generate_characters.j2").read_text(encoding="utf-8")
        characters_critique = Path("templates/prompts/user/characters/critique_characters.j2").read_text(encoding="utf-8")
        relationships_generate = Path("templates/prompts/user/relationships/generate_relationships.j2").read_text(encoding="utf-8")
        relationships_critique = Path("templates/prompts/user/relationships/critique_relationships.j2").read_text(encoding="utf-8")
        self.assertIn("居住状態・継続行為・頻度", brief_critique)
        self.assertIn("入力にない具体的な事実を補わない", characters_generate)
        self.assertIn("入力にない固有の事実", characters_critique)
        self.assertIn("双方に共通する内面・共同目的", relationships_generate)
        self.assertIn("双方に共通する内面・共同目的", relationships_critique)

    def test_world_critique_prompt_forbids_input_state_field_paths(self) -> None:
        prompt = Path("templates/prompts/user/world/critique_world.j2").read_text(encoding="utf-8")
        self.assertIn("候補のrootは `entities`", prompt)
        self.assertIn("入力状態の `brief` / `characters` / `relationships` をfieldに使わない", prompt)

    def test_threads_critique_prompt_documents_quoted_id_key_paths(self) -> None:
        prompt = Path("templates/prompts/user/threads/critique_threads.j2").read_text(encoding="utf-8")
        self.assertIn('character_knowledge["char-0004"]', prompt)
        self.assertIn('"field": "threads[0].character_knowledge[\\"char-0004\\"]"', prompt)
        self.assertIn("ハイフンを含む辞書キー", prompt)

    def test_initial_ledger_critique_and_revision_templates_are_evidence_bounded(self) -> None:
        stages = ("brief", "characters", "relationships", "world", "timeline", "threads")
        for stage in stages:
            with self.subTest(stage=stage):
                generate = Path(f"templates/prompts/user/{stage}/generate_{stage}.j2").read_text(encoding="utf-8")
                critique = Path(f"templates/prompts/user/{stage}/critique_{stage}.j2").read_text(encoding="utf-8")
                revision = Path(f"templates/prompts/user/{stage}/revision_{stage}.j2").read_text(encoding="utf-8")
                if stage != "brief":
                    self.assertIn("入力に根拠のない", generate)
                self.assertIn("候補に実在する文字列", critique)
                self.assertIn("全string field", critique)
                self.assertIn("引用されたfieldだけを修正", revision)

    def test_volume_chapter_templates_preserve_volume_action_allocation(self) -> None:
        templates = [
            Path("templates/prompts/user/volume_chapters/generate_volume_chapters.j2").read_text(encoding="utf-8"),
            Path("templates/prompts/user/volume_chapters/critique_volume_chapters.j2").read_text(encoding="utf-8"),
            Path("templates/prompts/user/volume_chapters/revision_volume_chapters.j2").read_text(encoding="utf-8"),
        ]
        for prompt in templates:
            self.assertIn("thread_targets", prompt)
            self.assertIn("作者真実", prompt)

    def test_scene_card_templates_allow_updates_only_for_characters_and_major_threads(self) -> None:
        templates = [
            Path("templates/prompts/user/scene_card/generate_scene_card.j2"),
            Path("templates/prompts/user/scene_card/revision_scene_card.j2"),
            Path("templates/prompts/user/scene_card/critique_scene_card.j2"),
        ]
        for template in templates:
            with self.subTest(template=template.name):
                contents = template.read_text(encoding="utf-8")
                self.assertIn("char-XXXX", contents)
                self.assertIn("thread-XXXX", contents)
                self.assertIn("entity-XXXX", contents)
        schema = Path("templates/prompts/schemas/scene_card.json").read_text(encoding="utf-8")
        self.assertIn("char-XXXX", schema)
        self.assertIn("thread-XXXX", schema)
        self.assertIn("entity/time/relationship IDは含めない", schema)

    def test_attempt_counter_restarts_for_each_llm_operation(self) -> None:
        client = _SequenceClient([
            CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content="{}"),
            CallRecord(kind="critique", phase="brief", ref="brief", attempt=2, seed=2, content="{}"),
        ])
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = client
        model.attempt = 0
        model.set_log_ref("v:1/4 c:1/1 s:1/1")
        model._call("generate", "brief", "prompt")
        model._call("critique", "brief", "prompt")
        attempts = [next(message["__attempt"] for message in messages if "__attempt" in message) for messages in client.messages]
        refs = [next(message["__ref"] for message in messages if "__ref" in message) for messages in client.messages]
        self.assertEqual(attempts, [1, 1])
        self.assertEqual(refs, ["v:1/4 c:1/1 s:1/1", "v:1/4 c:1/1 s:1/1"])

    def test_call_exhaustion_raises_llm_call_error_for_transport_and_non_object_json(self) -> None:
        scenarios = {
            "transport": [
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, error="ConnectionError: offline"),
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, error="ConnectionError: offline"),
            ],
            "non_object_json": [
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content="[]"),
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, content="[]"),
            ],
        }
        for name, records in scenarios.items():
            with self.subTest(name=name):
                client = _SequenceClient(records)
                model = OpenAIStoryModel.__new__(OpenAIStoryModel)
                model.client = client
                model.attempt = 0
                with self.assertRaisesRegex(LLMCallError, "brief のLLM呼び出しに失敗"):
                    model._call("generate", "brief", "prompt")
                self.assertEqual(client.calls, 2)
                self.assertEqual(client.raw_saves, 2)

    def test_call_logs_transport_and_json_parse_errors_for_each_retry(self) -> None:
        scenarios = {
            "transport": (
                [
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, error="ConnectionError: secret-token\nFORGED"),
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, error="ConnectionError: secret-token\nFORGED"),
                ],
                "LLM通信エラー",
            ),
            "json_parse": (
                [
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content="not json"),
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, content="not json"),
                ],
                "LLM JSONパースエラー",
            ),
        }
        for name, (records, message) in scenarios.items():
            with self.subTest(name=name):
                client = _SequenceClient(records)
                model = OpenAIStoryModel.__new__(OpenAIStoryModel)
                model.client = client
                model.attempt = 0
                with self.assertLogs("storycraft", level="ERROR") as captured:
                    with self.assertRaises(LLMCallError):
                        model._call("generate", "brief", "prompt")
                output = "\n".join(captured.output)
                self.assertEqual(output.count(message), 2)
                self.assertIn("attempt=1/2", output)
                self.assertIn("attempt=2/2", output)
                if name == "transport":
                    self.assertIn("error_type=ConnectionError", output)
                    self.assertNotIn("secret-token", output)
                    self.assertNotIn("FORGED", output)

    def test_llm_client_uses_compact_start_and_end_logs(self) -> None:
        thinking = SimpleNamespace(reasoning="考", content=None)
        content = SimpleNamespace(reasoning=None, content="本文")
        def delayed_stream():
            time.sleep(0.03)
            yield SimpleNamespace(choices=[SimpleNamespace(delta=thinking)])
            yield SimpleNamespace(choices=[SimpleNamespace(delta=content)])

        stream = delayed_stream()
        client = LLMClient.__new__(LLMClient)
        client.settings = SimpleNamespace(llm={
            "model": "test", "thinking": True,
            "first_event_timeout_seconds": 3600,
            "idle_timeout_seconds": 600,
            "stream_progress_log_interval_seconds": 0.01,
        })
        client.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_kwargs: stream))
        )
        messages = [{
            "__kind": "critique", "__phase": "scene_card", "__ref": "v:1/4 c:7/8 s:1/2",
            "__attempt": 1, "__retry_total": 2, "__quality_pass": "2/2",
        }]

        with self.assertLogs("storycraft", level="INFO") as captured:
            record = client.call_once(messages, {"type": "json_object"}, 1)

        output = "\n".join(captured.output)
        self.assertEqual(record.content, "本文")
        self.assertIn("LLM開始: stage=scene_card v:1/4,c:7/8,s:1/2 kind=critique quality_pass=2/2 retry=1/2", output)
        self.assertIn("LLM終了: stage=scene_card v:1/4,c:7/8,s:1/2 kind=critique quality_pass=2/2 retry=1/2", output)
        self.assertIn("INFO:storycraft:LLM待機: stage=scene_card v:1/4,c:7/8,s:1/2 kind=critique quality_pass=2/2 retry=1/2", output)
        self.assertRegex(output, r"経過=\d+\.\d{2}s")
        self.assertIn("chunks=0 thinking=0 content=0", output)
        self.assertNotIn("WARNING:storycraft:LLM待機", output)
        self.assertNotIn("状態=", output)
        self.assertNotIn("最終受信から=", output)
        self.assertNotIn("first_event_timeout=", output)
        self.assertNotIn("idle_timeout=", output)
        self.assertNotIn("attempt=", output)
        self.assertNotIn("phase=", output)
        self.assertNotIn("ref=", output)
        self.assertNotIn("thinking_chars=", output)
        self.assertNotIn("LLM呼び出し開始", output)
        self.assertNotIn("LLM思考開始", output)
        self.assertNotIn("LLM生成開始", output)
        self.assertNotIn("LLMストリーム接続済み", output)
        self.assertNotIn("LLM呼び出し完了", output)

    def test_llm_client_returns_transport_failure_without_duplicate_error_log(self) -> None:
        def fail_create(**kwargs: object) -> object:
            raise ConnectionError("secret-token\\nFORGED")

        client = LLMClient.__new__(LLMClient)
        client.settings = SimpleNamespace(llm={"model": "test"})
        client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail_create)))
        messages = [{"__kind": "generate", "__phase": "brief", "__ref": "brief", "__attempt": 1}]
        with self.assertNoLogs("storycraft", level="ERROR"):
            record = client.call_once(messages, {"type": "json_object"}, 1)
        self.assertEqual(record.error, "ConnectionError: secret-token\\nFORGED")

    def test_cli_logs_safe_exhausted_transport_error_once_per_layer(self) -> None:
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = _SequenceClient([
            CallRecord(
                kind="generate", phase="brief", ref="brief", attempt=1, seed=1,
                error="ConnectionError: secret-token\nFORGED",
            ),
        ])
        model.attempt = 0

        def fail_run(args: object) -> None:
            model._call("generate", "brief", "prompt")

        stderr = io.StringIO()
        with patch.object(sys, "argv", ["storycraft", "run", "--out", "/tmp/output", "--keywords", "test"]), \
             patch("storycraft.cli.cmd_run", side_effect=fail_run), \
             self.assertLogs("storycraft", level="ERROR") as captured, \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exited:
                cli.main()

        output = "\n".join(captured.output)
        stderr_output = stderr.getvalue()
        self.assertEqual(exited.exception.code, 2)
        self.assertEqual(output.count("LLM通信エラー"), 1)
        self.assertEqual(output.count("契約エラーにより終了します"), 1)
        self.assertIn("error_type=ConnectionError", output)
        self.assertNotIn("secret-token", output)
        self.assertNotIn("FORGED", output)
        self.assertIn("reason=transport:ConnectionError", stderr_output)
        self.assertNotIn("secret-token", stderr_output)
        self.assertNotIn("FORGED", stderr_output)

    def test_real_brief_and_volume_map_prompts_express_ownership_boundaries(self) -> None:
        brief = OpenAIStoryModel._render("generate", "brief", context={"keywords": ["霧の島", "4巻"]})
        volume_map = OpenAIStoryModel._render("generate", "volume_map", context={})
        self.assertIn("keywords", brief)
        self.assertIn("自動レビュー", brief)
        self.assertIn("Canon", volume_map)
        self.assertIn("新しい人物、世界設定、因果、秘密、出来事、回収条件を作らない", volume_map)
        self.assertIn("`thread_targets`", volume_map)
        self.assertIn("`brief.ending` は結末の唯一の正本", volume_map)

    def test_brief_quality_templates_enforce_reviewed_adoption_boundaries(self) -> None:
        generate = OpenAIStoryModel._render("generate", "brief", context={"keywords": ["霧の島"]})
        critique = OpenAIStoryModel._render("critique", "brief", candidate={}, context={"keywords": ["霧の島"]})
        revision = OpenAIStoryModel._render("revision", "brief", candidate={}, critique={"issues": []}, context={"keywords": ["霧の島"]})
        self.assertNotIn("内容評価は行わない", generate)
        self.assertIn("自動レビュー", generate)
        self.assertIn("物語開始時点", critique)
        self.assertIn("物語開始時点", revision)
        self.assertIn("未公表または暗示された秘密や伏線", critique)
        self.assertIn("最終状態・世界または共同体の変化・読後感", critique)
        self.assertIn("候補にない誤字・表現・事実を作らない", critique)
        self.assertIn("未公表または暗示された秘密や伏線", revision)
        self.assertIn("最終状態・世界または共同体の変化・読後感", revision)
        self.assertIn("将来の対処・直面・克服・関係発展", critique)
        self.assertIn("将来の対処・直面・克服・関係発展", revision)
        self.assertIn("動詞と目的語の結び付き", critique)

    def test_brief_templates_treat_keywords_as_reference_and_require_structured_people(self) -> None:
        generate = OpenAIStoryModel._render("generate", "brief", context={"keywords": ["2巻構成"]})
        critique = OpenAIStoryModel._render("critique", "brief", candidate={}, context={"keywords": ["2巻構成"]})
        revision = OpenAIStoryModel._render("revision", "brief", candidate={}, critique={"issues": []}, context={"keywords": ["2巻構成"]})
        schema = json.loads(Path("templates/prompts/schemas/brief.json").read_text(encoding="utf-8"))

        self.assertIn("参考情報", generate)
        self.assertIn("採用しない", generate)
        self.assertIn("巻数・章数はkeywordsの文言から機械的に決めず", generate)
        self.assertIn("不一致だけではissueにしない", critique)
        self.assertIn("keywordsへの一致を目的として巻数", revision)
        self.assertEqual(schema["properties"]["key_people"]["type"], "array")
        self.assertEqual(
            schema["properties"]["key_people"]["items"]["required"],
            ["name", "present_position", "initial_relation_to_protagonist"],
        )
        self.assertEqual(schema["properties"]["protagonist"]["type"], "object")
        self.assertEqual(
            schema["properties"]["protagonist"]["required"],
            ["name", "present_position", "core_trait", "current_pressure", "initial_wish"],
        )
        self.assertIn("包括的に禁止しない", generate)
        self.assertIn("未設定の秘密", generate)
        self.assertIn("必要な表現手法", critique)
        self.assertIn("未設定の秘密", critique)
        self.assertIn("不自然な複合名詞", critique)
        self.assertIn("静的な開始時点の関係", generate)
        self.assertIn("肯定的な制作指示", generate)
        self.assertIn("滞在場所・位置情報", generate)
        self.assertIn("将来の義務・契約", generate)
        self.assertIn("継続的な行為", generate)
        self.assertIn("頻度・動作の描写", generate)
        self.assertIn("具体的な関係を明示する表現", generate)
        self.assertIn("過去の開始時点や時間的経過", generate)
        self.assertIn("内部矛盾", generate)
        self.assertIn("冗長な修飾", generate)
        self.assertIn("出来事・動作を伴う表現", generate)
        self.assertIn("途中で終わる不完全な文", generate)
        self.assertIn("理由・動機・経緯・背景説明", generate)
        self.assertIn("状態描写", generate)
        self.assertIn("present_position", generate)
        self.assertIn("不自然な断片", revision)
        self.assertIn("抽象表現", critique)
        self.assertIn("主人公との直接的な関係", critique)
        self.assertIn("解決の過程や手段", critique)
        self.assertIn("`avoid` の各文", critique)
        self.assertIn("抽象語の組合せ", critique)
        self.assertIn("変化が始まる経緯", critique)
        self.assertIn("対象のない評価語", critique)
        self.assertIn("具体的に特定できる", generate)
        self.assertIn("直接的で簡潔な関係事実", revision)
        self.assertIn("滞在場所・位置情報", revision)
        self.assertIn("将来の義務・契約", revision)
        self.assertIn("継続的な行為", revision)
        self.assertIn("頻度・動作の描写", revision)
        self.assertIn("静的状況を具体的に記述する表現", revision)
        self.assertIn("過去の開始時点や時間的経過", revision)
        self.assertIn("内部矛盾", revision)
        self.assertIn("冗長な修飾", revision)
        self.assertIn("出来事・動作を伴う表現", revision)
        self.assertIn("句切れや不完全な文を含む記述", revision)
        self.assertIn("理由・動機・経緯・背景説明", revision)
        self.assertIn("状態描写", revision)
        self.assertIn("present_position", revision)
        self.assertIn("指摘されたfield以外を変更しない", revision)
        self.assertIn("完全なroot object", revision)

    def test_active_templates_and_schemas_have_only_current_stages(self) -> None:
        root = Path(__file__).parents[1] / "templates" / "prompts"
        user = root / "user"
        for kind in ("generate", "critique", "revision"):
            for stage in STAGES:
                path = user / stage / f"{kind}_{stage}.j2"
                contents = path.read_text(encoding="utf-8")
                self.assertIn("{{ output_schema }}", contents, path)
                self.assertTrue(contents.rstrip().endswith("{{ output_schema }}"), path)
                self.assertNotIn("{% include", contents, path)
        self.assertFalse((user / "plan").exists())
        self.assertFalse((root / "schemas" / "plan.json").exists())
        self.assertEqual(len(list(user.glob("*/*.j2"))), len(STAGES) * 3)
        for stage in STAGES:
            self.assertTrue((root / "schemas" / f"{stage}.json").is_file(), stage)

    def test_threads_revision_preserves_author_truth_while_removing_only_unsupported_future_claims(self) -> None:
        prompt = OpenAIStoryModel._render(
            "revision", "threads", candidate={}, critique={"issues": []}, context={},
        )
        self.assertIn("`author_truth` はCanonの作者真実であり、削除・空文化しない", prompt)
        self.assertIn("`initial_state` に混入した未確定の将来変化", prompt)

    def test_every_current_stage_has_renderable_generation_critique_and_revision_contract(self) -> None:
        for stage in STAGES:
            for prompt in (
                OpenAIStoryModel._render("generate", stage, context={}),
                OpenAIStoryModel._render("critique", stage, candidate={}, context={}),
                OpenAIStoryModel._render("revision", stage, candidate={}, critique={"issues": []}, context={}),
            ):
                self.assertNotIn("{{", prompt, stage)
                self.assertIn("## 出力スキーマ", prompt, stage)

    def test_system_template_owns_json_response_protocol(self) -> None:
        system = get_template_loader().render_system()
        self.assertIn("必ず有効なJSONオブジェクトのみを返す", system)
        self.assertIn("コードブロック", system)

    def test_jinja_json_policy_keeps_japanese_unescaped(self) -> None:
        loader = get_template_loader()
        self.assertFalse(loader.env.policies["json.dumps_kwargs"]["ensure_ascii"])
        rendered = loader.env.from_string("{{ value | tojson }}").render(value={"title": "雨の地図"})
        self.assertIn("雨の地図", rendered)


if __name__ == "__main__":
    unittest.main()
