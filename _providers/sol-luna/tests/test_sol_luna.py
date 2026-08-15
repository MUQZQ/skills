import json
import os
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
os.sys.path.insert(0, str(SCRIPT_DIR))

import sol_luna


VALID_TASK_BRIEF = "\n".join(
    [
        "目标：检查配置解析行为",
        "允许范围：sol-luna 控制器的配置读取逻辑",
        "禁止范围：不修改文件，不调用外部服务",
        "约束：只读检查，保持现有接口",
        "预期输出：结论和相关代码位置",
        "验证证据：返回读取路径和配置值",
    ]
)
VALID_CODEX_RESULT = {
    "result": "完成",
    "group_status": "DONE",
    "task_results": [
        {"task": "检查配置", "status": "SATISFIED", "evidence": ["测试通过"]}
    ],
    "files_changed": [],
    "verification": ["python -m unittest: PASS"],
    "concerns": [],
    "coordination": [],
}


class SolLunaConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.project = self.root / "project"
        self.home = self.root / "home"
        self.project.mkdir()
        self.home.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_default_config_keeps_luna_off_and_uses_auto_model(self) -> None:
        config = sol_luna.resolve_config(self.project, self.home, {})
        models = sol_luna.load_luna_models()

        self.assertEqual("off", config["mode"])
        self.assertEqual("auto", config["model"])
        self.assertEqual("gpt-5.6-luna", models[0].id)
        self.assertEqual("gpt-5.3-codex-spark", models[1].id)
        self.assertEqual(2000, config["max_task_chars"])
        self.assertEqual(1200, config["max_result_chars"])

    @patch("sol_luna.run_luna", return_value={"result": "完成"})
    def test_user_triggered_run_enables_luna_for_session_without_persisting(
        self, run_luna: MagicMock
    ) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            result = sol_luna.main(
                [
                    "--project-root",
                    str(self.project),
                    "--home",
                    str(self.home),
                    "run",
                    "scout",
                    "--user-triggered",
                    VALID_TASK_BRIEF,
                ]
            )

        self.assertEqual(0, result)
        self.assertEqual("auto", run_luna.call_args.args[2]["mode"])
        self.assertEqual(VALID_TASK_BRIEF, run_luna.call_args.args[1])
        self.assertFalse((self.project / ".codex" / "sol-luna.json").exists())
        self.assertFalse((self.home / ".codex" / "sol-luna.json").exists())

    @patch("sol_luna.run_luna", return_value={"result": "不应执行"})
    def test_run_requires_user_trigger_even_when_persistent_mode_is_auto(
        self, run_luna: MagicMock
    ) -> None:
        self.write_json(
            self.project / ".codex" / "sol-luna.json", {"mode": "auto"}
        )

        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            result = sol_luna.main(
                [
                    "--project-root",
                    str(self.project),
                    "--home",
                    str(self.home),
                    "run",
                    "scout",
                    "检查仓库",
                ]
            )

        self.assertEqual(2, result)
        self.assertIn("当前会话", stderr.getvalue())
        run_luna.assert_not_called()

    @patch("sol_luna.run_luna", return_value={"result": "不应执行"})
    def test_smoke_requires_user_trigger_even_when_persistent_mode_is_auto(
        self, run_luna: MagicMock
    ) -> None:
        self.write_json(
            self.project / ".codex" / "sol-luna.json", {"mode": "auto"}
        )

        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            result = sol_luna.main(
                [
                    "--project-root",
                    str(self.project),
                    "--home",
                    str(self.home),
                    "smoke",
                    "--model",
                    "flash",
                ]
            )

        self.assertEqual(2, result)
        self.assertIn("当前会话", stderr.getvalue())
        run_luna.assert_not_called()

    @patch(
        "sol_luna.run_luna",
        return_value={"modelUsage": {}, "result": "LUNA_FLASH_SMOKE_OK"},
    )
    def test_user_triggered_smoke_runs_without_persisting(
        self, run_luna: MagicMock
    ) -> None:
        with patch("sys.stdout", new_callable=StringIO):
            result = sol_luna.main(
                [
                    "--project-root",
                    str(self.project),
                    "--home",
                    str(self.home),
                    "smoke",
                    "--user-triggered",
                    "--model",
                    "flash",
                ]
            )

        self.assertEqual(0, result)
        self.assertEqual("auto", run_luna.call_args.args[2]["mode"])
        for field in sol_luna.TASK_BRIEF_FIELDS:
            self.assertIn(f"{field}：", run_luna.call_args.args[1])
        self.assertFalse((self.project / ".codex" / "sol-luna.json").exists())
        self.assertFalse((self.home / ".codex" / "sol-luna.json").exists())

    @patch(
        "sol_luna.run_luna",
        return_value={"modelUsage": {}, "result": "错误标记"},
    )
    def test_smoke_rejects_wrong_result_marker(self, _run_luna: MagicMock) -> None:
        with (
            patch("sys.stdout", new_callable=StringIO),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            result = sol_luna.main(
                [
                    "--project-root",
                    str(self.project),
                    "--home",
                    str(self.home),
                    "smoke",
                    "--user-triggered",
                    "--model",
                    "flash",
                ]
            )

        self.assertEqual(2, result)
        self.assertIn("冒烟标记不匹配", stderr.getvalue())

    def test_smoke_rejects_legacy_ignore_mode_escape(self) -> None:
        with patch("sys.stderr", new_callable=StringIO):
            with self.assertRaises(SystemExit):
                sol_luna.build_parser().parse_args(["smoke", "--ignore-mode"])

    def test_smoke_defaults_to_first_model_instead_of_all(self) -> None:
        args = sol_luna.build_parser().parse_args(["smoke"])

        self.assertEqual("default", args.model)

    def test_precedence_is_environment_then_project_then_global_then_default(self):
        self.write_json(
            self.home / ".codex" / "sol-luna.json",
            {"mode": "force", "model": "pro"},
        )
        self.write_json(
            self.project / ".codex" / "sol-luna.json",
            {"mode": "auto", "model": "flash"},
        )

        project_config = sol_luna.resolve_config(self.project, self.home, {})
        env_config = sol_luna.resolve_config(
            self.project,
            self.home,
            {"SOL_LUNA_MODE": "off", "SOL_LUNA_MODEL": "pro"},
        )

        self.assertEqual("auto", project_config["mode"])
        self.assertEqual("flash", project_config["model"])
        self.assertEqual("off", env_config["mode"])
        self.assertEqual("pro", env_config["model"])

    def test_auto_model_always_uses_first_user_model(self):
        config = sol_luna.resolve_config(self.project, self.home, {})

        normal = sol_luna.resolve_model(config, "normal")
        high = sol_luna.resolve_model(config, "high")

        self.assertEqual("codex", normal.backend)
        self.assertEqual("gpt-5.6-luna", normal.provider_model)
        self.assertEqual("codex", high.backend)
        self.assertEqual("gpt-5.6-luna", high.provider_model)

    def test_explicit_model_selection_uses_full_model_ids(self):
        config = sol_luna.resolve_config(self.project, self.home, {})

        self.assertEqual(
            "haiku",
            sol_luna.resolve_model(config, "high", requested="flash").claude_model,
        )
        self.assertEqual(
            "deepseek-v4-pro",
            sol_luna.resolve_model(config, "normal", requested="pro").provider_model,
        )

    def test_user_model_list_uses_first_entry_as_default_and_supports_selection(self):
        model_list_path = self.root / "luna-models.json"
        self.write_json(
            model_list_path,
            [
                {
                    "id": "qwen3-coder-flash",
                    "label": "Qwen3 Coder Flash",
                    "provider_model": "qwen3-coder-flash",
                    "claude_model": "haiku",
                    "override_model": "claude-haiku-4-5-20251001",
                    "aliases": ["flash"],
                },
                {
                    "id": "deepseek-v4-pro",
                    "label": "DeepSeek V4 Pro",
                    "provider_model": "deepseek-v4-pro",
                    "claude_model": "sonnet",
                    "override_model": "claude-sonnet-4-6",
                    "aliases": ["pro"],
                },
            ],
        )
        models = sol_luna.load_luna_models(model_list_path)
        config = sol_luna.resolve_config(self.project, self.home, {})

        default = sol_luna.resolve_model(config, "high", models=models)
        selected = sol_luna.resolve_model(
            config, "normal", requested="deepseek-v4-pro", models=models
        )

        self.assertEqual("qwen3-coder-flash", default.selection)
        self.assertEqual("qwen3-coder-flash", default.provider_model)
        self.assertEqual("deepseek-v4-pro", selected.selection)
        self.assertEqual("sonnet", selected.claude_model)

    def test_parser_lists_models_and_accepts_user_model_id(self):
        models_args = sol_luna.build_parser().parse_args(["models"])
        run_args = sol_luna.build_parser().parse_args(
            [
                "run",
                "worker",
                "--model",
                "qwen3-coder-flash",
                VALID_TASK_BRIEF,
            ]
        )

        self.assertEqual("models", models_args.command)
        self.assertEqual("qwen3-coder-flash", run_args.model)

    def test_model_list_rejects_empty_list_and_duplicate_selector(self):
        empty_path = self.root / "empty-models.json"
        duplicate_path = self.root / "duplicate-models.json"
        self.write_json(empty_path, [])
        self.write_json(
            duplicate_path,
            [
                {
                    "id": "model-a",
                    "label": "Model A",
                    "provider_model": "provider-a",
                    "claude_model": "haiku",
                    "override_model": "claude-haiku-4-5-20251001",
                    "aliases": ["cheap"],
                },
                {
                    "id": "model-b",
                    "label": "Model B",
                    "provider_model": "provider-b",
                    "claude_model": "sonnet",
                    "override_model": "claude-sonnet-4-6",
                    "aliases": ["cheap"],
                },
            ],
        )

        with self.assertRaisesRegex(sol_luna.SolLunaError, "非空 JSON 数组"):
            sol_luna.load_luna_models(empty_path)
        with self.assertRaisesRegex(sol_luna.SolLunaError, "选择名重复"):
            sol_luna.load_luna_models(duplicate_path)

    def test_model_list_supports_codex_and_legacy_claude_entries(self):
        model_list_path = self.root / "mixed-models.json"
        self.write_json(
            model_list_path,
            [
                {
                    "id": "gpt-5.6-luna",
                    "label": "GPT-5.6 Luna",
                    "backend": "codex",
                    "provider_model": "gpt-5.6-luna",
                    "reasoning_effort": "medium",
                    "aliases": ["luna"],
                },
                {
                    "id": "deepseek-v4-flash",
                    "label": "DeepSeek V4 Flash",
                    "provider_model": "deepseek-v4-flash",
                    "claude_model": "haiku",
                    "override_model": "claude-haiku-4-5-20251001",
                    "aliases": ["flash"],
                },
            ],
        )

        codex_model, claude_model = sol_luna.load_luna_models(model_list_path)

        self.assertEqual("codex", codex_model.backend)
        self.assertEqual("medium", codex_model.reasoning_effort)
        self.assertEqual("claude", claude_model.backend)
        self.assertEqual("haiku", claude_model.claude_model)

    def test_configure_claude_uses_user_model_list_as_authority(self):
        model_list_path = self.root / "custom-models.json"
        self.write_json(
            model_list_path,
            [
                {
                    "id": "custom-luna",
                    "label": "Custom Luna",
                    "provider_model": "custom-provider-model",
                    "claude_model": "haiku",
                    "override_model": "claude-haiku-4-5-20251001",
                    "aliases": [],
                }
            ],
        )
        models = sol_luna.load_luna_models(model_list_path)
        config = sol_luna.resolve_config(self.project, self.home, {})

        sol_luna.configure_claude_settings(self.home, config, models)
        updated = json.loads(
            (self.home / ".claude" / "settings.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            "custom-provider-model",
            updated["modelOverrides"]["claude-haiku-4-5-20251001"],
        )

    def test_configure_claude_ignores_codex_backend_entries(self):
        model_list_path = self.root / "mixed-models.json"
        self.write_json(
            model_list_path,
            [
                {
                    "id": "gpt-5.6-luna",
                    "label": "GPT-5.6 Luna",
                    "backend": "codex",
                    "provider_model": "gpt-5.6-luna",
                    "reasoning_effort": "medium",
                    "aliases": ["luna"],
                },
                {
                    "id": "deepseek-v4-flash",
                    "label": "DeepSeek V4 Flash",
                    "backend": "claude",
                    "provider_model": "deepseek-v4-flash",
                    "claude_model": "haiku",
                    "override_model": "claude-haiku-4-5-20251001",
                    "aliases": ["flash"],
                },
            ],
        )
        models = sol_luna.load_luna_models(model_list_path)
        config = sol_luna.resolve_config(self.project, self.home, {})

        sol_luna.configure_claude_settings(self.home, config, models)
        updated = json.loads(
            (self.home / ".claude" / "settings.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            {"claude-haiku-4-5-20251001": "deepseek-v4-flash"},
            updated["modelOverrides"],
        )

    def test_codex_command_is_ephemeral_bounded_and_has_no_bypass(self):
        command = sol_luna.build_codex_command(
            "worker", "gpt-5.3-codex-spark", "medium", self.project
        )

        self.assertIn("exec", command)
        self.assertIn("gpt-5.3-codex-spark", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("multi_agent", command)
        self.assertIn("sandbox_workspace_write.network_access=false", command)
        self.assertIn("mcp_servers={}", command)
        self.assertIn("--output-schema", command)
        self.assertIn("workspace-write", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        self.assertNotIn("--ignore-rules", command)

    @patch("sol_luna.run_codex_luna", return_value={"result": "完成"})
    def test_run_luna_dispatches_selected_codex_backend(
        self, run_codex_luna: MagicMock
    ) -> None:
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )

        result = sol_luna.run_luna(
            "worker",
            VALID_TASK_BRIEF,
            config,
            "normal",
            "spark",
            self.project,
        )

        self.assertEqual("完成", result["result"])
        route = run_codex_luna.call_args.args[3]
        self.assertEqual("codex", route.backend)
        self.assertEqual("gpt-5.3-codex-spark", route.provider_model)

    def test_codex_jsonl_result_reports_requested_model_without_claiming_proof(self):
        route = sol_luna.resolve_model(
            sol_luna.resolve_config(self.project, self.home, {}),
            "normal",
            "gpt-5.6-luna",
        )
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": json.dumps(VALID_CODEX_RESULT, ensure_ascii=False),
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 10, "output_tokens": 2},
                    }
                ),
            ]
        )

        payload = sol_luna.parse_codex_output(stdout, route)

        self.assertEqual("完成", payload["result"])
        self.assertEqual("DONE", payload["group_status"])
        self.assertEqual("SATISFIED", payload["task_results"][0]["status"])
        self.assertEqual("gpt-5.6-luna", payload["requestedModel"])
        self.assertEqual("command_only", payload["_sol_luna"]["model_verification"])
        self.assertNotIn("modelUsage", payload)

    def test_codex_jsonl_failure_event_overrides_prior_message(self):
        route = sol_luna.resolve_model(
            sol_luna.resolve_config(self.project, self.home, {}),
            "normal",
            "gpt-5.6-luna",
        )
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "尚未完成"},
                    }
                ),
                json.dumps(
                    {"type": "turn.failed", "error": {"message": "执行失败"}}
                ),
            ]
        )

        with self.assertRaisesRegex(sol_luna.SolLunaError, "执行失败"):
            sol_luna.parse_codex_output(stdout, route)

    def test_codex_jsonl_rejects_unstructured_final_result(self):
        route = sol_luna.resolve_model(
            sol_luna.resolve_config(self.project, self.home, {}),
            "normal",
            "gpt-5.6-luna",
        )
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "自由文本"},
            }
        )

        with self.assertRaisesRegex(sol_luna.SolLunaError, "结构化返回契约"):
            sol_luna.parse_codex_output(stdout, route)

    def test_result_contract_rejects_empty_evidence_and_verification(self):
        empty_evidence = json.loads(json.dumps(VALID_CODEX_RESULT))
        empty_evidence["task_results"][0]["evidence"] = []
        empty_verification = json.loads(json.dumps(VALID_CODEX_RESULT))
        empty_verification["verification"] = []

        for payload in (empty_evidence, empty_verification):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(sol_luna.SolLunaError, "结构化返回契约"):
                    sol_luna.validate_result_contract(payload)

    def test_result_contract_rejects_done_with_unsatisfied_task(self):
        payload = json.loads(json.dumps(VALID_CODEX_RESULT))
        payload["task_results"][0]["status"] = "UNSATISFIED"

        with self.assertRaisesRegex(sol_luna.SolLunaError, "组状态与 task 状态矛盾"):
            sol_luna.validate_result_contract(payload)

    def test_result_contract_keeps_done_concern_states_mutually_exclusive(self):
        done_with_concern = json.loads(json.dumps(VALID_CODEX_RESULT))
        done_with_concern["concerns"] = ["非阻塞风险"]
        concerned_without_concern = json.loads(json.dumps(VALID_CODEX_RESULT))
        concerned_without_concern["group_status"] = "DONE_WITH_CONCERNS"
        valid_concerned = json.loads(json.dumps(concerned_without_concern))
        valid_concerned["concerns"] = ["非阻塞风险"]

        for payload in (done_with_concern, concerned_without_concern):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(sol_luna.SolLunaError, "完成态与 concerns 矛盾"):
                    sol_luna.validate_result_contract(payload)
        self.assertEqual(
            "DONE_WITH_CONCERNS",
            sol_luna.validate_result_contract(valid_concerned)["group_status"],
        )

    def test_result_schema_requires_nonempty_task_evidence_and_verification(self):
        provider_root = Path(__file__).resolve().parents[1]
        schema = json.loads(
            (provider_root / "references" / "result-schema.json").read_text(
                encoding="utf-8"
            )
        )
        task_results = schema["properties"]["task_results"]
        evidence = task_results["items"]["properties"]["evidence"]

        self.assertEqual(1, task_results["minItems"])
        self.assertEqual(1, evidence["minItems"])
        self.assertEqual(1, schema["properties"]["verification"]["minItems"])
        self.assertEqual(3, len(schema["anyOf"]))
        done_branch, concerned_branch, incomplete_branch = schema["anyOf"]
        self.assertEqual(
            ["DONE"], done_branch["properties"]["group_status"]["enum"]
        )
        self.assertEqual(0, done_branch["properties"]["concerns"]["maxItems"])
        self.assertEqual(
            ["DONE_WITH_CONCERNS"],
            concerned_branch["properties"]["group_status"]["enum"],
        )
        self.assertEqual(
            1, concerned_branch["properties"]["concerns"]["minItems"]
        )
        self.assertEqual(
            ["NEEDS_CONTEXT", "NEEDS_COORDINATION", "BLOCKED"],
            incomplete_branch["properties"]["group_status"]["enum"],
        )

    def test_claude_output_is_normalized_to_shared_result_contract(self):
        route = sol_luna.resolve_model(
            sol_luna.resolve_config(self.project, self.home, {}),
            "normal",
            "deepseek-v4-flash",
        )
        raw_payload = {
            "result": json.dumps(VALID_CODEX_RESULT, ensure_ascii=False),
            "modelUsage": {"deepseek-v4-flash": {"inputTokens": 10}},
        }

        payload = sol_luna.parse_claude_output(raw_payload, route)

        self.assertEqual("完成", payload["result"])
        self.assertEqual("DONE", payload["group_status"])
        self.assertEqual("SATISFIED", payload["task_results"][0]["status"])
        self.assertEqual("verified", payload["_sol_luna"]["model_verification"])
        self.assertIn("deepseek-v4-flash", payload["modelUsage"])

    def test_codex_executable_skips_workspace_candidate(self):
        unsafe = self.project / "codex.exe"
        safe = Path(r"C:\Program Files\OpenAI Codex\codex.exe")

        with patch.object(sol_luna.shutil, "which") as which:
            which.side_effect = lambda name: str(unsafe) if name == "codex.exe" else str(safe)
            resolved = sol_luna.resolve_codex_executable(self.project)

        self.assertEqual(str(safe), resolved)

    def test_windows_codex_executable_prefers_spawnable_cmd_over_windowsapps_exe(self):
        windowsapps = (
            r"C:\Program Files\WindowsApps\OpenAI.Codex_26.810.4967.0_x64__2p2nqsd0c76g0"
            r"\app\resources\codex.exe"
        )
        npm_wrapper = r"C:\Users\tester\AppData\Roaming\npm\codex.cmd"

        with patch.object(sol_luna.os, "name", "nt"):
            with patch.object(sol_luna.shutil, "which") as which:
                which.side_effect = lambda name: {
                    "codex.exe": windowsapps,
                    "codex.cmd": npm_wrapper,
                }.get(name)
                resolved = sol_luna.resolve_codex_executable()

        self.assertEqual(npm_wrapper, resolved)

    def test_claude_executable_skips_workspace_candidate(self):
        unsafe = self.project / "claude.exe"
        safe = Path(r"C:\Program Files\Claude Code\claude.exe")

        with patch.object(sol_luna.shutil, "which") as which:
            which.side_effect = lambda name: str(unsafe) if name == "claude.exe" else str(safe)
            resolved = sol_luna.resolve_claude_executable(self.project)

        self.assertEqual(str(safe), resolved)

    def test_executable_resolver_skips_process_cwd_candidate(self):
        unsafe = Path.cwd() / "codex.exe"
        safe = Path(r"C:\Program Files\OpenAI Codex\codex.exe")

        with patch.object(sol_luna.shutil, "which") as which:
            which.side_effect = lambda name: str(unsafe) if name == "codex.exe" else str(safe)
            resolved = sol_luna.resolve_codex_executable()

        self.assertEqual(str(safe), resolved)

    @patch("sol_luna.resolve_codex_executable", return_value=r"C:\Tools\codex.exe")
    @patch("sol_luna.subprocess.Popen")
    def test_codex_runner_passes_task_by_stdin_and_parses_jsonl(
        self, popen: MagicMock, _resolve: MagicMock
    ) -> None:
        process = popen.return_value
        process.returncode = 0
        process.communicate.return_value = (
            json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": json.dumps(VALID_CODEX_RESULT, ensure_ascii=False),
                },
            }
            ),
            "",
        )
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )
        route = sol_luna.resolve_model(config, "normal", "gpt-5.6-luna")

        payload = sol_luna.run_codex_luna(
            "worker", VALID_TASK_BRIEF, config, route, self.project, quiet=True
        )

        command = popen.call_args.args[0]
        stdin_prompt = process.communicate.call_args.kwargs["input"]
        self.assertEqual("完成", payload["result"])
        self.assertIn("--ephemeral", command)
        self.assertEqual("-", command[-1])
        self.assertNotIn(VALID_TASK_BRIEF, " ".join(command))
        self.assertIn(VALID_TASK_BRIEF, stdin_prompt)

    @patch("sol_luna.resolve_codex_executable", return_value=r"C:\Tools\codex.exe")
    @patch("sol_luna.terminate_process_tree")
    @patch("sol_luna.subprocess.Popen")
    def test_codex_timeout_terminates_process_tree(
        self,
        popen: MagicMock,
        terminate_process_tree: MagicMock,
        _resolve: MagicMock,
    ) -> None:
        process = popen.return_value
        process.communicate.side_effect = subprocess.TimeoutExpired("codex", 1)
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )
        route = sol_luna.resolve_model(config, "normal", "gpt-5.6-luna")

        with self.assertRaisesRegex(sol_luna.SolLunaError, "timeout=1s"):
            sol_luna.run_codex_luna(
                "worker",
                VALID_TASK_BRIEF,
                config,
                route,
                self.project,
                quiet=True,
                timeout_seconds=1,
            )

        terminate_process_tree.assert_called_once_with(process)

    def test_windows_process_tree_termination_uses_taskkill(self):
        process = MagicMock(pid=1234)
        process.poll.return_value = None

        with patch.object(sol_luna.os, "name", "nt"), patch(
            "sol_luna.subprocess.run"
        ) as process_run:
            sol_luna.terminate_process_tree(process)

        process_run.assert_called_once()
        self.assertEqual(
            ["taskkill", "/PID", "1234", "/T", "/F"],
            process_run.call_args.args[0],
        )

    def test_configure_claude_merges_overrides_without_changing_secrets(self):
        settings_path = self.home / ".claude" / "settings.json"
        self.write_json(
            settings_path,
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "secret-value",
                    "ANTHROPIC_BASE_URL": "https://private.example",
                    "ANTHROPIC_MODEL": "deepseek-v4-pro",
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
                    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro",
                },
                "effortLevel": "xhigh",
                "modelOverrides": {"claude-opus-4-6": "existing-provider-model"},
            },
        )
        config = sol_luna.resolve_config(self.project, self.home, {})

        result = sol_luna.configure_claude_settings(self.home, config)
        updated = json.loads(settings_path.read_text(encoding="utf-8"))

        self.assertEqual("secret-value", updated["env"]["ANTHROPIC_AUTH_TOKEN"])
        self.assertEqual("https://private.example", updated["env"]["ANTHROPIC_BASE_URL"])
        self.assertNotIn("ANTHROPIC_MODEL", updated["env"])
        self.assertNotIn("ANTHROPIC_DEFAULT_HAIKU_MODEL", updated["env"])
        self.assertNotIn("ANTHROPIC_DEFAULT_SONNET_MODEL", updated["env"])
        self.assertEqual(
            "deepseek-v4-pro", updated["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"]
        )
        self.assertEqual("xhigh", updated["effortLevel"])
        self.assertEqual(
            "existing-provider-model",
            updated["modelOverrides"]["claude-opus-4-6"],
        )
        self.assertEqual(
            "deepseek-v4-flash",
            updated["modelOverrides"]["claude-haiku-4-5-20251001"],
        )
        self.assertEqual(
            "deepseek-v4-pro",
            updated["modelOverrides"]["claude-sonnet-4-6"],
        )
        self.assertTrue(Path(result["backup"]).exists())

    def test_configure_claude_preserves_unrelated_model_defaults(self):
        settings_path = self.home / ".claude" / "settings.json"
        self.write_json(
            settings_path,
            {
                "env": {
                    "ANTHROPIC_DEFAULT_OPUS_MODEL": "private-opus",
                    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "private-haiku",
                }
            },
        )
        config = sol_luna.resolve_config(self.project, self.home, {})

        sol_luna.configure_claude_settings(self.home, config)
        updated = json.loads(settings_path.read_text(encoding="utf-8"))

        self.assertEqual("private-opus", updated["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"])
        self.assertEqual("private-haiku", updated["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"])

    def test_configure_claude_ignores_project_override_ids(self):
        config = sol_luna.resolve_config(self.project, self.home, {})
        config["flash_claude_model"] = "claude-opus-4-6"
        config["flash_model"] = "private-haiku"
        settings_path = self.home / ".claude" / "settings.json"
        self.write_json(
            settings_path,
            {"env": {"ANTHROPIC_DEFAULT_HAIKU_MODEL": "private-haiku"}},
        )

        sol_luna.configure_claude_settings(self.home, config)
        updated = json.loads(
            (self.home / ".claude" / "settings.json").read_text(encoding="utf-8")
        )

        self.assertNotIn("claude-opus-4-6", updated["modelOverrides"])
        self.assertEqual(
            "deepseek-v4-flash",
            updated["modelOverrides"]["claude-haiku-4-5-20251001"],
        )
        self.assertEqual(
            "private-haiku", updated["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"]
        )

    def test_configure_claude_is_idempotent_when_overrides_are_current(self):
        config = sol_luna.resolve_config(self.project, self.home, {})
        first = sol_luna.configure_claude_settings(self.home, config)
        second = sol_luna.configure_claude_settings(self.home, config)

        self.assertEqual("updated", first["status"])
        self.assertEqual("unchanged", second["status"])
        self.assertIsNone(second["backup"])

    def test_parser_exposes_configure_claude_command(self):
        args = sol_luna.build_parser().parse_args(["configure-claude"])

        self.assertEqual("configure-claude", args.command)

    def test_status_model_routes_are_ordered_and_mark_first_as_default(self):
        config = sol_luna.resolve_config(self.project, self.home, {})

        routes = sol_luna.describe_model_routes(config)

        self.assertEqual(
            [
                "gpt-5.6-luna",
                "gpt-5.3-codex-spark",
                "gpt-5.4-mini",
                "gpt-5.6-terra",
                "deepseek-v4-flash",
                "deepseek-v4-pro",
            ],
            [route["id"] for route in routes],
        )
        self.assertTrue(routes[0]["default"])
        self.assertEqual("codex", routes[0]["backend"])
        self.assertEqual("medium", routes[0]["reasoning_effort"])
        self.assertFalse(routes[1]["default"])
        self.assertEqual("gpt-5.3-codex-spark", routes[1]["provider_model"])
        self.assertEqual("claude", routes[-2]["backend"])
        self.assertEqual("haiku", routes[-2]["claude_model"])

    def test_off_mode_rejects_luna_execution(self):
        config = sol_luna.resolve_config(
            self.project,
            self.home,
            {"SOL_LUNA_MODE": "off"},
        )

        with self.assertRaisesRegex(sol_luna.LunaDisabledError, "Luna 已关闭"):
            sol_luna.build_claude_command(
                role="scout",
                model="deepseek-v4-flash",
                prompt="检查仓库",
                config=config,
            )

    def test_read_only_roles_use_plan_mode_and_non_persistent_stream_output(self):
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )

        command = sol_luna.build_claude_command(
            role="critic",
            model="deepseek-v4-pro",
            prompt="审查变更",
            config=config,
        )

        self.assertEqual("claude", command[0])
        self.assertIn("luna-critic", command)
        self.assertIn("deepseek-v4-pro", command)
        self.assertIn("plan", command)
        self.assertIn("--no-session-persistence", command)
        self.assertIn("stream-json", command)
        self.assertEqual("审查变更", command[-1])

    def test_task_prompt_adds_planned_boundary_and_result_contract(self) -> None:
        config = sol_luna.resolve_config(self.project, self.home, {})

        for task_brief in (
            VALID_TASK_BRIEF,
            VALID_TASK_BRIEF.replace("\n", "\r\n"),
        ):
            with self.subTest(newline=repr(task_brief.splitlines(keepends=True)[0])):
                prompt = sol_luna.bound_task_prompt(task_brief, config)

                self.assertIn("单一目标", prompt)
                self.assertIn("允许范围", prompt)
                self.assertIn("禁止范围", prompt)
                self.assertIn("预期输出", prompt)
                self.assertIn("验证证据", prompt)
                self.assertIn("1200", prompt)
                self.assertIn("拆分建议", prompt)

    def test_task_prompt_rejects_each_missing_task_brief_field(self) -> None:
        config = sol_luna.resolve_config(self.project, self.home, {})
        lines = VALID_TASK_BRIEF.splitlines()

        for missing_field in sol_luna.TASK_BRIEF_FIELDS:
            with self.subTest(missing_field=missing_field):
                incomplete = "\n".join(
                    line for line in lines if not line.startswith(f"{missing_field}：")
                )
                with self.assertRaisesRegex(sol_luna.SolLunaError, missing_field):
                    sol_luna.bound_task_prompt(incomplete, config)

    def test_task_prompt_rejects_each_empty_task_brief_field(self) -> None:
        config = sol_luna.resolve_config(self.project, self.home, {})
        lines = VALID_TASK_BRIEF.splitlines()

        for empty_field in sol_luna.TASK_BRIEF_FIELDS:
            with self.subTest(empty_field=empty_field):
                incomplete = "\n".join(
                    f"{empty_field}：   "
                    if line.startswith(f"{empty_field}：")
                    else line
                    for line in lines
                )
                with self.assertRaisesRegex(sol_luna.SolLunaError, empty_field):
                    sol_luna.bound_task_prompt(incomplete, config)

    def test_incomplete_task_brief_is_rejected_before_process_start(self) -> None:
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )
        incomplete = VALID_TASK_BRIEF.replace(
            "验证证据：返回读取路径和配置值", "验证证据：   "
        )

        with patch("sol_luna.subprocess.Popen") as popen:
            with self.assertRaisesRegex(sol_luna.SolLunaError, "验证证据"):
                sol_luna.run_luna(
                    "scout",
                    incomplete,
                    config,
                    "normal",
                    "flash",
                    self.project,
                )

        popen.assert_not_called()

    def test_task_prompt_rejects_oversized_delegation(self):
        config = sol_luna.resolve_config(self.project, self.home, {})

        with self.assertRaisesRegex(sol_luna.SolLunaError, "任务颗粒过大"):
            sol_luna.bound_task_prompt("x" * 2001, config)

    def test_result_is_truncated_with_explicit_metadata(self):
        payload = {"result": "x" * 1201}

        bounded = sol_luna.bound_result(payload, 1200)

        self.assertEqual(1200, len(bounded["result"]))
        self.assertTrue(bounded["_sol_luna"]["result_truncated"])
        self.assertEqual(1201, bounded["_sol_luna"]["original_result_chars"])

    def test_worker_accepts_workspace_edits_without_bypass_permissions(self):
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )

        command = sol_luna.build_claude_command(
            role="worker",
            model="deepseek-v4-flash",
            prompt="实现有界任务",
            config=config,
        )

        self.assertIn("--permission-mode", command)
        self.assertIn("acceptEdits", command)
        self.assertIn("--allowedTools", command)
        self.assertIn("Bash", command)
        self.assertNotIn("bypassPermissions", command)
        self.assertNotIn("--dangerously-skip-permissions", command)

    def test_tester_can_run_bash_without_write_tools_or_bypass_permissions(self):
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )

        command = sol_luna.build_claude_command(
            role="tester",
            model="deepseek-v4-flash",
            prompt="运行指定测试",
            config=config,
        )

        self.assertIn("--permission-mode", command)
        self.assertIn("dontAsk", command)
        self.assertIn("--allowedTools", command)
        self.assertIn("Bash", command)
        self.assertNotIn("plan", command)
        self.assertNotIn("bypassPermissions", command)
        self.assertNotIn("--dangerously-skip-permissions", command)

    def test_windows_claude_command_wrapper_keeps_prompt_out_of_shell_command(self):
        with patch.object(sol_luna.shutil, "which") as which:
            which.side_effect = lambda name: (
                r"C:\Tools\claude.cmd" if name == "claude.cmd" else None
            )

            executable = sol_luna.resolve_claude_executable()
            command = [executable, "-p", "--model", "deepseek-v4-pro", "危险 & prompt"]
            wrapped, stdin_prompt = sol_luna.prepare_process_command(command)

        self.assertEqual("危险 & prompt", stdin_prompt)
        self.assertEqual("cmd.exe", wrapped[0])
        self.assertNotIn("危险 & prompt", " ".join(wrapped))
        self.assertIn("claude.cmd", " ".join(wrapped))

    def test_windows_wrapper_rejects_shell_metacharacters_in_fixed_arguments(self):
        command = [
            r"C:\Tools\claude.cmd",
            "-p",
            "--model",
            "deepseek-v4-pro & calc.exe",
            "安全 prompt",
        ]

        with patch.object(sol_luna.os, "name", "nt"):
            with self.assertRaisesRegex(sol_luna.SolLunaError, "shell 元字符"):
                sol_luna.prepare_process_command(command)

    def test_prompt_writer_reports_completion_from_background_thread(self):
        stream = StringIO()
        events: Queue[tuple[str, str | None]] = Queue()

        sol_luna._write_process_input(stream, "较大的 prompt", events)

        self.assertTrue(stream.closed)
        self.assertEqual(("stdin", None), events.get_nowait())

    def test_non_json_stdout_line_is_recorded_without_immediate_failure(self):
        noise: list[str] = []

        event = sol_luna.parse_stream_event("Claude warning banner\n", noise)

        self.assertIsNone(event)
        self.assertEqual(["Claude warning banner"], noise)

    def test_unknown_model_window_warning_is_rejected(self):
        warning = '"deepseek-v4-flash" is not a model this version of Claude Code recognizes'

        with self.assertRaisesRegex(sol_luna.SolLunaError, "未知模型窗口警告"):
            sol_luna.reject_unknown_model_warning([warning])

    def test_claude_command_requests_verbose_stream_json(self):
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )

        command = sol_luna.build_claude_command(
            role="critic",
            model="deepseek-v4-pro",
            prompt="审查变更",
            config=config,
        )

        self.assertIn("--verbose", command)
        output_index = command.index("--output-format")
        self.assertEqual("stream-json", command[output_index + 1])

    def test_event_monitor_reports_state_without_exposing_thinking(self):
        status = StringIO()
        monitor = sol_luna.EventMonitor(status_stream=status, quiet=False)

        monitor.handle(
            {
                "type": "system",
                "subtype": "init",
                "session_id": "session-123",
                "model": "deepseek-v4-pro",
            }
        )
        monitor.handle(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "thinking", "thinking": "敏感推理内容"},
                        {"type": "tool_use", "name": "Read"},
                    ]
                },
            }
        )

        output = status.getvalue()
        self.assertIn("RUNNING", output)
        self.assertIn("TOOL_ACTIVITY tool=Read", output)
        self.assertNotIn("敏感推理内容", output)

    def test_event_monitor_treats_quiet_as_status_not_failure(self):
        status = StringIO()
        monitor = sol_luna.EventMonitor(status_stream=status, quiet=False)

        monitor.report_quiet(elapsed_seconds=90.0)

        self.assertIn("QUIET", status.getvalue())
        self.assertFalse(monitor.failed)

    def test_event_monitor_does_not_report_quiet_after_result(self):
        status = StringIO()
        monitor = sol_luna.EventMonitor(status_stream=status, quiet=False)
        monitor.handle({"type": "result", "is_error": False, "duration_ms": 1})

        monitor.report_quiet(elapsed_seconds=90.0)

        self.assertNotIn("QUIET", status.getvalue())

    def test_event_monitor_deduplicates_cumulative_assistant_content(self):
        status = StringIO()
        monitor = sol_luna.EventMonitor(status_stream=status, quiet=False)
        event = {
            "type": "assistant",
            "message": {
                "id": "message-1",
                "content": [{"type": "tool_use", "name": "Read"}],
            },
        }

        monitor.handle(event)
        monitor.handle(event)

        self.assertEqual(1, status.getvalue().count("TOOL_ACTIVITY tool=Read"))

    def test_model_usage_validation_rejects_unexpected_model(self):
        payload = {
            "modelUsage": {"deepseek-v4-pro": {"inputTokens": 1}},
            "result": "完成",
        }

        with self.assertRaisesRegex(sol_luna.ModelMismatchError, "模型不一致"):
            sol_luna.validate_model_usage(payload, "deepseek-v4-flash")

    def test_set_config_updates_only_selected_scope(self):
        sol_luna.update_config(
            scope="project",
            project_root=self.project,
            home=self.home,
            updates={"model": "pro"},
        )

        project_path = self.project / ".codex" / "sol-luna.json"
        global_path = self.home / ".codex" / "sol-luna.json"
        self.assertEqual("pro", json.loads(project_path.read_text(encoding="utf-8"))["model"])
        self.assertFalse(global_path.exists())

    def test_all_role_templates_exist_and_read_only_roles_are_hardened(self):
        template_dir = sol_luna.role_template_dir()

        for role in ("scout", "worker", "critic", "tester"):
            template = template_dir / f"luna-{role}.md"
            self.assertTrue(template.exists(), f"缺少角色模板: {template}")
            content = template.read_text(encoding="utf-8")
            self.assertIn(f"name: luna-{role}", content)
            self.assertIn("model: inherit", content)
            self.assertIn("统一 JSON 返回契约", content)

        for role in ("scout", "critic"):
            content = (template_dir / f"luna-{role}.md").read_text(encoding="utf-8")
            self.assertIn("tools: Read, Grep, Glob", content)

        tester = (template_dir / "luna-tester.md").read_text(encoding="utf-8")
        self.assertIn("tools: Read, Grep, Glob, Bash", tester)

    def test_project_policy_requires_user_triggered_session_opt_in(self) -> None:
        provider_root = Path(__file__).resolve().parents[1]
        skills_root = provider_root.parents[1]
        policy = (
            provider_root / "references" / "project-template" / "AGENTS.md"
        ).read_text(encoding="utf-8")
        claude_policy = (
            provider_root / "references" / "project-template" / "CLAUDE.md"
        ).read_text(encoding="utf-8")
        contract = (provider_root / "CONTRACT.md").read_text(encoding="utf-8")
        adapter = (
            skills_root
            / "auto-code-generator"
            / "references"
            / "execution-providers"
            / "sol-luna.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Luna 默认关闭", policy)
        self.assertIn("当前会话", policy)
        self.assertIn("luna-models.json", policy)
        self.assertNotIn("--user-triggered", policy)
        self.assertNotIn("字段：非空内容", policy)
        self.assertNotIn("推荐闭环", policy)

        for content in (claude_policy, contract):
            self.assertIn("Luna 默认关闭", content)
            self.assertIn("--user-triggered", content)
            self.assertIn("字段：非空内容", content)
            for field in sol_luna.TASK_BRIEF_FIELDS:
                self.assertIn(field, content)

        self.assertIn("当前会话", adapter)
        self.assertIn("--user-triggered", adapter)
        self.assertIn("backend=codex", adapter)
        self.assertIn("backend=claude", adapter)
        self.assertIn("codex exec", adapter)
        for field in sol_luna.TASK_BRIEF_FIELDS:
            self.assertIn(field, adapter)

    def test_provider_contract_names_real_administration_entrypoints(self) -> None:
        provider_root = Path(__file__).resolve().parents[1]
        contract = (provider_root / "CONTRACT.md").read_text(encoding="utf-8")

        self.assertIn("scripts/bootstrap.sh", contract)
        for command in (
            "status",
            "models",
            "mode",
            "model",
            "configure-claude",
            "sync",
            "audit",
            "smoke",
        ):
            self.assertIn(f"`{command}`", contract)
        self.assertNotIn("`setup`、`status`、`config`", contract)
        self.assertIn("`luna-models.json`", contract)
        self.assertIn("第一项是默认模型", contract)
        self.assertIn("`gpt-5.6-luna`", contract)
        self.assertIn("`gpt-5.3-codex-spark`", contract)

    def test_project_template_does_not_pin_sol_or_native_subagent_model(self):
        provider_root = Path(__file__).resolve().parents[1]
        template = provider_root / "references" / "project-template"

        self.assertFalse((template / ".codex" / "config.toml").exists())
        self.assertEqual([], list((template / ".codex" / "agents").glob("*.toml")))
        self.assertFalse((provider_root / "scripts" / "prepare-luna-catalog.sh").exists())

    def test_replacing_custom_role_creates_unique_recoverable_backups(self):
        target_dir = self.home / ".claude" / "agents"
        target_dir.mkdir(parents=True)
        target = target_dir / "luna-scout.md"
        target.write_text("first custom", encoding="utf-8")

        first = sol_luna.sync_roles(
            "global", self.project, self.home, replace_custom=True
        )
        first_action = next(item["action"] for item in first if item["role"] == "scout")
        first_backups = sorted(target_dir.glob("luna-scout.md.*.bak"))

        target.write_text("second custom", encoding="utf-8")
        second = sol_luna.sync_roles(
            "global", self.project, self.home, replace_custom=True
        )
        second_action = next(item["action"] for item in second if item["role"] == "scout")
        second_backups = sorted(target_dir.glob("luna-scout.md.*.bak"))

        self.assertIn("replaced", first_action)
        self.assertIn("replaced", second_action)
        self.assertEqual(1, len(first_backups))
        self.assertEqual(2, len(second_backups))
        self.assertEqual(
            {"first custom", "second custom"},
            {path.read_text(encoding="utf-8") for path in second_backups},
        )


if __name__ == "__main__":
    unittest.main()
