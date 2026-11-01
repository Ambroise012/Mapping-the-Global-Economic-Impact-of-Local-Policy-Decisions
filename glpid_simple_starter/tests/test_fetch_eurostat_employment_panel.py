import json
import unittest
from datetime import date
from unittest.mock import patch

from scripts.fetch_eurostat_employment_panel import (
    fetch_country,
    parse_quarter,
    parse_bls_responses,
    parse_uk_csv,
    quarter_end,
    quarter_label,
)


class EurostatEmploymentPanelTests(unittest.TestCase):
    def test_quarter_helpers(self):
        self.assertEqual(parse_quarter("2021-Q1"), date(2021, 1, 1))
        self.assertEqual(quarter_label(date(2021, 10, 1)), "2021-Q4")
        self.assertEqual(quarter_end(date(2021, 10, 1)), date(2021, 12, 31))

    @patch("scripts.fetch_eurostat_employment_panel.urlopen")
    def test_extracts_seasonally_adjusted_quarterly_employment(self, urlopen):
        payload = {
            "value": {"0": 1000.5, "1": 1010.25},
            "dimension": {
                "time": {
                    "category": {"index": {"2021-Q1": 0, "2021-Q2": 1}}
                }
            },
        }

        class JsonResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        urlopen.return_value = JsonResponse()
        rows = fetch_country("FR", date(2021, 1, 1), date(2021, 4, 1))

        self.assertEqual([(row[0], row[1], row[2]) for row in rows], [
            (date(2021, 1, 1), date(2021, 3, 31), 1000.5),
            (date(2021, 4, 1), date(2021, 6, 30), 1010.25),
        ])
        self.assertIn("lfsi_emp_q", rows[0][3])
        self.assertIn("s_adj=SA", rows[0][3])

    def test_extracts_calendar_quarters_from_ons_rolling_period_csv(self):
        content = (
            "v4_0,mmm-mmm-yyyy,Time,uk-only,Geography,unit-of-measure,"
            "UnitOfMeasure,economic-activity,EconomicActivity,age-groups,"
            "AgeGroups,sex,Sex,seasonal-adjustment,SeasonalAdjustment\n"
            "32775975,jan-mar-2019,Jan-Mar 2019,K02000001,United Kingdom,"
            "levels,Levels,in-employment,In Employment,16+,16+,all-adults,"
            "All adults,seasonal-adjustment,Seasonally Adjusted\n"
            "32800000,apr-jun-2019,Apr-Jun 2019,K02000001,United Kingdom,"
            "levels,Levels,in-employment,In Employment,16+,16+,all-adults,"
            "All adults,seasonal-adjustment,Seasonally Adjusted\n"
            "10000000,jan-mar-2019,Jan-Mar 2019,K02000001,United Kingdom,"
            "levels,Levels,unemployed,Unemployed,16+,16+,all-adults,"
            "All adults,seasonal-adjustment,Seasonally Adjusted\n"
        )

        rows = parse_uk_csv(content, date(2019, 1, 1), date(2019, 4, 1))

        self.assertEqual(
            [(row[0], row[2]) for row in rows],
            [(date(2019, 1, 1), 32775.975), (date(2019, 4, 1), 32800.0)],
        )

    def test_aggregates_bls_monthly_employment_to_quarterly_means(self):
        observations = [
            {"year": "2021", "period": f"M{month:02d}", "value": str(1000 + month)}
            for month in range(1, 7)
        ]
        response = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [{"seriesID": "LNS12000000", "data": observations}]
            },
        }

        rows = parse_bls_responses(
            [response], date(2021, 1, 1), date(2021, 4, 1)
        )

        self.assertEqual(
            [(row[0], row[2]) for row in rows],
            [(date(2021, 1, 1), 1002.0), (date(2021, 4, 1), 1005.0)],
        )

    def test_omits_incomplete_final_bls_quarter(self):
        observations = [
            {"year": "2021", "period": f"M{month:02d}", "value": str(1000 + month)}
            for month in range(1, 4)
        ]
        observations.extend(
            [
                {"year": "2021", "period": "M04", "value": "1004"},
                {"year": "2021", "period": "M05", "value": "-"},
                {"year": "2021", "period": "M06", "value": "1006"},
            ]
        )
        response = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [{"seriesID": "LNS12000000", "data": observations}]
            },
        }

        rows = parse_bls_responses(
            [response], date(2021, 1, 1), date(2021, 4, 1)
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], date(2021, 1, 1))

    @patch("scripts.fetch_eurostat_employment_panel.urlopen")
    def test_rejects_missing_quarter(self, urlopen):
        payload = {
            "value": {"0": 1000.5},
            "dimension": {"time": {"category": {"index": {"2021-Q1": 0}}}},
        }

        class JsonResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(payload).encode()

        urlopen.return_value = JsonResponse()
        with self.assertRaisesRegex(ValueError, "Couverture temporelle"):
            fetch_country("FR", date(2021, 1, 1), date(2021, 4, 1))


if __name__ == "__main__":
    unittest.main()
