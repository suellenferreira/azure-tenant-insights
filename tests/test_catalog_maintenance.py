from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from scripts.catalog_maintenance import analyze_catalogs, generate_report


class CatalogMaintenanceTests(unittest.TestCase):
    def _bundle(self, verified: str = "2026-08-01") -> tuple[Path, tempfile.TemporaryDirectory]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        config = root / "config"
        config.mkdir()
        (config / "deprecated_types.json").write_text(
            json.dumps({"deprecated_types": []}), encoding="utf-8"
        )
        (config / "catalog_metadata.json").write_text(
            json.dumps(
                {
                    "catalog_version": "2026.08",
                    "review_due_days": 90,
                    "stale_days": 180,
                    "catalogs": [
                        {
                            "id": "deprecated_types",
                            "file": "deprecated_types.json",
                            "display_name": "Deprecated types",
                            "last_verified": verified,
                            "source": "https://example.test/retirements",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return root, temporary

    def test_current_catalog_has_no_actionable_review(self) -> None:
        root, temporary = self._bundle()
        self.addCleanup(temporary.cleanup)

        result = analyze_catalogs(root=root, check_urls=False, today=date(2026, 8, 20))

        self.assertFalse(result["actionable"])
        self.assertEqual(result["catalogs"][0]["status"], "current")

    def test_stale_catalog_includes_specific_reviewer_guidance(self) -> None:
        root, temporary = self._bundle(verified="2025-01-01")
        self.addCleanup(temporary.cleanup)

        result = analyze_catalogs(root=root, check_urls=False, today=date(2026, 8, 20))

        self.assertTrue(result["actionable"])
        finding = result["findings"][0]
        self.assertEqual(finding["catalog_id"], "deprecated_types")
        self.assertIn("retirement date", finding["recommended_action"].lower())
        self.assertIn("update_required", result["decision_options"])

    def test_missing_catalog_is_actionable_and_reported(self) -> None:
        root, temporary = self._bundle()
        self.addCleanup(temporary.cleanup)
        (root / "config" / "deprecated_types.json").unlink()
        report = root / "review.md"

        exit_code = generate_report(
            report,
            check_urls=False,
            root=root,
            today=date(2026, 8, 20),
        )

        text = report.read_text(encoding="utf-8")
        self.assertEqual(exit_code, 0)
        self.assertIn("Missing catalog", text)
        self.assertIn("Reviewer Decision", text)
        self.assertIn("update_required", text)

    def test_invalid_verification_date_becomes_actionable_finding(self) -> None:
        root, temporary = self._bundle(verified="not-a-date")
        self.addCleanup(temporary.cleanup)

        result = analyze_catalogs(root=root, check_urls=False, today=date(2026, 8, 20))

        self.assertTrue(result["actionable"])
        self.assertEqual(result["findings"][0]["issue"], "Invalid last_verified date")

    def test_invalid_manifest_becomes_actionable_finding(self) -> None:
        root, temporary = self._bundle()
        self.addCleanup(temporary.cleanup)
        (root / "config" / "catalog_metadata.json").write_text("[]", encoding="utf-8")

        result = analyze_catalogs(root=root, check_urls=False, today=date(2026, 8, 20))

        self.assertTrue(result["actionable"])
        self.assertEqual(result["findings"][0]["issue"], "Invalid catalog manifest")


if __name__ == "__main__":
    unittest.main()