import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv


SOURCE_ID = "source-yahoo-finance-chart"
SOURCE_URL = "https://finance.yahoo.com/"
CASES = {
    "us": {
        "territory_id": "us",
        "country_code": "US",
        "index_ticker": "^GSPC",
        "exposure_basis": "Candidate exposure to US federal corporate tax; verify eligibility and taxable income from filings.",
        "start_date": date(2017, 8, 1),
        "end_date": date(2018, 4, 1),
        "companies": [
            ("company-aapl", "Apple Inc.", "AAPL", "Technology"),
            ("company-msft", "Microsoft Corporation", "MSFT", "Technology"),
            ("company-googl", "Alphabet Inc.", "GOOGL", "Technology"),
            ("company-csco", "Cisco Systems, Inc.", "CSCO", "Technology"),
            ("company-orcl", "Oracle Corporation", "ORCL", "Technology"),
        ],
    },
    "uk": {
        "territory_id": "gb",
        "country_code": "GB",
        "index_ticker": "^FTSE",
        "exposure_basis": "Candidate exposure to UK Corporation Tax; verify taxable profits, reliefs, and any sector-specific rules from filings.",
        "start_date": date(2020, 10, 1),
        "end_date": date(2021, 6, 30),
        "companies": [
            ("company-barc", "Barclays PLC", "BARC.L", "Financials"),
            ("company-hsba", "HSBC Holdings plc", "HSBA.L", "Financials"),
            ("company-gsk", "GSK plc", "GSK.L", "Healthcare"),
            ("company-azn", "AstraZeneca PLC", "AZN.L", "Healthcare"),
            ("company-ulvr", "Unilever PLC", "ULVR.L", "Consumer Staples"),
        ],
    },
    "ie": {
        "territory_id": "ie",
        "country_code": "IE",
        "index_ticker": "^ISEQ",
        "exposure_basis": "Candidate exposure to Irish Pillar Two rules for large multinational groups; verify group revenue threshold and effective tax position from filings.",
        "start_date": date(2023, 7, 1),
        "end_date": date(2024, 4, 30),
        "companies": [
            ("company-rya", "Ryanair Holdings plc", "RYA.IR", "Industrials"),
            ("company-gl9", "Glanbia plc", "GL9.IR", "Consumer Staples"),
            ("company-birg", "Bank of Ireland Group plc", "BIRG.IR", "Financials"),
            ("company-dcc", "DCC plc", "DCC.L", "Industrials"),
        ],
    },
    "pa": {
        "territory_id": "us-pa",
        "country_code": "US",
        "index_ticker": "^GSPC",
        "exposure_basis": "Pennsylvania-headquartered candidate; actual Pennsylvania taxable income and apportionment must be verified from filings.",
        "start_date": date(2022, 6, 1),
        "end_date": date(2023, 3, 31),
        "policy": {
            "policy_id": "policy-pa-corporate-rate-2023",
            "title": "Pennsylvania corporate net income tax rate reduced from 9.99% to 8.99%",
            "policy_type": "corporate_income_tax_rate_reduction",
            "summary": "Act 53 of 2022 enacted a phased reduction in Pennsylvania's corporate net income tax rate; the first reduction to 8.99% took effect January 1, 2023.",
            "adoption_date": date(2022, 7, 8),
            "effective_date": date(2023, 1, 1),
            "source_id": "source-pa-act-53-2022",
            "source_title": "Pennsylvania Act 53 of 2022",
            "source_publisher": "Pennsylvania General Assembly",
            "source_url": "https://www.legis.state.pa.us/",
            "official_reference": "Pennsylvania Act 53 of 2022",
            "affected_sector": "Corporations subject to Pennsylvania corporate net income tax",
            "expected_mechanism": "Lower statutory state tax rate can reduce Pennsylvania tax liabilities on apportioned taxable income.",
        },
        "companies": [
            ("company-cm", "Comcast Corporation", "CMCSA", "Communication Services"),
            ("company-pnc", "The PNC Financial Services Group, Inc.", "PNC", "Financials"),
            ("company-hsy", "The Hershey Company", "HSY", "Consumer Staples"),
            ("company-ugi", "UGI Corporation", "UGI", "Utilities"),
            ("company-cck", "Crown Holdings, Inc.", "CCK", "Materials"),
        ],
    },
    "ny": {
        "territory_id": "us-ny",
        "territory_name": "New York",
        "territory_type": "state",
        "parent_territory_id": "us",
        "country_code": "US",
        "index_ticker": "^GSPC",
        "exposure_basis": "New York-headquartered candidate; actual New York apportionment and eligibility for the temporary surcharge must be verified from filings.",
        "start_date": date(2020, 10, 1),
        "end_date": date(2021, 7, 31),
        "policy": {
            "policy_id": "policy-ny-corporate-surcharge-2021",
            "title": "New York temporary corporate franchise tax surcharge increased for high-income taxpayers",
            "policy_type": "corporate_income_tax_surcharge",
            "summary": "New York's 2021 budget enacted a temporary increase in the business-income base tax rate for corporations with business income over the statutory threshold; eligibility depends on tax-year rules and apportionment.",
            "adoption_date": date(2021, 4, 19),
            "effective_date": date(2021, 1, 1),
            "source_id": "source-ny-s2509-2021",
            "source_title": "New York Senate Bill S2509C (2021-2022)",
            "source_publisher": "New York State Senate",
            "source_url": "https://www.nysenate.gov/legislation/bills/2021/S2509",
            "official_reference": "Chapter 59 of the Laws of 2021; verify the applicable tax title and thresholds in the enacted text.",
            "affected_sector": "Corporations meeting the statutory New York business-income and apportionment thresholds",
            "expected_mechanism": "Temporary surcharge increases New York corporate franchise tax for covered business income.",
        },
        "companies": [
            ("company-ibm-ny", "International Business Machines Corporation", "IBM", "Information Technology"),
            ("company-pfe-ny", "Pfizer Inc.", "PFE", "Health Care"),
            ("company-vz-ny", "Verizon Communications Inc.", "VZ", "Communication Services"),
            ("company-jpm-ny", "JPMorgan Chase & Co.", "JPM", "Financials"),
            ("company-gs-ny", "The Goldman Sachs Group, Inc.", "GS", "Financials"),
        ],
    },
    "fr": {
        "territory_id": "fr",
        "territory_name": "France",
        "territory_type": "country",
        "parent_territory_id": None,
        "country_code": "FR",
        "index_ticker": "^FCHI",
        "exposure_basis": "French-listed candidate subject to French corporate income tax rules; actual taxable income and eligibility should be verified from filings.",
        "start_date": date(2017, 8, 1),
        "end_date": date(2023, 1, 31),
        "policy": {
            "policy_id": "policy-fr-corporate-rate-25-2022",
            "title": "French standard corporate income tax rate reaches 25 percent",
            "policy_type": "corporate_income_tax_rate_reduction",
            "summary": "The phased French corporate tax-rate reduction reached the 25 percent standard rate in 2022; eligibility, special rates, and surcharges vary by taxpayer.",
            "adoption_date": date(2017, 12, 30),
            "effective_date": date(2022, 1, 1),
            "source_id": "source-fr-finance-act-2018",
            "source_title": "Loi n° 2017-1837 du 30 décembre 2017 de finances pour 2018",
            "source_publisher": "Légifrance",
            "source_url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000036339197",
            "official_reference": "Loi n° 2017-1837; phased corporate income tax rate schedule, verify conditions and later amendments.",
            "affected_sector": "Companies subject to French corporate income tax",
            "expected_mechanism": "Phased reduction in the standard corporate income tax rate reduces statutory tax on eligible taxable profits.",
        },
        "companies": [
            ("company-air-fr", "Airbus SE", "AIR.PA", "Industrials"),
            ("company-lvmh-fr", "LVMH Moet Hennessy Louis Vuitton SE", "MC.PA", "Consumer Discretionary"),
            ("company-loreal-fr", "L'Oreal S.A.", "OR.PA", "Consumer Staples"),
            ("company-sanofi-fr", "Sanofi", "SAN.PA", "Health Care"),
            ("company-bnp-fr", "BNP Paribas SA", "BNP.PA", "Financials"),
        ],
    },
}


