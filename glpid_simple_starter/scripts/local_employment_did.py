import argparse
import math
import os
import re
import sys
from datetime import date

import psycopg
import statsmodels.formula.api as smf
from dotenv import load_dotenv


DEFAULT_CONTROLS = [
    "us-wa-clark-county",
    "us-wa-spokane-county",
    "us-wa-thurston-county",
    "us-wa-whatcom-county",
    "us-wa-yakima-county",
]
INDICATORS = {
    "employment": ("qcew_private_employment", "emploi privé moyen", "persons"),
    "weekly-wage": ("qcew_private_avg_weekly_wage", "salaire hebdomadaire moyen", "USD/semaine"),
}
INDUSTRY_INDICATORS = {
    "goods-producing": "biens producteurs",
    "service-providing": "services",
    "information": "information",
    "finance-insurance": "finance et assurance",
    "professional-scientific-technical": "services professionnels, scientifiques et techniques",
    "management-of-companies": "gestion de sociétés",
    "administrative-support-waste": "services administratifs et déchets",
    "health-care-social-assistance": "santé et assistance sociale",
    "arts-entertainment-recreation": "arts, spectacles et loisirs",
    "accommodation-food-services": "hébergement et restauration",
}
for industry_code, industry_name in INDUSTRY_INDICATORS.items():
    INDICATORS[f"employment-{industry_code}"] = (
        f"qcew_private_employment_{industry_code}",
        f"emploi privé — {industry_name}",
        "persons",
    )
    INDICATORS[f"weekly-wage-{industry_code}"] = (
        f"qcew_private_avg_weekly_wage_{industry_code}",
        f"salaire hebdomadaire moyen — {industry_name}",
        "USD/semaine",
    )
QUARTER_PATTERN = re.compile(r"^(20\d{2})-Q([1-4])$")


def parse_quarter(value):
    match = QUARTER_PATTERN.fullmatch(value)
    if not match:
        raise argparse.ArgumentTypeError("Format attendu : AAAA-Qn, par exemple 2021-Q1.")
    year, quarter = map(int, match.groups())
    month = (quarter - 1) * 3 + 1
    return date(year, month, 1)


def quarter_label(period_start):
    return f"{period_start.year}-Q{(period_start.month - 1) // 3 + 1}"


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


