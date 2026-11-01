import argparse
import csv
import json
import os
import sys
import time
from datetime import date, timedelta
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv

DATASET = "lfsi_emp_q"
SOURCE_ID = "source-eurostat-lfsi-quarterly"
SOURCE_URL = (
    "https://ec.europa.eu/eurostat/databrowser/view/lfsi_emp_q/default/table"
    "?lang=en"
)
ONS_SOURCE_ID = "source-ons-labour-market-lfs"
ONS_URL = (
    "https://download.ons.gov.uk/downloads/datasets/labour-market/"
    "editions/PWT24/versions/1.csv"
)
BLS_SOURCE_ID = "source-bls-cps-employment"
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/LNS12000000"
INDICATOR_CODE = "eurostat_lfs_employment"
COUNTRIES = {
    "at": ("Austria", "AT"),
    "be": ("Belgium", "BE"),
    "ch": ("Switzerland", "CH"),
    "cz": ("Czechia", "CZ"),
    "de": ("Germany", "DE"),
    "dk": ("Denmark", "DK"),
    "es": ("Spain", "ES"),
    "fi": ("Finland", "FI"),
    "fr": ("France", "FR"),
    "ie": ("Ireland", "IE"),
    "it": ("Italy", "IT"),
    "nl": ("Netherlands", "NL"),
    "no": ("Norway", "NO"),
    "pt": ("Portugal", "PT"),
    "ro": ("Romania", "RO"),
    "se": ("Sweden", "SE"),
}
COUNTRY_NAMES = {
    **{territory_id: country[0] for territory_id, country in COUNTRIES.items()},
    "gb": "United Kingdom",
    "us": "United States",
}
COUNTRY_CODES = {
    **{territory_id: country[1] for territory_id, country in COUNTRIES.items()},
    "gb": "GB",
    "us": "US",
}
START_QUARTER = "2014-Q1"
END_QUARTER = "2025-Q4"


def parse_quarter(value):
    try:
        year_text, quarter_text = value.split("-Q")
        year, quarter = int(year_text), int(quarter_text)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError(
            "Format trimestriel attendu : AAAA-Qn, par exemple 2021-Q1."
        ) from exc
    if quarter not in range(1, 5):
        raise argparse.ArgumentTypeError("Le trimestre doit être compris entre Q1 et Q4.")
    return date(year, 3 * quarter - 2, 1)


def quarter_label(period_start):
    return f"{period_start.year}-Q{(period_start.month - 1) // 3 + 1}"


def quarter_end(period_start):
    if period_start.month == 10:
        next_quarter = date(period_start.year + 1, 1, 1)
    else:
        next_quarter = date(period_start.year, period_start.month + 3, 1)
    return next_quarter - timedelta(days=1)


def quarter_range(start, end):
    current = start
    while current <= end:
        yield current
        current = date(
            current.year + (current.month == 10),
            1 if current.month == 10 else current.month + 3,
            1,
        )


def fetch_country(country_code, start_quarter, end_quarter):
    query = urlencode(
        {
            "freq": "Q",
            "indic_em": "EMP_LFS",
            "s_adj": "SA",
            "sex": "T",
            "age": "Y15-74",
            "unit": "THS_PER",
            "geo": country_code,
            "sinceTimePeriod": quarter_label(start_quarter),
            "untilTimePeriod": quarter_label(end_quarter),
        }
    )
    url = (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        f"{DATASET}?{query}"
    )
    request = Request(url, headers={"User-Agent": "GLPID research data collection"})
    payload = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.load(response)
            break
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise RuntimeError(
                    f"Échec de l’API Eurostat pour {country_code} ({url}) : {exc}"
                ) from exc
            time.sleep(min(2**attempt, 30))
        except (URLError, TimeoutError, OSError) as exc:
            if attempt == 3:
                raise RuntimeError(
                    f"Échec de l’API Eurostat pour {country_code} ({url}) : {exc}"
                ) from exc
            time.sleep(2**attempt)

    if payload is None:
        raise RuntimeError(f"Réponse Eurostat vide pour {country_code}.")
    values = payload.get("value", {})
    time_index = payload.get("dimension", {}).get("time", {}).get("category", {}).get(
        "index", {}
    )
    periods = list(quarter_range(start_quarter, end_quarter))
    expected_periods = {quarter_label(period) for period in periods}
    if set(time_index) != expected_periods:
        raise ValueError(
            f"Couverture temporelle Eurostat inattendue pour {country_code} : "
            f"{len(time_index)} trimestre(s), {len(periods)} attendu(s)."
        )

    records = []
    for period in periods:
        position = time_index[quarter_label(period)]
        raw_value = values.get(str(position))
        if raw_value is None or float(raw_value) <= 0:
            raise ValueError(
                f"Observation absente ou non positive pour {country_code}, "
                f"{quarter_label(period)}."
            )
        records.append(
            (
                period,
                quarter_end(period),
                float(raw_value),
                url,
                SOURCE_ID,
                (
                    "Eurostat quarterly Labour Force Survey employment, persons aged "
                    "15-74, both sexes, seasonally adjusted; thousand persons. "
                    "National aggregate, not a local-firm outcome."
                ),
            )
        )
    return records


