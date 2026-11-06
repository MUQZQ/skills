import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CODE_REVIEW_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = CODE_REVIEW_ROOT.parent


class SharedCodeReviewPolicyTests(unittest.TestCase):
    def test_shared_review_does_not_embed_qeda_project_rules(self) -> None:
        coordinator = (CODE_REVIEW_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse((CODE_REVIEW_ROOT / "qeda-integration").exists())
        self.assertNotIn("qeda-integration", coordinator)
        self.assertNotIn("QEDA 测试集成", coordinator)
        self.assertIn("项目特定审查规则由目标项目提供", coordinator)

    def test_evidence_has_one_owner_and_acceptance_has_a_separate_boundary(self) -> None:
        coordinator = (CODE_REVIEW_ROOT / "SKILL.md").read_text(encoding="utf-8")
        evidence = (REPOSITORY_ROOT / "method-router/evidence-driven-dev/SKILL.md").read_text(
            encoding="utf-8"
        )
        standards = (REPOSITORY_ROOT / "coding-standards/SKILL.md").read_text(encoding="utf-8")
        for state in ("已确认", "已排除", "待验证"):
            self.assertIn(f"| {state} |", coordinator)
        self.assertIn("严重程度与证据状态独立", coordinator)
        self.assertIn("先判断完成度，再应用门槛", coordinator)
        self.assertIn("完整系统验收由 `evidence-driven-dev` 补充", coordinator)
        self.assertIn("证据状态与快照绑定统一引用 `code-review`", evidence)
        self.assertIn("不能用代码审查 COMPLETE 替代系统验收", evidence)
        self.assertIn("证据状态与绑定规则统一引用 `code-review`", standards)
        self.assertNotIn("代码阅读 < 只读查询 < 自动化测试 < 真实环境实测", evidence)

    def test_quality_and_incremental_coverage_are_explicit(self) -> None:
        coordinator = (CODE_REVIEW_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for dimension in (
            "行为正确性与回归",
            "安全",
            "可靠性与可用性",
            "效率与资源消耗",
            "可维护性",
            "语言与通用编码规范",
            "可移植性与兼容性",
        ):
            self.assertIn(f"| {dimension} |", coordinator)
        self.assertIn("缺少证据不是 N/A", coordinator)
        self.assertIn("未修改的消费者", coordinator)
        self.assertIn("最终组合快照", coordinator)
        self.assertIn("同一行的 SSRF 与缺少超时分别报告", coordinator)
        self.assertIn("树哈希只标识目标，不能证明测试实际运行了它", coordinator)

    def test_frozen_scenarios_cover_safety_and_normal_controls(self) -> None:
        corpus = json.loads((CODE_REVIEW_ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        self.assertEqual(corpus["skill_name"], "code-review")
        evals = corpus["evals"]
        self.assertEqual(len(evals), len({item["id"] for item in evals}))
        decisions = [entry for item in evals for entry in item["expected_decisions"]]
        self.assertEqual(len(decisions), len({entry["case_id"] for entry in decisions}))
        cases = {entry["case_id"]: entry for entry in decisions}
        required = {
            "repair_only",
            "reauthorized_review",
            "unrelated_worktree",
            "unselected",
            "partial_staging",
            "relabel",
            "skip",
            "quick_advisory",
            "no_commit_authority",
            "pending_auth",
            "vague_security",
            "self_review",
            "static_bug",
            "same_source",
            "normal_tsx",
            "combined_regression",
            "fifth_round",
            "stale_config",
            "no_progress",
            "full_p1",
            "final_clean",
        }
        self.assertEqual(set(cases), required)
        for item in evals:
            self.assertEqual(len(item["expectations"]), len(item["expected_decisions"]))
            self.assertTrue(item["prompt"])
        for case_id in (
            "partial_staging",
            "pending_auth",
            "self_review",
            "same_source",
            "fifth_round",
            "stale_config",
            "no_progress",
        ):
            self.assertEqual(cases[case_id]["status"], "INCOMPLETE")
            self.assertIs(cases[case_id]["can_commit"], False)
        for case_id in ("skip", "quick_advisory", "vague_security", "final_clean"):
            self.assertIs(cases[case_id]["can_commit"], True)
        self.assertIs(cases["relabel"]["can_commit"], False)
        self.assertIs(cases["no_commit_authority"]["can_commit"], False)

    @unittest.skipUnless(shutil.which("git"), "需要 Git 才能复现部分暂存场景")
    def test_worktree_success_does_not_validate_staged_source(self) -> None:
        # 在临时仓库真实制造“暂存缺陷、工作树修复”，证明两份运行结果不能互换。
        with tempfile.TemporaryDirectory(prefix="review-snapshot-") as directory:
            workspace = Path(directory)

            def git(*args: str) -> str:
                return subprocess.run(
                    ["git", *args],
                    cwd=workspace,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=15,
                ).stdout

            git("init", "-q")
            source = workspace / "logic.py"
            source.write_text(
                "def remaining(balance, debit):\n    return balance - debit\n",
                encoding="utf-8",
                newline="",
            )
            git("add", "logic.py")
            target_tree = git("write-tree").strip()
            staged_source = git("show", ":logic.py")
            source.write_text(
                "def remaining(balance, debit):\n    return max(0, balance - debit)\n",
                encoding="utf-8",
                newline="",
            )
            command = "from logic import remaining; assert remaining(1, 2) >= 0"
            worktree_run = subprocess.run(
                [sys.executable, "-B", "-c", command],
                cwd=workspace,
                check=False,
                capture_output=True,
                timeout=15,
            )
            staged_run = subprocess.run(
                [sys.executable, "-c", staged_source + "\nassert remaining(1, 2) >= 0\n"],
                cwd=workspace,
                check=False,
                capture_output=True,
                timeout=15,
            )

            self.assertEqual(worktree_run.returncode, 0)
            self.assertNotEqual(staged_run.returncode, 0)
            self.assertIn(b"AssertionError", staged_run.stderr)
            self.assertEqual(git("write-tree").strip(), target_tree)
            self.assertNotEqual(source.read_text(encoding="utf-8"), staged_source)


if __name__ == "__main__":
    unittest.main()
