import argparse
import math
import sys
from datetime import date

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


def _panel_frame(rows, required_columns, unit_columns, post_start):
    frame = pd.DataFrame(rows)
    missing_columns = set(required_columns) - set(frame.columns)
    if missing_columns:
        raise ValueError(
            "Colonnes manquantes : " + ", ".join(sorted(missing_columns)) + "."
        )
    if frame.empty:
        raise ValueError("Le fichier ne contient aucune observation.")

    frame = frame.loc[:, required_columns].copy()
    frame["period_start"] = pd.to_datetime(
        frame["period_start"], errors="coerce"
    ).dt.date
    if frame["period_start"].isna().any():
        raise ValueError("Chaque period_start doit être une date valide (AAAA-MM-JJ).")
    for column in ("value", "exposure", "treated"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
            if frame[column].isna().any() or not all(
                math.isfinite(value) for value in frame[column]
            ):
                raise ValueError(f"La colonne {column!r} contient une valeur non numérique.")

    if (frame["value"] < 0).any():
        raise ValueError("La colonne value ne peut pas contenir de valeurs négatives.")
    if frame[unit_columns].isna().any().any():
        raise ValueError("Les identifiants d’unité ne peuvent pas être vides.")

    key_columns = [*unit_columns, "period_start"]
    if frame.duplicated(key_columns).any():
        raise ValueError(
            "Le panel contient plusieurs lignes pour une même unité et période."
        )

    frame["period"] = frame["period_start"].astype(str)
    periods = sorted(frame["period_start"].unique())
    pre_periods = [period for period in periods if period < post_start]
    post_periods = [period for period in periods if period >= post_start]
    if len(pre_periods) < 2 or len(post_periods) < 2:
        raise ValueError("Il faut au moins 2 périodes avant et 2 après la date post.")

    expected = {
        (*unit, period)
        for unit in frame[unit_columns].drop_duplicates().itertuples(index=False, name=None)
        for period in periods
    }
    actual = {
        (*row[:-1], row[-1])
        for row in frame[[*unit_columns, "period_start"]].itertuples(
            index=False, name=None
        )
    }
    if actual != expected:
        raise ValueError(
            "Panel incomplet : chaque unité doit être observée à chaque période."
        )

    frame["post"] = (frame["period_start"] >= post_start).astype(int)
    return frame


def fit_within_firm_did(rows, post_start):
    """Compare local sites within each firm, absorbing firm-specific time shocks."""
    frame = _panel_frame(
        rows,
        ["firm_id", "location_id", "period_start", "treated", "value"],
        ["firm_id", "location_id"],
        post_start,
    )
    if not frame["treated"].isin([0, 1]).all():
        raise ValueError("treated doit valoir 0 ou 1.")
    if frame.groupby(["firm_id", "location_id"])["treated"].nunique().gt(1).any():
        raise ValueError("Le statut treated doit rester fixe pour chaque site.")
    if frame.groupby("location_id")["firm_id"].nunique().gt(1).any():
        raise ValueError("Un location_id ne peut appartenir qu’à une seule firme.")

    locations_per_firm = frame.groupby("firm_id")["location_id"].nunique()
    treated_per_firm = frame.groupby("firm_id")["treated"].nunique()
    if (locations_per_firm < 2).any() or (treated_per_firm < 2).any():
        raise ValueError(
            "Chaque firme doit avoir au moins un site traité et un site témoin."
        )

    firm_period_codes, _ = pd.factorize(
        pd.MultiIndex.from_frame(frame[["firm_id", "period"]]), sort=True
    )
    location_codes, _ = pd.factorize(frame["location_id"], sort=True)
    baseline_locations = set(
        frame.assign(location_code=location_codes)
        .groupby("firm_id")["location_code"]
        .min()
        .astype(int)
    )
    design = pd.get_dummies(firm_period_codes, prefix="firm_period", dtype=float)
    for location_code in range(frame["location_id"].nunique()):
        if location_code not in baseline_locations:
            design[f"location_{location_code}"] = (
                location_codes == location_code
            ).astype(float)
    design.insert(0, "treated:post", frame["treated"] * frame["post"])
    model = sm.OLS(frame["value"], design).fit(
        cov_type="cluster",
        cov_kwds={"groups": frame["location_id"], "use_correction": True},
    )
    if "treated:post" not in model.params:
        raise ValueError("Impossible d’estimer l’interaction treated × post.")
    return model, frame


def fit_continuous_exposure_did(rows, post_start):
    """Estimate the post-policy outcome change per unit of baseline exposure."""
    frame = _panel_frame(
        rows,
        ["company_id", "period_start", "exposure", "value"],
        ["company_id"],
        post_start,
    )
    if not frame["exposure"].between(0, 1).all():
        raise ValueError("exposure doit être une part comprise entre 0 et 1.")
    if frame.groupby("company_id")["exposure"].nunique().gt(1).any():
        raise ValueError(
            "L’exposition doit être mesurée avant la réforme et rester fixe "
            "sur toute la période."
        )
    if frame["company_id"].nunique() < 3:
        raise ValueError("Il faut au moins 3 entreprises pour la DiD à exposition continue.")

    model = smf.ols(
        "value ~ exposure:post + C(company_id) + C(period)",
        data=frame,
    ).fit(
        cov_type="cluster",
        cov_kwds={"groups": frame["company_id"], "use_correction": True},
    )
    if "exposure:post" not in model.params:
        raise ValueError("Impossible d’estimer l’interaction exposure × post.")
    return model, frame


def fit_salary_rdd(rows, cutoff, bandwidth, minimum_per_side=20):
    """Fit a local-linear sharp RDD with a triangular kernel around a cutoff."""
    if not math.isfinite(cutoff) or not math.isfinite(bandwidth) or bandwidth <= 0:
        raise ValueError("Le seuil doit être fini et la bande passante strictement positive.")
    if minimum_per_side < 2:
        raise ValueError("Il faut au moins 2 observations requises de chaque côté.")
    frame = pd.DataFrame(rows)
    missing_columns = {"running", "value"} - set(frame.columns)
    if missing_columns:
        raise ValueError(
            "Colonnes manquantes : " + ", ".join(sorted(missing_columns)) + "."
        )
    if frame.empty:
        raise ValueError("Le fichier ne contient aucune observation.")
    frame = frame[["running", "value"]].copy()
    for column in ("running", "value"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any() or not all(
            math.isfinite(value) for value in frame[column]
        ):
            raise ValueError(f"La colonne {column!r} contient une valeur non numérique.")
    if (frame["value"] < 0).any():
        raise ValueError("La colonne value ne peut pas contenir de valeurs négatives.")

    frame["distance"] = frame["running"] - cutoff
    frame = frame[frame["distance"].abs() < bandwidth].copy()
    frame["above"] = (frame["distance"] >= 0).astype(int)
    side_counts = frame["above"].value_counts()
    below_count = int(side_counts.get(0, 0))
    above_count = int(side_counts.get(1, 0))
    if min(below_count, above_count) < minimum_per_side:
        raise ValueError(
            f"RDD non estimable : au moins {minimum_per_side} observations sont requises "
            f"de chaque côté du seuil dans la bande passante (actuellement "
            f"{below_count} en dessous, {above_count} au-dessus)."
        )
    if frame.loc[frame["above"] == 0, "distance"].nunique() < 2 or frame.loc[
        frame["above"] == 1, "distance"
    ].nunique() < 2:
        raise ValueError("Il faut au moins 2 valeurs distinctes de running de chaque côté.")

    frame["weight"] = 1 - frame["distance"].abs() / bandwidth
    model = smf.wls(
        "value ~ above + distance + above:distance",
        data=frame,
        weights=frame["weight"],
    ).fit(cov_type="HC1")
    if "above" not in model.params:
        raise ValueError("Impossible d’estimer le saut au seuil.")
    return model, frame


def _print_result(model, coefficient, observations, design, note):
    estimate = float(model.params[coefficient])
    low, high = model.conf_int().loc[coefficient].tolist()
    print(f"Plan : {design}")
    print(f"Observations utilisées : {observations}")
    print(
        f"Effet estimé : {estimate:.6g} "
        f"(IC 95 % : {low:.6g} à {high:.6g}, p={model.pvalues[coefficient]:.4g})"
    )
    print(note)


def main():
    parser = argparse.ArgumentParser(
        description="Estimations causales locales exploratoires à partir d’un CSV."
    )
    parser.add_argument(
        "--design",
        choices=("within-firm", "continuous-did", "rdd"),
        required=True,
    )
    parser.add_argument("--input", required=True, help="CSV contenant les observations agrégées.")
    parser.add_argument(
        "--post-date",
        type=date.fromisoformat,
        help="Première période post-réforme (AAAA-MM-JJ), pour les deux DiD.",
    )
    parser.add_argument("--cutoff", type=float, help="Seuil de running pour le RDD.")
    parser.add_argument("--bandwidth", type=float, help="Bande passante autour du seuil RDD.")
    parser.add_argument("--minimum-per-side", type=int, default=20)
    args = parser.parse_args()

    try:
        data = pd.read_csv(args.input)
        if args.design == "within-firm":
            if args.post_date is None:
                parser.error("--post-date est requis avec --design within-firm.")
            model, frame = fit_within_firm_did(data.to_dict("records"), args.post_date)
            _print_result(
                model,
                "treated:post",
                len(frame),
                "DiD intra-entreprise ; effets fixes site et firme × période",
                "Les erreurs-types sont regroupées par site ; l’inférence reste fragile "
                "avec peu de sites.",
            )
        elif args.design == "continuous-did":
            if args.post_date is None:
                parser.error("--post-date est requis avec --design continuous-did.")
            model, frame = fit_continuous_exposure_did(
                data.to_dict("records"), args.post_date
            )
            _print_result(
                model,
                "exposure:post",
                len(frame),
                "DiD à exposition continue ; effets fixes entreprise et période",
                "L’effet correspond à une hausse de l’exposition de 0 à 1 ; "
                "l’exposition doit être pré-réforme et sourcée.",
            )
        else:
            if args.cutoff is None or args.bandwidth is None:
                parser.error("--cutoff et --bandwidth sont requis avec --design rdd.")
            if args.minimum_per_side < 2:
                parser.error("--minimum-per-side doit être au moins égal à 2.")
            model, frame = fit_salary_rdd(
                data.to_dict("records"),
                args.cutoff,
                args.bandwidth,
                args.minimum_per_side,
            )
            _print_result(
                model,
                "above",
                len(frame),
                "RDD sharp local linéaire pondérée, noyau triangulaire, erreurs HC1",
                "L’interprétation causale requiert un seuil légal d’assignation, "
                "l’absence de manipulation du running et des tests de robustesse.",
            )
    except (OSError, pd.errors.ParserError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
