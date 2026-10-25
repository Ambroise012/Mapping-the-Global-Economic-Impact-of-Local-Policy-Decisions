import argparse
import csv
import os
import sys
import time
from datetime import date, timedelta
from http.client import IncompleteRead, RemoteDisconnected
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv


SOURCE_ID = "source-bls-qcew"
QCEW_SOURCE_URL = "https://www.bls.gov/cew/"
COUNTIES = {
    "us-wa-king-county": ("King County, Washington", "53033"),
    "us-wa-clark-county": ("Clark County, Washington", "53011"),
    "us-wa-spokane-county": ("Spokane County, Washington", "53063"),
    "us-wa-thurston-county": ("Thurston County, Washington", "53067"),
    "us-wa-whatcom-county": ("Whatcom County, Washington", "53073"),
    "us-wa-yakima-county": ("Yakima County, Washington", "53077"),
}
CITY_SOURCE_ID = "source-seattle-jumpstart"
CITY_SOURCE_URL = "https://clerk.seattle.gov/search/ordinances/126109"
SEATTLE_POLICY_ID = "policy-seattle-jumpstart-2021"
INDUSTRIES = {
    "10": "all-industry-private",
    "101": "goods-producing",
    "102": "service-providing",
    "51": "information",
    "52": "finance-insurance",
    "54": "professional-scientific-technical",
    "55": "management-of-companies",
    "56": "administrative-support-waste",
    "62": "health-care-social-assistance",
    "71": "arts-entertainment-recreation",
    "72": "accommodation-food-services",
}


def quarter_dates(year, quarter):
    month = (quarter - 1) * 3 + 1
    start = date(year, month, 1)
    if quarter == 4:
        next_quarter = date(year + 1, 1, 1)
    else:
        next_quarter = date(year, month + 3, 1)
    end = next_quarter - timedelta(days=1)
    return start, end


def fetch_county_quarter(area_fips, year, quarter):
    url = f"https://data.bls.gov/cew/data/api/{year}/{quarter}/area/{area_fips}.csv"
    request = Request(url, headers={"User-Agent": "GLPID local employment research"})
    content = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                content = response.read().decode("utf-8-sig")
            break
        except HTTPError as exc:
            retryable = exc.code in (429, 500, 502, 503, 504)
            if not retryable or attempt == 3:
                raise RuntimeError(f"Échec du téléchargement QCEW ({url}) : {exc}") from exc
            retry_after = exc.headers.get("Retry-After")
            delay = min(int(retry_after), 60) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(delay)
        except (URLError, TimeoutError, IncompleteRead, RemoteDisconnected, ConnectionResetError) as exc:
            if attempt == 3:
                raise RuntimeError(f"Échec du téléchargement QCEW ({url}) : {exc}") from exc
            time.sleep(2 ** attempt)

    if content is None:
        raise RuntimeError(f"Téléchargement QCEW vide ({url}).")
    rows = csv.DictReader(StringIO(content))
    values = {}
    for row in rows:
        industry_code = row.get("industry_code")
        if (
            row.get("area_fips") != area_fips
            or row.get("own_code") != "5"
            or industry_code not in INDUSTRIES
        ):
            continue

        employment_fields = ("month1_emplvl", "month2_emplvl", "month3_emplvl")
        if any(not row.get(field) for field in (*employment_fields, "avg_wkly_wage")):
            continue
        employment = sum(int(row[field]) for field in employment_fields) / 3
        weekly_wage = float(row["avg_wkly_wage"])
        if employment > 0 and weekly_wage > 0:
            values[industry_code] = (employment, weekly_wage)

    if "10" not in values:
        raise ValueError(
            f"Ligne QCEW privée, tous secteurs (own_code=5, industry_code=10) "
            f"indisponible ou confidentielle pour {area_fips} {year}-Q{quarter}."
        )
    return values


def database_connection():
    load_dotenv()
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Paramètres manquants dans .env : {', '.join(missing)}")
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )


def persist_panel(records):
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE
                SET publisher = EXCLUDED.publisher,
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    url = EXCLUDED.url,
                    notes = EXCLUDED.notes
                """,
                (
                    SOURCE_ID,
                    "U.S. Bureau of Labor Statistics",
                    "Quarterly Census of Employment and Wages (QCEW)",
                    "government_statistics",
                    QCEW_SOURCE_URL,
                    "County-level private employment and average weekly wages by selected QCEW industry codes.",
                ),
            )
            cur.execute(
                """
                INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE
                SET publisher = EXCLUDED.publisher,
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    url = EXCLUDED.url,
                    notes = EXCLUDED.notes
                """,
                (
                    CITY_SOURCE_ID,
                    "City of Seattle",
                    "Seattle Ordinance 126109 — JumpStart Payroll Expense Tax",
                    "official_law",
                    CITY_SOURCE_URL,
                    "Official ordinance record. Verify dates and applicability against the enacted text.",
                ),
            )

            territories = [
                (
                    "us-wa",
                    "Washington",
                    "state",
                    "US",
                    None,
                    "State containing the treated proxy and comparison counties.",
                    None,
                ),
                (
                    "us-wa-seattle",
                    "Seattle, Washington",
                    "city",
                    "US",
                    "us-wa",
                    "Policy jurisdiction for the JumpStart Payroll Expense Tax. Employment data below are county-level, not city-level.",
                    CITY_SOURCE_URL,
                ),
            ]
            territories.extend(
                (
                    territory_id,
                    name,
                    "other",
                    "US",
                    "us-wa",
                    (
                        "King County is an imperfect county-level proxy for Seattle."
                        if territory_id == "us-wa-king-county"
                        else "QCEW county-level comparison geography; not a matched untreated city."
                    ),
                    QCEW_SOURCE_URL,
                )
                for territory_id, (name, _area_fips) in COUNTIES.items()
            )
            cur.executemany(
                """
                INSERT INTO territories
                    (territory_id, name, territory_type, country_code, parent_territory_id,
                     description, boundary_source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_id) DO UPDATE
                SET name = EXCLUDED.name,
                    territory_type = EXCLUDED.territory_type,
                    country_code = EXCLUDED.country_code,
                    parent_territory_id = EXCLUDED.parent_territory_id,
                    description = EXCLUDED.description,
                    boundary_source_url = EXCLUDED.boundary_source_url
                """,
                territories,
            )
            cur.execute(
                """
                INSERT INTO policy_changes
                    (policy_id, territory_id, title, policy_type, summary, adoption_date,
                     effective_date, status, affected_sector, expected_mechanism,
                     source_id, official_reference)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_id) DO UPDATE
                SET territory_id = EXCLUDED.territory_id,
                    title = EXCLUDED.title,
                    policy_type = EXCLUDED.policy_type,
                    summary = EXCLUDED.summary,
                    adoption_date = EXCLUDED.adoption_date,
                    effective_date = EXCLUDED.effective_date,
                    status = EXCLUDED.status,
                    affected_sector = EXCLUDED.affected_sector,
                    expected_mechanism = EXCLUDED.expected_mechanism,
                    source_id = EXCLUDED.source_id,
                    official_reference = EXCLUDED.official_reference
                """,
                (
                    SEATTLE_POLICY_ID,
                    "us-wa-seattle",
                    "Seattle JumpStart Payroll Expense Tax",
                    "local_payroll_expense_tax",
                    "Municipal payroll expense tax enacted in 2020 and effective in 2021. Liability depends on the statutory employer and compensation rules.",
                    date(2020, 7, 6),
                    date(2021, 1, 1),
                    "in_force",
                    "Employers meeting Seattle payroll and compensation thresholds under the applicable annual rules.",
                    "Payroll tax liability may affect employer costs, hiring, compensation, or location decisions.",
                    CITY_SOURCE_ID,
                    "Seattle Ordinance 126109",
                ),
            )
            cur.executemany(
                """
                INSERT INTO territory_indicators
                    (territory_indicator_id, territory_id, indicator_code, period_start,
                     period_end, value, unit, geographic_scope, source_id, source_page, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_indicator_id) DO UPDATE
                SET value = EXCLUDED.value,
                    source_id = EXCLUDED.source_id,
                    source_page = EXCLUDED.source_page,
                    notes = EXCLUDED.notes,
                    collected_at = now()
                """,
                records,
            )
    return len(records)


def load_panel(start_year, end_year):
    records = []
    quarter_count = 0
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            start, end = quarter_dates(year, quarter)
            for territory_id, (_name, area_fips) in COUNTIES.items():
                industry_values = fetch_county_quarter(area_fips, year, quarter)
                period_key = f"{year}-Q{quarter}"
                source_page = (
                    f"https://data.bls.gov/cew/data/api/{year}/{quarter}/area/{area_fips}.csv"
                )
                for industry_code, (employment, weekly_wage) in industry_values.items():
                    industry_name = INDUSTRIES[industry_code]
                    employment_indicator = (
                        "qcew_private_employment"
                        if industry_code == "10"
                        else f"qcew_private_employment_{industry_name}"
                    )
                    wage_indicator = (
                        "qcew_private_avg_weekly_wage"
                        if industry_code == "10"
                        else f"qcew_private_avg_weekly_wage_{industry_name}"
                    )
                    for indicator_code, value, unit, notes in (
                        (
                            employment_indicator,
                            employment,
                            "persons",
                            f"Mean monthly private employment, QCEW industry code {industry_code}.",
                        ),
                        (
                            wage_indicator,
                            weekly_wage,
                            "USD/week",
                            f"QCEW average weekly wage, industry code {industry_code}.",
                        ),
                    ):
                        records.append(
                            (
                                f"{territory_id}-{indicator_code}-{period_key.lower()}",
                                territory_id,
                                indicator_code,
                                start,
                                end,
                                value,
                                unit,
                                "regional",
                                SOURCE_ID,
                                source_page,
                                notes,
                            )
                        )
            quarter_count += 1
            print(f"Données QCEW téléchargées : {period_key}.")
    return records, quarter_count


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Télécharge les indicateurs QCEW d’emploi privé et de salaires par secteur "
            "pour King County et cinq comtés témoins, puis les enregistre dans PostgreSQL."
        )
    )
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()
    if args.start_year < 2015 or args.end_year < args.start_year:
        parser.error("Vérifie la plage d’années (début >= 2015 et fin >= début).")

    try:
        records, quarter_count = load_panel(args.start_year, args.end_year)
        row_count = persist_panel(records)
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        f"{row_count} indicateurs QCEW importés/mis à jour "
        f"({quarter_count} trimestres, {len(COUNTIES)} comtés)."
    )
    print(
        "Attention : King County est un proxy régional, pas une mesure de l’emploi "
        "dans la seule ville de Seattle."
    )


if __name__ == "__main__":
    main()
