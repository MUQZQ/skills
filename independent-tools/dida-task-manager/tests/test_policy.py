import unittest
from pathlib import Path


POLICY_FILE = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"


class DidaPolicyContractTest(unittest.TestCase):
    def test_task_data_cannot_be_read_by_implicit_invocation(self) -> None:
        content = POLICY_FILE.read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", content)
        self.assertNotIn("allow_implicit_invocation: true", content)

    def test_heartbeat_requires_explicit_user_authorization(self) -> None:
        skill = (POLICY_FILE.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("只有用户显式创建或启用的 heartbeat", skill)
        self.assertIn("不得由隐式调用启动", skill)

    def test_task_content_must_be_redacted_before_output(self) -> None:
        skill = (POLICY_FILE.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("最小必要字段", skill)
        self.assertIn("密码、Token、API Key", skill)
        self.assertIn("脱敏", skill)
        self.assertIn("不得写入日志、摘要或任务回写", skill)


if __name__ == "__main__":
    unittest.main()
