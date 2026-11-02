import csv
import unittest
from datetime import date
from pathlib import Path

from scripts.fetch_event_data import CASES as EVENT_CASES
from scripts.fetch_gdelt_context import CASES as GDELT_CASES
from scripts.fetch_qcew_local_panel import COUNTIES, INDUSTRIES


ROOT = Path(__file__).resolve().parents[1]


class LoudounCaseTests(unittest.TestCase):
    @staticmethod
    def records(path):
        with path.open(encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def test_event_study_uses_local_operations_not_headquarters(self):
        case = EVENT_CASES["loudoun"]

        self.assertEqual(case["territory_id"], "us-va-loudoun-county")
        self.assertEqual(case["headquarters_territory_id"], "us")
        self.assertEqual(case["exposure_type"], "operations")
        self.assertEqual(case["policy"]["adoption_date"], date(2023, 12, 6))
        self.assertEqual(
            {company[2] for company in case["companies"]}, {"AMZN", "EQIX"}
        )
        self.assertEqual(
            set(case["exposure_sources"]), {"company-amazon", "company-equinix"}
        )

    def test_qcew_includes_loudoun_and_nearby_descriptive_comparators(self):
        self.assertEqual(COUNTIES["us-va-loudoun-county"][1:], ("51107", "us-va"))
        self.assertEqual(COUNTIES["us-va-fairfax-county"][1:], ("51059", "us-va"))
        self.assertEqual(
            COUNTIES["us-va-prince-william-county"][1:], ("51153", "us-va")
        )
        self.assertEqual(
            INDUSTRIES["5182"], "data-processing-hosting-related-services"
        )

    def test_gdelt_loudoun_series_has_distinct_local_query(self):
        case = GDELT_CASES["loudoun"]

        self.assertEqual(case["territory_id"], "us-va-loudoun-county")
        self.assertEqual(
            case["indicator_code"], "gdelt_loudoun_data_center_article_count"
        )
        self.assertIn("Loudoun", case["query"])
        self.assertIn("Equinix", case["query"])

    def test_company_exposures_are_candidates_without_numeric_scores(self):
        rows = [
            row
            for row in self.records(
                ROOT / "data" / "templates" / "company_exposures.csv"
            )
            if row["territory_id"] == "us-va-loudoun-county"
        ]

        self.assertEqual(
            {row["company_id"] for row in rows},
            {"company-amazon", "company-equinix"},
        )
        self.assertTrue(all(row["exposure_type"] == "operations" for row in rows))
        self.assertTrue(all(row["exposure_score"] == "" for row in rows))
        self.assertTrue(all(row["source_id"] for row in rows))

    def test_virginia_tax_exemption_case_and_seed_data(self):
        case = EVENT_CASES["va-data-center"]
        policy = case["policy"]

        self.assertEqual(case["territory_id"], "us-va")
        self.assertIsNone(policy["adoption_date"])
        self.assertEqual(policy["effective_date"], date(2010, 7, 1))
        self.assertIn("$150 million", policy["summary"])
        self.assertIn("50 new jobs", policy["summary"])
        self.assertEqual(
            {company[2] for company in case["companies"]},
            {"AMZN", "MSFT", "GOOG", "EQIX"},
        )

        policies = self.records(ROOT / "data" / "templates" / "policy_changes.csv")
        seed_policy = next(
            row
            for row in policies
            if row["policy_id"] == "policy-va-data-center-equipment-exemption-2010"
        )
        self.assertEqual(seed_policy["adoption_date"], "")
        self.assertEqual(seed_policy["effective_date"], "2010-07-01")
        self.assertEqual(seed_policy["source_id"], "source-va-data-center-exemption")

        exposures = [
            row
            for row in self.records(
                ROOT / "data" / "templates" / "company_exposures.csv"
            )
            if row["territory_id"] == "us-va"
        ]
        self.assertEqual(
            {row["company_id"] for row in exposures},
            {
                "company-amazon-va-dc",
                "company-microsoft-va-dc",
                "company-alphabet-va-dc",
                "company-equinix-va-dc",
            },
        )
        self.assertTrue(all(row["exposure_score"] == "" for row in exposures))

    def test_seed_records_resolve_their_references(self):
        sources = {
            row["source_id"]
            for row in self.records(ROOT / "data" / "templates" / "sources.csv")
        }
        territories = {
            row["territory_id"]
            for row in self.records(ROOT / "data" / "territories.csv")
        }
        companies = {
            row["company_id"]
            for row in self.records(ROOT / "data" / "templates" / "companies.csv")
        }
        for policy in self.records(
            ROOT / "data" / "templates" / "policy_changes.csv"
        ):
            if policy["policy_id"].startswith(
                ("policy-loudoun-", "policy-va-data-center-")
            ):
                self.assertIn(policy["territory_id"], territories)
                self.assertIn(policy["source_id"], sources)
        for exposure in self.records(
            ROOT / "data" / "templates" / "company_exposures.csv"
        ):
            self.assertIn(exposure["company_id"], companies)
            self.assertIn(exposure["territory_id"], territories)
            self.assertIn(exposure["source_id"], sources)


if __name__ == "__main__":
    unittest.main()
