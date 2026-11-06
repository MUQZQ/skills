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
        coordinator = (REPOSITORY_ROOT / "code-review" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("不得把“用户请求 commit”本身当作自动触发条件", coordinator)
        self.assertIn("快速模式使用一个聚焦 Agent", coordinator)
        self.assertIn("全量使用一个独立主审负责完整覆盖", coordinator)
        self.assertIn("全量始终加载这两份清单", coordinator)
        self.assertIn("提交前审查只使用 `git diff --cached --name-only`", coordinator)
        self.assertIn("独立审查未指定深度默认全量", coordinator)
        self.assertIn("用户指定的 commit/range/diff 可解析", coordinator)
        self.assertIn("只读历史 commit/range 审查和精确暂存快照审查不要求工作区清洁", coordinator)
        self.assertNotIn("工作区安全检查通过", coordinator)
        self.assertIn("将本轮标记为 `INCOMPLETE`", coordinator)

    def test_global_review_skills_follow_the_coordinator_mode(self) -> None:
        coordinator = (REPOSITORY_ROOT / "code-review" / "SKILL.md").read_text(encoding="utf-8")
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
                f"| 全量；快速涉及{trigger} | `{skill_name}` |",
                coordinator,
            )

        self.assertIn("安全与通用编码规范在两种模式均应用", coordinator)
        self.assertIn("检查维度不与 Agent 数量一一对应", coordinator)
        self.assertIn("主审必须未参与本轮实施/修复", coordinator)
        self.assertNotIn("所有匹配的专项 skill 与四项全局 skill 分别通过 Agent 执行", coordinator)

    def test_root_policy_routes_to_the_authoritative_choice_gate(self) -> None:
        # 根指令只引用领域注册表，具体选择门槛由编排域拥有。
        policy = (REPOSITORY_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        registry = json.loads(
            (REPOSITORY_ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        domain = registry["domains"]["orchestration"]
        mapping = json.loads(
            (REPOSITORY_ROOT / domain["routing_source"]).read_text(encoding="utf-8")
        )
        route = mapping["routes"]["code-review-before-commit"]
        target = domain["skills"][route["skill_name"]]

        self.assertIn("skill-domain-mapping.yaml", policy)
        self.assertNotIn("1. 快速 / 2. 不做 / 3. 全量", policy)
        self.assertEqual(target["path"], "orchestration/code-review-before-commit/SKILL.md")
        self.assertTrue((REPOSITORY_ROOT / target["path"]).is_file())

    def test_completion_precedes_commit_eligibility(self) -> None:
        workflow = (ORCHESTRATION_ROOT / "code-review-before-commit" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("确认缺陷数为零不替代完成度检查", workflow)
        self.assertIn("快速或全量，状态 INCOMPLETE", workflow)
        self.assertIn("最终快照 COMPLETE 且已确认 P0/P1 为零", workflow)
        self.assertIn("第五轮末才完成修复且仍需下一轮复审", workflow)
        self.assertIn("不执行第六轮、不提交", workflow)
        self.assertIn("连续两轮未关闭任何阻断/高风险待验证项", workflow)
        self.assertIn("紧邻 commit 前", workflow)
        self.assertIn("不能用含未暂存修复的工作树测试代替", workflow)

    def test_quick_repair_does_not_reuse_the_old_review(self) -> None:
        workflow = (ORCHESTRATION_ROOT / "code-review-before-commit" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("用户仅追加修复授权", workflow)
        self.assertIn("分别报告 S0 审查和 S1 修复验证", workflow)
        self.assertIn("保留原提交阻断", workflow)
        self.assertIn("不重复索取已给出的授权", workflow)
        self.assertIn("未要求复审时不自行再跑 Code Review，也不提交", workflow)
        self.assertIn("无关的工作树变化不自动使结论失效", workflow)

    def test_registry_describes_choice_gate_instead_of_automatic_review(self) -> None:
        registry = json.loads(
            (REPOSITORY_ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        description = registry["domains"]["orchestration"]["skills"]["code-review-before-commit"][
            "description"
        ]

        self.assertIn("只询问一次", description)
        self.assertIn("1. 快速 / 2. 不做 / 3. 全量", description)
        self.assertIn("不得自动开启代码审查", description)
        self.assertNotIn("自动化审查工作流", description)


if __name__ == "__main__":
    unittest.main()
