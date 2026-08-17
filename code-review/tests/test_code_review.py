# -*- coding: utf-8 -*-

import unittest
from pathlib import Path


CODE_REVIEW_ROOT = Path(__file__).resolve().parents[1]


class SharedCodeReviewPolicyTests(unittest.TestCase):
    def test_shared_review_does_not_embed_qeda_project_rules(self) -> None:
        coordinator = (CODE_REVIEW_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertFalse((CODE_REVIEW_ROOT / "qeda-integration").exists())
        self.assertNotIn("qeda-integration", coordinator)
        self.assertNotIn("QEDA 测试集成", coordinator)
        self.assertIn("项目特定审查规则由目标项目提供", coordinator)


if __name__ == "__main__":
    unittest.main()
