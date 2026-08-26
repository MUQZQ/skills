import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_MAPPING = ROOT / "skill-domain-mapping.yaml"

MAPPING_FILES = {
    "meta-skills": "meta-skill-mapping.yaml",
    "independent-tools": "tool-mapping.yaml",
    "orchestration": "orchestration-mapping.yaml",
}
ROOT_MAPPING_DATA = json.loads(ROOT_MAPPING.read_text(encoding="utf-8"))
DOMAIN_CHILDREN = {
    domain: set(ROOT_MAPPING_DATA["domains"][domain]["skills"])
    for domain in MAPPING_FILES
}

CONSUMERS = (
    Path.home() / ".codex" / "skills",
    Path.home() / ".claude" / "skills",
    Path.home() / ".config" / "opencode" / "skills",
)


class AdditionalSkillDomainContractTest(unittest.TestCase):
    def test_domain_parents_own_their_children_and_mapping(self):
        for domain, children in DOMAIN_CHILDREN.items():
            with self.subTest(domain=domain):
                self.assertTrue((ROOT / domain / "SKILL.md").is_file())
                mapping_path = ROOT / domain / "references" / MAPPING_FILES[domain]
                mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
                self.assertEqual(domain, mapping["domain"])
                self.assertTrue(mapping["source_of_truth"])
                self.assertEqual(children, set(mapping["routes"]))
                for child in children:
                    self.assertTrue((ROOT / domain / child / "SKILL.md").is_file())
                    self.assertFalse((ROOT / child).exists())
                    self.assertEqual(
                        child,
                        mapping["routes"][child]["skill_name"],
                    )
                    self.assertNotIn("skill_path", mapping["routes"][child])

    def test_agents_references_single_repository_mapping(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`skill-domain-mapping.yaml`", agents)
        self.assertNotIn("| 元技能 | `meta-skills` |", agents)
        mapping = json.loads(ROOT_MAPPING.read_text(encoding="utf-8"))
        self.assertEqual(
            {"code-review", "coding-standards", "design", "method-router", *DOMAIN_CHILDREN},
            set(mapping["domains"]),
        )
        for domain, children in DOMAIN_CHILDREN.items():
            self.assertEqual(children, set(mapping["domains"][domain]["skills"]))

    def test_consumers_expose_parents_without_child_aliases(self):
        children = set().union(*DOMAIN_CHILDREN.values())
        for consumer in CONSUMERS:
            if not consumer.exists():
                continue
            with self.subTest(consumer=consumer):
                registry_copy = consumer / "skill-domain-mapping.yaml"
                self.assertTrue(registry_copy.is_file())
                self.assertEqual(
                    ROOT_MAPPING.read_text(encoding="utf-8"),
                    registry_copy.read_text(encoding="utf-8"),
                )
                for domain in DOMAIN_CHILDREN:
                    parent = consumer / domain
                    self.assertTrue(parent.exists())
                    self.assertTrue(os.path.isjunction(parent))
                    self.assertEqual((ROOT / domain).resolve(), parent.resolve())
                for child in children:
                    self.assertFalse((consumer / child).exists())


if __name__ == "__main__":
    unittest.main()
