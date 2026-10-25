import unittest
from datetime import date, timedelta

from scripts.causal_event_study import fit_did


class DifferenceInDifferencesTests(unittest.TestCase):
    def test_recovers_known_treatment_effect(self):
        panel = []
        start = date(2020, 1, 1)
        for company_number in range(6):
            treated = int(company_number < 3)
            for session in range(-5, 6):
                base_return = company_number * 0.001 + session * 0.0002
                treatment_effect = 0.01 if treated and session >= 0 else 0
                panel.append(
                    {
                        "company_id": f"company-{company_number}",
                        "name": f"Company {company_number}",
                        "sector": "same-sector",
                        "score": 1.0 if treated else 0.0,
                        "date": start + timedelta(days=session + 5),
                        "session": session,
                        "abnormal_return": base_return + treatment_effect,
                        "treated": treated,
                    }
                )

        model, _ = fit_did(panel, window_sessions=5)

        self.assertAlmostEqual(model.params["treated:post"], 0.01, places=10)


if __name__ == "__main__":
    unittest.main()
