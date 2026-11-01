import math
import os
from datetime import date

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.rows import dict_row
from scripts.local_employment_did import fit_local_did, quarter_label


APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_DIR, ".env"))

st.set_page_config(
    page_title="GLPID — exploration de la base",
    page_icon="🌍",
    layout="wide",
)


def connect_read_only():
    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Paramètres PostgreSQL manquants dans .env : " + ", ".join(missing)
        )
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        row_factory=dict_row,
    )


@st.cache_data(ttl=60)
def read_query(query, params=()):
    with connect_read_only() as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            return pd.DataFrame(conn.execute(query, params).fetchall())


@st.cache_data(ttl=60)
def load_metadata():
    return {
        "territories": read_query(
            """
            SELECT t.territory_id, t.name, t.territory_type, t.country_code,
                   t.parent_territory_id, parent.name AS parent_name,
                   t.description, t.boundary_source_url,
                   COUNT(DISTINCT p.policy_id) AS policy_count,
                   COUNT(DISTINCT i.territory_indicator_id) AS indicator_count
            FROM territories t
            LEFT JOIN territories parent
              ON parent.territory_id = t.parent_territory_id
            LEFT JOIN policy_changes p ON p.territory_id = t.territory_id
            LEFT JOIN territory_indicators i ON i.territory_id = t.territory_id
            GROUP BY t.territory_id, parent.name
            ORDER BY t.country_code NULLS LAST, t.territory_type, t.name
            """
        ),
        "sources": read_query(
            """
            SELECT s.source_id, s.publisher, s.title, s.source_type, s.url,
                   s.published_date, s.accessed_at, s.notes,
                   (SELECT COUNT(*) FROM policy_changes p
                    WHERE p.source_id = s.source_id) AS policy_count,
                   (SELECT COUNT(*) FROM territory_indicators i
                    WHERE i.source_id = s.source_id) AS indicator_count,
                   (SELECT COUNT(*) FROM company_indicators ci
                    WHERE ci.source_id = s.source_id) AS company_indicator_count,
                   (SELECT COUNT(*) FROM company_exposures e
                    WHERE e.source_id = s.source_id) AS exposure_count,
                   (SELECT COUNT(*) FROM company_prices cp
                    WHERE cp.source_id = s.source_id) AS company_price_count,
                   (SELECT COUNT(*) FROM market_index_prices mip
                    WHERE mip.source_id = s.source_id) AS market_price_count
            FROM sources s
            ORDER BY s.publisher, s.title
            """
        ),
        "source_items": read_query(
            """
            SELECT s.source_id, 'Politique' AS category, p.title AS information,
                   t.name AS territory, p.adoption_date AS period_start,
                   COALESCE(p.end_date, p.effective_date) AS period_end,
                   p.policy_id AS record_id
            FROM policy_changes p
            JOIN sources s ON s.source_id = p.source_id
            JOIN territories t ON t.territory_id = p.territory_id
            UNION ALL
            SELECT s.source_id, 'Indicateur territorial',
                   i.indicator_code || ' (' || i.unit || ', ' ||
                       i.geographic_scope || ')',
                   t.name, MIN(i.period_start), MAX(i.period_end),
                   COUNT(*)::text || ' observations'
            FROM territory_indicators i
            JOIN sources s ON s.source_id = i.source_id
            JOIN territories t ON t.territory_id = i.territory_id
            GROUP BY s.source_id, i.indicator_code, i.unit,
                     i.geographic_scope, t.name
            UNION ALL
            SELECT s.source_id, 'Indicateur d’entreprise',
                   c.name || ' — ' || ci.indicator_code || ' (' || ci.unit ||
                       ', portée ' || ci.geographic_scope || ')',
                   t.name, MIN(ci.period_start), MAX(ci.period_end),
                   COUNT(*)::text || ' observations'
            FROM company_indicators ci
            JOIN sources s ON s.source_id = ci.source_id
            JOIN companies c ON c.company_id = ci.company_id
            LEFT JOIN territories t ON t.territory_id = ci.territory_id
            GROUP BY s.source_id, c.name, ci.indicator_code, ci.unit,
                     ci.geographic_scope, t.name
            UNION ALL
            SELECT s.source_id, 'Exposition d’entreprise',
                   c.name || ' — ' || e.exposure_type ||
                       COALESCE(' (score ' || e.exposure_score::text || ')', ''),
                   t.name, e.start_date, e.end_date, e.exposure_id
            FROM company_exposures e
            JOIN sources s ON s.source_id = e.source_id
            JOIN companies c ON c.company_id = e.company_id
            JOIN territories t ON t.territory_id = e.territory_id
            UNION ALL
            SELECT s.source_id, 'Cours d’entreprise',
                   c.name || ' — cours boursiers',
                   NULL, MIN(cp.price_date), MAX(cp.price_date),
                   COUNT(*)::text || ' observations'
            FROM company_prices cp
            JOIN sources s ON s.source_id = cp.source_id
            JOIN companies c ON c.company_id = cp.company_id
            GROUP BY s.source_id, c.name
            UNION ALL
            SELECT s.source_id, 'Cours d’indice',
                   mip.index_name || ' — indice de marché',
                   NULL, MIN(mip.price_date), MAX(mip.price_date),
                   COUNT(*)::text || ' observations'
            FROM market_index_prices mip
            JOIN sources s ON s.source_id = mip.source_id
            GROUP BY s.source_id, mip.index_name
            ORDER BY source_id, category, information
            """
        ),
        "policies": read_query(
            """
            SELECT p.policy_id, p.title, p.policy_type, p.status, p.summary,
                   p.announcement_date, p.adoption_date, p.effective_date,
                   p.end_date, p.affected_sector, p.expected_mechanism,
                   p.official_reference, t.territory_id, t.name AS territory,
                   t.country_code, t.territory_type,
                   s.source_id, s.publisher, s.title AS source_title, s.url AS source_url
            FROM policy_changes p
            JOIN territories t ON t.territory_id = p.territory_id
            JOIN sources s ON s.source_id = p.source_id
            ORDER BY COALESCE(p.effective_date, p.adoption_date, p.announcement_date)
                     DESC NULLS LAST, p.title
            """
        ),
        "companies": read_query(
            """
            SELECT c.company_id, c.name, c.sector, c.ticker, c.country_code,
                   t.name AS headquarters_territory,
                   COUNT(DISTINCT e.exposure_id) AS exposure_count,
                   COUNT(DISTINCT i.indicator_id) AS indicator_count
            FROM companies c
            LEFT JOIN territories t
              ON t.territory_id = c.headquarters_territory_id
            LEFT JOIN company_exposures e ON e.company_id = c.company_id
            LEFT JOIN company_indicators i ON i.company_id = c.company_id
            GROUP BY c.company_id, t.name
            ORDER BY c.name
            """
        ),
        "indicator_catalog": read_query(
            """
            SELECT indicator_code, unit, geographic_scope,
                   COUNT(*) AS observations,
                   COUNT(DISTINCT territory_id) AS territories,
                   MIN(period_start) AS first_period,
                   MAX(period_end) AS last_period
            FROM territory_indicators
            GROUP BY indicator_code, unit, geographic_scope
            ORDER BY indicator_code, unit, geographic_scope
            """
        ),
    }


