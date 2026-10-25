import argparse
import os
import sys
from datetime import timedelta

import psycopg
import statsmodels.formula.api as smf
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


def load_event_panel(conn, policy_id, event_column, index_name, pre_sessions, window_sessions):
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT policy_id, territory_id, title, {event_column}
            FROM policy_changes
            WHERE policy_id = %s
            """,
            (policy_id,),
        )
        policy = cur.fetchone()
        if policy is None:
            raise ValueError(f"Aucune réforme trouvée pour policy_id={policy_id!r}.")
        policy_id, territory_id, title, event_date = policy
        if event_date is None:
            raise ValueError(f"La date {event_column!r} est vide pour {policy_id!r}.")

        cur.execute(
            """
            SELECT DISTINCT c.company_id, c.name, c.sector, e.exposure_score,
                            e.source_id, e.source_page
            FROM company_exposures e
            JOIN companies c ON c.company_id = e.company_id
            WHERE e.territory_id = %s
              AND (e.start_date IS NULL OR e.start_date <= %s)
              AND (e.end_date IS NULL OR e.end_date >= %s)
            ORDER BY c.company_id
            """,
            (territory_id, event_date, event_date),
        )
        companies = cur.fetchall()

        cur.execute(
            """
            SELECT price_date
            FROM market_index_prices
            WHERE index_name = %s
            ORDER BY price_date
            """,
            (index_name,),
        )
        calendar = [row[0] for row in cur.fetchall()]

    if not calendar:
        raise ValueError(f"Aucune cotation de calendrier pour l’indice {index_name!r}.")
    anchor_index = next((i for i, trading_date in enumerate(calendar) if trading_date >= event_date), None)
    if anchor_index is None:
        raise ValueError(f"L’indice {index_name!r} n’a pas de séances à partir du {event_date}.")
    if anchor_index < pre_sessions + 1 or anchor_index + window_sessions >= len(calendar):
        raise ValueError(
            f"Données insuffisantes autour du {event_date} : il faut au moins "
            f"{pre_sessions + 1} séances avant et {window_sessions} après."
        )

    anchor_date = calendar[anchor_index]
    first_date = calendar[anchor_index - pre_sessions - 1]
    last_date = calendar[anchor_index + window_sessions]
    query_from = first_date - timedelta(days=10)

    with conn.cursor() as cur:
        cur.execute(
            """
            WITH company_prices AS (
                SELECT DISTINCT ON (c.company_id, cp.price_date)
                       c.company_id, c.name, c.sector, e.exposure_score,
                       cp.price_date, COALESCE(cp.adjusted_close_price, cp.close_price) AS close_price
                FROM company_exposures e
                JOIN companies c ON c.company_id = e.company_id
                JOIN company_prices cp ON cp.company_id = c.company_id
                WHERE e.territory_id = %s
                  AND e.exposure_score IS NOT NULL
                  AND (e.start_date IS NULL OR e.start_date <= %s)
                  AND (e.end_date IS NULL OR e.end_date >= %s)
                  AND cp.price_date BETWEEN %s AND %s
                ORDER BY c.company_id, cp.price_date, e.created_at DESC
            ),
            stock_returns AS (
                SELECT company_id, name, sector, exposure_score, price_date,
                       close_price / NULLIF(LAG(close_price) OVER (
                           PARTITION BY company_id ORDER BY price_date
                       ), 0) - 1 AS stock_return
                FROM company_prices
            ),
            index_prices AS (
                SELECT price_date, close_value,
                       LAG(close_value) OVER (ORDER BY price_date) AS previous_close
                FROM market_index_prices
                WHERE index_name = %s
                  AND price_date BETWEEN %s AND %s
            ),
            index_returns AS (
                SELECT price_date, close_value / NULLIF(previous_close, 0) - 1 AS index_return
                FROM index_prices
            )
            SELECT s.company_id, s.name, s.sector, s.exposure_score, s.price_date,
                   s.stock_return, i.index_return
            FROM stock_returns s
            JOIN index_returns i ON i.price_date = s.price_date
            WHERE s.price_date BETWEEN %s AND %s
              AND s.stock_return IS NOT NULL
              AND i.index_return IS NOT NULL
            ORDER BY s.company_id, s.price_date
            """,
            (
                territory_id,
                event_date,
                event_date,
                query_from,
                last_date,
                index_name,
                query_from,
                last_date,
                first_date,
                last_date,
            ),
        )
        rows = cur.fetchall()

    return {
        "policy_id": policy_id,
        "territory_id": territory_id,
        "title": title,
        "event_date": event_date,
        "anchor_date": anchor_date,
        "anchor_index": anchor_index,
        "calendar": calendar,
        "companies": companies,
        "rows": rows,
        "first_date": first_date,
        "last_date": last_date,
    }


def build_panel(data, control_max, treatment_min):
    if not data["companies"]:
        raise ValueError("Aucune société n’est enregistrée comme exposée à ce territoire.")

    scores = {}
    for company_id, name, sector, score, source_id, source_page in data["companies"]:
        if score is None or source_id is None or not source_page:
            continue
        previous = scores.get(company_id)
        if previous and previous["score"] != float(score):
            raise ValueError(
                f"Plusieurs scores d’exposition différents existent pour {company_id}. "
                "Conserve un score pré-événement documenté par entreprise et territoire."
            )
        scores[company_id] = {
            "name": name,
            "sector": sector or "unknown",
            "score": float(score),
        }

    treated = {company_id for company_id, row in scores.items() if row["score"] >= treatment_min}
    control = {company_id for company_id, row in scores.items() if row["score"] <= control_max}
    middle = set(scores) - treated - control

    if len(treated) < 3 or len(control) < 3:
        missing_scores = len(data["companies"]) - len(scores)
        raise ValueError(
            "Comparaison causale non estimable : il faut au moins 3 sociétés traitées "
            f"(exposition >= {treatment_min}) et 3 témoins "
            f"(exposition <= {control_max}). Données actuelles : {len(treated)} traitées, "
            f"{len(control)} témoins, {missing_scores} scores d’exposition manquants. "
            "Renseigne company_exposures.exposure_score, source_id et source_page avec une mesure "
            "documentée antérieure à la réforme ; complète aussi companies.sector. "
            "Ne marque pas arbitrairement les sociétés comme témoins."
        )

    treated_sectors = {scores[c]["sector"] for c in treated if scores[c]["sector"] != "unknown"}
    control_sectors = {scores[c]["sector"] for c in control if scores[c]["sector"] != "unknown"}
    common_sectors = treated_sectors & control_sectors
    if not common_sectors:
        raise ValueError(
            "Aucun secteur renseigné n’est représenté à la fois parmi les sociétés traitées "
            "et témoins. Complète companies.sector et ajoute des témoins comparables."
        )

    treated = {c for c in treated if scores[c]["sector"] in common_sectors}
    control = {c for c in control if scores[c]["sector"] in common_sectors}
    if len(treated) < 3 or len(control) < 3:
        raise ValueError(
            "Après appariement sur les secteurs communs, il reste moins de trois entreprises "
            "dans un des groupes. Ajoute des témoins du même secteur."
        )

    selected = treated | control
    prices = {}
    calendar = data["calendar"]
    date_to_session = {trading_date: index for index, trading_date in enumerate(calendar)}
    anchor_session = date_to_session[data["anchor_date"]]
    for company_id, name, sector, score, price_date, stock_return, index_return in data["rows"]:
        if company_id not in selected or price_date not in date_to_session:
            continue
        relative_session = date_to_session[price_date] - anchor_session
        prices.setdefault(company_id, []).append(
            {
                "company_id": company_id,
                "name": name,
                "sector": sector or "unknown",
                "score": float(score),
                "date": price_date,
                "session": relative_session,
                "abnormal_return": float(stock_return) - float(index_return),
                "treated": int(company_id in treated),
            }
        )

    panel = [row for company_rows in prices.values() for row in company_rows]
    if not panel:
        raise ValueError("Aucune cotation quotidienne commune aux sociétés et à l’indice dans la période.")
    return panel, treated, control, middle, common_sectors


def fit_did(panel, window_sessions):
    import pandas as pd

    selected = [
        row for row in panel
        if -window_sessions <= row["session"] <= window_sessions
    ]
    if len({row["company_id"] for row in selected if row["treated"]}) < 3:
        raise ValueError("Moins de 3 sociétés traitées ont des cotations dans la fenêtre.")
    if len({row["company_id"] for row in selected if not row["treated"]}) < 3:
        raise ValueError("Moins de 3 sociétés témoins ont des cotations dans la fenêtre.")

    frame = pd.DataFrame(selected)
    frame["post"] = (frame["session"] >= 0).astype(int)
    model = smf.ols(
        "abnormal_return ~ treated:post + C(company_id) + C(date)",
        data=frame,
    ).fit(
        cov_type="cluster",
        cov_kwds={"groups": frame["company_id"], "use_correction": True},
    )
    if "treated:post" not in model.params:
        raise ValueError("Impossible d’identifier le terme traité × après dans cette fenêtre.")
    return model, frame


def run_analysis(data, window_sessions, pre_sessions, pre_exclude_sessions, placebo_offset, control_max, treatment_min):
    panel, treated, control, middle, common_sectors = build_panel(data, control_max, treatment_min)
    model, event_frame = fit_did(panel, window_sessions)
    estimate = float(model.params["treated:post"])
    conf_low, conf_high = model.conf_int().loc["treated:post"].tolist()
    p_value = float(model.pvalues["treated:post"])
    post_sessions = len({row["session"] for row in event_frame if row["session"] >= 0})

    pre_rows = [
        row for row in panel
        if -pre_sessions <= row["session"] <= -pre_exclude_sessions
    ]
    pretrend = None
    if len({row["date"] for row in pre_rows}) >= 5 and len({row["company_id"] for row in pre_rows}) >= 6:
        import pandas as pd

        pre_frame = pd.DataFrame(pre_rows)
        pretrend_model = smf.ols(
            "abnormal_return ~ treated:session + C(company_id) + C(date)",
            data=pre_frame,
        ).fit(
            cov_type="cluster",
            cov_kwds={"groups": pre_frame["company_id"], "use_correction": True},
        )
        if "treated:session" in pretrend_model.params:
            pretrend = (
                float(pretrend_model.params["treated:session"]),
                float(pretrend_model.pvalues["treated:session"]),
            )

    placebo = None
    placebo_anchor = -placebo_offset
    placebo_rows = [
        row for row in panel
        if placebo_anchor - window_sessions <= row["session"] <= placebo_anchor + window_sessions
    ]
    if (
        len({row["company_id"] for row in placebo_rows if row["treated"]}) >= 3
        and len({row["company_id"] for row in placebo_rows if not row["treated"]}) >= 3
    ):
        import pandas as pd

        placebo_frame = pd.DataFrame(placebo_rows)
        placebo_frame["post"] = (placebo_frame["session"] >= placebo_anchor).astype(int)
        placebo_model = smf.ols(
            "abnormal_return ~ treated:post + C(company_id) + C(date)",
            data=placebo_frame,
        ).fit(
            cov_type="cluster",
            cov_kwds={"groups": placebo_frame["company_id"], "use_correction": True},
        )
        if "treated:post" in placebo_model.params:
            placebo = (
                float(placebo_model.params["treated:post"]),
                float(placebo_model.pvalues["treated:post"]),
            )

    print(f"Politique : {data['policy_id']} — {data['title']}")
    print(f"Territoire : {data['territory_id']}")
    print(f"Date d’événement enregistrée : {data['event_date']} ; séance de référence : {data['anchor_date']}")
    print(
        f"Fenêtre : -{window_sessions}/+{window_sessions} séances ; "
        f"panel {data['first_date']} à {data['last_date']}"
    )
    print(f"Traitement : score >= {treatment_min}; témoins : score <= {control_max}")
    print(
        f"Entreprises analysées : {len(treated)} traitées, {len(control)} témoins; "
        f"{len(middle)} score(s) intermédiaire(s) exclus"
    )
    print(f"Secteurs communs : {', '.join(sorted(common_sectors))}")
    print("\nDifférences-en-différences sur rendements anormaux (action - indice) :")
    print(f"Effet quotidien estimé : {estimate * 100:.4f} points de pourcentage")
    print(
        f"IC 95 % : [{conf_low * 100:.4f} ; {conf_high * 100:.4f}] points ; "
        f"p-valeur clusterisée par entreprise : {p_value:.4f}"
    )
    print(f"Séances post-événement dans la fenêtre : {post_sessions}")
    print(
        "Effet cumulatif indicatif : "
        f"{estimate * post_sessions * 100:.4f} points de pourcentage"
    )
    if pretrend is None:
        print("Pré-tendance : non estimable (historique ou nombre de sociétés insuffisant).")
    else:
        print(
            "Pré-tendance différentielle par séance : "
            f"{pretrend[0] * 100:.4f} points ; p-valeur {pretrend[1]:.4f}"
        )
    if placebo is None:
        print("Placebo : non estimable (données pré-événement insuffisantes).")
    else:
        print(
            f"Placebo {placebo_offset} séances avant : effet quotidien "
            f"{placebo[0] * 100:.4f} points ; p-valeur {placebo[1]:.4f}"
        )
    print(
        "\nPrudence : erreurs-types clusterisées avec peu d’entreprises = inférence fragile. "
        "Une pré-tendance non significative ne prouve pas la comparabilité. "
        "La causalité exige des expositions documentées avant l’événement, des témoins crédibles, "
        "l’absence de chocs concomitants et idéalement des tests placebo multiples."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Différences-en-différences sur rendements boursiers, avec diagnostics pré-tendance et placebo."
    )
    parser.add_argument("--policy-id", required=True)
    parser.add_argument(
        "--event-column",
        default="adoption_date",
        choices=["announcement_date", "adoption_date", "effective_date"],
    )
    parser.add_argument("--index-name", required=True)
    parser.add_argument("--window-sessions", type=int, default=5, help="Séances avant/après l’événement")
    parser.add_argument("--pre-sessions", type=int, default=60, help="Longueur de la période pré-événement")
    parser.add_argument("--pre-exclude-sessions", type=int, default=5, help="Séances avant l’événement exclues du test de pré-tendance")
    parser.add_argument("--placebo-offset", type=int, default=20, help="Décalage du test placebo en séances avant l’événement")
    parser.add_argument("--control-max", type=float, default=0.1, help="Score maximum pour le groupe témoin")
    parser.add_argument("--treatment-min", type=float, default=0.5, help="Score minimum pour le groupe traité")
    args = parser.parse_args()

    if args.window_sessions < 1 or args.pre_sessions <= args.pre_exclude_sessions:
        parser.error("Vérifie les longueurs de fenêtre et de période pré-événement.")
    if args.pre_exclude_sessions < args.window_sessions:
        parser.error("--pre-exclude-sessions doit être >= --window-sessions.")
    if args.placebo_offset <= args.window_sessions:
        parser.error("--placebo-offset doit dépasser --window-sessions.")
    if not 0 <= args.control_max < args.treatment_min <= 1:
        parser.error("Les scores doivent satisfaire 0 <= control-max < treatment-min <= 1.")

    try:
        with connect() as conn:
            data = load_event_panel(
                conn,
                args.policy_id,
                args.event_column,
                args.index_name,
                args.pre_sessions,
                args.window_sessions,
            )
            run_analysis(
                data,
                args.window_sessions,
                args.pre_sessions,
                args.pre_exclude_sessions,
                args.placebo_offset,
                args.control_max,
                args.treatment_min,
            )
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
