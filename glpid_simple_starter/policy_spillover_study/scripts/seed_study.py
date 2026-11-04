import json
import os
from pathlib import Path
import sys

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "seed_cases.json"


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


def load_seed(path=DATA_FILE):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def seed_database(seed):
    with connect() as conn:
        with conn.cursor() as cur:
            for territory in seed["territories"]:
                cur.execute(
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
                    (
                        territory["territory_id"],
                        territory["name"],
                        territory["territory_type"],
                        territory.get("country_code"),
                        territory.get("parent_territory_id"),
                        territory["description"],
                    ),
                )
            for source in seed["sources"]:
                cur.execute(
                    """
                    INSERT INTO sources
                        (source_id, publisher, title, source_type, url, published_date, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id) DO UPDATE
                    SET publisher = EXCLUDED.publisher,
                        title = EXCLUDED.title,
                        source_type = EXCLUDED.source_type,
                        url = EXCLUDED.url,
                        published_date = EXCLUDED.published_date,
                        notes = EXCLUDED.notes
                    """,
                    (
                        source["source_id"],
                        source["publisher"],
                        source["title"],
                        source["source_type"],
                        source["url"],
                        source.get("published_date"),
                        source["notes"],
                    ),
                )
            for case in seed["cases"]:
                cur.execute(
                    """
                    INSERT INTO policy_diffusion_cases
                        (case_id, policy_family, title, origin_territory_id,
                         anchor_policy_title, anchor_date, anchor_event_type,
                         target_level, gdelt_query, scope_note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_id) DO UPDATE
                    SET policy_family = EXCLUDED.policy_family,
                        title = EXCLUDED.title,
                        origin_territory_id = EXCLUDED.origin_territory_id,
                        anchor_policy_title = EXCLUDED.anchor_policy_title,
                        anchor_date = EXCLUDED.anchor_date,
                        anchor_event_type = EXCLUDED.anchor_event_type,
                        target_level = EXCLUDED.target_level,
                        gdelt_query = EXCLUDED.gdelt_query,
                        scope_note = EXCLUDED.scope_note
                    """,
                    (
                        case["case_id"],
                        case["policy_family"],
                        case["title"],
                        case["origin_territory_id"],
                        case["anchor_policy_title"],
                        case["anchor_date"],
                        case["anchor_event_type"],
                        case["target_level"],
                        case["gdelt_query"],
                        case["scope_note"],
                    ),
                )
            for event in seed["events"]:
                cur.execute(
                    """
                    INSERT INTO policy_diffusion_events
                        (event_id, case_id, territory_id, event_level, event_type,
                         relationship, event_date, policy_title, source_id,
                         source_page, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO UPDATE
                    SET case_id = EXCLUDED.case_id,
                        territory_id = EXCLUDED.territory_id,
                        event_level = EXCLUDED.event_level,
                        event_type = EXCLUDED.event_type,
                        relationship = EXCLUDED.relationship,
                        event_date = EXCLUDED.event_date,
                        policy_title = EXCLUDED.policy_title,
                        source_id = EXCLUDED.source_id,
                        source_page = EXCLUDED.source_page,
                        notes = EXCLUDED.notes
                    """,
                    (
                        event["event_id"],
                        event["case_id"],
                        event["territory_id"],
                        event["event_level"],
                        event["event_type"],
                        event["relationship"],
                        event["event_date"],
                        event["policy_title"],
                        event["source_id"],
                        event["source_page"],
                        event["notes"],
                    ),
                )
    return len(seed["cases"]), len(seed["events"])


def main():
    try:
        cases, events = seed_database(load_seed())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"{cases} cas et {events} événements législatifs insérés/mis à jour.")


if __name__ == "__main__":
    main()
