import unittest
from datetime import date
import json
from pathlib import Path
from unittest.mock import patch

from policy_spillover_study.study import (
    add_months,
    build_country_snapshot,
    build_us_state_snapshot,
    horizon_status,
    month_range,
    parse_timeline,
)
from policy_spillover_study.scripts.fetch_attention import (
    chunk_is_complete,
    chunk_months,
    year_chunks,
)
from policy_spillover_study.scripts.verify_sources import (
    fetch_page,
    parse_metadata,
    parse_retry_after,
)

STUDY_DIR = Path(__file__).resolve().parents[1]


class StudyHelpersTests(unittest.TestCase):
    def test_source_metadata_parser_extracts_title_and_description(self):
        body = (
            b'<html><head><title>Official Bill Page</title>'
            b'<meta name="description" content="Official legislative record">'
            b"</head></html>"
        )
        self.assertEqual(
            parse_metadata(body, "text/html"),
            ("Official Bill Page", "Official legislative record"),
        )

    def test_source_metadata_parser_ignores_non_html(self):
        self.assertEqual(parse_metadata(b'{"data":1}', "application/json"), (None, None))

    def test_gateway_response_is_not_a_verified_source(self):
        class FakeResponse:
            status = 202
            headers = {"Content-Type": "text/html"}

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"<html><title>Gateway response</title></html>"

            def geturl(self):
                return "https://example.test/gateway"

        with patch(
            "policy_spillover_study.scripts.verify_sources.urlopen",
            return_value=FakeResponse(),
        ):
            result = fetch_page("https://example.test/source")
        self.assertEqual(result["http_status"], 202)
        self.assertIn("document non validé", result["error_text"])
        self.assertIsNone(result["page_title"])
        self.assertIsNone(result["content_sha256"])

    def test_retry_after_is_bounded_and_validated(self):
        self.assertEqual(parse_retry_after("12"), 12)
        self.assertEqual(parse_retry_after("1000"), 300)
        self.assertIsNone(parse_retry_after("tomorrow"))

    def test_month_range_includes_month_starts(self):
        self.assertEqual(
            list(month_range(date(2024, 11, 1), date(2025, 1, 31))),
            [date(2024, 11, 1), date(2024, 12, 1), date(2025, 1, 1)],
        )

    def test_gdelt_requests_are_split_by_calendar_year(self):
        self.assertEqual(
            list(year_chunks(date(2019, 1, 1), date(2021, 10, 31))),
            [
                (date(2019, 1, 1), date(2019, 12, 31)),
                (date(2020, 1, 1), date(2020, 12, 31)),
                (date(2021, 1, 1), date(2021, 10, 31)),
            ],
        )

    def test_completed_gdelt_chunk_contains_every_month(self):
        months = chunk_months(date(2019, 1, 1), date(2019, 12, 31))
        self.assertEqual(len(months), 12)
        self.assertEqual(min(months), date(2019, 1, 1))
        self.assertEqual(max(months), date(2019, 12, 1))
        stored_queries = {month: "right to repair" for month in months}
        self.assertTrue(
            chunk_is_complete(
                stored_queries, "right to repair", date(2019, 1, 1), date(2019, 12, 31)
            )
        )
        self.assertFalse(
            chunk_is_complete(
                {month: "right to repair" for month in months - {date(2019, 6, 1)}},
                "right to repair",
                date(2019, 1, 1),
                date(2019, 12, 31),
            )
        )
        self.assertFalse(
            chunk_is_complete(
                stored_queries, "(right to repair)", date(2019, 1, 1), date(2019, 12, 31)
            )
        )

    def test_seeded_gdelt_queries_group_or_terms(self):
        seed = json.loads(
            (STUDY_DIR / "data" / "seed_cases.json").read_text(encoding="utf-8")
        )
        queries = {case["gdelt_query"] for case in seed["cases"]}
        self.assertEqual(len(queries), 6)
        for query in queries:
            self.assertTrue(query.startswith("("), query)
            self.assertTrue(query.endswith(")"), query)

    def test_parse_timeline_aggregates_daily_counts(self):
        payload = {
            "timeline": [
                {
                    "series": "Article Count",
                    "data": [
                        {"date": "20240101000000", "value": "3"},
                        {"date": "20240102000000", "value": "2"},
                    ],
                }
            ]
        }
        self.assertEqual(parse_timeline(payload), {date(2024, 1, 1): 5})

    def test_parse_timeline_rejects_empty_response(self):
        with self.assertRaises(ValueError):
            parse_timeline({"timeline": []})
        with self.assertRaises(ValueError):
            parse_timeline({"timeline": [{"series": "Article Count", "data": []}]})

    def test_add_months_clamps_month_end(self):
        self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))

    def test_us_state_snapshot_tracks_proposals_and_adoptions_by_date(self):
        events = [
            {
                "event_id": "va-proposal",
                "territory_id": "us-va",
                "event_level": "state",
                "event_type": "proposed",
                "relationship": "same_family",
                "event_date": date(2021, 1, 13),
                "policy_title": "Virginia privacy bill",
            },
            {
                "event_id": "va-adoption",
                "territory_id": "us-va",
                "event_level": "state",
                "event_type": "adopted",
                "relationship": "same_family",
                "event_date": date(2021, 3, 2),
                "policy_title": "Virginia privacy law",
            },
            {
                "event_id": "eu-analogue",
                "territory_id": "eu",
                "event_level": "international",
                "event_type": "adopted",
                "relationship": "partial_analogue",
                "event_date": date(2021, 2, 1),
                "policy_title": "Non-state analogue",
            },
        ]
        proposal_snapshot = build_us_state_snapshot(
            events, "us-ca", date(2018, 6, 28), date(2021, 1, 31)
        )
        adoption_snapshot = build_us_state_snapshot(
            events, "us-ca", date(2018, 6, 28), date(2021, 12, 31)
        )
        proposal_by_state = {row["abbreviation"]: row for row in proposal_snapshot}
        adoption_by_state = {row["abbreviation"]: row for row in adoption_snapshot}
        self.assertEqual(len(proposal_snapshot), 50)
        self.assertEqual(proposal_by_state["CA"]["status"], "Point d’ancrage")
        self.assertEqual(proposal_by_state["VA"]["status"], "Projet documenté")
        self.assertEqual(adoption_by_state["VA"]["status"], "Loi adoptée")
        self.assertEqual(
            adoption_by_state["NY"]["status"], "Non documenté dans le pilote"
        )

    def test_country_snapshot_maps_national_laws_and_marks_analogues(self):
        events = [
            {
                "event_id": "fr-anchor",
                "territory_id": "fr",
                "territory_type": "country",
                "jurisdiction": "France",
                "country_code": "FR",
                "event_level": "national",
                "event_type": "adopted",
                "relationship": "same_family",
                "event_date": date(2017, 3, 27),
            },
            {
                "event_id": "de-analogue",
                "territory_id": "de",
                "territory_type": "country",
                "jurisdiction": "Germany",
                "country_code": "DE",
                "event_level": "national",
                "event_type": "adopted",
                "relationship": "partial_analogue",
                "event_date": date(2021, 7, 16),
                "policy_title": "German due diligence law",
            },
            {
                "event_id": "eu-directive",
                "territory_id": "eu",
                "territory_type": "region",
                "jurisdiction": "European Union",
                "event_level": "international",
                "event_type": "adopted",
                "relationship": "successor",
                "event_date": date(2024, 6, 13),
            },
        ]
        snapshot = build_country_snapshot(
            events, "fr", date(2017, 3, 27), date(2022, 12, 31)
        )
        by_country = {row["country"]: row for row in snapshot}
        self.assertEqual(by_country["France"]["status"], "Point d’ancrage")
        self.assertEqual(by_country["Germany"]["status"], "Adoption analogue")
        self.assertNotIn("European Union", by_country)
        early_snapshot = build_country_snapshot(
            events, "fr", date(2017, 3, 27), date(2019, 12, 31)
        )
        early_by_country = {row["country"]: row for row in early_snapshot}
        self.assertEqual(early_by_country["Germany"]["status"], "Événement ultérieur")

    def test_horizon_counts_only_adopted_same_family_or_successor_events(self):
        case = {"anchor_date": date(2020, 1, 1), "target_level": "international"}
        events = [
            {
                "event_type": "adopted",
                "relationship": "same_family",
                "event_level": "state",
                "event_date": date(2020, 8, 1),
            },
            {
                "event_type": "adopted",
                "relationship": "partial_analogue",
                "event_level": "state",
                "event_date": date(2020, 9, 1),
            },
            {
                "event_type": "adopted",
                "relationship": "same_family",
                "event_level": "international",
                "event_date": date(2020, 10, 1),
            },
            {
                "event_type": "proposed",
                "relationship": "same_family",
                "event_level": "international",
                "event_date": date(2020, 6, 1),
            },
            {
                "event_type": "vetoed",
                "relationship": "successor",
                "event_level": "federal",
                "event_date": date(2020, 11, 1),
            },
        ]
        result = horizon_status(case, events, 12, date(2022, 1, 1))
        self.assertEqual(result["status"], "Adoption documentée")
        self.assertEqual(len(result["adoptions"]), 1)
        self.assertEqual(result["strict_status"], "Adoption après proposition postérieure")
        self.assertEqual(len(result["strict_adoptions"]), 1)

    def test_horizon_reports_open_window(self):
        result = horizon_status(
            {"anchor_date": date(2026, 1, 1), "target_level": "international"},
            [],
            12,
            date(2026, 11, 1),
        )
        self.assertEqual(result["status"], "Fenêtre en cours")

    def test_seeded_case_horizons_match_curated_timeline(self):
        seed = json.loads(
            (STUDY_DIR / "data" / "seed_cases.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(seed["cases"]), 12)
        self.assertEqual(len(seed["events"]), 46)
        self.assertEqual(len({case["policy_family"] for case in seed["cases"]}), 6)
        events_by_case = {}
        for event in seed["events"]:
            event["event_date"] = date.fromisoformat(event["event_date"])
            events_by_case.setdefault(event["case_id"], []).append(event)
        expected = {
            "pay-transparency-co-2019": ("Aucune adoption enregistrée", "Aucune adoption enregistrée"),
            "pay-transparency-ny-2022": ("Adoption documentée", "Adoption documentée"),
            "pay-transparency-ca-2022": ("Adoption documentée", "Adoption documentée"),
            "right-repair-ny-2022": ("Aucune adoption enregistrée", "Adoption documentée"),
            "right-repair-co-2023": ("Aucune adoption enregistrée", "Adoption documentée"),
            "right-repair-ca-2023": ("Adoption documentée", "Adoption documentée"),
            "ai-safety-sb1047-2024": ("Aucune adoption enregistrée", "Fenêtre en cours"),
            "consumer-privacy-ca-2018": (
                "Aucune adoption enregistrée",
                "Adoption documentée",
            ),
            "consumer-privacy-va-2021": ("Adoption documentée", "Adoption documentée"),
            "consumer-privacy-co-2021": ("Adoption documentée", "Adoption documentée"),
            "digital-services-tax-fr-2019": ("Adoption documentée", "Adoption documentée"),
            "corporate-due-diligence-fr-2017": (
                "Aucune adoption enregistrée",
                "Aucune adoption enregistrée",
            ),
        }
        for case in seed["cases"]:
            if isinstance(case["anchor_date"], str):
                case["anchor_date"] = date.fromisoformat(case["anchor_date"])
            horizons = tuple(
                horizon_status(
                    case,
                    events_by_case.get(case["case_id"], []),
                    horizon,
                    date(2026, 11, 4),
                )["status"]
                for horizon in (12, 36)
            )
            self.assertEqual(horizons, expected[case["case_id"]])

        strict_expected = {
            "pay-transparency-co-2019": (
                "Aucune adoption équivalente documentée",
                "Proposition postérieure, sans adoption dans la fenêtre",
            ),
            "pay-transparency-ny-2022": (
                "Adoption après une proposition antérieure",
                "Adoption après une proposition antérieure",
            ),
            "pay-transparency-ca-2022": (
                "Adoption après une proposition antérieure",
                "Adoption après une proposition antérieure",
            ),
            "right-repair-ny-2022": (
                "Proposition postérieure, sans adoption dans la fenêtre",
                "Adoption après proposition postérieure",
            ),
            "right-repair-co-2023": (
                "Aucune adoption équivalente documentée",
                "Adoption après une proposition antérieure",
            ),
            "right-repair-ca-2023": (
                "Adoption après une proposition antérieure",
                "Adoption après une proposition antérieure",
            ),
            "ai-safety-sb1047-2024": (
                "Aucune adoption équivalente documentée",
                "Fenêtre en cours",
            ),
            "consumer-privacy-ca-2018": (
                "Aucune adoption équivalente documentée",
                "Adoption après proposition postérieure",
            ),
            "consumer-privacy-va-2021": (
                "Adoption après proposition postérieure",
                "Adoption après proposition postérieure",
            ),
            "consumer-privacy-co-2021": (
                "Adoption après proposition postérieure",
                "Adoption après proposition postérieure",
            ),
            "digital-services-tax-fr-2019": (
                "Adoption après une proposition antérieure",
                "Adoption après une proposition antérieure",
            ),
            "corporate-due-diligence-fr-2017": (
                "Aucune adoption équivalente documentée",
                "Aucune adoption équivalente documentée",
            ),
        }
        for case in seed["cases"]:
            if isinstance(case["anchor_date"], str):
                case["anchor_date"] = date.fromisoformat(case["anchor_date"])
            statuses = tuple(
                horizon_status(
                    case,
                    events_by_case.get(case["case_id"], []),
                    horizon,
                    date(2026, 11, 4),
                )["strict_status"]
                for horizon in (12, 36)
            )
            self.assertEqual(statuses, strict_expected[case["case_id"]])


if __name__ == "__main__":
    unittest.main()
