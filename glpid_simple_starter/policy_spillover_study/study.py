import calendar
from datetime import date
import math


US_STATES = (
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
)


def month_range(start, end):
    current = date(start.year, start.month, 1)
    while current <= end:
        yield current
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def parse_timeline(payload):
    timeline = payload.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        raise ValueError("GDELT n’a retourné aucune série chronologique.")
    series = next(
        (item for item in timeline if item.get("series", "").lower() == "article count"),
        timeline[0] if len(timeline) == 1 else None,
    )
    if series is None or not isinstance(series.get("data"), list) or not series["data"]:
        raise ValueError("La réponse GDELT ne contient pas une série unique d’articles.")

    counts = {}
    for point in series["data"]:
        point_date = date.fromisoformat(
            f"{point['date'][:4]}-{point['date'][4:6]}-{point['date'][6:8]}"
        )
        value = float(point["value"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("GDELT a renvoyé un volume d’articles invalide.")
        month = date(point_date.year, point_date.month, 1)
        counts[month] = counts.get(month, 0) + int(value)
    return counts


def add_months(value, months):
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero_based = divmod(month_index, 12)
    month = month_zero_based + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_us_state_snapshot(events, anchor_territory_id, anchor_date, as_of):
    states = {
        f"us-{abbreviation.lower()}": {
            "abbreviation": abbreviation,
            "state": state_name,
            "status": "Non documenté dans le pilote",
            "event_date": None,
            "policy_title": None,
        }
        for abbreviation, state_name in US_STATES
    }

    if as_of >= anchor_date and anchor_territory_id in states:
        anchor = states[anchor_territory_id]
        anchor.update(
            status="Point d’ancrage",
            event_date=anchor_date,
            policy_title="Point d’ancrage de l’étude",
        )

    ordered_events = sorted(
        (
            event
            for event in events
            if event.get("territory_id") in states
            and event.get("event_level") == "state"
            and event.get("relationship") in ("same_family", "successor")
            and event.get("event_date") is not None
            and anchor_date < event["event_date"] <= as_of
        ),
        key=lambda event: (event["event_date"], event.get("event_id", "")),
    )
    for event in ordered_events:
        state = states[event["territory_id"]]
        if state["status"] == "Point d’ancrage":
            continue
        if state["event_date"] is not None and state["event_date"] > event["event_date"]:
            continue
        status = {
            "proposed": "Projet documenté",
            "adopted": "Loi adoptée",
            "effective": "En vigueur",
            "vetoed": "Vetoé",
            "withdrawn": "Retiré",
            "introduced": "Projet déposé",
        }.get(event["event_type"], "Événement documenté")
        state.update(
            status=status,
            event_date=event["event_date"],
            policy_title=event.get("policy_title"),
        )

    return list(states.values())


def build_country_snapshot(events, anchor_territory_id, anchor_date, as_of):
    countries = {}
    for event in events:
        if event.get("territory_type") != "country":
            continue
        territory_id = event.get("territory_id")
        if territory_id not in countries:
            countries[territory_id] = {
                "territory_id": territory_id,
                "country": event.get("jurisdiction"),
                "country_code": event.get("country_code"),
                "status": "Non documenté dans le pilote",
                "event_date": None,
                "policy_title": None,
            }

    anchor = countries.get(anchor_territory_id)
    if as_of >= anchor_date and anchor is not None:
        anchor.update(
            status="Point d’ancrage",
            event_date=anchor_date,
            policy_title="Point d’ancrage de l’étude",
        )

    for event in events:
        if (
            event.get("territory_type") == "country"
            and event.get("event_level") == "national"
            and event.get("territory_id") in countries
            and event.get("event_date") is not None
            and event["event_date"] > as_of
        ):
            country = countries[event["territory_id"]]
            if country["event_date"] is None or country["event_date"] > event["event_date"]:
                country.update(
                    status="Événement ultérieur",
                    event_date=event["event_date"],
                    policy_title=event.get("policy_title"),
                )

    ordered_events = sorted(
        (
            event
            for event in events
            if event.get("territory_type") == "country"
            and event.get("territory_id") in countries
            and event.get("event_level") == "national"
            and event.get("relationship") in ("same_family", "partial_analogue", "successor")
            and event.get("event_date") is not None
            and anchor_date < event["event_date"] <= as_of
        ),
        key=lambda event: (event["event_date"], event.get("event_id", "")),
    )
    for event in ordered_events:
        country = countries[event["territory_id"]]
        if country["status"] == "Point d’ancrage":
            continue
        if (
            country["event_date"] is not None
            and country["status"] != "Événement ultérieur"
            and country["event_date"] > event["event_date"]
        ):
            continue
        status = {
            "proposed": "Projet documenté",
            "adopted": "Adoption analogue" if event["relationship"] == "partial_analogue" else "Loi adoptée",
            "effective": "En vigueur",
            "vetoed": "Vetoé",
            "withdrawn": "Retiré",
            "introduced": "Projet déposé",
        }.get(event["event_type"], "Événement documenté")
        country.update(
            status=status,
            event_date=event["event_date"],
            policy_title=event.get("policy_title"),
        )

    return list(countries.values())


def horizon_status(case, events, horizon_months, as_of):
    horizon_end = add_months(case["anchor_date"], horizon_months)
    eligible_events = [
        event
        for event in events
        if event["relationship"] in ("same_family", "successor")
        and (
            event["event_level"] == case["target_level"]
            or (case["target_level"] == "international" and event["event_level"] == "national")
        )
        and case["anchor_date"] < event["event_date"] <= min(horizon_end, as_of)
    ]
    adoptions = [event for event in eligible_events if event["event_type"] == "adopted"]
    proposals = [event for event in eligible_events if event["event_type"] == "proposed"]
    strict_adoptions = [
        adoption
        for adoption in adoptions
        if any(proposal["event_date"] <= adoption["event_date"] for proposal in proposals)
    ]

    if as_of < horizon_end:
        status = "Fenêtre en cours"
        strict_status = "Fenêtre en cours"
    else:
        status = "Adoption documentée" if adoptions else "Aucune adoption enregistrée"
        if strict_adoptions:
            strict_status = "Adoption après proposition postérieure"
        elif proposals:
            strict_status = "Proposition postérieure, sans adoption dans la fenêtre"
        elif adoptions:
            strict_status = "Adoption après une proposition antérieure"
        else:
            strict_status = "Aucune adoption équivalente documentée"
    return {
        "horizon_end": horizon_end,
        "status": status,
        "adoptions": adoptions,
        "proposals": proposals,
        "strict_status": strict_status,
        "strict_adoptions": strict_adoptions,
    }
