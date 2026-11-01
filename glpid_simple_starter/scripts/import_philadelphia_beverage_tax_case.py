import os
from datetime import date

import psycopg
from dotenv import load_dotenv


CITY_SOURCE_ID = "source-philadelphia-beverage-tax-city"
STUDY_SOURCE_ID = "source-philadelphia-beverage-tax-jama-2019"
POLICY_ID = "policy-philadelphia-beverage-tax-2017"
CITY_SOURCE_URL = (
    "https://www.phila.gov/services/payments-assistance-taxes/business-taxes/"
    "philadelphia-beverage-tax/"
)
STUDY_SOURCE_URL = "https://pubmed.ncbi.nlm.nih.gov/31087022/"

STORE_TYPES = {
    "supermarkets": "supermarchés",
    "mass_merchandise": "magasins généralistes",
    "pharmacies": "pharmacies",
}
YEARS = (2016, 2017)
PRICE_CENTS_PER_OUNCE = {
    "us-pa-philadelphia": {
        "supermarkets": (5.43, 6.24),
        "mass_merchandise": (5.28, 6.24),
        "pharmacies": (6.60, 8.28),
    },
    "us-md-baltimore": {
        "supermarkets": (5.33, 5.50),
        "mass_merchandise": (6.34, 6.52),
        "pharmacies": (6.76, 6.93),
    },
}
VOLUME_MILLION_OUNCES_PER_FOUR_WEEKS = {
    "us-pa-philadelphia": {
        "supermarkets": (4.85, 1.99),
        "mass_merchandise": (2.98, 1.72),
        "pharmacies": (0.16, 0.13),
    },
    "us-md-baltimore": {
        "supermarkets": (2.83, 2.81),
        "mass_merchandise": (1.05, 1.00),
        "pharmacies": (0.14, 0.13),
    },
}
DID_PRICE_EFFECTS = {
    "supermarkets": (0.65, "0.60 à 0.69"),
    "mass_merchandise": (0.87, "0.72 à 1.02"),
    "pharmacies": (1.56, "1.50 à 1.62"),
}
DID_VOLUME_EFFECTS = {
    "supermarkets": (-2.85, "-4.10 à -1.60"),
    "mass_merchandise": (-1.20, "-2.04 à -0.36"),
    "pharmacies": (-0.02, "-0.03 à -0.01"),
}