def load_rows(conn, territory_ids, indicator_code, start_date, end_date):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT territory_id, period_start, value
            FROM territory_indicators
            WHERE territory_id = ANY(%s)
              AND indicator_code = %s
              AND period_start BETWEEN %s AND %s
            ORDER BY period_start, territory_id
            """,
            (territory_ids, indicator_code, start_date, end_date),
        )
        rows = cur.fetchall()
    missing_values = [
        f"{territory_id} {period_start}"
        for territory_id, period_start, value in rows
        if value is None
    ]
    if missing_values:
        raise ValueError(
            "Valeur d’indicateur manquante pour "
            + ", ".join(missing_values[:10])
            + "."
        )
    return [
        {"territory_id": territory_id, "period_start": period_start, "value": float(value)}
        for territory_id, period_start, value in rows
    ]


def fit_local_did(rows, treated_id, control_ids, post_start, adoption_start=None):
    import pandas as pd

    adoption_start = adoption_start or post_start
    if post_start < adoption_start:
        raise ValueError("La période postérieure ne peut pas commencer avant l’adoption.")
    required_ids = {treated_id, *control_ids}
    selected = [
        row for row in rows
        if row["territory_id"] in required_ids
        and (row["period_start"] < adoption_start or row["period_start"] >= post_start)
    ]
    if not selected:
        raise ValueError("Aucune observation trouvée. Télécharge d’abord les données QCEW.")
    invalid_values = [
        f"{row['territory_id']} {row['period_start']}"
        for row in selected
        if row["value"] <= 0
    ]
    if invalid_values:
        raise ValueError(
            "Valeurs d’indicateur non positives pour "
            + ", ".join(invalid_values[:10])
            + "."
        )

    periods = sorted({row["period_start"] for row in selected})
    if len(periods) < 12:
        raise ValueError("Il faut au moins 12 trimestres observés pour une analyse exploratoire.")
    pre_periods = [period for period in periods if period < adoption_start]
    post_periods = [period for period in periods if period >= post_start]
    if len(pre_periods) < 8 or len(post_periods) < 8:
        raise ValueError("Il faut au moins 8 trimestres avant et 8 après la date choisie.")

    observed_ids = {row["territory_id"] for row in selected}
    missing_ids = required_ids - observed_ids
    if missing_ids:
        raise ValueError(f"Territoires sans données : {', '.join(sorted(missing_ids))}.")

    expected = {(territory_id, period) for territory_id in required_ids for period in periods}
    actual = {(row["territory_id"], row["period_start"]) for row in selected}
    if actual != expected or len(actual) != len(selected):
        missing_count = len(expected - actual)
        raise ValueError(
            f"Panel incomplet : {missing_count} cellule(s) territoire-trimestre manquante(s). "
            "Vérifie aussi l’absence de doublons, puis recharge les données avant l’estimation."
        )

    frame = pd.DataFrame(selected)
    frame["period"] = frame["period_start"].map(quarter_label)
    frame["time_index"] = frame["period_start"].map(
        lambda period: period.year * 4 + (period.month - 1) // 3
    )
    frame["treated"] = (frame["territory_id"] == treated_id).astype(int)
    frame["post"] = (frame["period_start"] >= post_start).astype(int)
    frame["log_value"] = frame["value"].map(math.log)

    model = smf.ols(
        "log_value ~ treated:post + C(territory_id) + C(period)",
        data=frame,
    ).fit(
        cov_type="cluster",
        cov_kwds={"groups": frame["territory_id"], "use_correction": True},
    )
    if "treated:post" not in model.params:
        raise ValueError("Impossible d’estimer l’interaction traité × après.")

    pre_frame = frame[frame["period_start"] < adoption_start]
    pretrend_model = smf.ols(
        "log_value ~ treated:time_index + C(territory_id) + C(period)",
        data=pre_frame,
    ).fit(
        cov_type="cluster",
        cov_kwds={"groups": pre_frame["territory_id"], "use_correction": True},
    )
    pretrend = None
    if "treated:time_index" in pretrend_model.params:
        pretrend = (
            float(pretrend_model.params["treated:time_index"]),
            float(pretrend_model.pvalues["treated:time_index"]),
        )
    return model, frame, pretrend


def main():
    parser = argparse.ArgumentParser(
        description="DiD exploratoire sur les indicateurs trimestriels d’emploi ou de salaire QCEW."
    )
    parser.add_argument("--indicator", choices=sorted(INDICATORS), default="employment")
    parser.add_argument("--treated-id", default="us-wa-king-county")
    parser.add_argument("--control-ids", nargs="+", default=DEFAULT_CONTROLS)
    parser.add_argument("--post-quarter", type=parse_quarter, default=parse_quarter("2020-Q3"))
    parser.add_argument("--adoption-quarter", type=parse_quarter, default=parse_quarter("2020-Q3"))
    parser.add_argument("--start-quarter", type=parse_quarter, default=parse_quarter("2015-Q1"))
    parser.add_argument("--end-quarter", type=parse_quarter, default=parse_quarter("2025-Q4"))
    args = parser.parse_args()
    if args.start_quarter >= args.end_quarter:
        parser.error("--start-quarter doit précéder --end-quarter.")
    if args.post_quarter <= args.start_quarter or args.post_quarter > args.end_quarter:
        parser.error("--post-quarter doit se trouver dans la période étudiée.")
    if args.post_quarter < args.adoption_quarter:
        parser.error("--post-quarter ne peut pas précéder --adoption-quarter.")
    if args.treated_id in args.control_ids or len(set(args.control_ids)) != len(args.control_ids):
        parser.error("Les territoires témoins doivent être uniques et distincts du territoire traité.")

    indicator_code, indicator_label, unit = INDICATORS[args.indicator]
    try:
        with connect() as conn:
            rows = load_rows(
                conn,
                [args.treated_id, *args.control_ids],
                indicator_code,
                args.start_quarter,
                args.end_quarter,
            )
        model, frame, pretrend = fit_local_did(
            rows,
            args.treated_id,
            args.control_ids,
            args.post_quarter,
            args.adoption_quarter,
        )
    except (RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    estimate = float(model.params["treated:post"])
    conf_low, conf_high = model.conf_int().loc["treated:post"].tolist()
    percent_effect = 100 * (math.exp(estimate) - 1)
    percent_low = 100 * (math.exp(conf_low) - 1)
    percent_high = 100 * (math.exp(conf_high) - 1)
    print(f"Indicateur : {indicator_label} ({unit}), échelle logarithmique")
    print(f"Territoire traité proxy : {args.treated_id}")
    print(f"Comtés témoins : {', '.join(args.control_ids)}")
    print(
        f"Période : {quarter_label(args.start_quarter)} à {quarter_label(args.end_quarter)} ; "
        f"après = à partir de {quarter_label(args.post_quarter)}"
    )
    if args.post_quarter == args.adoption_quarter:
        print("Trimestres de transition exclus : aucun.")
    else:
        print(
            "Trimestres de transition exclus : "
            f"{quarter_label(args.adoption_quarter)} à avant {quarter_label(args.post_quarter)}."
        )
    print(f"Observations : {len(frame)} ({frame['period'].nunique()} trimestres)")
    print(
        f"Coefficient DiD : {estimate:.5f}; variation relative estimée : {percent_effect:.2f}% "
        f"(IC 95% clusterisé : {percent_low:.2f}% à {percent_high:.2f}%, "
        f"p={model.pvalues['treated:post']:.4f})"
    )
    if pretrend is None:
        print("Tendance pré-traitement : non estimable.")
    else:
        print(
            "Écart de tendance linéaire avant l’adoption : "
            f"{pretrend[0]:.6f} par trimestre (p={pretrend[1]:.4f})."
        )
    print(
        "Interprétation prudente : estimation exploratoire sur King County, non sur Seattle. "
        f"Les erreurs clusterisées reposent sur {frame['territory_id'].nunique()} comtés; "
        "l’inférence est fragile avec peu de grappes. "
        "La pandémie, les retombées vers les comtés voisins et les différences locales "
        "empêchent d’attribuer directement le résultat à la taxe."
    )


if __name__ == "__main__":
    main()
