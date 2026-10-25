import argparse
import calendar
import json
import os
import sys
import time
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv


SOURCE_ID = "source-gdelt-doc-api"
SOURCE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
TERRITORY_ID = "us-wa-seattle"
QUERY = 'Seattle AND (JumpStart OR "payroll expense tax")'
INDICATOR_CODE = "gdelt_jumpstart_seattle_article_count"


def month_range(start, end):
    current_year, current_month = start.year, start.month
    while (current_year, current_month) <= (end.year, end.month):
        month_end = calendar.monthrange(current_year, current_month)[1]
        yield date(current_year, current_month, 1), date(current_year, current_month, month_end)
        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1


def parse_raw_timeline(payload):
    timeline = payload.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        raise ValueError("GDELT n’a retourné aucune série chronologique pour cette requête.")
    series = next(
        (item for item in timeline if item.get("series", "").lower() == "article count"),
        timeline[0] if len(timeline) == 1 else None,
    )
    if series is None or not isinstance(series.get("data"), list) or not series["data"]:
        raise ValueError(
            "La réponse GDELT ne contient pas une série unique de volumes bruts d’articles."
        )

    monthly_counts = {}
    for point in series["data"]:
        point_date = datetime.strptime(point["date"][:8], "%Y%m%d").date()
        month_start = date(point_date.year, point_date.month, 1)
        monthly_counts[month_start] = monthly_counts.get(month_start, 0) + int(float(point["value"]))
    if not monthly_counts:
        raise ValueError("La série de volumes bruts GDELT ne contient aucune observation.")
    return monthly_counts


def fetch_timeline(start, end):
    params = {
        "query": QUERY,
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d000000"),
        "enddatetime": end.strftime("%Y%m%d235959"),
    }
    url = f"{SOURCE_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "GLPID research context collection"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                retry_after = exc.headers.get("Retry-After")
                delay = (
                    min(int(retry_after), 120)
                    if retry_after and retry_after.isdigit()
                    else 15 * (attempt + 1)
                )
                time.sleep(delay)
                continue
            raise RuntimeError(f"Échec de la requête GDELT ({url}) : {exc}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Échec de la requête GDELT ({url}) : {exc}") from exc
    else:
        raise RuntimeError("GDELT a refusé la requête après plusieurs tentatives.")

    return parse_raw_timeline(payload), url


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


def persist_timeline(monthly_counts, start, end, source_page):
    records = []
    for period_start, period_end in month_range(start, end):
        count = monthly_counts.get(period_start, 0)
        records.append(
            (
                f"{TERRITORY_ID}-{INDICATOR_CODE}-{period_start:%Y-%m}",
                TERRITORY_ID,
                INDICATOR_CODE,
                period_start,
                period_end,
                count,
                "articles/month",
                "local",
                SOURCE_ID,
                source_page,
                (
                    f"Raw GDELT DOC API article count for query {QUERY!r}; "
                    "media-attention context only, not an economic outcome or exposure measure."
                ),
            )
        )

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM territories WHERE territory_id = %s", (TERRITORY_ID,))
            if cur.fetchone() is None:
                raise ValueError(
                    f"Territoire {TERRITORY_ID!r} absent. Charge d’abord le panel QCEW Seattle."
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
                    SOURCE_ID,
                    "GDELT Project",
                    "GDELT DOC API — raw article volume timeline",
                    "news",
                    SOURCE_URL,
                    "Search-derived media attention counts; coverage and query matching are imperfect.",
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


def main():
    parser = argparse.ArgumentParser(
        description="Importe dans PostgreSQL le volume mensuel de mentions médiatiques GDELT sur JumpStart."
    )
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2019, 1, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2022, 12, 31))
    args = parser.parse_args()
    if args.end_date < args.start_date:
        parser.error("--end-date doit être postérieure ou égale à --start-date.")
    if args.start_date.day != 1 or args.end_date.day != calendar.monthrange(
        args.end_date.year, args.end_date.month
    )[1]:
        parser.error("Les dates doivent couvrir des mois entiers.")

    try:
        monthly_counts, source_page = fetch_timeline(args.start_date, args.end_date)
        count = persist_timeline(monthly_counts, args.start_date, args.end_date, source_page)
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"{count} compte(s) mensuel(s) GDELT importé(s)/mis à jour dans PostgreSQL.")
    print(
        "Ces mentions mesurent l’attention médiatique approximative, pas l’impact économique "
        "ni une preuve causale."
    )


if __name__ == "__main__":
    main()
