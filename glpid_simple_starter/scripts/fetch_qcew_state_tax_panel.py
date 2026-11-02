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
SOURCE_URL = "https://www.bls.gov/cew/"
STATES = {
    "us-pa": ("Pennsylvania", "42"),
    "us-de": ("Delaware", "10"),
    "us-md": ("Maryland", "24"),
    "us-nj": ("New Jersey", "34"),
    "us-ny": ("New York", "36"),
    "us-oh": ("Ohio", "39"),
    "us-wv": ("West Virginia", "54"),
    "us-va": ("Virginia", "51"),
}
POLICY_SOURCE_ID = "source-pa-act-53-2022"
POLICY_SOURCE_URL = "https://www.legis.state.pa.us/WU01/LI/LI/US/PDF/2022/0/0053..PDF"
PENNSYLVANIA_CIT_RATES = {
    2022: 9.99,
    2023: 8.99,
    2024: 8.49,
    2025: 7.99,
}


def quarter_dates(year, quarter):
    month = (quarter - 1) * 3 + 1
    start = date(year, month, 1)
    if quarter == 4:
        next_quarter = date(year + 1, 1, 1)
    else:
        next_quarter = date(year, month + 3, 1)
    return start, next_quarter - timedelta(days=1)


def parse_state_quarter(content, area_fips):
    rows = csv.DictReader(StringIO(content))
    for row in rows:
        if (
            row.get("area_fips") == area_fips
            and row.get("own_code") == "5"
            and row.get("industry_code") == "10"
        ):
            employment_fields = ("month1_emplvl", "month2_emplvl", "month3_emplvl")
            fields = (*employment_fields, "avg_wkly_wage")
            if any(not row.get(field) for field in fields):
                raise ValueError(
                    f"QCEW ne publie pas l’emploi privé total ou le salaire "
                    f"pour la zone {area_fips}."
                )
            employment = sum(int(row[field]) for field in employment_fields) / 3
            weekly_wage = float(row["avg_wkly_wage"])
            if employment <= 0 or weekly_wage <= 0:
                raise ValueError(
                    f"Valeur QCEW non positive pour la zone {area_fips}."
                )
            return employment, weekly_wage
    raise ValueError(
        f"QCEW ne contient pas la ligne privée, tous secteurs "
        f"(own_code=5, industry_code=10) pour la zone {area_fips}."
    )


def fetch_state_quarter(area_fips, year, quarter):
    url = f"https://data.bls.gov/cew/data/api/{year}/{quarter}/area/{area_fips}000.csv"
    request = Request(url, headers={"User-Agent": "GLPID state tax research"})
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
            delay = (
                min(int(retry_after), 60)
                if retry_after and retry_after.isdigit()
                else 2**attempt
            )
            time.sleep(delay)
        except (
            URLError,
            TimeoutError,
            IncompleteRead,
            RemoteDisconnected,
            ConnectionResetError,
        ) as exc:
            if attempt == 3:
                raise RuntimeError(f"Échec du téléchargement QCEW ({url}) : {exc}") from exc
            time.sleep(2**attempt)

    if content is None:
        raise RuntimeError(f"Téléchargement QCEW vide ({url}).")
    return parse_state_quarter(content, f"{area_fips}000")


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


def load_panel(start_year, end_year):
    records = []
    quarter_count = 0
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            period_start, period_end = quarter_dates(year, quarter)
            period_key = f"{year}-Q{quarter}"
            for territory_id, (state_name, area_fips) in STATES.items():
                employment, weekly_wage = fetch_state_quarter(
                    area_fips, year, quarter
                )
                source_page = (
                    f"https://data.bls.gov/cew/data/api/{year}/{quarter}/"
                    f"area/{area_fips}000.csv"
                )
                for indicator_code, value, unit, notes in (
                    (
                        "qcew_private_employment",
                        employment,
                        "persons",
                        "Mean monthly private employment, QCEW state-level, all industries.",
                    ),
                    (
                        "qcew_private_avg_weekly_wage",
                        weekly_wage,
                        "USD/week",
                        "QCEW average weekly wage, state-level, all industries.",
                    ),
                ):
                    records.append(
                        (
                            f"{territory_id}-{indicator_code}-{period_key.lower()}",
                            territory_id,
                            indicator_code,
                            period_start,
                            period_end,
                            value,
                            unit,
                            "regional",
                            SOURCE_ID,
                            source_page,
                            notes,
                        )
                    )
                print(f"{state_name}: {period_key} téléchargé.", flush=True)
            quarter_count += 1
    return records, quarter_count


