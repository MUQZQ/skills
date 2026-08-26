# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
AUTO_ROOT = SKILLS_ROOT / "orchestration" / "auto-code-generator"
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
            "Luna 默认开启",
            "mode=off",
            "--user-triggered",
            "完整内聚场景组",
            "六字段任务卡",
            "不得拆分 RED、GREEN、REFACTOR",
            "充分利用可用卡槽",
            "领导协调、依赖确认、证据",
            "安全隔离证据不足时串行优先",
            "任务不清晰先问 Sol",
            "NEEDS_CONTEXT` / `NEEDS_COORDINATION",
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
            "只用 Sol",
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

        default_auto = next(
            item
            for item in evals
            if item["name"] == "no_view_and_default_auto_luna"
        )
        self.assertIn("native_spawn", default_auto["expected_output"])

        explicit_off = next(
            item for item in evals if item["name"] == "explicit_sol_only_disables_luna"
        )
        self.assertIn("只用 Sol", explicit_off["prompt"])
        self.assertIn("不调用 native_spawn", explicit_off["expected_output"])
        self.assertIn("codex_exec", explicit_off["expected_output"])

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

    def test_shared_dag_method_and_auto_code_projection_are_explicit(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        router = (SKILLS_ROOT / "method-router" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        mapping = (
            SKILLS_ROOT / "method-router" / "references" / "method-mapping.yaml"
        ).read_text(encoding="utf-8")
        management = (
            SKILLS_ROOT / "method-router" / "management-collaboration" / "SKILL.md"
        ).read_text(encoding="utf-8")
        dag_method_path = (
            SKILLS_ROOT
            / "method-router"
            / "management-collaboration"
            / "references"
            / "dag-scheduling.md"
        )
        self.assertTrue(dag_method_path.is_file())
        dag_method = dag_method_path.read_text(encoding="utf-8")
        evals = json.loads(
            (AUTO_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )["evals"]
        eval_by_name = {item["name"]: item for item in evals}

        for phrase in ("DAG", "有向无环图", "依赖图", "拓扑", "关键路径"):
            self.assertIn(phrase, router)
            self.assertIn(phrase, mapping)
        self.assertIn("references/dag-scheduling.md", management)
        for phrase in (
            "u → v",
            "未知节点",
            "自依赖",
            "环路径",
            "NEEDS_COORDINATION",
            "图收缩",
            "ready_queue",
            "完成事件驱动",
            "不等待同一拓扑层",
            "关键路径剩余长度",
            "只阻塞失败节点的后继",
            "eligible(node, running, reservations)",
            "原子登记",
        ):
            self.assertIn(phrase, dag_method)
        for phrase in (
            "task DAG",
            "场景组 DAG",
            "五项隔离门禁",
            "../../method-router/management-collaboration/references/dag-scheduling.md",
            "完成事件驱动",
            "ready_queue",
            "不等待同一拓扑层全部结束",
            "缩短关键路径和总执行时长",
            "不以填满卡槽或最大化并发数为目标",
            "部分 task 合格不能释放依赖整个场景组的后继",
        ):
            self.assertIn(phrase, skill)
        self.assertTrue(
            {
                "cyclic_dependency_blocks",
                "diamond_dependency_waves",
                "scenario_group_graph_contraction",
                "contraction_introduced_cycle_replans",
                "same_wave_write_conflict",
                "ready_queue_releases_successor_immediately",
                "partial_group_acceptance_does_not_release_successor",
                "running_reservation_blocks_newly_ready_successor",
            }.issubset(eval_by_name)
        )
        release_eval = eval_by_name["ready_queue_releases_successor_immediately"]
        self.assertIn("A 已由 Sol 验收", release_eval["prompt"])
        self.assertIn("立即释放 C", release_eval["expected_output"])
        self.assertIn("不等待 B", release_eval["expected_output"])
        partial_eval = eval_by_name[
            "partial_group_acceptance_does_not_release_successor"
        ]
        self.assertIn("不能释放 C", partial_eval["expected_output"])
        self.assertIn("重算", partial_eval["expected_output"])
        reservation_eval = eval_by_name[
            "running_reservation_blocks_newly_ready_successor"
        ]
        self.assertIn("继续等待", reservation_eval["expected_output"])
        self.assertIn("预留", reservation_eval["expected_output"])

    def test_fallback_archive_not_applicable_can_reach_authorized_commit(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        eval_names = {
            item["name"]
            for item in json.loads(
                (AUTO_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
            )["evals"]
        }

        for phrase in (
            "archive=SUCCESS | N/A | FAILED",
            "archive=N/A",
            "VERIFIED + archive SUCCESS/N/A + 独立 Git 授权",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("fallback_verified_local_commit_without_archive", eval_names)

    def test_incremental_delivery_checkpoint_commit_contract(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        evals = json.loads(
            (AUTO_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )["evals"]
        eval_by_name = {item["name"]: item for item in evals}

        for phrase in (
            "INCREMENTAL_CHECKPOINT",
            "AUTHORIZED_COMMIT_SET",
            "完整验收的交付切片",
            "混合未完成任务",
            "精确暂存快照",
            "reviewed_tree",
            "COMMIT_TREE_MISMATCH",
            "恰好一个 parent",
            "Apply 内 checkpoint",
            "最终 closeout",
            "更新完整 Target baseline",
            "不触发归档",
            "无剩余授权内 diff",
            "提交失败 <状态/原因>",
        ):
            self.assertIn(phrase, skill)

        positive = eval_by_name["incremental_checkpoint_after_accepted_slice"]
        self.assertIn("做完一部分", positive["prompt"])
        for phrase in (
            "LOCAL_COMMIT + INCREMENTAL_CHECKPOINT",
            "AUTHORIZED_COMMIT_SET",
            "staged snapshot",
            "Target baseline",
            "Change base",
            "不归档",
            "不推导 push",
        ):
            self.assertIn(phrase, positive["expected_output"])

        mixed = eval_by_name["incremental_checkpoint_rejects_mixed_unfinished_file"]
        for phrase in (
            "不能把混合 A/B 改动的 manifest",
            "不能默认用补丁暂存",
            "精确暂存快照",
            "不提交",
            "不创建空提交",
        ):
            self.assertIn(phrase, mixed["expected_output"])

        drift = eval_by_name["incremental_checkpoint_rejects_index_drift"]
        for phrase in (
            "reviewed_tree",
            "紧邻 commit 前",
            "拒绝进行中的 merge/rebase/cherry-pick/revert",
            "恰好一个 parent",
            "parent 等于 pre_commit_head",
            "COMMIT_TREE_MISMATCH",
            "不得自动 amend",
            "不得 push",
        ):
            self.assertIn(phrase, drift["expected_output"])

        closeout = eval_by_name["incremental_checkpoint_finishes_with_closeout"]
        for phrase in (
            "Stage 4/5",
            "最终 closeout",
            "VERIFIED",
            "archive=SUCCESS",
            "不创建空 commit",
            "checkpoint hashes",
            "先执行最终 closeout",
            "再输出包含最终 hash/status 的最终报告",
            "hash/status",
        ):
            self.assertIn(phrase, closeout["expected_output"])

    def test_time_management_reaches_assignment_provider_and_result_contract(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        adapter = (
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md"
        ).read_text(encoding="utf-8")
        schema = json.loads(
            (PROVIDER_ROOT / "references" / "result-schema.json").read_text(
                encoding="utf-8"
            )
        )

        for phrase in (
            "time_management:",
            "timebox:",
            "critical_path:",
            "checkpoints:",
            "timeout_action:",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("六字段任务卡的“约束”", adapter)
        for phrase in (
            "runner 无关的统一返回验收规则",
            "原生和外部",
            "更新 tracker 前",
            "带 timebox 的结果不得使用 `N/A`",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("time_management", schema["required"])
        self.assertEqual(
            ["status", "timebox", "checkpoints", "timeout_action"],
            schema["properties"]["time_management"]["required"],
        )
        self.assertEqual(
            ["ON_TRACK", "CHECKPOINT", "TIMEBOX_EXPIRED", "N/A"],
            schema["properties"]["time_management"]["properties"]["status"][
                "enum"
            ],
        )


if __name__ == "__main__":
    unittest.main()