def metric(column, label, value):
    column.metric(label, f"{int(value):,}".replace(",", " "))


def apply_shared_filters(frame, country, territory_type, date_range):
    filtered = frame.copy()
    if country != "Tous":
        filtered = filtered[filtered["country_code"].fillna("") == country]
    if territory_type != "Tous":
        filtered = filtered[filtered["territory_type"] == territory_type]
    if not filtered.empty and date_range:
        event_date = filtered["effective_date"].fillna(filtered["adoption_date"])
        event_date = pd.to_datetime(
            event_date.fillna(filtered["announcement_date"]), errors="coerce"
        )
        start, end = date_range
        filtered = filtered[
            event_date.isna()
            | ((event_date.dt.date >= start) & (event_date.dt.date <= end))
        ]
    return filtered


def show_overview(metadata, policies, territories, sources):
    st.subheader("Vue d’ensemble")
    columns = st.columns(5)
    metric(columns[0], "Territoires", len(territories))
    metric(columns[1], "Réformes fiscales", len(policies))
    metric(columns[2], "Sources", len(sources))
    metric(columns[3], "Entreprises", len(metadata["companies"]))
    metric(columns[4], "Séries d’indicateurs", len(metadata["indicator_catalog"]))

    st.caption(
        "Les compteurs décrivent les enregistrements présents dans PostgreSQL. "
        "Une source référencée ne signifie pas nécessairement que l’ensemble de ses "
        "données a été téléchargé."
    )

    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("#### Réformes dans le temps")
        timeline = policies.copy()
        timeline["date_affichee"] = timeline["effective_date"].fillna(
            timeline["adoption_date"]
        )
        timeline["date_affichee"] = timeline["date_affichee"].fillna(
            timeline["announcement_date"]
        )
        timeline = timeline.dropna(subset=["date_affichee"])
        if timeline.empty:
            st.info("Aucune réforme avec date renseignée.")
        else:
            fig = px.scatter(
                timeline,
                x="date_affichee",
                y="territory",
                color="status",
                symbol="status",
                hover_name="title",
                hover_data={
                    "policy_type": True,
                    "date_affichee": True,
                    "source_title": True,
                },
                labels={
                    "date_affichee": "Date effective (ou adoption/annonce)",
                    "territory": "Territoire",
                    "status": "Statut",
                    "policy_type": "Type",
                    "source_title": "Source",
                },
            )
            fig.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("#### Données disponibles par type d’indicateur")
        catalog = metadata["indicator_catalog"]
        if catalog.empty:
            st.info("Aucun indicateur territorial enregistré.")
        else:
            counts = (
                catalog.groupby("geographic_scope", dropna=False)["observations"]
                .sum()
                .reset_index()
            )
            fig = px.pie(
                counts,
                names="geographic_scope",
                values="observations",
                hole=0.48,
                labels={"geographic_scope": "Portée géographique"},
            )
            fig.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)


def show_policies(policies):
    st.subheader("Changements fiscaux et politiques")
    if policies.empty:
        st.info("Aucun changement fiscal ne correspond aux filtres.")
        return
    table = policies[
        [
            "title",
            "territory",
            "policy_type",
            "status",
            "announcement_date",
            "adoption_date",
            "effective_date",
            "end_date",
            "affected_sector",
            "expected_mechanism",
            "source_title",
            "source_url",
        ]
    ].rename(
        columns={
            "title": "Politique",
            "territory": "Territoire",
            "policy_type": "Type",
            "status": "Statut",
            "announcement_date": "Annonce",
            "adoption_date": "Adoption",
            "effective_date": "Entrée en vigueur",
            "end_date": "Fin",
            "affected_sector": "Secteur concerné",
            "expected_mechanism": "Mécanisme attendu",
            "source_title": "Source",
            "source_url": "Lien source",
        }
    )
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Lien source": st.column_config.LinkColumn("Lien source"),
        },
    )


def show_territories(territories):
    st.subheader("Territoires")
    if territories.empty:
        st.info("Aucun territoire ne correspond aux filtres.")
        return
    view = territories[
        [
            "name",
            "territory_type",
            "country_code",
            "parent_name",
            "description",
            "policy_count",
            "indicator_count",
            "boundary_source_url",
        ]
    ].rename(
        columns={
            "name": "Territoire",
            "territory_type": "Type",
            "country_code": "Pays",
            "parent_name": "Territoire parent",
            "description": "Description",
            "policy_count": "Politiques",
            "indicator_count": "Observations territoriales",
            "boundary_source_url": "Source des limites",
        }
    )
    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source des limites": st.column_config.LinkColumn("Source des limites"),
        },
    )
    st.caption(
        "La base ne contient pas encore de géométries cartographiques. "
        "Cette vue affiche donc les relations territoire parent/enfant sans inventer de frontières."
    )