def fetch_uk(start_quarter, end_quarter):
    request = Request(ONS_URL, headers={"User-Agent": "GLPID research data collection"})
    try:
        with urlopen(request, timeout=60) as response:
            content = response.read().decode("utf-8-sig")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Échec du téléchargement ONS ({ONS_URL}) : {exc}") from exc
    return parse_uk_csv(content, start_quarter, end_quarter)


def parse_uk_csv(content, start_quarter, end_quarter):
    rows = csv.DictReader(StringIO(content))
    records = []
    for row in rows:
        if (
            row.get("Geography") != "United Kingdom"
            or row.get("economic-activity") != "in-employment"
            or row.get("AgeGroups") != "16+"
            or row.get("Sex") != "All adults"
            or row.get("SeasonalAdjustment") != "Seasonally Adjusted"
            or row.get("UnitOfMeasure") != "Levels"
        ):
            continue
        date_parts = row["mmm-mmm-yyyy"].lower().split("-")
        if len(date_parts) != 3:
            continue
        start_month = {"jan": 1, "apr": 4, "jul": 7, "oct": 10}.get(date_parts[0])
        if start_month is None:
            continue
        period_start = date(int(date_parts[2]), start_month, 1)
        if not start_quarter <= period_start <= end_quarter:
            continue
        value = float(row["v4_0"]) / 1000
        if value <= 0:
            raise ValueError(
                f"Observation ONS non positive pour {quarter_label(period_start)}."
            )
        records.append(
            (
                period_start,
                quarter_end(period_start),
                value,
                ONS_URL,
                ONS_SOURCE_ID,
                (
                    "ONS Labour Force Survey (PWT24), seasonally adjusted employment "
                    "level for UK residents aged 16+, all adults, converted from persons "
                    "to thousand persons. Available calendar quarters begin in 2019-Q1; "
                    "definition differs slightly from Eurostat ages 15-74."
                ),
            )
        )
    records.sort()
    expected_periods = [
        period
        for period in quarter_range(start_quarter, end_quarter)
        if date(2019, 1, 1) <= period <= date(2025, 1, 1)
    ]
    if [record[0] for record in records] != expected_periods:
        raise ValueError(
            "Couverture ONS inattendue : les trimestres disponibles doivent être "
            "continus entre 2019-Q1 et 2025-Q1."
        )
    if not records:
        raise ValueError("Aucune période ONS n’est disponible dans la fenêtre demandée.")
    return records


def parse_bls_responses(responses, start_quarter, end_quarter):
    monthly_values = {}
    for payload in responses:
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(
                f"Réponse BLS non réussie : {payload.get('message', payload.get('status'))}"
            )
        series = payload.get("Results", {}).get("series", [])
        if not series or series[0].get("seriesID") != "LNS12000000":
            raise ValueError("La série BLS LNS12000000 est absente de la réponse.")
        for observation in series[0].get("data", []):
            period_code = observation.get("period", "")
            if not period_code.startswith("M") or period_code == "M13":
                continue
            month = int(period_code[1:])
            if month not in range(1, 13):
                continue
            period = date(int(observation["year"]), month, 1)
            if observation["value"] in ("", "-", None):
                continue
            monthly_values[period] = float(observation["value"])
    records = []
    for period_start in quarter_range(start_quarter, end_quarter):
        months = [
            date(period_start.year, period_start.month + offset, 1)
            for offset in range(3)
        ]
        if any(month not in monthly_values for month in months):
            if period_start == end_quarter:
                continue
            raise ValueError(
                f"Couverture BLS incomplète pour {quarter_label(period_start)}."
            )
        records.append(
            (
                period_start,
                quarter_end(period_start),
                sum(monthly_values[month] for month in months) / 3,
                f"{BLS_URL}?startyear={period_start.year}&endyear={period_start.year}",
                BLS_SOURCE_ID,
                (
                    "U.S. BLS Current Population Survey, civilian employment level "
                    "(LNS12000000), seasonally adjusted, age 16+, in thousands; "
                    "quarterly mean of three monthly estimates. National aggregate, "
                    "not a local-firm outcome. Definition differs slightly from "
                    "Eurostat ages 15-74."
                ),
            )
        )
    if not records:
        raise ValueError("Aucune période BLS complète n’est disponible dans la fenêtre.")
    return records


def fetch_us(start_quarter, end_quarter):
    responses = []
    chunk_start = start_quarter.year
    while chunk_start <= end_quarter.year:
        chunk_end = min(chunk_start + 9, end_quarter.year)
        url = f"{BLS_URL}?startyear={chunk_start}&endyear={chunk_end}"
        request = Request(url, headers={"User-Agent": "GLPID research data collection"})
        try:
            with urlopen(request, timeout=45) as response:
                responses.append(json.load(response))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Échec de l’API BLS ({url}) : {exc}") from exc
        chunk_start = chunk_end + 1
    return parse_bls_responses(responses, start_quarter, end_quarter)


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


