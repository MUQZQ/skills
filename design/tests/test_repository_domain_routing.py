#!/usr/bin/env python3
"""Repository routing must follow AGENTS -> domain -> concrete Skill."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
DESIGN_SKILL = ROOT / "design" / "SKILL.md"
DESIGN_MAPPING = ROOT / "design" / "references" / "design-mapping.yaml"


class RepositoryDomainRoutingContractTest(unittest.TestCase):
    def test_agents_references_repository_mapping_without_domain_duplication(self) -> None:
        content = AGENTS.read_text(encoding="utf-8")
        self.assertIn("AGENTS.md → 领域模块 → 具体 Skill", content)
        self.assertIn("`skill-domain-mapping.yaml`", content)
        self.assertNotIn("| 设计与视觉 | `design` |", content)

    def test_design_mapping_is_v1_source_of_truth(self) -> None:
        content = DESIGN_MAPPING.read_text(encoding="utf-8")
        self.assertIn('version: "1.0"', content)
        self.assertIn("domain: design", content)
        self.assertIn("source_of_truth: true", content)
        self.assertIn("registry_source: ../../skill-domain-mapping.yaml", content)
        self.assertIn("resolution: platform_skill_registry", content)
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
