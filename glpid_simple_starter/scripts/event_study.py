import argparse
import os
import sys
from datetime import timedelta

import psycopg
from dotenv import load_dotenv


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


def fetch_policy(conn, policy_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT policy_id, territory_id, title, announcement_date, adoption_date, effective_date
            FROM policy_changes
            WHERE policy_id = %s
            """,
            (policy_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"Aucune réforme trouvée pour policy_id={policy_id!r}.")
    return {
        "policy_id": row[0],
        "territory_id": row[1],
        "title": row[2],
        "announcement_date": row[3],
        "adoption_date": row[4],
        "effective_date": row[5],
    }


def estimate_event_study(conn, policy_id, event_column="effective_date", window_days=5, index_name="^GSPC"):
    if window_days < 1:
        raise ValueError("window_days doit être supérieur ou égal à 1.")

    policy = fetch_policy(conn, policy_id)
    event_date = policy[event_column]
    if event_date is None:
        raise ValueError(f"La colonne {event_column!r} est vide pour la politique {policy_id!r}.")

    start_date = event_date - timedelta(days=window_days)
    end_date = event_date + timedelta(days=window_days)
    lookback_date = start_date - timedelta(days=10)

    sql = """
        WITH exposed AS (
            SELECT DISTINCT company_id
            FROM company_exposures
            WHERE territory_id = %s
              AND (start_date IS NULL OR start_date <= %s)
              AND (end_date IS NULL OR end_date >= %s)
        ),
        price_data AS (
            SELECT cp.company_id,
                   c.name,
                   cp.price_date,
                   COALESCE(cp.adjusted_close_price, cp.close_price) AS close_price,
                   LAG(COALESCE(cp.adjusted_close_price, cp.close_price)) OVER (
                       PARTITION BY cp.company_id
                       ORDER BY cp.price_date
                   ) AS prev_close
            FROM company_prices cp
            JOIN companies c ON c.company_id = cp.company_id
            WHERE cp.company_id IN (SELECT company_id FROM exposed)
              AND cp.price_date BETWEEN %s AND %s
        ),
        returns AS (
            SELECT company_id,
                   name,
                   price_date,
                   (close_price - prev_close) / NULLIF(prev_close, 0) AS company_return
            FROM price_data
            WHERE prev_close IS NOT NULL
              AND price_date BETWEEN %s AND %s
        ),
        index_data AS (
            SELECT price_date,
                   close_value,
                   LAG(close_value) OVER (ORDER BY price_date) AS prev_close_value
            FROM market_index_prices
            WHERE index_name = %s
              AND price_date BETWEEN %s AND %s
        ),
        index_returns AS (
            SELECT price_date,
                   (close_value - prev_close_value) / NULLIF(prev_close_value, 0) AS index_return
            FROM index_data
            WHERE prev_close_value IS NOT NULL
              AND price_date BETWEEN %s AND %s
        ),
        abnormal AS (
            SELECT r.company_id,
                   r.name,
                   r.price_date,
                   r.company_return - i.index_return AS abnormal_return
            FROM returns r
            JOIN index_returns i ON i.price_date = r.price_date
        )
        SELECT company_id,
               name,
               SUM(abnormal_return) AS car,
               AVG(abnormal_return) AS avg_abnormal_return,
               COUNT(*) AS observations
        FROM abnormal
        WHERE price_date BETWEEN %s AND %s
        GROUP BY company_id, name
        ORDER BY car DESC
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                policy["territory_id"],
                event_date,
                event_date,
                lookback_date,
                end_date,
                start_date,
                end_date,
                index_name,
                lookback_date,
                end_date,
                start_date,
                end_date,
                start_date,
                end_date,
            ),
        )
        rows = cur.fetchall()

    if not rows:
        print(
            f"Aucun résultat pour la fenêtre [{start_date} ; {end_date}]. "
            f"Vérifie les entreprises exposées au territoire {policy['territory_id']}, "
            f"leurs cours et les cours de l’indice {index_name!r}."
        )
        return []

    print(f"Politique: {policy['policy_id']} — {policy['title']}")
    print(f"Territoire: {policy['territory_id']} — date d’événement ({event_column}): {event_date}")
    print(f"Fenêtre: {start_date} à {end_date}")
    print(f"Indice de référence: {index_name}")
    print("\nRésultat de l’analyse d’événement (CAR ajusté sur l’indice):")
    print("company_id | company | CAR | avg_abnormal_return | observations")
    for company_id, name, car, avg_abnormal, observations in rows:
        print(f"{company_id} | {name} | {car:.6f} | {avg_abnormal:.6f} | {observations}")
    return rows


def main():
    parser = argparse.ArgumentParser(description="Calcule un event study simple sur une politique et ses entreprises exposées.")
    parser.add_argument("--policy-id", required=True, help="Identifiant de la réforme à analyser, ex. policy-uk-corporation-tax-2023")
    parser.add_argument("--event-column", default="effective_date", choices=["announcement_date", "adoption_date", "effective_date"], help="Date de l’événement à tester")
    parser.add_argument("--window-days", type=int, default=5, help="Nombre de jours avant/après la date d’événement à inclure")
    parser.add_argument("--index-name", default="^GSPC", help="Nom de l’indice dans market_index_prices (par défaut : ^GSPC)")
    args = parser.parse_args()

    try:
        conn = connect()
        with conn:
            estimate_event_study(
                conn,
                args.policy_id,
                event_column=args.event_column,
                window_days=args.window_days,
                index_name=args.index_name,
            )
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
