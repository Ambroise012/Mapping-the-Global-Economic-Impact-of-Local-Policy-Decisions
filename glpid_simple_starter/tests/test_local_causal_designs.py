import unittest
from datetime import date

from scripts.local_causal_designs import (
    fit_continuous_exposure_did,
    fit_salary_rdd,
    fit_within_firm_did,
)


class LocalCausalDesignsTests(unittest.TestCase):
    def test_within_firm_did_recovers_effect_with_firm_time_shocks(self):
        rows = []
        periods = [date(2020 + index // 4, (index % 4) * 3 + 1, 1) for index in range(12)]
        for firm_number in range(4):
            for treated in (0, 1):
                location_id = f"firm-{firm_number}-site-{treated}"
                for period_index, period in enumerate(periods):
                    value = 10 + firm_number + period_index * 2
                    if period >= date(2022, 1, 1):
                        value += firm_number * 3
                        if treated:
                            value += 5
                    rows.append(
                        {
                            "firm_id": f"firm-{firm_number}",
                            "location_id": location_id,
                            "period_start": period,
                            "treated": treated,
                            "value": value,
                        }
                    )

        model, _frame = fit_within_firm_did(rows, date(2022, 1, 1))

        self.assertAlmostEqual(model.params["treated:post"], 5, places=8)

    def test_continuous_exposure_did_recovers_slope(self):
        rows = []
        periods = [date(2020 + index // 4, (index % 4) * 3 + 1, 1) for index in range(12)]
        for company_number in range(8):
            exposure = company_number / 7
            for period_index, period in enumerate(periods):
                value = 20 + company_number + period_index * 2
                if period >= date(2022, 1, 1):
                    value += exposure * 10
                rows.append(
                    {
                        "company_id": f"company-{company_number}",
                        "period_start": period,
                        "exposure": exposure,
                        "value": value,
                    }
                )

        model, _frame = fit_continuous_exposure_did(rows, date(2022, 1, 1))

        self.assertAlmostEqual(model.params["exposure:post"], 10, places=8)

    def test_rdd_recovers_jump_at_documented_threshold(self):
        rows = []
        for index in range(-40, 41):
            distance = index * 1000
            value = 1000 + 0.002 * distance + (5 if distance >= 0 else 0)
            rows.append({"running": 150_000 + distance, "value": value})

        model, frame = fit_salary_rdd(
            rows,
            cutoff=150_000,
            bandwidth=40_000,
            minimum_per_side=20,
        )

        self.assertAlmostEqual(model.params["above"], 5, places=8)
        self.assertEqual(len(frame), 79)

    def test_continuous_exposure_must_be_pre_policy_and_constant(self):
        rows = [
            {
                "company_id": "a",
                "period_start": date(2020, month, 1),
                "exposure": exposure,
                "value": 10,
            }
            for exposure, month in ((0.1, 1), (0.2, 4), (0.1, 7), (0.1, 10))
        ]
        with self.assertRaisesRegex(ValueError, "fixe"):
            fit_continuous_exposure_did(rows, date(2020, 7, 1))

    def test_rdd_rejects_too_few_observations_on_either_side(self):
        rows = [
            {"running": value, "value": 10}
            for value in range(-5, 6)
        ]
        with self.assertRaisesRegex(ValueError, "RDD non estimable"):
            fit_salary_rdd(rows, cutoff=0, bandwidth=10, minimum_per_side=6)


if __name__ == "__main__":
    unittest.main()