def persist_panel(records):
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, 'government_statistics', %s, %s)
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
                    "Quarterly Census of Employment and Wages (QCEW), state-level",
                    SOURCE_URL,
                    "State-level private employment and average weekly wage, all industries.",
                ),
            )
            cur.execute(
                """
                INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, 'official_law', %s, %s)
                ON CONFLICT (source_id) DO UPDATE
                SET publisher = EXCLUDED.publisher,
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    url = EXCLUDED.url,
                    notes = EXCLUDED.notes
                """,
                (
                    POLICY_SOURCE_ID,
                    "Pennsylvania General Assembly",
                    "Pennsylvania Act 53 of 2022",
                    POLICY_SOURCE_URL,
                    "Act establishing phased reductions in the Pennsylvania corporate net income tax rate.",
                ),
            )
            territories = [
                (
                    territory_id,
                    state_name,
                    "state",
                    "US",
                    "us",
                    "State-level QCEW outcome panel for exploratory policy comparisons; not a firm-level measure.",
                )
                for territory_id, (state_name, _area_fips) in STATES.items()
            ]
            cur.executemany(
                """
                INSERT INTO territories
                    (territory_id, name, territory_type, country_code,
                     parent_territory_id, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_id) DO UPDATE
                SET name = EXCLUDED.name,
                    territory_type = EXCLUDED.territory_type,
                    country_code = EXCLUDED.country_code,
                    parent_territory_id = EXCLUDED.parent_territory_id,
                    description = EXCLUDED.description
                """,
                territories,
            )
            cur.execute(
                """
                INSERT INTO policy_changes
                    (policy_id, territory_id, title, policy_type, summary,
                     adoption_date, effective_date, status, affected_sector,
                     expected_mechanism, source_id, official_reference)
                VALUES (
                    'policy-pa-corporate-rate-2023', 'us-pa',
                    'Pennsylvania corporate net income tax rate phased reduction',
                    'corporate_income_tax_rate_reduction',
                    'Act 53 of 2022 established a phased reduction of the Pennsylvania corporate net income tax rate, starting at 8.99 percent in 2023.',
                    DATE '2022-07-08', DATE '2023-01-01', 'in_force',
                    'Corporations subject to Pennsylvania corporate net income tax',
                    'The phased rate reduction changes state corporate income tax liabilities for eligible apportioned taxable profits.',
                    %s, 'Pennsylvania Act 53 of 2022'
                )
                ON CONFLICT (policy_id) DO UPDATE
                SET territory_id = EXCLUDED.territory_id,
                    title = EXCLUDED.title,
                    policy_type = EXCLUDED.policy_type,
                    summary = EXCLUDED.summary,
                    adoption_date = EXCLUDED.adoption_date,
                    effective_date = EXCLUDED.effective_date,
                    source_id = EXCLUDED.source_id,
                    official_reference = EXCLUDED.official_reference
                """,
                (POLICY_SOURCE_ID,),
            )
            rate_indicators = [
                (
                    f"tax-us-pa-cit-{year}",
                    "us-pa",
                    "statutory_corporate_income_tax_rate",
                    date(year, 1, 1),
                    date(year, 12, 31),
                    rate,
                    "percent",
                    "regional",
                    POLICY_SOURCE_ID,
                    "Act 53 of 2022, phased corporate net income tax rate schedule",
                    "Pennsylvania statutory corporate net income tax rate; does not equal any individual firm's effective tax rate.",
                )
                for year, rate in PENNSYLVANIA_CIT_RATES.items()
            ]
            cur.executemany(
                """
                INSERT INTO territory_indicators
                    (territory_indicator_id, territory_id, indicator_code,
                     period_start, period_end, value, unit, geographic_scope,
                     source_id, source_page, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_indicator_id) DO UPDATE
                SET value = EXCLUDED.value,
                    unit = EXCLUDED.unit,
                    source_id = EXCLUDED.source_id,
                    source_page = EXCLUDED.source_page,
                    notes = EXCLUDED.notes
                """,
                rate_indicators,
            )
            cur.executemany(
                """
                INSERT INTO territory_indicators
                    (territory_indicator_id, territory_id, indicator_code,
                     period_start, period_end, value, unit, geographic_scope,
                     source_id, source_page, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_indicator_id) DO UPDATE
                SET value = EXCLUDED.value,
                    unit = EXCLUDED.unit,
                    source_id = EXCLUDED.source_id,
                    source_page = EXCLUDED.source_page,
                    notes = EXCLUDED.notes
                """,
                records,
            )
    return len(records)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Télécharge les séries QCEW d’emploi et de salaire pour la Pennsylvanie, "
            "ses États de comparaison et la Virginie."
        )
    )
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()
    if args.start_year < 2015 or args.end_year < args.start_year:
        parser.error("La plage doit commencer en 2015 ou après et la fin suivre le début.")
    if args.end_year > 2025:
        parser.error("Le dernier millésime QCEW pris en charge par ce test est 2025.")

    try:
        records, quarter_count = load_panel(args.start_year, args.end_year)
        row_count = persist_panel(records)
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        f"{row_count} indicateurs QCEW importés/mis à jour "
        f"({quarter_count} trimestres, {len(STATES)} États)."
    )
    print(
        "Prudence : les États témoins peuvent connaître leurs propres changements "
        "de politique ; ce panel ne suffit pas à valider une DiD causale."
    )


if __name__ == "__main__":
    main()
