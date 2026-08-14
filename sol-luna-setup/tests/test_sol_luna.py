import json
import os
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

    def write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_default_config_keeps_luna_off_and_uses_auto_model(self) -> None:
        config = sol_luna.resolve_config(self.project, self.home, {})

        self.assertEqual("off", config["mode"])
        self.assertEqual("auto", config["model"])
        self.assertEqual("deepseek-v4-flash", config["flash_model"])
        self.assertEqual("deepseek-v4-pro", config["pro_model"])
        self.assertEqual(
            "claude-haiku-4-5-20251001", config["flash_claude_model"]
        )
        self.assertEqual("claude-sonnet-4-6", config["pro_claude_model"])
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
        return_value={"modelUsage": {}, "result": "冒烟完成"},
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

    def test_smoke_rejects_legacy_ignore_mode_escape(self) -> None:
        with patch("sys.stderr", new_callable=StringIO):
            with self.assertRaises(SystemExit):
                sol_luna.build_parser().parse_args(["smoke", "--ignore-mode"])

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

    def test_auto_model_routes_known_claude_ids_and_expected_provider_ids(self):
        config = sol_luna.resolve_config(self.project, self.home, {})

        flash = sol_luna.resolve_model(config, "normal")
        pro = sol_luna.resolve_model(config, "high")

        self.assertEqual("haiku", flash.claude_model)
        self.assertEqual("deepseek-v4-flash", flash.provider_model)
        self.assertEqual("sonnet", pro.claude_model)
        self.assertEqual("deepseek-v4-pro", pro.provider_model)

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

    def test_status_model_routes_do_not_include_secrets(self):
        config = sol_luna.resolve_config(self.project, self.home, {})

        routes = sol_luna.describe_model_routes(config)

        self.assertEqual(
            {
                "flash": {
                    "claude_model": "haiku",
                    "override_model": "claude-haiku-4-5-20251001",
                    "provider_model": "deepseek-v4-flash",
                },
                "pro": {
                    "claude_model": "sonnet",
                    "override_model": "claude-sonnet-4-6",
                    "provider_model": "deepseek-v4-pro",
                },
            },
            routes,
        )

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

    def test_worker_does_not_use_bypass_permissions(self):
        config = sol_luna.resolve_config(
            self.project, self.home, {"SOL_LUNA_MODE": "auto"}
        )

        command = sol_luna.build_claude_command(
            role="worker",
            model="deepseek-v4-flash",
            prompt="实现有界任务",
            config=config,
        )

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

        for role in ("scout", "critic"):
            content = (template_dir / f"luna-{role}.md").read_text(encoding="utf-8")
            self.assertIn("tools: Read, Grep, Glob", content)

        tester = (template_dir / "luna-tester.md").read_text(encoding="utf-8")
        self.assertIn("tools: Read, Grep, Glob, Bash", tester)

    def test_project_policy_requires_user_triggered_session_opt_in(self) -> None:
        setup_root = Path(__file__).resolve().parents[1]
        policy = (
            setup_root / "references" / "project-template" / "AGENTS.md"
        ).read_text(encoding="utf-8")
        claude_policy = (
            setup_root / "references" / "project-template" / "CLAUDE.md"
        ).read_text(encoding="utf-8")
        skill = (setup_root / "SKILL.md").read_text(encoding="utf-8")

        for content in (policy, claude_policy, skill):
            self.assertIn("Luna 默认关闭", content)
            self.assertIn("--user-triggered", content)
            self.assertIn("字段：非空内容", content)
            for field in sol_luna.TASK_BRIEF_FIELDS:
                self.assertIn(field, content)

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
