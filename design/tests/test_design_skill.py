import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN_SKILL = ROOT / "design" / "SKILL.md"
AGENTS = ROOT / "AGENTS.md"
UI_UX_SKILL = ROOT / "ui-ux-pro-max" / "SKILL.md"


def section(text: str, heading: str, next_heading: str) -> str:
    pattern = rf"^{re.escape(heading)}\s*$.*?(?=^{re.escape(next_heading)}\s*$)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"缺少章节: {heading}")
    return match.group(0)


class DesignSkillContractTest(unittest.TestCase):
    def test_design_router_has_exact_skill_mappings(self) -> None:
        content = DESIGN_SKILL.read_text(encoding="utf-8")
        expected_routes = (
            "| `ui-ux-pro-max` | UI/UX 知识检索、评审、设计系统建议与实现指导；不直接负责项目文件修改 |",
            "| `frontend-design` | 创建或修改实际前端界面、页面与组件 |",
            "| `drawio-skill` | 流程图、架构图、UML、ER 与 Draw.io 产物 |",
            "| `visualize:visualize` | 对话内交互式可视化、图表、模拟器与解释工具 |",
            "| `presentations:Presentations` / `documents:documents` / `pdf:pdf` | 对应办公文档产物 |",
        )
        for route in expected_routes:
            with self.subTest(route=route):
                self.assertIn(route, content)

    def test_design_router_is_thin_and_single_owner(self) -> None:
        content = DESIGN_SKILL.read_text(encoding="utf-8")
        required_contracts = (
            "用户显式指定具体 Skill 时直接服从",
            "每个任务只选择一个主 Skill",
            "系统或产品问题定义、架构决策与重构方法进入 `method-router`",
            "视觉、交互、图示或办公文档产物明确时由 `design` 直接路由",
            "只执行所选主 Skill 的验收合同",
            "不建立第二套生命周期、任务状态或 Git 权限",
        )
        for contract in required_contracts:
            with self.subTest(contract=contract):
                self.assertIn(contract, content)

        forbidden_leaf_details = ("44px", "WCAG", "Tailwind", "Lucide", "CSS token")
        for detail in forbidden_leaf_details:
            with self.subTest(detail=detail):
                self.assertNotIn(detail, content)

    def test_agents_routes_design_domain_only_to_parent(self) -> None:
        content = AGENTS.read_text(encoding="utf-8")
        design_section = section(content, "## 设计能力", "## 方法论体系")
        self.assertIn(
            "| `design` | 设计领域统一入口；按产物和阶段路由到具体 Skill |",
            design_section,
        )
        for leaf in ("ui-ux-pro-max", "frontend-design", "drawio-skill"):
            with self.subTest(leaf=leaf):
                self.assertNotIn(f"| `{leaf}` |", design_section)
        self.assertIn(
            "系统或产品问题定义、架构决策与重构方法进入 `method-router`；视觉、交互、图示或办公文档产物明确时进入 `design`。",
            design_section,
        )

    def test_ui_ux_leaf_is_guidance_only_and_uses_portable_script_path(self) -> None:
        content = UI_UX_SKILL.read_text(encoding="utf-8")
        frontmatter = content.split("---", 2)[1]
        self.assertNotIn("building", frontmatter)
        self.assertNotIn("fixing interfaces", frontmatter)
        self.assertIn(
            "When the task requires editing UI code, use `frontend-design` as the primary Skill",
            content,
        )
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", content)
        self.assertIn("<ui-ux-pro-max-skill-dir>/scripts/search.py", content)
        self.assertIn(
            "Resolve `<ui-ux-pro-max-skill-dir>` to the absolute directory containing this `SKILL.md`",
            content,
        )
        self.assertNotIn("Then synthesize the design system + detailed searches and implement.", content)
        self.assertIn("## Before Delivering Native/Mobile App UI", content)
        self.assertNotIn("`r`n", content)

    def test_agents_preserves_crlf(self) -> None:
        data = AGENTS.read_bytes()
        without_crlf = data.replace(b"\r\n", b"")
        self.assertNotIn(b"\n", without_crlf)

    def test_leaf_skills_remain_top_level_compatibility_entries(self) -> None:
        for name in ("ui-ux-pro-max", "frontend-design", "drawio-skill"):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name / "SKILL.md").is_file())
                self.assertFalse((ROOT / "design" / name).exists())


if __name__ == "__main__":
    unittest.main()
