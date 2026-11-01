import unittest

from scripts.fetch_qcew_state_tax_panel import parse_state_quarter


class QcewStateTaxPanelTests(unittest.TestCase):
    def test_extracts_state_private_employment_and_wage(self):
        content = (
            '"area_fips","own_code","industry_code","month1_emplvl",'
            '"month2_emplvl","month3_emplvl","avg_wkly_wage"\n'
            '"42000","5","10","1000","1100","1200","1500"\n'
            '"42000","0","10","9000","9000","9000","9000"\n'
        )

        self.assertEqual(parse_state_quarter(content, "42000"), (1100, 1500.0))

    def test_rejects_suppressed_state_total(self):
        content = (
            '"area_fips","own_code","industry_code","month1_emplvl",'
            '"month2_emplvl","month3_emplvl","avg_wkly_wage"\n'
            '"42000","5","10","","","",""\n'
        )

        with self.assertRaisesRegex(ValueError, "ne publie pas"):
            parse_state_quarter(content, "42000")

    def test_rejects_missing_state_total(self):
        content = (
            '"area_fips","own_code","industry_code","month1_emplvl",'
            '"month2_emplvl","month3_emplvl","avg_wkly_wage"\n'
            '"42000","5","54","100","110","120","1800"\n'
        )

        with self.assertRaisesRegex(ValueError, "ne contient pas"):
            parse_state_quarter(content, "42000")


if __name__ == "__main__":
    unittest.main()