def show_sources(sources, source_items):
    st.subheader("Sources et traçabilité")
    if sources.empty:
        st.info("Aucune source ne correspond aux filtres.")
        return
    view = sources[
        [
            "publisher",
            "title",
            "source_type",
            "published_date",
            "accessed_at",
            "policy_count",
            "indicator_count",
            "company_indicator_count",
            "exposure_count",
            "company_price_count",
            "market_price_count",
            "notes",
            "url",
        ]
    ].rename(
        columns={
            "publisher": "Éditeur",
            "title": "Titre",
            "source_type": "Type",
            "published_date": "Publication",
            "accessed_at": "Consultée le",
            "policy_count": "Politiques liées",
            "indicator_count": "Indicateurs territoriaux",
            "company_indicator_count": "Indicateurs d’entreprise",
            "exposure_count": "Expositions documentées",
            "company_price_count": "Cours d’entreprise",
            "market_price_count": "Cours d’indice",
            "notes": "Notes",
            "url": "URL",
        }
    )
    st.dataframe(
        view,
        use_container_width=True,
        hide_index=True,
        column_config={"URL": st.column_config.LinkColumn("URL")},
    )
    st.markdown("#### Quelle information est reliée à chaque source ?")
    for row in sources.itertuples(index=False):
        linked_items = source_items[source_items["source_id"] == row.source_id]
        with st.expander(f"{row.publisher} — {row.title}"):
            st.markdown(f"**Type :** {row.source_type}")
            st.markdown(f"**URL :** [{row.url}]({row.url})")
            if row.notes:
                st.markdown(f"**Description de la source :** {row.notes}")
            if linked_items.empty:
                st.info(
                    "Cette source est référencée dans le catalogue, mais aucune ligne "
                    "de données actuellement en base ne lui est rattachée."
                )
                continue
            detail = linked_items[
                [
                    "category",
                    "information",
                    "territory",
                    "period_start",
                    "period_end",
                    "record_id",
                ]
            ].rename(
                columns={
                    "category": "Type de donnée",
                    "information": "Information / indicateur",
                    "territory": "Territoire",
                    "period_start": "Début de période",
                    "period_end": "Fin de période",
                    "record_id": "Référence / volume",
                }
            )
            st.dataframe(detail, use_container_width=True, hide_index=True)


def show_indicators(territories):
    st.subheader("Indicateurs et évolution")
    selected_territories = st.multiselect(
        "Territoires à comparer",
        territories["name"].tolist(),
        default=territories.loc[
            territories["territory_id"].isin(["us-pa", "us-de", "us-md", "us-nj"]),
            "name",
        ].tolist()[:4],
    )
    selected_ids = territories.loc[
        territories["name"].isin(selected_territories), "territory_id"
    ].tolist()
    if not selected_ids:
        st.info("Sélectionnez au moins un territoire.")
        return

    catalog = read_query(
        """
        SELECT DISTINCT indicator_code, unit, geographic_scope
        FROM territory_indicators
        WHERE territory_id = ANY(%s)
        ORDER BY indicator_code, unit, geographic_scope
        """,
        (selected_ids,),
    )
    if catalog.empty:
        st.info("Aucun indicateur territorial n’est enregistré pour cette sélection.")
        return

    indicator_options = catalog["indicator_code"].drop_duplicates().tolist()
    preferred_indicator = "qcew_private_employment"
    if preferred_indicator in indicator_options:
        indicator_options.remove(preferred_indicator)
        indicator_options.insert(0, preferred_indicator)
    selected_indicator = st.selectbox("Indicateur", indicator_options)
    available_units = catalog.loc[
        catalog["indicator_code"] == selected_indicator, "unit"
    ].drop_duplicates()
    selected_unit = st.selectbox("Unité", available_units.tolist())
    series_meta = catalog[
        (catalog["indicator_code"] == selected_indicator)
        & (catalog["unit"] == selected_unit)
    ]
    geographic_scope = st.selectbox(
        "Portée géographique",
        series_meta["geographic_scope"].drop_duplicates().tolist(),
    )

    data = read_query(
        """
        SELECT t.name AS territory, i.indicator_code, i.period_start,
               i.period_end, i.value, i.unit, i.geographic_scope,
               s.title AS source_title, s.url AS source_url
        FROM territory_indicators i
        JOIN territories t ON t.territory_id = i.territory_id
        JOIN sources s ON s.source_id = i.source_id
        WHERE i.indicator_code = %s AND i.unit = %s
          AND i.geographic_scope = %s AND i.territory_id = ANY(%s)
        ORDER BY i.period_start, t.name
        """,
        (selected_indicator, selected_unit, geographic_scope, selected_ids),
    )
    if data.empty:
        st.info("Aucune observation pour cette sélection.")
        return
    if data["value"].isna().any():
        st.warning("Certaines lignes ont une valeur manquante ; elles ne sont pas tracées.")
    fig = px.line(
        data.dropna(subset=["value"]),
        x="period_start",
        y="value",
        color="territory",
        markers=True,
        hover_data=["period_end", "source_title", "source_url"],
        labels={
            "period_start": "Période",
            "value": selected_unit,
            "territory": "Territoire",
        },
    )
    fig.update_layout(height=500, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Les séries peuvent avoir des échelles, périmètres et sources différents. "
        "La comparaison graphique ne constitue pas une estimation causale."
    )
    st.dataframe(data, use_container_width=True, hide_index=True)


