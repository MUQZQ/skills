# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
AUTO_ROOT = SKILLS_ROOT / "orchestration" / "auto-code-generator"
PROVIDER_ROOT = SKILLS_ROOT / "_providers" / "sol-luna"


class AutoCodeGeneratorContractTests(unittest.TestCase):
    def test_luna_is_one_native_model_without_catalog_or_fallback(self) -> None:
        active_files = (
            AUTO_ROOT / "SKILL.md",
            AUTO_ROOT / "evals" / "evals.json",
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md",
            PROVIDER_ROOT / "CONTRACT.md",
        )

        for path in active_files:
            content = path.read_text(encoding="utf-8")
            self.assertIn("gpt-5.6-luna", content, path)
            for retired in (
                "deepseek",
                "DeepSeek",
                "gpt-5.3-codex-spark",
                "gpt-5.4-mini",
                "gpt-5.6-terra",
                "codex_exec",
                "claude_code",
                "modelOverrides",
            ):
                self.assertNotIn(retired, content, path)

        for path in (
            AUTO_ROOT / "SKILL.md",
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md",
            PROVIDER_ROOT / "CONTRACT.md",
        ):
            content = path.read_text(encoding="utf-8")
            self.assertIn("spawn_agent", content, path)
            self.assertIn('model="gpt-5.6-luna"', content, path)
            self.assertIn("reasoning_effort", content, path)
            self.assertIn('fork_turns="none"', content, path)
            self.assertIn("由 Sol 直接执行", content, path)

        adapter = (
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md"
        ).read_text(encoding="utf-8")
        self.assertIn("宿主实际能力面", adapter)
        self.assertIn("宿主能力超出当前授权", adapter)
        self.assertIn("不换模", adapter)
        self.assertIn("不调用外部 runner", adapter)

    def test_luna_permission_gate_fails_closed_without_host_enforcement(self) -> None:
        contract_files = (
            AUTO_ROOT / "SKILL.md",
            AUTO_ROOT / "references" / "execution-providers" / "sol-luna.md",
            PROVIDER_ROOT / "CONTRACT.md",
        )

        for path in contract_files:
            content = path.read_text(encoding="utf-8")
            self.assertIn("任务卡不是安全边界", content, path)
            self.assertIn("只读工具白名单", content, path)
            self.assertIn("路径沙箱", content, path)
            self.assertIn("命令限制", content, path)
            self.assertIn("宿主无法强制", content, path)
            self.assertIn("由 Sol 直接执行", content, path)

        for retired in (
            "luna-models.json",
            "scripts/sol_luna.py",
            "scripts/bootstrap.sh",
            "tests/test_sol_luna.py",
            "references/project-template/AGENTS.md",
            "references/project-template/CLAUDE.md",
            "references/project-template/.claude/agents/luna-scout.md",
            "references/project-template/.claude/agents/luna-worker.md",
            "references/project-template/.claude/agents/luna-critic.md",
            "references/project-template/.claude/agents/luna-tester.md",
        ):
            self.assertFalse((PROVIDER_ROOT / retired).exists(), retired)

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
            "只用 Sol",
            "gpt-5.6-luna",
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

    def test_shared_provider_is_not_a_user_triggered_skill(self) -> None:
        self.assertTrue((PROVIDER_ROOT / "CONTRACT.md").is_file())
        self.assertFalse((PROVIDER_ROOT / "SKILL.md").exists())
        self.assertTrue((PROVIDER_ROOT / "references" / "result-schema.json").is_file())

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
            "统一返回验收规则",
            "原生 Luna",
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

    def test_demo_fast_is_default_and_spec_intent_selects_full(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for phrase in (
            "Delivery profile",
            "默认 Delivery profile 为 `DEMO_FAST`",
            "有 spec",
            "按 spec 实施",
            "完整模式",
            "全流程",
            "生产级",
            "选择 `FULL`",
            "不能从文件数量或 Agent 自行偏好切 FULL",
            "`FULL` 只改变交付深度，不改变生命周期所有者或风险档位",
            "同时输出生命周期所有者和 `Light | Standard | Strict` 风险档位",
            "只有 `DEMO_FAST` 要求一个可观察 Demo 目标和排除项",
            "`FULL` 使用 spec 或任务定义的可观察交付目标",
            "当前用户明确、正向的执行意图",
            "否定、引用、历史转述或仅讨论词语本身",
            "不能按关键词子串匹配",
        ):
            self.assertIn(phrase, skill)

    def test_demo_fast_preserves_minimum_tdd_and_blocks_strict_boundary(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for phrase in (
            "本地、可逆、单一可演示 happy path",
            "`DEMO_FAST` 只允许 `Light` 风险档位",
            "Standard 或 Strict",
            "风险档位门禁优先于 Delivery profile",
            "架构",
            "公共契约",
            "数据迁移",
            "安全权限隐私支付",
            "并发一致性",
            "不可逆外部操作",
            "项目强制门禁",
            "停止并报告 `BLOCKED`",
            "需要用户明确改为 spec/FULL",
            "不得静默升级 FULL",
            "只读基线和权限",
            "一个可观察 Demo 目标",
            "排除项",
            "RED → GREEN → REFACTOR",
            "可重复 smoke",
            "不虚构 RED",
            "聚焦自审",
            "项目原生聚焦测试",
            "本地 Demo smoke",
            "不能收敛为一个本地、可逆、单一可演示 happy path",
            "缩小 Demo 目标或明确改为 spec/FULL",
            "不得自行创建额外归档工件",
            "不能跳过项目官方归档、关闭或强制门禁",
            "意图冲突且无法消歧时结果为 `BLOCKED`",
        ):
            self.assertIn(phrase, skill)

    def test_demo_fast_report_is_not_production_or_git_authorization(self) -> None:
        skill = (AUTO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        evals = json.loads(
            (AUTO_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )["evals"]
        eval_by_name = {item["name"]: item for item in evals}

        for phrase in (
            "production_ready=false",
            "已验证 happy path",
            "延期项/风险",
            "运行 Demo 命令",
            "不推导 commit/push/PR/deploy",
            "Demo VERIFIED",
            "生产就绪",
            "Delivery profile：`DEMO_FAST | FULL`",
            "PLAN_ONLY",
            "validation=PENDING",
            "拟运行 Demo 命令",
            "PLAN_ONLY` 的最终结果为 `INCOMPLETE",
        ):
            self.assertIn(phrase, skill)

        self.assertEqual(len(evals), len(eval_by_name))
        self.assertEqual(len(evals), len({item["id"] for item in evals}))
        expected_ids = {
            "default_demo_fast_local_happy_path": 30,
            "demo_fast_strict_boundary_requires_explicit_full": 31,
            "explicit_spec_intent_uses_full": 32,
            "demo_fast_does_not_infer_git_or_production_ready": 33,
            "negated_or_quoted_spec_does_not_select_full": 34,
            "standard_without_full_intent_blocks": 35,
        }
        self.assertEqual(
            expected_ids,
            {name: eval_by_name[name]["id"] for name in expected_ids},
        )

        planned = eval_by_name["default_demo_fast_local_happy_path"]
        self.assertIn("INCOMPLETE", planned["expected_output"])
        self.assertIn("validation=PENDING", planned["expected_output"])
        self.assertIn("拟运行 Demo 命令", planned["expected_output"])
        self.assertNotIn("已验证 happy path", planned["expected_output"])

        blocked = eval_by_name["demo_fast_strict_boundary_requires_explicit_full"]
        self.assertIn("不得静默升级 FULL", blocked["expected_output"])
        self.assertIn("项目生命周期", blocked["expected_output"])
        self.assertIn("Strict", blocked["expected_output"])
        self.assertNotIn("Standard/Strict", blocked["expected_output"])

        full = eval_by_name["explicit_spec_intent_uses_full"]
        self.assertIn("选择 FULL", full["expected_output"])
        self.assertIn("生命周期所有者", full["expected_output"])
        self.assertIn("风险档位", full["expected_output"])

        demo = eval_by_name["demo_fast_does_not_infer_git_or_production_ready"]
        self.assertIn("无官方生命周期归档操作", demo["prompt"])
        self.assertIn("pnpm demo -- --scenario happy-path", demo["prompt"])
        self.assertIn("pnpm demo -- --scenario happy-path", demo["expected_output"])
        self.assertIn("不创建非官方归档", demo["expected_output"])

        negated = eval_by_name["negated_or_quoted_spec_does_not_select_full"]
        self.assertIn("不是按 spec 实施", negated["prompt"])
        self.assertIn("不能按子串", negated["expected_output"])
        self.assertIn("DEMO_FAST", negated["expected_output"])

        standard = eval_by_name["standard_without_full_intent_blocks"]
        self.assertIn("Standard", standard["prompt"])
        self.assertIn("BLOCKED", standard["expected_output"])
        self.assertIn("缩小为 Light", standard["expected_output"])
        self.assertIn("明确 spec/FULL", standard["expected_output"])


if __name__ == "__main__":
    unittest.main()
