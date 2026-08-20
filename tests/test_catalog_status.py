from datetime import date
import unittest

from processors.catalog_status import catalog_warnings, load_catalog_status
from writers.catalog_status import catalog_badge_html, catalog_status_html


class CatalogStatusTests(unittest.TestCase):
    def test_status_thresholds_and_warning_generation(self) -> None:
        status = load_catalog_status(as_of=date(2026, 11, 30))
        by_id = {item["id"]: item for item in status["catalogs"]}

        self.assertEqual(by_id["deprecated_types"]["status"], "stale")
        self.assertEqual(by_id["misconfiguration_rules"]["status"], "review_due")
        self.assertEqual(status["overall_status"], "stale")
        self.assertTrue(catalog_warnings(status))

    def test_current_catalogs_do_not_generate_warnings(self) -> None:
        status = load_catalog_status(as_of=date(2026, 8, 19))

        self.assertEqual(status["overall_status"], "current")
        self.assertEqual(catalog_warnings(status), [])

    def test_html_discloses_catalog_version_and_local_evaluation(self) -> None:
        status = load_catalog_status(as_of=date(2026, 8, 19))

        table = catalog_status_html(status)
        badge = catalog_badge_html(status, ("deprecated_types",))

        self.assertIn("2026.08", table)
        self.assertIn("evaluated locally", table)
        self.assertIn("Warnings do not block the scan", badge)

    def test_excel_catalog_sheet_contains_provenance(self) -> None:
        import openpyxl

        from writers.excel_writer import _write_catalog_status_sheet

        workbook = openpyxl.Workbook()
        _write_catalog_status_sheet(
            workbook,
            {"catalog_status": load_catalog_status(as_of=date(2026, 8, 19))},
        )
        sheet = workbook["CatalogStatus"]

        self.assertIn("older than 90 days", sheet["A1"].value)
        self.assertEqual(sheet["A4"].value, "Catalog")
        self.assertEqual(sheet["C5"].value, "2026.08")
        self.assertEqual(sheet["F5"].value, "current")


if __name__ == "__main__":
    unittest.main()