def persist_panel(country_records):
    territories = [
        (
            territory_id,
            COUNTRY_NAMES[territory_id],
            "country",
            COUNTRY_CODES[territory_id],
            (
                "National employment series for the exploratory corporate-tax "
                "policy panel; not a local-firm outcome."
            ),
        )
        for territory_id in country_records
    ]
    indicators = []
    for territory_id, observations in country_records.items():
        for (
            period_start,
            period_end,
            value,
            source_page,
            source_id,
            notes,
        ) in observations:
            period = quarter_label(period_start).lower()
            indicators.append(
                (
                    f"{territory_id}-eurostat-lfs-employment-{period}",
                    territory_id,
                    INDICATOR_CODE,
                    period_start,
                    period_end,
                    value,
                    "thousand persons",
                    "national",
                    source_id,
                    source_page,
                    notes,
                )
            )

    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO sources
                    (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, 'government_statistics', %s, %s)
                ON CONFLICT (source_id) DO UPDATE
                SET publisher = EXCLUDED.publisher,
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    url = EXCLUDED.url,
                    notes = EXCLUDED.notes
                """,
                [
                    (
                        SOURCE_ID,
                        "Eurostat",
                        "Employment and labour force by sex and age — quarterly data (lfsi_emp_q)",
                        SOURCE_URL,
                        (
                            "Quarterly Labour Force Survey employment for ages 15-74, both "
                            "sexes, seasonally adjusted, in thousand persons. Data accessed "
                            "through the official Eurostat dissemination API."
                        ),
                    ),
                    (
                        ONS_SOURCE_ID,
                        "Office for National Statistics",
                        "UK Labour Market — Labour Force Survey, PWT24",
                        ONS_URL,
                        (
                            "Seasonally adjusted quarterly UK LFS employment levels for ages "
                            "16+, all adults. PWT24 edition published in June 2025; series "
                            "used here is available from 2019-Q1 to 2025-Q1."
                        ),
                    ),
                    (
                        BLS_SOURCE_ID,
                        "U.S. Bureau of Labor Statistics",
                        "Current Population Survey — civilian employment level (LNS12000000)",
                        BLS_URL,
                        (
                            "Monthly seasonally adjusted CPS civilian employment level for "
                            "people aged 16+, aggregated as quarterly means and stored in "
                            "thousand persons."
                        ),
                    ),
                ],
            )
            cur.executemany(
                """
                INSERT INTO territories
                    (territory_id, name, territory_type, country_code, description)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (territory_id) DO UPDATE
                SET name = EXCLUDED.name,
                    territory_type = EXCLUDED.territory_type,
                    country_code = EXCLUDED.country_code,
                    description = EXCLUDED.description
                """,
                territories,
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
                    source_id = EXCLUDED.source_id,
                    source_page = EXCLUDED.source_page,
                    notes = EXCLUDED.notes
                """,
                indicators,
            )
    return len(indicators)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Télécharge depuis Eurostat un panel trimestriel harmonisé d’emploi "
            "national et le charge dans PostgreSQL."
        )
    )
    parser.add_argument("--start-quarter", type=parse_quarter, default=parse_quarter(START_QUARTER))
    parser.add_argument("--end-quarter", type=parse_quarter, default=parse_quarter(END_QUARTER))
    args = parser.parse_args()
    if args.start_quarter > args.end_quarter:
        parser.error("Le trimestre de début doit précéder celui de fin.")

    try:
        country_records = {}
        for territory_id, (country_name, country_code) in COUNTRIES.items():
            country_records[territory_id] = fetch_country(
                country_code, args.start_quarter, args.end_quarter
            )
            print(
                f"{country_name}: {len(country_records[territory_id])} trimestres "
                f"téléchargés.",
                flush=True,
            )
        country_records["gb"] = fetch_uk(args.start_quarter, args.end_quarter)
        print(
            "United Kingdom (ONS): "
            f"{len(country_records['gb'])} trimestres téléchargés "
            f"({quarter_label(country_records['gb'][0][0])} à "
            f"{quarter_label(country_records['gb'][-1][0])}).",
            flush=True,
        )
        country_records["us"] = fetch_us(args.start_quarter, args.end_quarter)
        print(
            f"United States (BLS): {len(country_records['us'])} trimestres complets "
            f"({quarter_label(country_records['us'][0][0])} à "
            f"{quarter_label(country_records['us'][-1][0])}).",
            flush=True,
        )
        if country_records["us"][-1][0] != args.end_quarter:
            print(
                f"United States (BLS): {quarter_label(args.end_quarter)} non importé, "
                "car les trois estimations mensuelles complètes ne sont pas publiées.",
                flush=True,
            )
        row_count = persist_panel(country_records)
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        f"{row_count} observations d’emploi nationales importées/mises à jour."
    )


if __name__ == "__main__":
    main()
