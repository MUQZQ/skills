#!/usr/bin/env python3
"""Malformed source data must be reported instead of crashing validation."""

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_data import _check_color_contract, _parse_row_number  # noqa: E402


class TestMalformedDataReporting(unittest.TestCase):
    def test_invalid_destructive_color_is_reported(self) -> None:
        problems = []
        _check_color_contract([{"Product Type": "Broken", "Destructive": "#1"}], problems)
        self.assertTrue(any("invalid Destructive token" in problem for problem in problems))

    def test_invalid_row_number_is_reported(self) -> None:
        problems = []
        number = _parse_row_number("not-a-number", "reasoning", problems)
        self.assertIsNone(number)
        self.assertTrue(any("invalid No" in problem for problem in problems))

    def test_non_object_catalog_json_is_reported(self) -> None:
        import tempfile
        from unittest import mock
        import validate_data

        with tempfile.TemporaryDirectory() as data_dir:
            source = Path(data_dir) / "phosphor-icons-upstream.json"
            source.write_text("[]", encoding="utf-8")
            problems = []
            with mock.patch.object(validate_data, "DATA_DIR", Path(data_dir)):
                valid = validate_data._valid_catalog_source_key(
                    "phosphor-icons-upstream.json",
                    {"Snapshot": "catalog-summary.json", "Count": 1},
                    ("catalog-snapshot", "phosphor-icons-catalog-2.1.1"),
                    problems,
                )

        self.assertFalse(valid)
        self.assertTrue(any("catalog sourceFile must be an object" in problem for problem in problems))

    def test_malformed_and_credential_urls_are_reported(self) -> None:
        import validate_data

        for ref in ("https://[", "https://user:token@github.com/project"):
            with self.subTest(ref=ref):
                problems = []
                valid = validate_data._valid_provenance_source(
                    {"type": "official", "ref": ref}, 0, ("style", "demo"), problems
                )
                self.assertFalse(valid)
                self.assertTrue(problems)

        problems = []
        validate_data._check_stack_freshness_contract(
            "react",
            [{
                "No": "1",
                "Status": "active",
                "Applies To": "react 19",
                "Severity": "Critical",
                "Docs URL": "https://[",
                "Verified At": "2026-08-26",
            }],
            problems,
        )
        self.assertTrue(any("official Docs URL" in problem for problem in problems))

    def test_non_object_catalog_items_are_reported(self) -> None:
        import validate_data

        problems = []
        manifest = {
            "source": {
                "package": "@phosphor-icons/core",
                "version": "2.1.1",
                "reactPackage": "@phosphor-icons/react",
                "reactVersion": "2.1.10",
            },
            "reactImports": {
                "clientModule": "@phosphor-icons/react",
                "ssrModule": "@phosphor-icons/react/ssr",
            },
            "status": "active",
            "verifiedAt": "2026-08-26",
            "weights": ["thin", "light", "regular", "bold", "fill", "duotone"],
            "iconCount": 1,
            "icons": [None],
            "curatedValidatedCount": 0,
        }
        validate_data._check_phosphor_catalog([], manifest, problems)
        self.assertTrue(any("icon entry must be an object" in problem for problem in problems))

    def test_invalid_source_file_type_and_missing_summary_inputs_are_reported(self) -> None:
        import tempfile
        from unittest import mock
        import validate_data

        problems = []
        self.assertFalse(validate_data._valid_dataset_source_key(
            None, {}, ("dataset-contract", "broken"), problems
        ))

        with tempfile.TemporaryDirectory() as data_dir:
            with mock.patch.object(validate_data, "DATA_DIR", Path(data_dir)):
                validate_data._check_catalog_summary(
                    {"verifiedAt": "2026-08-26", "counts": {}}, {}, {}, problems
                )
        self.assertTrue(any("catalog summary inputs are unreadable" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
