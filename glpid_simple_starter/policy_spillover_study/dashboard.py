import os
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.rows import dict_row

from policy_spillover_study.study import (
    build_country_snapshot,
    build_us_state_snapshot,
    horizon_status,
)


LEVEL_LABELS = {
    "city": "Ville",
    "state": "État",
    "federal": "Fédéral",
    "national": "National",
    "international": "International",
}
EVENT_LABELS = {
    "introduced": "Déposé",
    "proposed": "Proposé",
    "adopted": "Adopté",
    "effective": "Entré en vigueur",
    "vetoed": "Vetoé",
    "withdrawn": "Retiré",
}
RELATION_LABELS = {
    "same_family": "Même famille",
    "partial_analogue": "Analogue partiel",
    "successor": "Texte successeur",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="GLPID — diffusion réglementaire",
    page_icon="📜",
    layout="wide",
)


def connect_read_only():
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
        row_factory=dict_row,
    )


@st.cache_data(ttl=60)
def load_data():
    with connect_read_only() as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            cases = pd.DataFrame(
                conn.execute(
                    """
                    SELECT c.case_id, c.origin_territory_id, origin.territory_type AS origin_territory_type,
                           c.policy_family, c.title, c.anchor_policy_title,
                           c.anchor_date, c.anchor_event_type, c.target_level,
                           c.gdelt_query, c.scope_note, origin.name AS origin_jurisdiction
                    FROM policy_diffusion_cases c
                    JOIN territories origin ON origin.territory_id = c.origin_territory_id
                    ORDER BY c.policy_family
                    """
                ).fetchall(),
                columns=[
                    "case_id",
                    "origin_territory_id",
                    "origin_territory_type",
                    "policy_family",
                    "title",
                    "anchor_policy_title",
                    "anchor_date",
                    "anchor_event_type",
                    "target_level",
                    "gdelt_query",
                    "scope_note",
                    "origin_jurisdiction",
                ],
            )
            events = pd.DataFrame(
                conn.execute(
                    """
                    SELECT e.event_id, e.case_id, e.territory_id, e.event_date,
                           e.event_level, e.event_type,
                           e.relationship, e.policy_title, e.source_id, t.name AS jurisdiction,
                           t.territory_type, t.country_code,
                           e.source_page, e.notes
                    FROM policy_diffusion_events e
                    JOIN territories t ON t.territory_id = e.territory_id
                    ORDER BY e.case_id, e.event_date, e.event_id
                    """
                ).fetchall(),
                columns=[
                    "event_id",
                    "case_id",
                    "territory_id",
                    "event_date",
                    "event_level",
                    "event_type",
                    "relationship",
                    "policy_title",
                    "source_id",
                    "jurisdiction",
                    "territory_type",
                    "country_code",
                    "source_page",
                    "notes",
                ],
            )
            attention = pd.DataFrame(
                conn.execute(
                    """
                    SELECT policy_family, month_start, article_count, query_text, source_page
                    FROM policy_diffusion_attention
                    ORDER BY policy_family, month_start
                    """
                ).fetchall(),
                columns=[
                    "policy_family",
                    "month_start",
                    "article_count",
                    "query_text",
                    "source_page",
                ],
            )
            source_checks = pd.DataFrame(
                conn.execute(
                    """
                    SELECT s.source_id, s.publisher, s.title, s.url,
                           check_result.checked_at, check_result.http_status,
                           check_result.page_title, check_result.meta_description,
                           check_result.content_sha256, check_result.error_text
                    FROM sources s
                    JOIN (
                        SELECT DISTINCT source_id
                        FROM policy_diffusion_events
                    ) used ON used.source_id = s.source_id
                    LEFT JOIN LATERAL (
                        SELECT checked_at, http_status, page_title, meta_description,
                               content_sha256, error_text
                        FROM policy_diffusion_source_checks c
                        WHERE c.source_id = s.source_id
                        ORDER BY c.checked_at DESC
                        LIMIT 1
                    ) check_result ON TRUE
                    ORDER BY s.publisher, s.title
                    """
                ).fetchall(),
                columns=[
                    "source_id",
                    "publisher",
                    "title",
                    "url",
                    "checked_at",
                    "http_status",
                    "page_title",
                    "meta_description",
                    "content_sha256",
                    "error_text",
                ],
            )
            glpid_counts = pd.DataFrame(
                conn.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM territories) AS territoires,
                        (SELECT COUNT(*) FROM sources) AS sources,
                        (SELECT COUNT(*) FROM policy_changes) AS politiques,
                        (SELECT COUNT(*) FROM territory_indicators) AS indicateurs_territoriaux,
                        (SELECT COUNT(*) FROM companies) AS entreprises,
                        (SELECT COUNT(*) FROM company_indicators) AS indicateurs_entreprises
                    """
                ).fetchall()
            )
            glpid_policies = pd.DataFrame(
                conn.execute(
                    """
                    SELECT p.title AS politique, t.name AS territoire, p.status AS statut,
                           p.adoption_date AS adoption, p.effective_date AS entrée_en_vigueur
                    FROM policy_changes p
                    JOIN territories t ON t.territory_id = p.territory_id
                    ORDER BY p.effective_date NULLS LAST, p.title
                    """
                ).fetchall()
            )
    return cases, events, attention, glpid_counts, glpid_policies, source_checks


st.title("Diffusion des politiques publiques")
st.caption(
    "Étude exploratoire GLPID — fiscalité, réglementation économique, transparence salariale, "
    "droit à la réparation, confidentialité des données et sécurité de l’IA"
)
if st.button("Actualiser les données depuis PostgreSQL"):
    load_data.clear()
    st.rerun()

try:
    cases, events, attention, glpid_counts, glpid_policies, source_checks = load_data()
except (psycopg.Error, RuntimeError) as exc:
    st.error(f"Connexion ou lecture de la base impossible : {exc}")
    st.info(
        "Vérifiez .env, puis exécutez la migration "
        "`policy_spillover_study\\sql\\003_policy_diffusion.sql` et "
        "`policy_spillover_study\\scripts\\seed_study.py` depuis glpid_simple_starter."
    )
    st.stop()

if cases.empty:
    st.warning("Aucun cas chargé. Exécutez policy_spillover_study\\scripts\\seed_study.py.")
    st.stop()

st.warning(
    f"{len(cases)} cas sélectionnés dans {cases['policy_family'].nunique()} familles constituent "
    "un échantillon descriptif non représentatif, trop petit pour entraîner ou valider un "
    "modèle prédictif. Plusieurs cas partagent les mêmes lois et ne sont donc pas indépendants. "
    "Les volumes GDELT sont un proxy d’attention médiatique ; ils ne démontrent ni soutien "
    "public ni causalité."
)

with st.expander("Vue rapide de la base GLPID"):
    st.dataframe(glpid_counts, use_container_width=True, hide_index=True)
    st.caption("Le nombre d’indicateurs d’entreprise est affiché séparément : il ne doit pas être confondu avec les indicateurs territoriaux agrégés.")
    st.dataframe(glpid_policies, use_container_width=True, hide_index=True)

as_of = pd.Timestamp.now().date()
case_events = {
    case_id: group.to_dict("records")
    for case_id, group in events.groupby("case_id")
} if not events.empty else {}
summary_rows = []
for case in cases.to_dict("records"):
    related_events = case_events.get(case["case_id"], [])
    for horizon in (12, 36):
        result = horizon_status(case, related_events, horizon, as_of)
        summary_rows.append(
            {
                "Famille": case["policy_family"],
                "Ancre": case["anchor_policy_title"],
                "Juridiction d’origine": case["origin_jurisdiction"],
                "Échéance": f"{horizon} mois",
                "Cible": LEVEL_LABELS.get(case["target_level"], case["target_level"]),
                "Adoption dans la fenêtre": result["status"],
                "Séquence stricte": result["strict_status"],
                "Adoptions documentées": len(result["adoptions"]),
                "Adoptions après proposition postérieure": len(result["strict_adoptions"]),
                "Fin de fenêtre": result["horizon_end"],
            }
        )

adopted_count = (
    int((events["event_type"] == "adopted").sum()) if not events.empty else 0
)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Cas d’origine", len(cases))
col2.metric("Lignes de chronologie sourcées", len(events))
col3.metric("Lignes codées « adopté »", adopted_count)
col4.metric("Observations GDELT", len(attention))

st.subheader("Fenêtres d’observation")
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
strict_results = {
    horizon: [
        row
        for row in summary_rows
        if row["Échéance"] == f"{horizon} mois"
        and row["Séquence stricte"] != "Fenêtre en cours"
    ]
    for horizon in (12, 36)
}
col1, col2 = st.columns(2)
for column, horizon in zip((col1, col2), (12, 36)):
    rows = strict_results[horizon]
    positive = sum(row["Adoptions après proposition postérieure"] > 0 for row in rows)
    column.metric(
        f"Proposition ultérieure puis adoption — {horizon} mois",
        f"{positive} / {len(rows)} fenêtres observables",
    )
st.caption(
    "Cette règle temporelle stricte exige une proposition au niveau cible après l’ancre, "
    "puis une adoption dans la fenêtre. Elle écarte les initiatives déjà engagées, sans "
    "pour autant prouver un lien causal."
)
st.caption(
    "« Aucune adoption enregistrée » signifie qu’aucune adoption admissible n’est présente "
    "dans cette chronologie, pas qu’aucune politique comparable n’existe."
)

st.subheader("Propagation géographique — monde")
st.caption(
    "Chronologies internationales incluant des lois nationales. Les pays non colorés ne sont "
    "pas documentés dans le cas sélectionné; ils ne sont pas réputés dépourvus de loi."
)
country_case_ids = {
    case_id
    for case_id, case_events_for_map in case_events.items()
    if any(
        event.get("territory_type") == "country"
        and event.get("event_level") == "national"
        for event in case_events_for_map
    )
}
country_cases = cases.loc[
    (cases["origin_territory_type"] == "country")
    & cases["case_id"].isin(country_case_ids)
]
if country_cases.empty:
    st.info("Aucune séquence de politiques nationales n’est documentée pour la carte mondiale.")
else:
    country_case_names = dict(zip(country_cases["case_id"], country_cases["title"]))
    country_case_options = sorted(
        country_case_names,
        key=lambda case_id: (
            -sum(
                event.get("territory_type") == "country"
                and event.get("event_level") == "national"
                for event in case_events[case_id]
            ),
            country_case_names[case_id],
        ),
    )
    country_case_id = st.selectbox(
        "Cas d’ancrage de la carte mondiale",
        country_case_options,
        format_func=country_case_names.get,
        key="world_map_case_id",
    )
    country_case = country_cases.loc[country_cases["case_id"] == country_case_id].iloc[0].to_dict()
    country_events = case_events.get(country_case_id, [])
    dated_country_events = [
        event
        for event in country_events
        if event.get("territory_type") == "country"
        and event.get("event_level") == "national"
        and event.get("event_date") is not None
    ]
    first_country_year = country_case["anchor_date"].year
    last_country_year = max(
        [first_country_year] + [event["event_date"].year for event in dated_country_events]
    )
    if first_country_year == last_country_year:
        country_year = first_country_year
        st.caption(f"Une seule année est documentée pour ce cas : {country_year}.")
    else:
        country_year = st.slider(
            "Année d’observation — carte mondiale",
            min_value=first_country_year,
            max_value=last_country_year,
            value=last_country_year,
            key="world_map_year",
        )
    country_snapshot = pd.DataFrame(
        build_country_snapshot(
            country_events,
            country_case["origin_territory_id"],
            country_case["anchor_date"],
            pd.Timestamp(year=country_year, month=12, day=31).date(),
        )
    )
    country_map1, country_map2, country_map3 = st.columns(3)
    country_map1.metric("Point d’ancrage", country_case["origin_jurisdiction"])
    country_map2.metric(
        "Lois nationales documentées",
        int((country_snapshot["status"] == "Loi adoptée").sum()),
    )
    country_map3.metric(
        "Adoptions analogues",
        int((country_snapshot["status"] == "Adoption analogue").sum()),
    )
    world_figure = px.choropleth(
        country_snapshot,
        locations="country",
        locationmode="country names",
        color="status",
        scope="world",
        hover_name="country",
        hover_data={
            "territory_id": False,
            "country_code": False,
            "status": True,
            "event_date": True,
            "policy_title": True,
        },
        color_discrete_map={
            "Point d’ancrage": "#d62728",
            "Événement ultérieur": "#9ca3af",
            "Projet documenté": "#f2c14e",
            "Loi adoptée": "#2ca02c",
            "Adoption analogue": "#9467bd",
            "En vigueur": "#1f77b4",
            "Non documenté dans le pilote": "#e5e7eb",
        },
    )
    world_figure.update_layout(
        height=520,
        margin={"r": 0, "t": 20, "l": 0, "b": 0},
        legend_title_text="Dans la chronologie",
    )
    st.plotly_chart(world_figure, use_container_width=True)
    st.caption(
        "Les lois nationales comparées peuvent différer par leur champ et leur calendrier. "
        "Les jalons postérieurs à l’année choisie sont grisés; une succession temporelle ou "
        "une analogie ne démontre pas une influence causale."
    )

st.subheader("Propagation géographique — États-Unis")
st.caption(
    "Carte temporelle des cas dont la cible est un État américain. Le curseur affiche "
    "l’état de la chronologie à la fin de chaque année."
)
state_case_ids = {
    case_id
    for case_id, case_events_for_map in case_events.items()
    if any(event["event_level"] == "state" for event in case_events_for_map)
}
state_cases = cases.loc[
    (cases["target_level"] == "state") & cases["case_id"].isin(state_case_ids)
]
if state_cases.empty:
    st.info("Aucun cas de diffusion entre États américains n’est documenté.")
else:
    state_case_names = dict(zip(state_cases["case_id"], state_cases["title"]))
    map_case_id = st.selectbox(
        "Cas d’ancrage de la carte",
        list(state_case_names),
        format_func=state_case_names.get,
        key="map_case_id",
    )
    map_case = state_cases.loc[state_cases["case_id"] == map_case_id].iloc[0].to_dict()
    map_events = case_events.get(map_case_id, [])
    dated_state_events = [
        event
        for event in map_events
        if event["event_level"] == "state" and event["event_date"] is not None
    ]
    first_year = map_case["anchor_date"].year
    last_year = max(
        [first_year] + [event["event_date"].year for event in dated_state_events]
    )
    if first_year == last_year:
        map_year = first_year
        st.caption(f"Une seule année est documentée pour ce cas : {map_year}.")
    else:
        map_year = st.slider(
            "Année d’observation",
            min_value=first_year,
            max_value=last_year,
            value=last_year,
            key="map_year",
        )
    snapshot = pd.DataFrame(
        build_us_state_snapshot(
            map_events,
            map_case["origin_territory_id"],
            map_case["anchor_date"],
            pd.Timestamp(year=map_year, month=12, day=31).date(),
        )
    )
    map_col1, map_col2, map_col3 = st.columns(3)
    map_col1.metric(
        "Point d’ancrage",
        map_case["origin_jurisdiction"],
    )
    map_col2.metric("États avec adoption documentée", int((snapshot["status"] == "Loi adoptée").sum()))
    map_col3.metric("Projets documentés", int((snapshot["status"] == "Projet documenté").sum()))
    figure = px.choropleth(
        snapshot,
        locations="abbreviation",
        locationmode="USA-states",
        color="status",
        scope="usa",
        hover_name="state",
        hover_data={
            "abbreviation": False,
            "status": True,
            "event_date": True,
            "policy_title": True,
        },
        color_discrete_map={
            "Non documenté dans le pilote": "#e5e7eb",
            "Point d’ancrage": "#d62728",
            "Projet documenté": "#f2c14e",
            "Loi adoptée": "#2ca02c",
            "En vigueur": "#1f77b4",
            "Vetoé": "#9467bd",
            "Retiré": "#7f7f7f",
            "Projet déposé": "#ff9f1c",
        },
        category_orders={
            "status": [
                "Non documenté dans le pilote",
                "Point d’ancrage",
                "Projet déposé",
                "Projet documenté",
                "Loi adoptée",
                "En vigueur",
                "Vetoé",
                "Retiré",
            ]
        },
        labels={
            "status": "Étape documentée",
            "event_date": "Date",
            "policy_title": "Texte",
        },
        title=f"{map_case['anchor_policy_title']} — situation au 31 décembre {map_year}",
    )
    figure.update_geos(showlakes=True, lakecolor="white", bgcolor="rgba(0,0,0,0)")
    figure.update_layout(legend_title_text="Dans la chronologie")
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "« Non documenté dans le pilote » ne signifie pas qu’aucune loi n’existe dans cet "
        "État. La carte ne représente que les textes vérifiés et reliés à ce cas; l’ordre "
        "temporel ne démontre ni influence ni causalité."
    )

st.subheader("Explorer un cas")
case_names = dict(zip(cases["case_id"], cases["title"]))
selected_case_id = st.selectbox("Cas d’origine", list(case_names), format_func=case_names.get)
selected_case = cases.loc[cases["case_id"] == selected_case_id].iloc[0].to_dict()
selected_events = events.loc[events["case_id"] == selected_case_id].copy()
selected_attention = attention.loc[
    attention["policy_family"] == selected_case["policy_family"]
].copy()
st.markdown(
    f"**Point de départ :** {selected_case['anchor_policy_title']} — "
    f"{selected_case['origin_jurisdiction']} ({selected_case['anchor_date']}, "
    f"{EVENT_LABELS.get(selected_case['anchor_event_type'], selected_case['anchor_event_type'])}). "
    f"**Niveau cible :** "
    f"{LEVEL_LABELS.get(selected_case['target_level'], selected_case['target_level'])}."
)
st.write(selected_case["scope_note"])

if selected_attention.empty:
    if attention.empty:
        st.info(
            "Aucune série GDELT n’est encore chargée. Depuis le dossier "
            "glpid_simple_starter, exécutez "
            "`python policy_spillover_study\\scripts\\fetch_attention.py`."
        )
    else:
        total_rows = len(attention)
        loaded_families = ", ".join(sorted(attention["policy_family"].unique()))
        st.info(
            f"Aucune série GDELT n’est chargée pour « {selected_case['policy_family']} ». "
            f"La base contient {total_rows} observation(s) pour : {loaded_families}. "
            "Choisissez un cas d’une famille collectée pour afficher sa série."
        )
else:
    selected_attention["month_start"] = pd.to_datetime(selected_attention["month_start"])
    figure = px.line(
        selected_attention,
        x="month_start",
        y="article_count",
        markers=True,
        labels={"month_start": "Mois", "article_count": "Articles correspondants"},
        title="Attention médiatique mensuelle — volume GDELT brut",
    )
    if not selected_events.empty:
        for event in selected_events.to_dict("records"):
            figure.add_vline(
                x=pd.Timestamp(event["event_date"]),
                line_dash="dot",
                opacity=0.45,
                annotation_text=f"{event['jurisdiction']} — {event['event_type']}",
                annotation_position="top",
            )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Les termes de recherche sont fixes pour chaque cas. Le volume dépend du choix des "
        "termes et de la couverture GDELT ; il ne mesure pas directement la visibilité sociétale."
    )

st.subheader("Chronologie législative et sources")
if selected_events.empty:
    st.info("Aucun événement législatif n’est chargé pour ce cas.")
else:
    selected_events["event_level"] = selected_events["event_level"].map(
        lambda value: LEVEL_LABELS.get(value, value)
    )
    selected_events["event_type"] = selected_events["event_type"].map(
        lambda value: EVENT_LABELS.get(value, value)
    )
    selected_events["relationship"] = selected_events["relationship"].map(
        lambda value: RELATION_LABELS.get(value, value)
    )
    display_events = selected_events.rename(
        columns={
            "event_date": "Date",
            "jurisdiction": "Juridiction",
            "event_level": "Niveau",
            "event_type": "Étape",
            "relationship": "Lien avec le cas",
            "policy_title": "Texte",
            "notes": "Notes et limites",
            "source_page": "Source officielle",
        }
    )[
        [
            "Date",
            "Juridiction",
            "Niveau",
            "Étape",
            "Lien avec le cas",
            "Texte",
            "Notes et limites",
            "Source officielle",
        ]
    ]
    st.dataframe(
        display_events,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source officielle": st.column_config.LinkColumn(
                "Source officielle", display_text="Ouvrir"
            )
        },
    )

with st.expander("État de vérification des sources officielles"):
    case_source_ids = set(
        events.loc[events["case_id"] == selected_case_id, "source_id"].tolist()
    )
    selected_sources = source_checks.loc[
        source_checks["source_id"].isin(case_source_ids)
    ].copy()
    if selected_sources.empty:
        st.info("Aucune source associée à ce cas.")
    elif selected_sources["checked_at"].isna().all():
        st.info(
            "Les URL sont enregistrées, mais leur récupération HTTP n’a pas encore été vérifiée. "
            "Lancez `policy_spillover_study\\scripts\\verify_sources.py`."
        )
    else:
        selected_sources["État HTTP"] = selected_sources["http_status"].fillna(
            "Échec de connexion"
        )
        selected_sources["Vérifiée le"] = selected_sources["checked_at"]
        selected_sources["Titre récupéré"] = selected_sources["page_title"]
        selected_sources["Erreur"] = selected_sources["error_text"]
        st.dataframe(
            selected_sources[
                ["publisher", "title", "url", "Vérifiée le", "État HTTP", "Titre récupéré", "Erreur"]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("URL officielle", display_text="Ouvrir")
            },
        )

with st.expander("Requête GDELT utilisée"):
    st.code(selected_case["gdelt_query"])