def published_indicators():
    records = []
    for territory_id, store_values in PRICE_CENTS_PER_OUNCE.items():
        for store_type, yearly_values in store_values.items():
            for year, value in zip(YEARS, yearly_values):
                records.append(
                    (
                        f"pbt-price-{territory_id}-{store_type}-{year}",
                        territory_id,
                        f"pbt_mean_taxed_beverage_price_{store_type}",
                        date(year, 1, 1),
                        date(year, 12, 31),
                        value,
                        "US cents per ounce",
                        "local",
                        STUDY_SOURCE_ID,
                        STUDY_SOURCE_URL,
                        (
                            f"Valeur annuelle publiée pour les boissons taxées, "
                            f"{STORE_TYPES[store_type]}, {year}; données agrégées "
                            "de chaînes de magasins, non microdonnées."
                        ),
                    )
                )

    for territory_id, store_values in VOLUME_MILLION_OUNCES_PER_FOUR_WEEKS.items():
        for store_type, yearly_values in store_values.items():
            for year, value in zip(YEARS, yearly_values):
                records.append(
                    (
                        f"pbt-volume-{territory_id}-{store_type}-{year}",
                        territory_id,
                        f"pbt_taxed_beverage_volume_{store_type}",
                        date(year, 1, 1),
                        date(year, 12, 31),
                        value,
                        "million ounces per four-week period",
                        "local",
                        STUDY_SOURCE_ID,
                        STUDY_SOURCE_URL,
                        (
                            f"Volume moyen publié par période de quatre semaines, "
                            f"{STORE_TYPES[store_type]}, {year}; données agrégées "
                            "des magasins étudiés, pas le volume total du marché."
                        ),
                    )
                )

    for indicator_suffix, territory_id, yearly_values, unit, description in (
        (
            "philadelphia_total_volume",
            "us-pa-philadelphia",
            (2475.0, 1214.0),
            "million ounces per year",
            "Ventes annuelles totales de boissons taxées rapportées pour Philadelphie.",
        ),
        (
            "border_zip_total_volume",
            "us-pa-philadelphia-border-zipcodes",
            (713.1, 1021.3),
            "million ounces per year",
            "Ventes annuelles rapportées dans les codes postaux de Pennsylvanie "
            "limitrophes inclus dans l'étude.",
        ),
    ):
        for year, value in zip(YEARS, yearly_values):
            records.append(
                (
                    f"pbt-total-{indicator_suffix}-{year}",
                    territory_id,
                    f"pbt_{indicator_suffix}",
                    date(year, 1, 1),
                    date(year, 12, 31),
                    value,
                    unit,
                    "local",
                    STUDY_SOURCE_ID,
                    STUDY_SOURCE_URL,
                    (
                        f"{description} {year}. Ce sont les résultats agrégés "
                        "publiés pour des détaillants en chaîne, et non l'ensemble "
                        "du marché."
                    ),
                )
            )

    for store_type, (value, confidence_interval) in DID_PRICE_EFFECTS.items():
        records.append(
            (
                f"pbt-published-did-price-{store_type}",
                "us-pa-philadelphia",
                f"pbt_published_did_price_effect_{store_type}",
                date(2017, 1, 1),
                date(2017, 12, 31),
                value,
                "US cents per ounce",
                "local",
                STUDY_SOURCE_ID,
                STUDY_SOURCE_URL,
                (
                    "Estimation différence-en-différences publiée, Philadelphie "
                    "contre Baltimore, 2016–2017. IC 95 % : "
                    f"{confidence_interval} centimes par once; p < 0,001. "
                    "Valeur de l'article, non recalculée par ce projet."
                ),
            )
        )

    for store_type, (value, confidence_interval) in DID_VOLUME_EFFECTS.items():
        records.append(
            (
                f"pbt-published-did-volume-{store_type}",
                "us-pa-philadelphia",
                f"pbt_published_did_volume_effect_{store_type}",
                date(2017, 1, 1),
                date(2017, 12, 31),
                value,
                "million ounces per four-week period",
                "local",
                STUDY_SOURCE_ID,
                STUDY_SOURCE_URL,
                (
                    "Estimation différence-en-différences publiée, Philadelphie "
                    "contre Baltimore, 2016–2017. IC 95 % : "
                    f"{confidence_interval} millions d'onces par période de "
                    "quatre semaines; "
                    + ("p = 0,001." if store_type == "mass_merchandise" else "p < 0,001.")
                    + " Valeur de l'article, non recalculée par ce projet."
                ),
            )
        )
    return records


def database_connection():
    load_dotenv()
    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
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


