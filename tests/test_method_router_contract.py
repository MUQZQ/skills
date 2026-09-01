#!/usr/bin/env python3
"""Method-router configuration must resolve deterministically and stay documented."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "method-router" / "references" / "method-mapping.yaml"
METHOD_PATH = ROOT / "method-router" / "SKILL.md"
README_PATH = ROOT / "README.md"
DIAGRAM_PATH = ROOT / "skill-domain-architecture.drawio"
SOURCE_BASIS_PATH = ROOT / "method-router" / "references" / "munger-source-basis.md"
LEAF_SKILLS = (
    ("multidisciplinary-models", "多元思维模型", "multidisciplinary_models"),
    ("mental-model-lattice", "思维模型格栅", "mental_model_lattice"),
    ("inversion-thinking", "逆向思考", "inversion_thinking"),
    ("circle-of-competence", "能力圈", "circle_of_competence"),
    ("margin-of-safety", "安全边际", "margin_of_safety"),
    ("incentive-analysis", "激励机制分析", "incentive_analysis"),
    ("psychological-misjudgment", "心理误判检查", "psychological_misjudgment"),
    ("checklist-patience", "检查清单与耐心等待", "checklist_patience"),
)
LEAF_NAMES = tuple(item[0] for item in LEAF_SKILLS)
LEAF_REQUIRED_TERMS = {
    "multidisciplinary-models": ("具体机制", "不代替思维模型格栅"),
    "mental-model-lattice": ("不可比较", "unresolved"),
    "inversion-thinking": ("pre-mortem", "FTA"),
    "circle-of-competence": ("适用边界", "不能只凭熟悉感"),
    "margin-of-safety": ("阈值只能来自", "unknown", "不编造数值阈值"),
    "incentive-analysis": ("可观察的行为预测", "不推断人格或内心动机"),
    "psychological-misjudgment": ("1995_spoken", "2005 修订版", "25 项"),
    "checklist-patience": ("NEEDS_INPUT", "不自动创建提醒"),
}
OLD_COMPOSITE_NAME = "munger-mental-models"


def _scalar(value: str):
    value = value.strip().strip("'\"")
    if value == "true":
        return True
    if value == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _parse_routes(text: str) -> list[dict]:
    """Parse the deliberately small routes subset without adding a YAML dependency."""
    route_text = text.split("\nroutes:\n", 1)[1].split("\nskill_registry:\n", 1)[0]
    routes: list[dict] = []
    current: dict | None = None
    section = ""

    for line in route_text.splitlines():
        if line.startswith("- type: "):
            if current:
                routes.append(current)
            current = {
                "type": _scalar(line.split(":", 1)[1]),
                "condition": {},
                "chain": [],
            }
            section = ""
        elif current is None:
            continue
        elif line == "  condition: {}":
            section = ""
        elif line == "  condition:":
            section = "condition"
        elif line == "  chain:":
            section = "chain"
        elif line.startswith("  priority: "):
            current["priority"] = _scalar(line.split(":", 1)[1])
        elif section == "condition" and re.match(r"^    [a-z_]+:", line):
            key, value = line.strip().split(":", 1)
            current["condition"][key] = _scalar(value)
        elif section == "chain" and line.startswith("  - skill_name: "):
            current["chain"].append(_scalar(line.split(":", 1)[1]))
        elif line.startswith("  rationale: "):
            current["rationale"] = _scalar(line.split(":", 1)[1])
            section = ""

    if current:
        routes.append(current)
    return routes


def _resolve(routes: list[dict], context: dict, default_priority: int) -> dict:
    candidates = []
    for route in routes:
        if route["type"] != context["type"]:
            continue
        if all(context.get(key) == value for key, value in route["condition"].items()):
            candidates.append(route)
    if not candidates:
        raise LookupError(context)
    return max(
        candidates,
        key=lambda route: (
            route.get("priority", default_priority),
            len(route["condition"]),
        ),
    )


class MethodRouterContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mapping = MAPPING_PATH.read_text(encoding="utf-8")
        cls.method = METHOD_PATH.read_text(encoding="utf-8")
        cls.routes = _parse_routes(cls.mapping)

    def test_route_context_and_resolution_policy_are_explicit(self) -> None:
        for field in (
            "type",
            "urgency",
            "domain",
            "has_data",
            "complexity",
            "sub_type",
            "scope",
            "cynefin_pre",
        ):
            with self.subTest(field=field):
                self.assertRegex(
                    self.mapping,
                    rf"(?m)^    {field}: ",
                )
        self.assertIn("strategy: highest_priority_then_specificity", self.mapping)
        self.assertIn(
            "preprocess: execute_meta_route_when_cynefin_pre_true", self.mapping
        )
        self.assertIn("tie_breaker: ask_user_with_top_3", self.mapping)
        self.assertIn("no_match: type_fallback", self.mapping)

    def test_every_classified_type_has_a_fallback(self) -> None:
        classification = self.mapping.split("\nclassification:\n", 1)[1].split(
            "\nurgency:\n", 1
        )[0]
        classified_types = set(re.findall(r"(?m)^  ([a-z_]+):$", classification))
        fallback_text = self.mapping.split("\nfallbacks:\n", 1)[1].split(
            "\nroutes:\n", 1
        )[0]
        fallback_types = set(re.findall(r"(?m)^  ([a-z_]+):$", fallback_text))
        self.assertEqual(classified_types, fallback_types)
        self.assertEqual(
            {
                "diagnose",
                "decide",
                "design",
                "improve",
                "risk",
                "report",
                "manage",
                "goal",
                "learning",
            },
            classified_types,
        )

    def test_high_priority_routes_are_not_shadowed_by_generic_routes(self) -> None:
        default_priority_match = re.search(
            r"(?m)^  default_priority: (\d+)$", self.mapping
        )
        self.assertIsNotNone(default_priority_match)
        default_priority = int(default_priority_match.group(1))
        scenarios = (
            (
                {
                    "type": "diagnose",
                    "urgency": "critical",
                    "has_data": True,
                    "domain": "data",
                    "complexity": "high",
                    "sub_type": "multi_factor",
                },
                "ooda-loop",
            ),
            (
                {
                    "type": "diagnose",
                    "urgency": "normal",
                    "has_data": True,
                    "domain": "data",
                    "complexity": "high",
                    "sub_type": "multi_factor",
                },
                "fishbone",
            ),
            (
                {
                    "type": "diagnose",
                    "urgency": "normal",
                    "has_data": True,
                    "domain": "data",
                    "complexity": "high",
                },
                "mece",
            ),
            (
                {
                    "type": "diagnose",
                    "urgency": "normal",
                    "has_data": True,
                    "domain": "data",
                    "complexity": "normal",
                },
                "deep-analysis",
            ),
            (
                {
                    "type": "diagnose",
                    "urgency": "normal",
                    "has_data": False,
                    "domain": "general",
                    "complexity": "normal",
                },
                "5whys",
            ),
            (
                {
                    "type": "manage",
                    "sub_type": "structured_discussion",
                },
                "six-hats",
            ),
            ({"type": "manage", "sub_type": "personal_tasks"}, "gtd"),
            ({"type": "report", "sub_type": "feedback"}, "sbi"),
            ({"type": "report", "sub_type": "deep_retro"}, "double-loop"),
            ({"type": "design", "scope": "blank_slate"}, "discovery-sprint"),
            ({"type": "decide", "sub_type": "tech_selection"}, "adl-matrix"),
        )
        for context, expected in scenarios:
            with self.subTest(context=context):
                route = _resolve(self.routes, context, default_priority)
                self.assertEqual(expected, route["chain"][0])

        fishbone_route = _resolve(
            self.routes,
            {
                "type": "diagnose",
                "urgency": "normal",
                "has_data": "unknown",
                "domain": "general",
                "complexity": "normal",
                "sub_type": "multi_factor",
            },
            default_priority,
        )
        self.assertEqual(["fishbone", "5whys", "scqa"], fishbone_route["chain"])

    def test_data_driven_diagnosis_is_domain_gated(self) -> None:
        deep_routes = [
            route for route in self.routes if route["chain"][0] == "deep-analysis"
        ]
        self.assertEqual(1, len(deep_routes))
        self.assertEqual("data", deep_routes[0]["condition"].get("domain"))
        with self.assertRaises(LookupError):
            _resolve(
                self.routes,
                {
                    "type": "diagnose",
                    "urgency": "normal",
                    "has_data": True,
                    "domain": "code",
                    "complexity": "normal",
                },
                500,
            )

    def test_each_route_explains_choice_and_rejected_alternative(self) -> None:
        self.assertGreaterEqual(len(self.routes), 40)
        for route in self.routes:
            with self.subTest(route=route):
                rationale = route.get("rationale", "")
                self.assertIn("因为", rationale)
                self.assertIn("而非", rationale)
                self.assertNotIn("补充", rationale)

    def test_registry_and_route_references_match_the_root_authority(self) -> None:
        root_mapping = json.loads(
            (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        registered = {
            entry["skill_name"]
            for entry in root_mapping["domains"]["method-router"]["skills"].values()
        }
        registry_text = self.mapping.split("\nskill_registry:\n", 1)[1].split(
            "\ncomposition_rules:\n", 1
        )[0]
        declared = set(re.findall(r"(?m)^  - skill_name: ([a-z0-9-]+)$", registry_text))
        referenced = {
            skill_name for route in self.routes for skill_name in route["chain"]
        }
        self.assertEqual(registered, declared)
        self.assertTrue(referenced <= registered)

    def test_eight_leaf_skills_are_registered_with_physical_paths_and_decide_category(
        self,
    ) -> None:
        root_mapping = json.loads(
            (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        skills = root_mapping["domains"]["method-router"]["skills"]
        self.assertEqual(
            set(LEAF_NAMES), {name for name in skills if name in LEAF_NAMES}
        )
        for name, _, _ in LEAF_SKILLS:
            with self.subTest(skill=name):
                entry = skills[name]
                self.assertEqual(name, entry["skill_name"])
                self.assertEqual(f"method-router/{name}/SKILL.md", entry["path"])
                skill_path = ROOT / entry["path"]
                self.assertTrue(skill_path.is_file())
                self.assertIn(f"name: {name}", skill_path.read_text(encoding="utf-8"))
                evals_path = skill_path.parent / "evals" / "evals.json"
                self.assertTrue(evals_path.is_file())
                evals = json.loads(evals_path.read_text(encoding="utf-8"))
                self.assertEqual(name, evals["skill_name"])
                self.assertGreaterEqual(len(evals["evals"]), 1)
                self.assertGreaterEqual(
                    len(evals["evals"][0].get("expectations", [])),
                    3,
                )
        self.assertNotIn(OLD_COMPOSITE_NAME, skills)

        registry_text = self.mapping.split("\nskill_registry:\n", 1)[1].split(
            "\ncomposition_rules:\n", 1
        )[0]
        for name in LEAF_NAMES:
            with self.subTest(registry=name):
                self.assertRegex(
                    registry_text,
                    rf"(?ms)- skill_name: {name}\n    category: decide",
                )

    def test_each_leaf_skill_is_independently_executable_and_boundary_scoped(
        self,
    ) -> None:
        for name, title, _ in LEAF_SKILLS:
            skill = (ROOT / "method-router" / name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            with self.subTest(skill=name):
                self.assertIn(f"# {title}", skill)
                self.assertIn("## 输入", skill)
                self.assertIn("## 执行", skill)
                self.assertIn("## 输出", skill)
                self.assertIn("## 边界", skill)
                self.assertIn("munger-source-basis.md", skill)
                for term in LEAF_REQUIRED_TERMS[name]:
                    self.assertIn(term, skill)

    def test_shared_munger_source_basis_has_source_hierarchy_and_links(self) -> None:
        source = SOURCE_BASIS_PATH.read_text(encoding="utf-8")
        for source_term in (
            "来源层级",
            "1994",
            "Worldly Wisdom",
            "真实性",
            "1995",
            "2005",
            "Jacobi",
            "Graham",
            "Buffett-Munger",
            "编辑性组合",
            "检查清单+耐心等待",
            "https://press.stripe.com/poor-charlies-almanack",
            "https://mungerarchive.com/recordings/usc-1994-worldly-wisdom/",
            (
                "https://jamesclear.com/great-speeches/"
                "a-lesson-on-elementary-worldly-wisdom-by-charlie-munger"
            ),
            "https://www.rbcpa.com/wp-content/uploads/2017/01/Mungerspeech_june_95.pdf",
            "https://www.emit.org/munger.pdf",
        ):
            with self.subTest(source_term=source_term):
                self.assertIn(source_term, source)

    def test_eight_leaf_routes_are_narrow_unique_and_learning_does_not_hit(
        self,
    ) -> None:
        self.assertIn("version: '3.8'", self.mapping)
        self.assertIn("last_updated: '2026-09-01'", self.mapping)
        decide_block = self.mapping.split("\n  decide:\n", 1)[1].split(
            "\n  design:\n", 1
        )[0]
        for name, title, sub_type in LEAF_SKILLS:
            with self.subTest(route=name):
                route = _resolve(
                    self.routes,
                    {"type": "decide", "sub_type": sub_type},
                    500,
                )
                self.assertEqual([name], route["chain"])
                self.assertIn(title, decide_block)
                self.assertEqual(500, route["priority"])

        leaf_sub_types = {item[2] for item in LEAF_SKILLS}
        leaf_routes = [
            route
            for route in self.routes
            if route["type"] == "decide"
            and route["condition"].get("sub_type") in leaf_sub_types
        ]
        self.assertEqual(8, len(leaf_routes))
        self.assertEqual(
            leaf_sub_types,
            {route["condition"]["sub_type"] for route in leaf_routes},
        )
        self.assertEqual(52, len(self.routes))

        with self.assertRaises(LookupError):
            _resolve(
                self.routes,
                {"type": "learning", "sub_type": "multidisciplinary_models"},
                500,
            )
        for route_type in {route["type"] for route in self.routes} - {"decide"}:
            with self.subTest(non_decide_type=route_type):
                try:
                    resolved = _resolve(
                        self.routes,
                        {
                            "type": route_type,
                            "sub_type": "multidisciplinary_models",
                        },
                        500,
                    )
                except LookupError:
                    continue
                self.assertTrue(set(resolved["chain"]).isdisjoint(LEAF_NAMES))
        self.assertNotIn(OLD_COMPOSITE_NAME, self.mapping)

    def test_munger_full_route_is_the_eight_leaf_composition(self) -> None:
        route = _resolve(
            self.routes,
            {"type": "decide", "sub_type": "munger_full"},
            500,
        )
        self.assertEqual(list(LEAF_NAMES), route["chain"])
        self.assertIn("因为", route["rationale"])
        self.assertIn("而非", route["rationale"])

    def test_readme_and_method_router_counts_include_eight_leaf_skills(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn("73 个注册 Skill", readme)
        self.assertIn("48 个方法论 Skill", readme)
        self.assertIn("10 个功能块", readme)
        self.assertIn("8 个独立叶子 Skill", readme)
        self.assertIn("不是第九个综合 Skill", readme)
        self.assertIn("48 个框架", self.method)
        self.assertIn("10 个功能块", self.method)
        self.assertIn("munger_full", self.method)
        self.assertNotIn(OLD_COMPOSITE_NAME, self.method)
        self.assertNotIn(OLD_COMPOSITE_NAME, readme)

    def test_old_composite_entity_and_workspace_are_removed(self) -> None:
        old_composite = ROOT / "method-router" / OLD_COMPOSITE_NAME
        self.assertFalse(old_composite.exists())
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("method-router/munger-methods-workspace/", gitignore)
        self.assertNotIn("method-router/munger-mental-models-workspace/", gitignore)
        self.assertTrue(SOURCE_BASIS_PATH.is_file())

    def test_method_document_matches_the_mapping_contract(self) -> None:
        for route_type in ("goal", "learning", "meta"):
            with self.subTest(route_type=route_type):
                self.assertIn(f"`{route_type}`", self.method)
        self.assertNotIn("`critical` / `normal` / `planning`", self.method)
        self.assertNotIn("最终报告无论入口统一使用 SCQA 模板", self.method)
        self.assertIn("highest_priority_then_specificity", self.method)
        self.assertIn("同一目的的替代 Skill", self.method)
        self.assertIn("`has_data=true` 且 `domain=data`", self.method)
        self.assertIn("fishbone → 5whys → SCQA", self.method)
        self.assertIn("特异度等于匹配的条件字段数量", self.method)
        self.assertNotIn("confidence", self.method)
        self.assertNotIn("置信度", self.method)

    def test_readme_and_drawio_cover_discovery_resolution_and_eight_leaves(
        self,
    ) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        for text in (
            "Discovery Sprint",
            "highest_priority_then_specificity",
            "route_context",
            "73 个",
            "48 个",
        ):
            with self.subTest(document="README", text=text):
                self.assertIn(text, readme)

        diagram = DIAGRAM_PATH.read_text(encoding="utf-8")
        for text in (
            "discovery-sprint",
            "highest_priority_then_specificity",
            "route_context",
            "73 个",
            "48 个",
            *LEAF_NAMES,
        ):
            with self.subTest(document="Draw.io", text=text):
                self.assertIn(text, diagram)
        self.assertNotIn(OLD_COMPOSITE_NAME, diagram)


if __name__ == "__main__":
    unittest.main(verbosity=2)
