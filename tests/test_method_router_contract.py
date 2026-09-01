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
        declared = set(
            re.findall(r"(?m)^  - skill_name: ([a-z0-9-]+)$", registry_text)
        )
        referenced = {
            skill_name for route in self.routes for skill_name in route["chain"]
        }
        self.assertEqual(registered, declared)
        self.assertTrue(referenced <= registered)

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

    def test_readme_and_drawio_cover_discovery_and_resolution(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        for text in (
            "Discovery Sprint",
            "highest_priority_then_specificity",
            "route_context",
            "65 个",
            "40 个",
        ):
            with self.subTest(document="README", text=text):
                self.assertIn(text, readme)

        diagram = DIAGRAM_PATH.read_text(encoding="utf-8")
        for text in (
            "discovery-sprint",
            "highest_priority_then_specificity",
            "route_context",
            "65 个",
            "40 个",
        ):
            with self.subTest(document="Draw.io", text=text):
                self.assertIn(text, diagram)


if __name__ == "__main__":
    unittest.main(verbosity=2)