def connect():
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


def fetch_history(ticker, start_date, end_date):
    period1 = int(datetime.combine(start_date, time.min, timezone.utc).timestamp())
    period2 = int(datetime.combine(end_date + timedelta(days=1), time.min, timezone.utc).timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{quote(ticker, safe='')}?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    request = Request(url, headers={"User-Agent": "GLPID research project/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Téléchargement des cours de {ticker} impossible : {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Réponse JSON invalide pour {ticker}.") from exc

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Source de données en erreur pour {ticker} : {chart['error']}")
    results = chart.get("result")
    if not results:
        raise RuntimeError(f"Aucune série historique renvoyée pour le symbole {ticker}.")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quotes = (result.get("indicators", {}).get("quote") or [{}])[0]
    adjusted = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or []
    closes = quotes.get("close") or []
    volumes = quotes.get("volume") or []
    rows = []
    currency = result.get("meta", {}).get("currency")

    for index, timestamp in enumerate(timestamps):
        close = closes[index] if index < len(closes) else None
        if close is None:
            continue
        adjusted_close = adjusted[index] if index < len(adjusted) else None
        price_date = datetime.fromtimestamp(timestamp, timezone.utc).date()
        rows.append((price_date, float(close), float(adjusted_close) if adjusted_close is not None else None,
                     volumes[index] if index < len(volumes) else None, currency))

    if not rows:
        raise RuntimeError(f"Aucun cours quotidien exploitable renvoyé pour {ticker}.")
    return rows


def store_history(conn, case, start_date, end_date):
    territory_id = case["territory_id"]
    country_code = case["country_code"]
    index_ticker = case["index_ticker"]
    index_id = "".join(character.lower() if character.isalnum() else "-" for character in index_ticker).strip("-")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
            VALUES (%s, 'Yahoo Finance', 'Historical daily market prices', 'other', %s,
                    'Retrieved from the Yahoo Finance chart endpoint; verify current access and reuse terms.')
            ON CONFLICT (source_id) DO UPDATE
            SET publisher = EXCLUDED.publisher,
                title = EXCLUDED.title,
                source_type = EXCLUDED.source_type,
                url = EXCLUDED.url,
                notes = EXCLUDED.notes
            """,
            (SOURCE_ID, SOURCE_URL),
        )

        if case.get("territory_type"):
            parent_territory_id = case.get("parent_territory_id")
            policy = case["policy"]
            cur.execute(
                """
                INSERT INTO territories
                    (territory_id, name, territory_type, country_code, parent_territory_id, description)
                VALUES (%s, %s, %s, %s, %s,
                        'Subnational tax jurisdiction used for the event-study example.')
                ON CONFLICT (territory_id) DO UPDATE
                SET name = EXCLUDED.name,
                    territory_type = EXCLUDED.territory_type,
                    country_code = EXCLUDED.country_code,
                    parent_territory_id = EXCLUDED.parent_territory_id,
                    description = EXCLUDED.description
                """
                ,
                (
                    territory_id,
                    case["territory_name"],
                    case["territory_type"],
                    country_code,
                    parent_territory_id,
                ),
            )
            cur.execute(
                """
                INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, 'official_law', %s,
                        'Official legislative source for the policy event; verify provisions and eligibility in the enacted text.')
                ON CONFLICT (source_id) DO UPDATE
                SET publisher = EXCLUDED.publisher,
                    title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type,
                    url = EXCLUDED.url,
                    notes = EXCLUDED.notes
                """,
                (
                    policy["source_id"],
                    policy["source_publisher"],
                    policy["source_title"],
                    policy["source_url"],
                ),
            )
            cur.execute(
                """
                INSERT INTO policy_changes
                    (policy_id, territory_id, title, policy_type, summary, announcement_date,
                     adoption_date, effective_date, status, affected_sector, expected_mechanism, source_id,
                     official_reference)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'in_force', %s, %s, %s, %s)
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
                    policy["policy_id"],
                    territory_id,
                    policy["title"],
                    policy["policy_type"],
                    policy["summary"],
                    policy.get("announcement_date"),
                    policy["adoption_date"],
                    policy["effective_date"],
                    policy["affected_sector"],
                    policy["expected_mechanism"],
                    policy["source_id"],
                    policy["official_reference"],
                ),
            )

        for company_id, name, ticker, sector in case["companies"]:
            cur.execute(
                """
                INSERT INTO companies (company_id, name, country_code, sector, ticker, headquarters_territory_id, notes)
                VALUES (%s, %s, %s, %s, %s, %s,
                        'Candidate for a jurisdictional tax-policy event study; actual tax exposure should be verified from filings.')
                ON CONFLICT (company_id) DO UPDATE
                SET name = EXCLUDED.name,
                    country_code = EXCLUDED.country_code,
                    sector = EXCLUDED.sector,
                    ticker = EXCLUDED.ticker,
                    headquarters_territory_id = EXCLUDED.headquarters_territory_id,
                    notes = EXCLUDED.notes
                """,
                (company_id, name, country_code, sector, ticker, territory_id),
            )
            cur.execute(
                """
                INSERT INTO company_exposures
                    (exposure_id, company_id, territory_id, exposure_type, exposure_basis,
                     exposure_score, start_date, notes)
                VALUES (%s, %s, %s, 'headquarters', %s,
                        NULL, NULL, 'Headquarters-based candidate only; state taxable income and apportionment not measured.')
                ON CONFLICT (exposure_id) DO UPDATE
                SET company_id = EXCLUDED.company_id,
                    territory_id = EXCLUDED.territory_id,
                    exposure_type = EXCLUDED.exposure_type,
                    exposure_basis = EXCLUDED.exposure_basis,
                    start_date = NULL,
                    exposure_score = NULL,
                    notes = EXCLUDED.notes
                """,
                (f"exposure-{company_id}-{territory_id}", company_id, territory_id, case["exposure_basis"]),
            )

            prices = fetch_history(ticker, start_date, end_date)
            cur.executemany(
                """
                INSERT INTO company_prices
                    (company_price_id, company_id, price_date, close_price, adjusted_close_price,
                     volume, currency, source_id, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, price_date) DO UPDATE
                SET close_price = EXCLUDED.close_price,
                    adjusted_close_price = EXCLUDED.adjusted_close_price,
                    volume = EXCLUDED.volume,
                    currency = EXCLUDED.currency,
                    source_id = EXCLUDED.source_id,
                    notes = EXCLUDED.notes
                """,
                [
                    (
                        f"price-{ticker.lower()}-{price_date.isoformat()}",
                        company_id,
                        price_date,
                        close,
                        adjusted_close,
                        volume,
                        currency,
                        SOURCE_ID,
                        "Historical daily price downloaded for the event-study example.",
                    )
                    for price_date, close, adjusted_close, volume, currency in prices
                ],
            )
            print(f"{ticker}: {len(prices)} séances importées.")

        index_prices = fetch_history(index_ticker, start_date, end_date)
        cur.executemany(
            """
            INSERT INTO market_index_prices
                (market_index_price_id, index_name, price_date, close_value, currency, source_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (index_name, price_date) DO UPDATE
            SET close_value = EXCLUDED.close_value,
                currency = EXCLUDED.currency,
                source_id = EXCLUDED.source_id,
                notes = EXCLUDED.notes
            """,
            [
                (
                    f"index-{territory_id}-{index_id}-{price_date.isoformat()}",
                    index_ticker,
                    price_date,
                    close,
                    currency,
                    SOURCE_ID,
                    "S&P 500 historical daily index value downloaded for the event-study example.",
                )
                for price_date, close, _adjusted_close, _volume, currency in index_prices
            ],
        )
        print(f"{index_ticker}: {len(index_prices)} séances importées.")


def main():
    parser = argparse.ArgumentParser(
        description="Télécharge et importe des cours historiques pour un exemple d'étude d'événement fiscal."
    )
    parser.add_argument("--case", choices=sorted(CASES), default="us", help="Jeu d’entreprises et indice à charger")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    args = parser.parse_args()
    case = CASES[args.case]
    start_date = args.start_date or case["start_date"]
    end_date = args.end_date or case["end_date"]
    if end_date < start_date:
        parser.error("--end-date doit être postérieure ou égale à --start-date.")

    try:
        with connect() as conn:
            store_history(conn, case, start_date, end_date)
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
