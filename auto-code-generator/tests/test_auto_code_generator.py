from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]
AUTO_ROOT = SKILLS_ROOT / "auto-code-generator"
PROVIDER_ROOT = SKILLS_ROOT / "_providers" / "sol-luna"


class AutoCodeGeneratorContractTests(unittest.TestCase):
    def test_maintained_view_initialization_and_drift_contract_is_explicit(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for phrase in (
            "维护视图契约",
            "已有 change 投影",
            "有效当前维护视图",
            "schema 全项目模板",
            "已存在但损坏",
            "结构有效不代表语义正确",
            "prospective current view",
        ):
            self.assertIn(phrase, skill)

    def test_sol_luna_adapter_preserves_a_cohesive_scenario_group(self) -> None:
        adapter = (
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md"
        ).read_text(encoding="utf-8")

        for phrase in (
            "当前会话显式同意",
            "--user-triggered",
            "完整内聚场景组",
            "六字段任务卡",
            "不得拆分 RED、GREEN、REFACTOR",
            "provider 不适用",
        ):
            self.assertIn(phrase, adapter)

    def test_codex_backend_prefers_native_runner_without_model_substitution(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        adapter = (
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md"
        ).read_text(encoding="utf-8")
        contract = (PROVIDER_ROOT / "CONTRACT.md").read_text(encoding="utf-8")
        project_policy = (
            PROVIDER_ROOT / "references" / "project-template" / "CLAUDE.md"
        ).read_text(encoding="utf-8")
        controller = (PROVIDER_ROOT / "scripts" / "sol_luna.py").read_text(
            encoding="utf-8"
        )

        for content in (adapter, contract):
            self.assertIn("native_spawn", content)
            self.assertIn("codex_exec", content)
            self.assertNotIn("不使用原生 `spawn_agent`", content)

        for phrase in (
            "当前用户消息",
            "当前会话暴露的原生 allowlist",
            "`spawn_agent` 工具说明",
            "精确模型",
            "仅在启动前",
            "不得静默换模",
            "返回 Agent 标识",
        ):
            self.assertIn(phrase, adapter)

        for phrase in (
            "直接调用 `spawn_agent`",
            "fork_turns=\"none\"",
            "外部 runner",
        ):
            self.assertIn(phrase, skill)
        self.assertNotIn("spawn_agent", controller)

        self.assertIn("原生优先", project_policy)
        self.assertNotIn("native_spawn", project_policy)
        self.assertNotIn("codex_exec", project_policy)

        evals = json.loads(
            (AUTO_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )["evals"]
        native_first = next(
            item for item in evals if item["name"] == "codex_native_first_runner"
        )
        self.assertIn("gpt-5.3-codex-spark", native_first["prompt"])
        self.assertIn("native only", native_first["expected_output"])
        self.assertIn("权限边界", native_first["expected_output"])

        unauthorized = next(
            item
            for item in evals
            if item["name"] == "no_view_and_unauthorized_luna_do_not_invent"
        )
        self.assertIn("native_spawn", unauthorized["expected_output"])
        self.assertIn("codex_exec", unauthorized["expected_output"])

        started_failure = next(
            item
            for item in evals
            if item["name"] == "started_native_failure_does_not_fallback"
        )
        self.assertIn("Agent 标识", started_failure["prompt"])
        self.assertIn("禁止调用 codex_exec", started_failure["expected_output"])

        permission_mismatch = next(
            item
            for item in evals
            if item["name"] == "native_permission_mismatch"
        )
        self.assertIn("权限能力", permission_mismatch["prompt"])
        self.assertIn("同一精确模型", permission_mismatch["expected_output"])

    def test_shared_provider_is_not_a_user_triggered_skill(self) -> None:
        self.assertTrue((PROVIDER_ROOT / "CONTRACT.md").is_file())
        self.assertFalse((PROVIDER_ROOT / "SKILL.md").exists())
        self.assertTrue((PROVIDER_ROOT / "scripts" / "sol_luna.py").is_file())
        self.assertTrue((PROVIDER_ROOT / "tests" / "test_sol_luna.py").is_file())

    def test_shared_provider_retains_claude_roles_without_native_catalog(self) -> None:
        required_files = (
            ".gitignore",
            "scripts/bootstrap.sh",
            "references/project-template/AGENTS.md",
            "references/project-template/CLAUDE.md",
            "references/project-template/.claude/agents/luna-scout.md",
            "references/project-template/.claude/agents/luna-worker.md",
            "references/project-template/.claude/agents/luna-critic.md",
            "references/project-template/.claude/agents/luna-tester.md",
        )

        missing = [path for path in required_files if not (PROVIDER_ROOT / path).is_file()]
        self.assertEqual([], missing)
        for retired in (
            "scripts/prepare-luna-catalog.sh",
            "references/project-template/scripts/prepare-luna-catalog.sh",
            "references/project-template/.codex/config.toml",
            "references/project-template/.codex/agents/luna_scout.toml",
            "references/project-template/.codex/agents/luna_worker.toml",
            "references/project-template/.codex/agents/luna_critic.toml",
            "references/project-template/.codex/agents/luna_tester.toml",
        ):
            self.assertFalse((PROVIDER_ROOT / retired).exists(), retired)

    def test_provider_result_statuses_match_auto_code_contract(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        schema = json.loads(
            (PROVIDER_ROOT / "references" / "result-schema.json").read_text(
                encoding="utf-8"
            )
        )
        group_statuses = schema["properties"]["group_status"]["enum"]
        task_statuses = schema["properties"]["task_results"]["items"]["properties"][
            "status"
        ]["enum"]

        self.assertEqual(
            [
                "DONE",
                "DONE_WITH_CONCERNS",
                "NEEDS_CONTEXT",
                "NEEDS_COORDINATION",
                "BLOCKED",
            ],
            group_statuses,
        )
        self.assertEqual(["SATISFIED", "UNSATISFIED", "BLOCKED"], task_statuses)
        for status in (*group_statuses, *task_statuses):
            self.assertIn(f"`{status}`", skill)


if __name__ == "__main__":
    unittest.main()
