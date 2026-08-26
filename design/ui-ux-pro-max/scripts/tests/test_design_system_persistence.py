#!/usr/bin/env python3
"""Persistence contracts for generated design systems."""

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from design_system import (  # noqa: E402
    generate_design_system,
    persist_design_system,
    safe_slug,
)
from search import format_persistence_summary  # noqa: E402


class TestSafeSlug(unittest.TestCase):
    def test_non_ascii_names_get_distinct_stable_slugs(self) -> None:
        first = safe_slug("项目甲")
        second = safe_slug("项目乙")
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, "default")
        self.assertRegex(first, re.compile(r"^[a-z0-9_-]+$"))
        self.assertEqual(first, safe_slug("项目甲"))

    def test_windows_reserved_device_names_are_escaped(self) -> None:
        for name in ("CON", "PRN", "AUX", "NUL", "COM1", "LPT9"):
            with self.subTest(name=name):
                self.assertNotEqual(safe_slug(name).upper(), name)


class TestPersistenceStatus(unittest.TestCase):
    def test_existing_page_reports_partial_conflict_after_master_creation(self) -> None:
        rows = {
            "product": [{"Product Type": "SaaS (General)"}],
            "style": [{"Style ID": "minimal"}],
            "color": [{"Product Type": "SaaS (General)"}],
            "typography": [{"Font Pairing Name": "Professional"}],
            "landing": [{"Pattern Name": "Hero + Features + CTA"}],
        }

        def search_result(_query, domain, _limit):
            return {"results": rows[domain]}

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "design-system" / "demo" / "pages" / "dashboard.md"
            page.parent.mkdir(parents=True)
            page.write_text("existing", encoding="utf-8")

            with patch("design_system.search", side_effect=search_result):
                generated = generate_design_system(
                    "SaaS dashboard",
                    project_name="Demo",
                    page="dashboard",
                    output_dir=tmp,
                    persist=True,
                )
            result = generated["persistence"]

            self.assertEqual(result["status"], "partial_conflict")
            self.assertEqual(len(result["created_files"]), 1)
            self.assertTrue((Path(tmp) / "design-system" / "demo" / "MASTER.md").is_file())
            self.assertEqual(page.read_text(encoding="utf-8"), "existing")

    def test_unverified_generation_is_not_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("design_system.search", return_value={"results": []}):
                result = generate_design_system(
                    "unknown product",
                    persist=True,
                    output_dir=tmp,
                )

            self.assertEqual(result["persistence"]["status"], "skipped_unverified")
            self.assertFalse((Path(tmp) / "design-system").exists())

    def test_structured_core_domains_are_required_for_verification(self) -> None:
        rows = {
            "product": [{"Product Type": "SaaS (General)"}],
            "style": [{"Style ID": "minimal"}],
            "color": [{"Product Type": "SaaS (General)"}],
            "typography": [{"Font Pairing Name": "Professional"}],
            "landing": [{"Pattern Name": "Hero + Features + CTA"}],
        }

        def search_result(_query, domain, _limit):
            return {"results": rows[domain]}

        with tempfile.TemporaryDirectory() as tmp:
            with patch("design_system.search", side_effect=search_result):
                result = generate_design_system("SaaS dashboard", persist=True, output_dir=tmp)
            self.assertEqual(result["persistence"]["status"], "success")

    def test_malformed_core_domain_rows_block_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("design_system.search", return_value={"results": [{}]}):
                result = generate_design_system("SaaS dashboard", persist=True, output_dir=tmp)
            self.assertEqual(result["persistence"]["status"], "skipped_unverified")

    def test_missing_core_domain_blocks_persistence(self) -> None:
        def search_result(_query, domain, _limit):
            return {"results": [] if domain == "style" else [{}]}

        with tempfile.TemporaryDirectory() as tmp:
            with patch("design_system.search", side_effect=search_result):
                result = generate_design_system("checkout", persist=True, output_dir=tmp)
            self.assertEqual(result["persistence"]["status"], "skipped_unverified")


class TestPersistenceSummary(unittest.TestCase):
    def test_statuses_are_not_reported_as_success(self) -> None:
        skipped = format_persistence_summary({"status": "skipped_unverified"})
        partial = format_persistence_summary({"status": "partial_conflict"})
        success = format_persistence_summary({
            "status": "success",
            "design_system_dir": "design-system/demo",
            "created_files": ["MASTER.md"],
        })
        self.assertTrue(skipped[0].startswith("ERROR:"))
        self.assertTrue(partial[0].startswith("WARNING:"))
        self.assertTrue(success[0].startswith("OK:"))


class TestPersistenceBoundaries(unittest.TestCase):
    def test_direct_persistence_rejects_forged_verification_marker(self) -> None:
        from design_system import persist_design_system

        with tempfile.TemporaryDirectory() as output_dir:
            result = persist_design_system(
                {"project_name": "unsafe", "_verification": {"verified": True}},
                output_dir=output_dir,
            )

            self.assertEqual("skipped_unverified", result["status"])
            self.assertFalse((Path(output_dir) / "design-system").exists())

    def test_persistence_options_require_design_system_mode(self) -> None:
        from search import validate_persistence_args

        for persist, page, force in (
            (True, None, False),
            (False, "dashboard", False),
            (False, None, True),
        ):
            with self.subTest(persist=persist, page=page, force=force):
                with self.assertRaises(ValueError):
                    validate_persistence_args(False, persist, page, force)

        validate_persistence_args(True, True, "dashboard", True)

    def test_failed_persistence_statuses_use_nonzero_exit_codes(self) -> None:
        from search import persistence_exit_code

        self.assertEqual(0, persistence_exit_code("success"))
        self.assertEqual(0, persistence_exit_code("skipped_exists"))
        self.assertNotEqual(0, persistence_exit_code("skipped_unverified"))
        self.assertNotEqual(0, persistence_exit_code("partial_conflict"))
        self.assertNotEqual(0, persistence_exit_code("unexpected"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