def quarter_start(value):
    month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, month, 1)


def shift_quarter(value, offset):
    quarter_index = value.year * 4 + (value.month - 1) // 3 + offset
    year, quarter = divmod(quarter_index, 4)
    return date(year, quarter * 3 + 1, 1)


def first_full_quarter(value):
    quarter = quarter_start(value)
    return quarter if value == quarter else shift_quarter(quarter, 1)


def show_causal_test(policies, territories):
    st.subheader("Tester un effet causal (exploratoire)")
    st.warning(
        "Une DiD estime une association sous hypothèses (notamment tendances parallèles "
        "et absence de chocs différentiels). Elle ne prouve pas automatiquement la causalité. "
        "Les résultats dépendent du choix des témoins, de la période et des données disponibles."
    )
    if policies.empty:
        st.info("Aucune réforme n’est enregistrée.")
        return

    policy_options = policies.copy()
    outcome_coverage = read_query(
        """
        SELECT p.policy_id, i.indicator_code, i.unit, i.geographic_scope,
               COUNT(DISTINCT i.period_start)
                   FILTER (WHERE i.period_start < date_trunc('quarter', p.adoption_date)::date)
                   AS pre_periods,
               COUNT(DISTINCT i.period_start)
                   FILTER (WHERE i.period_start >= (
                       date_trunc('quarter', p.effective_date)
                       + CASE
                           WHEN p.effective_date = date_trunc('quarter', p.effective_date)::date
                               THEN INTERVAL '0 month'
                           ELSE INTERVAL '3 months'
                         END
                   )::date)
                   AS post_periods,
               MIN(i.period_start) AS first_period,
               MAX(i.period_start) AS last_period
        FROM policy_changes p
        JOIN territory_indicators i
          ON i.territory_id = CASE
              WHEN p.policy_id = 'policy-seattle-jumpstart-2021'
                  THEN 'us-wa-king-county'
              ELSE p.territory_id
          END
        WHERE p.policy_id = ANY(%s)
        GROUP BY p.policy_id, i.indicator_code, i.unit, i.geographic_scope,
                 p.adoption_date, p.effective_date
        HAVING COUNT(DISTINCT i.period_start)
                   FILTER (WHERE i.period_start < date_trunc('quarter', p.adoption_date)::date) >= 8
           AND COUNT(DISTINCT i.period_start)
                   FILTER (WHERE i.period_start >= (
                       date_trunc('quarter', p.effective_date)
                       + CASE
                           WHEN p.effective_date = date_trunc('quarter', p.effective_date)::date
                               THEN INTERVAL '0 month'
                           ELSE INTERVAL '3 months'
                         END
                   )::date) >= 8
        ORDER BY p.policy_id, i.indicator_code
        """,
        (policy_options["policy_id"].tolist(),),
    )
    policy_ids = policy_options["policy_id"].tolist()
    preferred_policy_index = (
        policy_ids.index("policy-pa-corporate-rate-2023")
        if "policy-pa-corporate-rate-2023" in policy_ids
        else 0
    )
    policy_id = st.selectbox(
        "Réforme à étudier",
        policy_ids,
        index=preferred_policy_index,
        format_func=lambda value: (
            f"{policy_options.loc[policy_options['policy_id'] == value, 'title'].iloc[0]} — "
            f"{policy_options.loc[policy_options['policy_id'] == value, 'territory'].iloc[0]} "
            f"[{'panel trimestriel candidat' if value in set(outcome_coverage['policy_id']) else 'résultat à charger'}]"
        ),
    )
    policy = policy_options.loc[policy_options["policy_id"] == policy_id].iloc[0]
    compatible_indicators = outcome_coverage[
        outcome_coverage["policy_id"] == policy_id
    ].copy()
    is_seattle_proxy = policy_id == "policy-seattle-jumpstart-2021"
    treated_id = "us-wa-king-county" if is_seattle_proxy else policy["territory_id"]
    st.markdown(
        f"**Territoire de la réforme :** {policy['territory']}  \n"
        f"**Adoption :** {policy['adoption_date']} — "
        f"**entrée en vigueur :** {policy['effective_date']}  \n"
        f"**Source de la politique :** [{policy['source_title']}]({policy['source_url']})"
    )
    if policy_id == "policy-philadelphia-beverage-tax-2017":
        st.markdown("#### Résultats publiés pour la taxe sur les boissons de Philadelphia")
        st.markdown(
            "Une étude évaluée par les pairs compare Philadelphia à Baltimore en "
            "[différence-en-différences (JAMA Network Open, 2019)]"
            "(https://pubmed.ncbi.nlm.nih.gov/31087022/). Elle rapporte une hausse "
            "des prix et une baisse des ventes de boissons taxées. Les estimations "
            "ci-dessous sont transcrites de l’article : elles ne sont pas recalculées "
            "à partir des microdonnées."
        )
        published_effects = read_query(
            """
            SELECT i.indicator_code AS résultat, i.value AS estimation,
                   i.unit AS unité, i.period_start AS période,
                   i.notes AS interprétation, i.source_page AS référence
            FROM territory_indicators i
            WHERE i.territory_id = %s
              AND i.indicator_code LIKE 'pbt_published_did_%%'
            ORDER BY i.indicator_code
            """,
            (policy["territory_id"],),
        )
        if published_effects.empty:
            st.info(
                "Les estimations de l’article ne sont pas encore chargées. "
                "Exécutez le script d’import Philadelphia documenté dans README_FR.md."
            )
        else:
            published_effects["résultat"] = (
                published_effects["résultat"]
                .str.replace("pbt_published_did_", "", regex=False)
                .str.replace("_", " ", regex=False)
                .str.capitalize()
            )
            st.dataframe(
                published_effects,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "référence": st.column_config.LinkColumn("Référence"),
                    "interprétation": st.column_config.TextColumn(
                        "Interprétation et incertitude", width="large"
                    ),
                },
            )
        st.caption(
            "Les données commerciales IRI sous-jacentes ne sont pas ouvertes. "
            "L’article analyse 291 magasins, représentant environ 25 % des onces "
            "taxées vendues à Philadelphia. Les quelques observations annuelles "
            "importées ne constituent pas un panel trimestriel et ne permettent pas "
            "de reproduire l’estimation ici."
        )
    if is_seattle_proxy:
        st.warning(
            "Les données QCEW disponibles portent sur King County, et non sur la ville "
            "de Seattle seule. King County est utilisé ici comme proxy : il inclut des "
            "zones non soumises à JumpStart, donc l’estimation peut être diluée et ne "
            "représente pas un effet municipal direct."
        )
    if policy_id == "policy-fr-corporate-rate-25-2022":
        st.warning(
            "Le résultat Eurostat est l’emploi national total des 15–74 ans, et non "
            "l’emploi des entreprises directement assujetties à l’IS. C’est un résultat "
            "macroéconomique indirect ; une DiD peut refléter d’autres différences "
            "nationales et ne mesure pas un effet propre aux multinationales."
        )
    if policy_id == "policy-ie-pillar-two":
        st.warning(
            "La série Eurostat mesure l’emploi national total, pas l’emploi des "
            "multinationales concernées. En outre, de nombreux pays comparateurs ont "
            "aussi mis en œuvre le Pilier Deux : ils ne constituent pas automatiquement "
            "des témoins non traités. L’estimation est donc exploratoire, pas une "
            "identification causale de cette réforme."
        )
    if policy_id in ("policy-uk-corporation-tax-2023", "policy-us-tcja-corporate-rate"):
        st.warning(
            "Le résultat national mesure l’emploi des personnes, pas l’emploi des "
            "entreprises soumises à l’impôt. Les séries nationales proviennent d’enquêtes "
            "et de définitions d’âge différentes selon les pays ; la comparaison est "
            "exploratoire et ne suffit pas à isoler l’effet de la réforme."
        )

    if pd.isna(policy["effective_date"]) or pd.isna(policy["adoption_date"]):
        st.warning(
            "Cette réforme n’a pas toutes les dates d’adoption et d’entrée en vigueur "
            "enregistrées. Consultez la source officielle et complétez la fiche de politique "
            "avant de définir une fenêtre causale."
        )
        return

    adoption_quarter = quarter_start(policy["adoption_date"])
    post_quarter = first_full_quarter(policy["effective_date"])
    if compatible_indicators.empty:
        suggested_start = shift_quarter(min(adoption_quarter, post_quarter), -8)
        suggested_end = shift_quarter(post_quarter, 7)
        st.info(
            "Cette réforme reste sélectionnable, mais aucun indicateur de résultat "
            "trimestriel du territoire traité ne couvre actuellement au moins 8 trimestres avant "
            "l’adoption et 8 après l’entrée en vigueur. La fenêtre ci-dessous est une "
            "suggestion de collecte, pas une fenêtre estimable avec les données actuelles."
        )
        st.markdown("#### Fenêtre recommandée pour une future collecte")
        suggested_cols = st.columns(4)
        suggested_cols[0].metric("Début suggéré", quarter_label(suggested_start))
        suggested_cols[1].metric("Adoption", quarter_label(adoption_quarter))
        suggested_cols[2].metric("Début effectif", quarter_label(post_quarter))
        suggested_cols[3].metric("Fin suggérée", quarter_label(suggested_end))
        date_cols = st.columns(2)
        candidate_start = date_cols[0].date_input(
            "Début de la fenêtre candidate",
            value=suggested_start,
            key=f"candidate_start_{policy_id}",
        )
        candidate_end = date_cols[1].date_input(
            "Fin de la fenêtre candidate",
            value=suggested_end,
            key=f"candidate_end_{policy_id}",
        )
        if candidate_start >= candidate_end:
            st.error("La date de début candidate doit précéder la date de fin.")
        st.caption(
            "Cette fenêtre vise au moins 8 trimestres de chaque côté, hors transition "
            "entre adoption et entrée en vigueur. Ces dates sont modifiables pour préparer "
            "l'étude, mais ne créent pas d'observations. Il faut importer les mêmes "
            "indicateurs et périodes pour le territoire traité et des témoins crédibles."
        )
        coverage = read_query(
            """
            SELECT i.indicator_code AS indicateur, i.unit AS unite,
                   i.geographic_scope AS portee,
                   COUNT(DISTINCT i.period_start) AS periodes,
                   MIN(i.period_start) AS debut,
                   MAX(i.period_end) AS fin,
                   s.title AS source, s.url AS source_url
            FROM territory_indicators i
            JOIN sources s ON s.source_id = i.source_id
            WHERE i.territory_id = %s
            GROUP BY i.indicator_code, i.unit, i.geographic_scope,
                     s.source_id
            ORDER BY i.indicator_code
            """,
            (treated_id,),
        )
        if coverage.empty:
            st.warning(
                "Aucun indicateur territorial n’est encore relié à ce territoire. "
                "La base doit d’abord recevoir des séries de résultats datées."
            )
        else:
            st.markdown("#### Données déjà présentes pour ce territoire")
            st.dataframe(
                coverage,
                use_container_width=True,
                hide_index=True,
                column_config={"source_url": st.column_config.LinkColumn("Lien source")},
            )
        st.markdown("#### Dates de référence enregistrées")
        date_rows = pd.DataFrame(
            [
                ("Annonce", policy["announcement_date"]),
                ("Adoption", policy["adoption_date"]),
                ("Entrée en vigueur", policy["effective_date"]),
                ("Fin", policy["end_date"]),
            ],
            columns=["Événement", "Date"],
        )
        st.dataframe(date_rows, use_container_width=True, hide_index=True)
        return

    indicator_keys = list(
        compatible_indicators[["indicator_code", "unit", "geographic_scope"]]
        .itertuples(index=False, name=None)
    )
    default_key = next(
        (
            key
            for key in indicator_keys
            if key[0] == "qcew_private_employment"
        ),
        indicator_keys[0],
    )
    selected_key = st.selectbox(
        "Résultat observé",
        indicator_keys,
        index=indicator_keys.index(default_key),
        format_func=lambda key: (
            f"{key[0]} — {key[1]} ({key[2]}) "
            f"[{int(compatible_indicators.loc[compatible_indicators['indicator_code'] == key[0], 'pre_periods'].iloc[0])} pré / "
            f"{int(compatible_indicators.loc[compatible_indicators['indicator_code'] == key[0], 'post_periods'].iloc[0])} post]"
        ),
    )
    indicator_code, unit, geographic_scope = selected_key

    cross_country_comparison = indicator_code == "eurostat_lfs_employment"
    available_territories = read_query(
        """
        SELECT t.territory_id, t.name, t.territory_type,
               COUNT(DISTINCT i.period_start) AS periods,
               MIN(i.period_start) AS first_period,
               MAX(i.period_start) AS last_period
        FROM territory_indicators i
        JOIN territories t ON t.territory_id = i.territory_id
        WHERE i.indicator_code = %s AND i.unit = %s
          AND i.geographic_scope = %s
          AND (%s OR t.country_code IS NOT DISTINCT FROM %s)
        GROUP BY t.territory_id
        ORDER BY t.name
        """,
        (
            indicator_code,
            unit,
            geographic_scope,
            cross_country_comparison,
            policy["country_code"],
        ),
    )
    control_options = available_territories[
        available_territories["territory_id"] != treated_id
    ]
    if control_options.empty:
        st.info(
            "Aucun territoire témoin ne possède le même indicateur, la même unité "
            "et la même portée géographique."
        )
        return
    if not cross_country_comparison:
        st.caption(
            "Les témoins proposés sont ceux ayant au moins une observation de cet "
            "indicateur dans le même pays. La complétude du panel est contrôlée au "
            "moment de l’estimation."
        )
    preferred_controls = {
        "fr": ["de", "be", "nl", "at", "dk", "se", "ch", "no"],
        "gb": ["de", "fr", "nl", "be", "dk", "se", "ch", "no"],
        "us": ["de", "fr", "nl", "be", "dk", "se", "ch", "no"],
        "us-pa": ["us-de", "us-md", "us-nj", "us-ny", "us-oh", "us-wv"],
        "us-wa-king-county": [
            "us-wa-clark-county",
            "us-wa-spokane-county",
            "us-wa-thurston-county",
            "us-wa-whatcom-county",
            "us-wa-yakima-county",
        ],
    }.get(treated_id, [])
    controls_available = control_options["territory_id"].tolist()
    default_controls = [
        territory_id
        for territory_id in preferred_controls
        if territory_id in controls_available
    ]
    if not default_controls and policy_id != "policy-ie-pillar-two":
        default_controls = (
            control_options.sort_values("periods", ascending=False)
            .head(5)["territory_id"]
            .tolist()
        )
    if policy_id == "policy-ie-pillar-two":
        st.info(
            "Aucun témoin n’est présélectionné : choisissez explicitement les pays "
            "de comparaison et vérifiez leur calendrier du Pilier Deux avant d’estimer."
        )
    elif cross_country_comparison:
        st.caption(
            "Les témoins sont des pays choisis parmi les séries LFS Eurostat disponibles. "
            "La comparabilité macroéconomique et l’absence de réformes concomitantes "
            "doivent être justifiées pour l’étude."
        )
    selected_controls = st.multiselect(
        "Territoires témoins (même indicateur)",
        controls_available,
        default=default_controls,
        format_func=lambda value: control_options.loc[
            control_options["territory_id"] == value, "name"
        ].iloc[0],
    )
    result_sources = read_query(
        """
        SELECT s.publisher, s.title, s.url, COUNT(*) AS observations,
               COUNT(DISTINCT i.territory_id) AS territories,
               MIN(i.period_start) AS first_period,
               MAX(i.period_end) AS last_period
        FROM territory_indicators i
        JOIN sources s ON s.source_id = i.source_id
        WHERE i.indicator_code = %s AND i.unit = %s
          AND i.geographic_scope = %s
          AND i.territory_id = ANY(%s)
        GROUP BY s.source_id
        ORDER BY s.publisher, s.title
        """,
        (
            indicator_code,
            unit,
            geographic_scope,
            [treated_id, *selected_controls],
        ),
    )
    with st.expander("Sources des résultats observés"):
        if result_sources.empty:
            st.info("Aucune source associée aux observations sélectionnées.")
        else:
            st.markdown(
                f"Ces sources documentent **{indicator_code}** pour les territoires "
                "sélectionnés. Le volume et les périodes indiqués sont ceux actuellement "
                "présents dans la base."
            )
            st.dataframe(
                result_sources.rename(
                    columns={
                        "publisher": "Éditeur",
                        "title": "Source",
                        "url": "URL",
                        "observations": "Lignes en base",
                        "territories": "Territoires",
                        "first_period": "Première période",
                        "last_period": "Dernière période",
                    }
                ),
                use_container_width=True,
                hide_index=True,
                column_config={"URL": st.column_config.LinkColumn("URL")},
            )

    selected_territory_ids = [treated_id, *selected_controls]
    available_periods = read_query(
        """
        SELECT period_start, COUNT(DISTINCT territory_id) AS territory_count,
               COUNT(*) AS row_count, COUNT(value) AS non_null_values
        FROM territory_indicators
        WHERE indicator_code = %s AND unit = %s AND geographic_scope = %s
          AND territory_id = ANY(%s)
        GROUP BY period_start
        ORDER BY period_start
        """,
        (
            indicator_code,
            unit,
            geographic_scope,
            selected_territory_ids,
        ),
    )
    period_starts = [
        row.period_start
        for row in available_periods.itertuples(index=False)
        if row.period_start is not None
        and row.territory_count == len(selected_territory_ids)
        and row.row_count == len(selected_territory_ids)
        and row.non_null_values == len(selected_territory_ids)
    ]
    pre_periods = [period for period in period_starts if period < adoption_quarter]
    post_periods = [period for period in period_starts if period >= post_quarter]
    if len(pre_periods) < 8 or len(post_periods) < 8:
        st.warning(
            f"Panel commun insuffisant pour ces témoins et ces dates : "
            f"{len(pre_periods)} trimestres avant l’adoption, "
            f"{len(post_periods)} après l’entrée en vigueur ; 8 minimum sont requis "
            "dans chaque période. Les dates ne peuvent pas compenser des données manquantes."
        )
        st.caption(
            "Essayez d’autres territoires témoins, une autre période pertinente pour la "
            "réforme, ou chargez des observations supplémentaires. Les résultats ne sont "
            "pas estimés tant que le panel n’est pas équilibré."
        )
        return

    quarter_options = sorted({*period_starts, adoption_quarter, post_quarter})
    selected_start = st.selectbox(
        "Premier trimestre de l’analyse",
        quarter_options,
        index=quarter_options.index(pre_periods[0]),
        format_func=quarter_label,
    )
    selected_end = st.selectbox(
        "Dernier trimestre de l’analyse",
        quarter_options,
        index=quarter_options.index(post_periods[-1]),
        format_func=quarter_label,
    )
    analysis_transition_quarter = min(adoption_quarter, post_quarter)
    if adoption_quarter > post_quarter:
        st.info(
            "L’entrée en vigueur de cette réforme est rétroactive et précède son adoption "
            "formelle. Pour éviter une transition située après le traitement, le trimestre "
            "d’analyse par défaut est celui de l’entrée en vigueur ; la date légale "
            "d’adoption reste affichée séparément."
        )
    adoption_options = [
        period
        for period in quarter_options
        if sum(candidate < period for candidate in period_starts) >= 8
        and sum(candidate >= post_quarter for candidate in period_starts) >= 8
    ]
    selected_adoption = st.selectbox(
        "Trimestre d’adoption (début de la transition)",
        adoption_options,
        index=adoption_options.index(analysis_transition_quarter)
        if analysis_transition_quarter in adoption_options
        else 0,
        format_func=quarter_label,
    )
    post_options = [
        period
        for period in quarter_options
        if sum(candidate < selected_adoption for candidate in period_starts) >= 8
        and sum(candidate >= period for candidate in period_starts) >= 8
    ]
    if not post_options:
        st.warning("Aucune date de traitement ne conserve 8 périodes avant et après.")
        return
    selected_post = st.selectbox(
        "Trimestre de début du traitement effectif",
        post_options,
        index=post_options.index(post_quarter) if post_quarter in post_options else 0,
        format_func=quarter_label,
    )
    st.caption(
        "Les trimestres entre adoption et traitement effectif sont exclus. "
        "Les autres dates peuvent être modifiées pour tester des variantes ou des placebos."
    )

    if st.button("Estimer la différence-en-différences", type="primary"):
        if len(selected_controls) < 2:
            st.error(
                "Sélectionnez au moins deux territoires témoins. Avec peu de territoires, "
                "l’inférence par erreurs clusterisées reste néanmoins fragile."
            )
            return
        if selected_start >= selected_end:
            st.error("Le début de la période doit précéder sa fin.")
            return
        if selected_adoption > selected_post:
            st.error("L’adoption ne peut pas commencer après le traitement effectif.")
            return

        model_rows = read_query(
            """
            SELECT territory_id, period_start, value
            FROM territory_indicators
            WHERE territory_id = ANY(%s)
              AND indicator_code = %s AND unit = %s
              AND geographic_scope = %s
              AND period_start BETWEEN %s AND %s
            ORDER BY period_start, territory_id
            """,
            (
                [treated_id, *selected_controls],
                indicator_code,
                unit,
                geographic_scope,
                selected_start,
                selected_end,
            ),
        )
        rows = model_rows.to_dict("records")
        try:
            model, frame, pretrend = fit_local_did(
                rows,
                treated_id,
                selected_controls,
                selected_post,
                selected_adoption,
            )
        except (ValueError, ZeroDivisionError) as exc:
            st.error(f"Estimation impossible : {exc}")
            return

        coefficient = float(model.params["treated:post"])
        lower, upper = model.conf_int().loc["treated:post"].tolist()
        effect = 100 * (math.exp(coefficient) - 1)
        effect_low = 100 * (math.exp(lower) - 1)
        effect_high = 100 * (math.exp(upper) - 1)
        p_value = float(model.pvalues["treated:post"])
        result_cols = st.columns(4)
        result_cols[0].metric("Effet DiD estimé", f"{effect:+.2f}%")
        result_cols[1].metric(
            "Intervalle de confiance 95%",
            f"[{effect_low:+.2f}% ; {effect_high:+.2f}%]",
        )
        result_cols[2].metric("p-valeur", f"{p_value:.4f}")
        result_cols[3].metric(
            "Observations",
            f"{len(frame)} ({frame['period'].nunique()} trimestres)",
        )
        if len(selected_controls) + 1 < 10:
            st.warning(
                f"Seulement {len(selected_controls) + 1} territoires (grappes) : "
                "les intervalles et p-valeurs clusterisés sont fragiles."
            )
        if pretrend is None:
            st.info("La pré-tendance différentielle n’a pas pu être estimée.")
        else:
            st.write(
                f"**Diagnostic de pré-tendance :** écart linéaire = "
                f"{pretrend[0]:.6f} par trimestre (p = {pretrend[1]:.4f}). "
                "Une pré-tendance détectable fragilise l’interprétation causale ; "
                "une pré-tendance non significative ne prouve pas l’hypothèse."
            )

        pre_frame = frame[frame["period_start"] < selected_adoption]
        baselines = pre_frame.groupby("treated")["value"].mean()
        if not baselines.empty and (baselines > 0).all():
            trend = (
                frame.groupby(["period_start", "treated"], as_index=False)["value"]
                .mean()
            )
            trend["groupe"] = trend["treated"].map(
                {1: f"Traité — {policy['territory']}", 0: "Témoins (moyenne)"}
            )
            trend["indice_base_100"] = trend.apply(
                lambda row: row["value"] / baselines[row["treated"]] * 100,
                axis=1,
            )
            fig = px.line(
                trend,
                x="period_start",
                y="indice_base_100",
                color="groupe",
                markers=True,
                labels={
                    "period_start": "Trimestre",
                    "indice_base_100": "Indice (moyenne pré-réforme = 100)",
                    "groupe": "Groupe",
                },
            )
            fig.add_shape(
                type="line",
                x0=selected_post,
                x1=selected_post,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(dash="dash", color="#777"),
            )
            fig.add_annotation(
                x=selected_post,
                y=1,
                xref="x",
                yref="paper",
                text="Début effectif",
                showarrow=False,
                yshift=10,
            )
            fig.update_layout(height=430, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Résultat : {indicator_code} ({unit}), traité = {policy['territory']}, "
            f"témoins = {', '.join(control_options.loc[control_options['territory_id'].isin(selected_controls), 'name'])}. "
            "Cette estimation dépend du plan choisi et ne constitue pas à elle seule "
            "une preuve de causalité."
        )


