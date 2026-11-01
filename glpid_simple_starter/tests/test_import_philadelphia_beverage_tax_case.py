import unittest

from scripts.import_philadelphia_beverage_tax_case import (
    DID_PRICE_EFFECTS,
    DID_VOLUME_EFFECTS,
    STUDY_SOURCE_ID,
    published_indicators,
)


class PhiladelphiaBeverageTaxCaseTests(unittest.TestCase):
    def test_published_data_have_unique_ids_and_resolve_to_study_source(self):
        indicators = published_indicators()
        ids = [row[0] for row in indicators]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(indicators)
        self.assertTrue(all(row[8] == STUDY_SOURCE_ID for row in indicators))

    def test_imports_reported_difference_in_differences_estimates(self):
        indicators = {
            row[2]: row
            for row in published_indicators()
            if row[2].startswith("pbt_published_did_")
        }

        self.assertEqual(len(indicators), 6)
        self.assertEqual(
            indicators["pbt_published_did_price_effect_supermarkets"][5],
            DID_PRICE_EFFECTS["supermarkets"][0],
        )
        self.assertEqual(
            indicators["pbt_published_did_volume_effect_supermarkets"][5],
            DID_VOLUME_EFFECTS["supermarkets"][0],
        )
        self.assertIn("non recalculée", indicators[
            "pbt_published_did_volume_effect_supermarkets"
        ][10])

    def test_annual_snapshots_are_not_mislabeled_as_quarterly_data(self):
        annual = [
            row for row in published_indicators()
            if row[2] == "pbt_mean_taxed_beverage_price_supermarkets"
        ]

        self.assertEqual(len(annual), 4)
        self.assertTrue(all(row[6] == "US cents per ounce" for row in annual))
        self.assertTrue(all(row[3].month == 1 and row[3].day == 1 for row in annual))


if __name__ == "__main__":
    unittest.main()
