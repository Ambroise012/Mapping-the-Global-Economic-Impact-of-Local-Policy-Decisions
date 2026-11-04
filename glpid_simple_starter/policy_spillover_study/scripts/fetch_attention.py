import argparse
import calendar
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_spillover_study.study import month_range, parse_timeline


SOURCE_ID = "source-policy-spillover-gdelt"
SOURCE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def connect():
    load_dotenv(PROJECT_ROOT / ".env")
    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Paramètres PostgreSQL manquants dans .env : " + ", ".join(missing))
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        **{"password": os.environ["PGPASSWORD"]},
    )


def fetch_timeline(query, start, end):
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d000000"),
        "enddatetime": end.strftime("%Y%m%d235959"),
    }
    url = f"{SOURCE_URL}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "GLPID policy spillover research"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "inconnu")
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                preview = body[:160].decode("utf-8", "replace").replace("\n", " ")
                raise RuntimeError(
                    f"Réponse GDELT non JSON (type {content_type}) : {preview}"
                ) from exc
            return parse_timeline(payload), url
        except HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                retry_after = exc.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 15 * (attempt + 1)
                time.sleep(min(delay, 120))
                continue
            raise RuntimeError(f"Échec de la requête GDELT : HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"Échec de la requête GDELT : {exc}") from exc
    raise RuntimeError("GDELT a refusé la requête après plusieurs tentatives.")


def persist_attention(policy_family, query, counts, start, end, source_page):
    records = [
        (policy_family, month, counts.get(month, 0), query, SOURCE_ID, source_page)
        for month in month_range(start, end)
    ]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, 'GDELT Project', 'GDELT DOC API — attention médiatique des politiques',
                        'news', %s, %s)
                ON CONFLICT (source_id) DO UPDATE
                SET title = EXCLUDED.title, url = EXCLUDED.url, notes = EXCLUDED.notes
                """,
                (
                    SOURCE_ID,
                    SOURCE_URL,
                    "Comptes bruts issus de requêtes textuelles ; couverture et pertinence imparfaites.",
                ),
            )
            cur.executemany(
                """
                INSERT INTO policy_diffusion_attention
                    (policy_family, month_start, article_count, query_text, source_id, source_page)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_family, month_start) DO UPDATE
                SET article_count = EXCLUDED.article_count,
                    query_text = EXCLUDED.query_text,
                    source_id = EXCLUDED.source_id,
                    source_page = EXCLUDED.source_page,
                    collected_at = now()
                """,
                records,
            )
    return len(records)


def year_chunks(start, end):
    for year in range(start.year, end.year + 1):
        chunk_start = max(start, date(year, 1, 1))
        chunk_end = min(end, date(year, 12, 31))
        yield chunk_start, chunk_end


def chunk_months(start, end):
    return set(month_range(start, end))


def chunk_is_complete(existing, query, start, end):
    return all(existing.get(month) == query for month in chunk_months(start, end))


def load_existing_months(families, start, end):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT policy_family, month_start, query_text
            FROM policy_diffusion_attention
            WHERE policy_family = ANY(%s)
              AND month_start BETWEEN %s AND %s
            """,
            (families, start, end),
        ).fetchall()
    return {
        family: {
            month_start: query_text
            for row_family, month_start, query_text in rows
            if row_family == family
        }
        for family in families
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collecte les volumes mensuels GDELT des cas de diffusion enregistrés."
    )
    parser.add_argument("--family", help="Famille de politiques ; par défaut, toutes les familles.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2019, 1, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 10, 31))
    args = parser.parse_args()
    if args.end_date < args.start_date:
        parser.error("--end-date doit être postérieure ou égale à --start-date.")
    if args.start_date.day != 1 or args.end_date.day != calendar.monthrange(
        args.end_date.year, args.end_date.month
    )[1]:
        parser.error("Les dates doivent couvrir des mois entiers.")

    try:
        with connect() as conn:
            cases = conn.execute(
                """
                SELECT policy_family, gdelt_query
                FROM policy_diffusion_cases
                GROUP BY policy_family, gdelt_query
                ORDER BY policy_family
                """
            ).fetchall()
        if args.family:
            cases = [row for row in cases if row[0] == args.family]
            if not cases:
                raise ValueError(f"Famille inconnue : {args.family}")
        if not cases:
            raise ValueError("Aucun cas. Exécutez d’abord seed_study.py.")
        existing_months = load_existing_months(
            [family for family, _ in cases], args.start_date, args.end_date
        )
        requests = [
            (policy_family, query, chunk_start, chunk_end)
            for policy_family, query in cases
            for chunk_start, chunk_end in year_chunks(args.start_date, args.end_date)
        ]
        skipped = 0
        completed = 0
        for index, (policy_family, query, chunk_start, chunk_end) in enumerate(requests):
            if chunk_is_complete(
                existing_months[policy_family], query, chunk_start, chunk_end
            ):
                print(
                    f"{policy_family} {chunk_start.year} : déjà complet, "
                    "aucune requête GDELT."
                )
                skipped += 1
                continue
            try:
                counts, source_page = fetch_timeline(query, chunk_start, chunk_end)
            except RuntimeError as exc:
                raise RuntimeError(
                    f"{policy_family} {chunk_start.year} "
                    f"({chunk_start.isoformat()}–{chunk_end.isoformat()}) : {exc}. "
                    "Les tranches précédemment importées sont conservées ; "
                    "relancez la même commande pour reprendre."
                ) from exc
            expected_months = chunk_months(chunk_start, chunk_end)
            saved = persist_attention(
                policy_family, query, counts, chunk_start, chunk_end, source_page
            )
            existing_months[policy_family].update(
                {month: query for month in expected_months}
            )
            completed += 1
            print(
                f"{policy_family} {chunk_start.year} : "
                f"{saved} observations mensuelles importées/mises à jour."
            )
            if index < len(requests) - 1:
                time.sleep(2)
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if completed == 0 and skipped:
        print("Toutes les tranches demandées étaient déjà complètes.")
    elif skipped:
        print(f"{skipped} tranche(s) annuelle(s) déjà complète(s) ignorée(s).")
    print("GDELT mesure l’attention médiatique approximative, pas le soutien public ni la causalité.")


if __name__ == "__main__":
    main()
