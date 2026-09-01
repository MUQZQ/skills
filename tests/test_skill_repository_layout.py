#!/usr/bin/env python3
"""Repository Skills must follow AGENTS -> domain Skill -> child Skill."""

import json
import os
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSUMERS = (
    Path.home() / ".codex" / "skills",
    Path.home() / ".claude" / "skills",
    Path.home() / ".config" / "opencode" / "skills",
)

ROOT_MAPPING_DATA = json.loads(
    (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
)
DOMAIN_CHILDREN = {
    domain: set(config["skills"])
    for domain, config in ROOT_MAPPING_DATA["domains"].items()
}
ROOT_SKILLS = set(DOMAIN_CHILDREN)
MOVED_CHILDREN = {
    child: domain
    for domain, children in DOMAIN_CHILDREN.items()
    for child in children
}


class SkillRepositoryLayoutContractTest(unittest.TestCase):
    def test_root_contains_only_domain_or_independent_skills(self) -> None:
        actual = {
            path.name for path in ROOT.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        self.assertEqual(ROOT_SKILLS, actual)

    def test_every_domain_child_is_physically_nested(self) -> None:
        for domain, children in DOMAIN_CHILDREN.items():
            for child in children:
                with self.subTest(domain=domain, child=child):
                    self.assertTrue((ROOT / domain / child / "SKILL.md").is_file())

    def test_moved_children_have_no_root_duplicates(self) -> None:
        for child in MOVED_CHILDREN:
            with self.subTest(child=child):
                self.assertFalse((ROOT / child).exists())

    def test_consumers_expose_domains_without_child_aliases(self) -> None:
        if not all(consumer.exists() for consumer in CONSUMERS):
            self.skipTest("consumer skill roots are not installed on this machine")
        aliases = set(MOVED_CHILDREN) | {"refactor-tdd"}
        for consumer in CONSUMERS:
            registry_copy = consumer / "skill-domain-mapping.yaml"
            self.assertTrue(registry_copy.is_file())
            self.assertEqual(
                (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8"),
                registry_copy.read_text(encoding="utf-8"),
            )
            for domain in DOMAIN_CHILDREN:
                with self.subTest(consumer=consumer, domain=domain):
                    self.assertTrue((consumer / domain / "SKILL.md").is_file())
                    self.assertTrue(os.path.isjunction(consumer / domain))
                    self.assertEqual((ROOT / domain).resolve(), (consumer / domain).resolve())
                for child in DOMAIN_CHILDREN[domain]:
                    with self.subTest(consumer=consumer, domain=domain, child=child):
                        self.assertTrue((consumer / domain / child / "SKILL.md").is_file())
            for alias in aliases:
                with self.subTest(consumer=consumer, alias=alias):
                    self.assertFalse(os.path.lexists(consumer / alias))

    def test_root_registry_owns_nested_paths(self) -> None:
        registry = json.loads(
            (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        for domain, children in DOMAIN_CHILDREN.items():
            for child in children:
                with self.subTest(domain=domain, child=child):
                    self.assertEqual(
                        f"{domain}/{child}/SKILL.md",
                        registry["domains"][domain]["skills"][child]["path"],
                    )

        for relative_path in (
            "design/references/design-mapping.yaml",
            "method-router/references/method-mapping.yaml",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("skill_path:", content)
            self.assertNotRegex(content, r"(?m)^\s*path:\s*")

    def test_agents_references_single_repository_mapping(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`skill-domain-mapping.yaml`", agents)
        self.assertNotIn("| 代码审查 | `code-review` |", agents)
        for duplicated_section in {
            "## 全流程自动化",
            "## 共享执行 Provider（非 Skill）",
            "## 代码质量",
            "## 设计能力",
            "## 分支与同步",
            "## 方法论体系",
        }:
            self.assertNotIn(duplicated_section, agents)
        mapping = json.loads(
            (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        self.assertTrue(mapping["source_of_truth"])
        self.assertEqual(set(DOMAIN_CHILDREN), set(mapping["domains"]))
        for domain, children in DOMAIN_CHILDREN.items():
            self.assertEqual(children, set(mapping["domains"][domain]["skills"]))

    def test_active_skill_registry_has_unique_names(self) -> None:
        paths = [ROOT / name / "SKILL.md" for name in ROOT_SKILLS]
        paths.extend(
            ROOT / domain / child / "SKILL.md"
            for domain, children in DOMAIN_CHILDREN.items()
            for child in children
        )
        names = []
        for path in paths:
            match = re.search(r"(?m)^name:\s*([^\r\n]+)", path.read_text(encoding="utf-8"))
            self.assertIsNotNone(match, path)
            names.append(match.group(1).strip())

        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all("auto-code-generator-workspace" not in str(path) for path in paths))
        self.assertTrue(all("_providers" not in str(path) for path in paths))

    def test_root_mapping_describes_every_child_skill(self) -> None:
        mapping = json.loads(
            (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        registered_names = []
        for domain, children in DOMAIN_CHILDREN.items():
            for directory_name in children:
                with self.subTest(domain=domain, skill=directory_name):
                    skill = mapping["domains"][domain]["skills"][directory_name]
                    skill_path = ROOT / skill["path"]
                    self.assertTrue(skill_path.read_bytes().startswith(b"---"))
                    frontmatter_name = re.search(
                        r"(?m)^name:\s*([^\r\n]+)",
                        skill_path.read_text(encoding="utf-8"),
                    )
                    self.assertIsNotNone(frontmatter_name)
                    self.assertEqual(skill["skill_name"], frontmatter_name.group(1).strip())
                    self.assertTrue(skill["skill_name"].strip())
                    self.assertTrue(skill["description"].strip())
                    self.assertNotIn(skill["description"].strip(), {">", "|"})
                    self.assertEqual(
                        f"{domain}/{directory_name}/SKILL.md",
                        skill["path"],
                    )
                    registered_names.append(skill["skill_name"])
        self.assertEqual(len(registered_names), len(set(registered_names)))

    def test_method_router_supports_blank_slate_discovery(self) -> None:
        method_skills = ROOT_MAPPING_DATA["domains"]["method-router"]["skills"]
        self.assertIn("discovery-sprint", method_skills)

        skill_path = ROOT / method_skills["discovery-sprint"]["path"]
        skill_text = skill_path.read_text(encoding="utf-8")
        for required_text in (
            "完全初始",
            "事实 / 推断 / 假设",
            "来源",
            "头脑风暴",
            "首个可验证实验",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text, skill_text)

        method_mapping = (
            ROOT / "method-router" / "references" / "method-mapping.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("scope: blank_slate", method_mapping)
        self.assertIn("skill_name: discovery-sprint", method_mapping)

    def test_repository_readme_owns_repository_specific_guidance(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("AGENTS.md", readme)
        self.assertIn("通用约束", readme)
        self.assertIn("skill-domain-mapping.yaml", readme)
        self.assertIn("skill-domain-architecture.drawio", readme)
        self.assertIn("agents-sync", readme)

    def test_routing_authority_scopes_are_explicit(self) -> None:
        root_mapping = json.loads(
            (ROOT / "skill-domain-mapping.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual("repository_registry_and_paths", root_mapping["authority_scope"])
        for path in (
            ROOT / "meta-skills" / "references" / "meta-skill-mapping.yaml",
            ROOT / "independent-tools" / "references" / "tool-mapping.yaml",
            ROOT / "orchestration" / "references" / "orchestration-mapping.yaml",
        ):
            mapping = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("domain_intent_routing", mapping["authority_scope"])
            self.assertEqual("../../skill-domain-mapping.yaml", mapping["registry_source"])
            for route in mapping["routes"].values():
                self.assertIn("skill_name", route)
                self.assertNotIn("skill_path", route)

    def test_sync_and_router_documents_preserve_safe_dynamic_resolution(self) -> None:
        sync = (ROOT / "meta-skills" / "agents-sync" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("$PSScriptRoot", sync)
        self.assertNotIn("Remove-Item -LiteralPath $target -Recurse -Force", sync)
        self.assertIn("Move-Item", sync)
        self.assertIn("LinkType -ne \"Junction\"", sync)
        self.assertIn("skill-domain-mapping.yaml", sync)
        self.assertIn("ConvertFrom-Json", sync)
        self.assertNotIn("Get-ChildItem $srcRoot -Directory", sync)
        self.assertIn("$allowedRoots", sync)
        self.assertIn("[Guid]::NewGuid()", sync)
        self.assertNotIn("Remove-Item $target", sync)
        self.assertIn("$domainEntry.LinkType -eq \"Junction\"", sync)
        self.assertIn("Split-Path $domainSource -Parent", sync)
        self.assertIn("$item.PSIsContainer", sync)
        self.assertNotIn("if (Test-Path -LiteralPath $target)", sync)
        self.assertIn("stale-managed", sync)
        self.assertIn("$fileSyncPairs", sync)
        self.assertIn("$managedFileTargets", sync)
        self.assertIn('Join-Path $srcRoot "skill-domain-mapping.yaml"', sync)
        self.assertIn('$item.LinkType -ne "HardLink"', sync)

        method = (ROOT / "method-router" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("共 14 个", method)
        self.assertNotIn("ADR（缺失）", method)

        provider = (
            ROOT
            / "orchestration"
            / "auto-code-generator"
            / "references"
            / "execution-providers"
            / "sol-luna.md"
        ).read_text(encoding="utf-8")
        self.assertIn("向上三级", provider)

    def test_code_review_routes_design_documents_through_design_domain(self) -> None:
        review = (ROOT / "code-review" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`design`", review)
        self.assertNotIn("`design-review/SKILL.md`", review)
        self.assertIn("skill-domain-mapping.yaml", review)
        self.assertNotIn("code-review/{subskill-name}/SKILL.md", review)


if __name__ == "__main__":
    unittest.main(verbosity=2)