def persist_case():
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO sources
                    (source_id, publisher, title, source_type, url, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE
                SET publisher = EXCLUDED.publisher, title = EXCLUDED.title,
                    source_type = EXCLUDED.source_type, url = EXCLUDED.url,
                    notes = EXCLUDED.notes
                """,
                [
                    (
                        CITY_SOURCE_ID,
                        "City of Philadelphia",
                        "Philadelphia Beverage Tax — règles et taux",
                        "official_law",
                        CITY_SOURCE_URL,
                        "Page officielle : taxe de 1,5 cent par once de boisson sucrée distribuée.",
                    ),
                    (
                        STUDY_SOURCE_ID,
                        "JAMA Network Open",
                        "Association of a Beverage Tax With Changes in Beverage Prices and Sales",
                        "academic",
                        STUDY_SOURCE_URL,
                        (
                            "Étude évaluée par les pairs, PMID 31087022, DOI "
                            "10.1001/jama.2019.4249. Différence-en-différences "
                            "Philadelphie–Baltimore et analyse de codes postaux "
                            "limitrophes; 291 magasins, données commerciales IRI "
                            "(environ 25 % des onces taxées vendues à Philadelphie). "
                            "Les valeurs importées sont celles publiées dans l'article; "
                            "les microdonnées IRI ne sont pas incluses ni ouvertes."
                        ),
                    ),
                ],
            )
            cur.executemany(
                """
                INSERT INTO territories
                    (territory_id, name, territory_type, country_code,
                     parent_territory_id, description, boundary_source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_id) DO UPDATE
                SET name = EXCLUDED.name, territory_type = EXCLUDED.territory_type,
                    country_code = EXCLUDED.country_code,
                    parent_territory_id = EXCLUDED.parent_territory_id,
                    description = EXCLUDED.description,
                    boundary_source_url = EXCLUDED.boundary_source_url
                """,
                [
                    ("us-pa", "Pennsylvania", "state", "US", None, "État américain.", None),
                    ("us-md", "Maryland", "state", "US", None, "État américain.", None),
                    (
                        "us-pa-philadelphia",
                        "Philadelphia, Pennsylvania",
                        "city",
                        "US",
                        "us-pa",
                        "Territoire traité de la taxe sur les boissons, entrée en vigueur en 2017.",
                        CITY_SOURCE_URL,
                    ),
                    (
                        "us-md-baltimore",
                        "Baltimore, Maryland",
                        "city",
                        "US",
                        "us-md",
                        "Ville témoin de l'étude publiée; pas une ville témoin non traitée par cette taxe.",
                        STUDY_SOURCE_URL,
                    ),
                    (
                        "us-pa-philadelphia-border-zipcodes",
                        "Codes postaux de Pennsylvanie limitrophes de Philadelphia",
                        "other",
                        "US",
                        "us-pa",
                        (
                            "Zone d'étude construite à partir de codes postaux limitrophes "
                            "de Philadelphia; ce n'est pas une juridiction fiscale distincte."
                        ),
                        STUDY_SOURCE_URL,
                    ),
                ],
            )
            cur.execute(
                """
                INSERT INTO policy_changes
                    (policy_id, territory_id, title, policy_type, summary,
                     adoption_date, effective_date, status, affected_sector,
                     expected_mechanism, source_id, official_reference)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (policy_id) DO UPDATE
                SET territory_id = EXCLUDED.territory_id, title = EXCLUDED.title,
                    policy_type = EXCLUDED.policy_type, summary = EXCLUDED.summary,
                    adoption_date = EXCLUDED.adoption_date,
                    effective_date = EXCLUDED.effective_date, status = EXCLUDED.status,
                    affected_sector = EXCLUDED.affected_sector,
                    expected_mechanism = EXCLUDED.expected_mechanism,
                    source_id = EXCLUDED.source_id,
                    official_reference = EXCLUDED.official_reference
                """,
                (
                    POLICY_ID,
                    "us-pa-philadelphia",
                    "Philadelphia Beverage Tax",
                    "local_excise_tax",
                    (
                        "Taxe d'accise municipale de 1,5 cent par once sur les boissons "
                        "sucrées distribuées à Philadelphia, en vigueur depuis le "
                        "1er janvier 2017. Une étude publiée rapporte une hausse des "
                        "prix et une baisse des ventes; voir ses estimations dans "
                        "les indicateurs, sans les confondre avec une réplication."
                    ),
                    date(2016, 6, 20),
                    date(2017, 1, 1),
                    "in_force",
                    "Distributeurs et détaillants de boissons sucrées; prix et ventes au détail.",
                    (
                        "Répercussion sur les prix et substitution de la demande; "
                        "achats transfrontaliers possibles dans les codes postaux "
                        "limitrophes."
                    ),
                    CITY_SOURCE_ID,
                    "Philadelphia Beverage Tax, Bill No. 160176",
                ),
            )
            records = published_indicators()
            cur.executemany(
                """
                INSERT INTO territory_indicators
                    (territory_indicator_id, territory_id, indicator_code,
                     period_start, period_end, value, unit, geographic_scope,
                     source_id, source_page, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (territory_indicator_id) DO UPDATE
                SET territory_id = EXCLUDED.territory_id,
                    indicator_code = EXCLUDED.indicator_code,
                    period_start = EXCLUDED.period_start,
                    period_end = EXCLUDED.period_end, value = EXCLUDED.value,
                    unit = EXCLUDED.unit, geographic_scope = EXCLUDED.geographic_scope,
                    source_id = EXCLUDED.source_id, source_page = EXCLUDED.source_page,
                    notes = EXCLUDED.notes, collected_at = now()
                """,
                records,
            )
    return len(records)


def main():
    count = persist_case()
    print(
        f"Cas de Philadelphia importé/mis à jour : {count} observations publiées "
        f"(prix, volumes et estimations DiD). Les microdonnées IRI ne sont pas incluses."
    )


if __name__ == "__main__":
    main()
