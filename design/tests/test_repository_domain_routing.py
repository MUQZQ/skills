#!/usr/bin/env python3
"""Repository routing must follow AGENTS -> domain -> concrete Skill."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
DESIGN_SKILL = ROOT / "design" / "SKILL.md"
DESIGN_MAPPING = ROOT / "design" / "references" / "design-mapping.yaml"


class RepositoryDomainRoutingContractTest(unittest.TestCase):
    def test_agents_exposes_only_natural_domain_entries(self) -> None:
        content = AGENTS.read_text(encoding="utf-8")
        expected = {
            "自动化实施": "auto-code-generator",
            "代码质量": "code-review",
            "设计产物": "design",
            "方法论": "method-router",
            "Git 分支": "branch-manager",
        }
        self.assertIn("AGENTS.md → 领域模块 → 具体 Skill", content)
        for domain, router in expected.items():
            self.assertIn(f"| {domain} | `{router}` |", content)
        self.assertIn("专业单用途 Skill", content)

    def test_design_mapping_is_v1_source_of_truth(self) -> None:
        content = DESIGN_MAPPING.read_text(encoding="utf-8")
        self.assertIn('version: "1.0"', content)
        self.assertIn("domain: design", content)
        self.assertIn("source_of_truth: true", content)
        for route, skill in {
            "ui_ux_guidance": "ui-ux-pro-max",
            "frontend_implementation": "frontend-design",
            "diagram": "drawio-skill",
            "interactive_visualization": "visualize:visualize",
            "presentation": "presentations:Presentations",
            "document": "documents:documents",
            "pdf": "pdf:pdf",
        }.items():
            self.assertIn(f"  {route}:", content)
            self.assertIn(f"primary_skill: {skill}", content)

    def test_design_router_loads_mapping_before_selecting_leaf(self) -> None:
        content = DESIGN_SKILL.read_text(encoding="utf-8")
        self.assertIn("references/design-mapping.yaml", content)
        self.assertIn("唯一权威路由映射", content)
        self.assertIn("先读取映射，再选择一个主 Skill", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
