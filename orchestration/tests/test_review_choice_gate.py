# -*- coding: utf-8 -*-

import json
import unittest
from pathlib import Path

ORCHESTRATION_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ORCHESTRATION_ROOT.parent


class ReviewChoiceGateTests(unittest.TestCase):
    def test_commit_review_requires_one_of_three_explicit_modes(self) -> None:
        workflow = (ORCHESTRATION_ROOT / "code-review-before-commit" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("不得自动启动 `code-review`", workflow)
        expected_prompt = """**本次提交前 Code Review 请选择：**

  1. 快速
  2. 不做
  3. 全量

  **直接回复 1、2 或 3。**"""
        self.assertIn("只询问一次", workflow)
        self.assertIn(expected_prompt, workflow)
        for number, mode in (("1", "快速"), ("2", "不做"), ("3", "全量")):
            self.assertIn(f"`{number}`/“{mode}”", workflow)
        self.assertIn("## 快速模式", workflow)
        self.assertIn("## 不做模式", workflow)
        self.assertIn("## 全量模式", workflow)
        self.assertIn("保持本次模式不变，只允许重试", workflow)

    def test_code_review_coordinator_is_not_commit_auto_triggered(self) -> None:
        coordinator = (REPOSITORY_ROOT / "code-review" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("不得把“用户请求 commit”本身当作自动触发条件", coordinator)
        self.assertIn("快速模式使用一个聚焦 Agent", coordinator)
        self.assertIn("全量审查必须同时执行安全、SOLID、代码坏味道、通用编码规范", coordinator)
        self.assertIn("提交前审查只使用 `git diff --cached --name-only`", coordinator)
        self.assertIn("独立审查请求若未指定深度，默认使用“全量”", coordinator)
        self.assertIn("用户指定的 commit/range/diff 可解析", coordinator)
        self.assertIn("只读历史 commit/range 审查和精确暂存快照审查不要求工作区清洁", coordinator)
        self.assertNotIn("工作区安全检查通过", coordinator)
        self.assertIn("将本轮标记为 `INCOMPLETE`", coordinator)

    def test_global_review_skills_follow_the_coordinator_mode(self) -> None:
        coordinator = (REPOSITORY_ROOT / "code-review" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        fast_mode_triggers = {
            "solid-principles": "架构设计或结构重构",
            "code-smells": "坏味道治理或结构重构",
        }
        for skill_name, trigger in fast_mode_triggers.items():
            policy = (REPOSITORY_ROOT / "code-review" / skill_name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            activation = policy.split("## 何时激活", maxsplit=1)[1].split(
                "## 已激活后的重点场景", maxsplit=1
            )[0]
            self.assertIn("模式门禁只有两条", activation)
            self.assertIn("全量代码审查时始终激活", activation)
            self.assertIn(
                f"快速模式仅在 `code-review` 协调器明确判定变更涉及{trigger}时激活",
                activation,
            )
            self.assertIn("不得根据后续重点场景自行扩大范围", activation)
            self.assertNotIn("任何代码审查时都应用此规则", policy)
            self.assertIn(
                f"快速模式追加 `{skill_name}` 的唯一条件：变更明确涉及{trigger}",
                coordinator,
            )
            self.assertIn(
                f'| **全量审查；快速模式在“变更明确涉及{trigger}”时追加** | `{skill_name}` |',
                coordinator,
            )

        self.assertIn(
            "快速模式以安全审查与通用编码规范为基础，并在满足唯一条件时追加 "
            "SOLID 或代码坏味道规则；所有适用规则合并到单轮聚焦审查",
            coordinator,
        )
        self.assertIn(
            "快速=安全+通用规范，并继续评估 SOLID/坏味道的唯一追加条件；"
            "全量=安全+SOLID+坏味道+通用规范",
            coordinator,
        )
        self.assertNotIn("快速模式只将安全审查与通用编码规范合并到单轮聚焦审查", coordinator)
        self.assertNotIn(
            "快速=安全+通用规范，全量=安全+SOLID+坏味道+通用规范",
            coordinator,
        )

    def test_root_policy_uses_the_same_numbered_choice_gate(self) -> None:
        policy = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("提交前审查选择门禁", policy)
        self.assertIn("1. 快速 / 2. 不做 / 3. 全量", policy)
        self.assertIn("不得自动开启 `code-review`", policy)
        self.assertNotIn("提交前必须通过 `code-review`", policy)

    def test_registry_describes_choice_gate_instead_of_automatic_review(self) -> None:
        registry = json.loads((REPOSITORY_ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8"))
        description = registry["domains"]["orchestration"]["skills"]["code-review-before-commit"]["description"]

        self.assertIn("只询问一次", description)
        self.assertIn("1. 快速 / 2. 不做 / 3. 全量", description)
        self.assertIn("不得自动开启代码审查", description)
        self.assertNotIn("自动化审查工作流", description)


if __name__ == "__main__":
    unittest.main()
