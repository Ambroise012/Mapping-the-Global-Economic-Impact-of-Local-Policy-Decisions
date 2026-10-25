import unittest
from io import BytesIO
from datetime import date
from math import exp, log
from unittest.mock import patch

from scripts.fetch_qcew_local_panel import fetch_county_quarter, quarter_dates
from scripts.fetch_gdelt_context import month_range, parse_raw_timeline
from scripts.local_employment_did import (
    INDICATORS,
    fit_local_did,
    parse_quarter,
    quarter_label,
)


class LocalEmploymentDidTests(unittest.TestCase):
    def test_parses_and_formats_quarter(self):
        self.assertEqual(parse_quarter("2021-Q1"), date(2021, 1, 1))
        self.assertEqual(quarter_label(date(2021, 10, 1)), "2021-Q4")
        self.assertEqual(quarter_dates(2025, 4), (date(2025, 10, 1), date(2025, 12, 31)))
        self.assertEqual(
            INDICATORS["employment-professional-scientific-technical"][0],
            "qcew_private_employment_professional-scientific-technical",
        )

    def test_recovers_known_log_treatment_effect(self):
        rows = []
        start_year = 2017
        for county_index, territory_id in enumerate(
            ["treated", "control-a", "control-b", "control-c"]
        ):
            for index in range(24):
                year = start_year + index // 4
                month = (index % 4) * 3 + 1
                is_treated = county_index == 0
                post = date(year, month, 1) >= date(2020, 1, 1)
                log_value = county_index * 0.02 + index * 0.01
                if is_treated and post:
                    log_value += log(1.05)
                value = exp(log_value)
                rows.append(
                    {
                        "territory_id": territory_id,
                        "period_start": date(year, month, 1),
                        "value": value,
                    }
                )

        model, _frame, _pretrend = fit_local_did(
            rows,
            treated_id="treated",
            control_ids=["control-a", "control-b", "control-c"],
            post_start=date(2020, 1, 1),
        )

        self.assertAlmostEqual(model.params["treated:post"], log(1.05), places=8)

    @patch("scripts.fetch_qcew_local_panel.urlopen")
    def test_qcew_parser_keeps_available_industries_and_skips_suppressed(self, urlopen):
        csv_content = (
            "area_fips,own_code,industry_code,month1_emplvl,month2_emplvl,"
            "month3_emplvl,avg_wkly_wage\n"
            "53033,5,10,100,110,120,2000\n"
            "53033,5,54,10,11,12,3000\n"
            "53033,5,51,,,,\n"
            "53033,0,54,900,900,900,9000\n"
        ).encode()
        urlopen.return_value.__enter__.return_value.read.return_value = csv_content

        result = fetch_county_quarter("53033", 2021, 1)

        self.assertEqual(result["10"], (110, 2000.0))
        self.assertEqual(result["54"], (11, 3000.0))
        self.assertNotIn("51", result)

    def test_gdelt_daily_counts_are_aggregated_by_month(self):
        payload = {
            "timeline": [
                {
                    "series": "Article Count",
                    "data": [
                        {"date": "20200131T000000Z", "value": 2},
                        {"date": "20200201T000000Z", "value": 3},
                        {"date": "20200202T000000Z", "value": 4},
                    ],
                }
            ]
        }

        self.assertEqual(
            parse_raw_timeline(payload),
            {date(2020, 1, 1): 2, date(2020, 2, 1): 7},
        )
        self.assertEqual(
            list(month_range(date(2020, 1, 1), date(2020, 2, 29))),
            [(date(2020, 1, 1), date(2020, 1, 31)), (date(2020, 2, 1), date(2020, 2, 29))],
        )

    def test_rejects_incomplete_panel(self):
        rows = [
            {"territory_id": territory_id, "period_start": date(2019, month, 1), "value": 100}
            for territory_id in ("treated", "control-a", "control-b")
            for month in (1, 4, 7, 10)
        ]
        with self.assertRaisesRegex(ValueError, "au moins 12 trimestres"):
            fit_local_did(
                rows,
                treated_id="treated",
                control_ids=["control-a", "control-b"],
                post_start=date(2020, 1, 1),
            )


if __name__ == "__main__":
    unittest.main()