def show_companies(companies):
    st.subheader("Entreprises et expositions")
    if companies.empty:
        st.info("Aucune entreprise enregistrée.")
        return
    st.dataframe(
        companies.rename(
            columns={
                "name": "Entreprise",
                "sector": "Secteur",
                "ticker": "Ticker",
                "country_code": "Pays",
                "headquarters_territory": "Territoire du siège",
                "exposure_count": "Expositions documentées",
                "indicator_count": "Indicateurs d’entreprise",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Une entreprise peut être enregistrée sans indicateur local ou exposition validée ; "
        "les comptes indiquent uniquement les enregistrements disponibles."
    )


st.title("🌍 GLPID — exploration de la base")
st.markdown(
    "Explorez les réformes, territoires, sources et séries économiques. "
    "Les vues sont descriptives : elles ne démontrent pas à elles seules un effet causal."
)

try:
    data = load_metadata()
except (psycopg.Error, RuntimeError, ValueError) as exc:
    st.error(f"Connexion ou lecture de PostgreSQL impossible : {exc}")
    st.info("Vérifiez que PostgreSQL est démarré et que le fichier .env est configuré.")
    st.stop()

territories = data["territories"]
policies_all = data["policies"]
if territories.empty:
    st.warning("La base ne contient encore aucun territoire.")
    st.stop()

st.sidebar.header("Filtres")
countries = ["Tous"] + sorted(
    value for value in territories["country_code"].dropna().unique().tolist() if value
)
selected_country = st.sidebar.selectbox("Pays", countries)
territory_types = ["Tous"] + sorted(
    territories["territory_type"].dropna().unique().tolist()
)
selected_type = st.sidebar.selectbox("Type de territoire", territory_types)

all_dates = policies_all[
    ["announcement_date", "adoption_date", "effective_date", "end_date"]
].stack()
all_dates = pd.to_datetime(all_dates, errors="coerce").dropna()
if all_dates.empty:
    selected_dates = None
else:
    earliest = all_dates.min().date()
    latest = max(date.today(), all_dates.max().date())
    selected_dates = st.sidebar.date_input(
        "Période des politiques",
        value=(earliest, latest),
        min_value=earliest,
        max_value=latest,
    )
    if not isinstance(selected_dates, tuple) or len(selected_dates) != 2:
        selected_dates = None

policies_filtered = apply_shared_filters(
    policies_all, selected_country, selected_type, selected_dates
)
territories_filtered = territories.copy()
if selected_country != "Tous":
    territories_filtered = territories_filtered[
        territories_filtered["country_code"].fillna("") == selected_country
    ]
if selected_type != "Tous":
    territories_filtered = territories_filtered[
        territories_filtered["territory_type"] == selected_type
    ]
sources_filtered = data["sources"]
if selected_country != "Tous":
    policy_source_ids = set(
        policies_filtered.loc[
            policies_filtered["country_code"] == selected_country, "source_id"
        ]
    )
    indicator_sources = read_query(
        """
        SELECT DISTINCT source_id
        FROM territory_indicators
        WHERE territory_id = ANY(%s)
        """,
        (territories_filtered["territory_id"].tolist(),),
    )
    source_ids = policy_source_ids | set(indicator_sources["source_id"].tolist())
    sources_filtered = sources_filtered[
        sources_filtered["source_id"].isin(source_ids)
    ]

tabs = st.tabs(
    [
        "Vue d’ensemble",
        "Politiques",
        "Territoires",
        "Sources et données",
        "Indicateurs",
        "Tester un effet causal",
        "Entreprises",
    ]
)
with tabs[0]:
    show_overview(data, policies_filtered, territories_filtered, sources_filtered)
with tabs[1]:
    show_policies(policies_filtered)
with tabs[2]:
    show_territories(territories_filtered)
with tabs[3]:
    show_sources(sources_filtered, data["source_items"])
with tabs[4]:
    show_indicators(territories_filtered)
with tabs[5]:
    show_causal_test(policies_all, territories)
with tabs[6]:
    show_companies(data["companies"])
