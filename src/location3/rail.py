"""Validate and merge cited, shortlist-only London rail research."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .orr import performance_for, validate_performance
from .fields import http_url, iso_date, iso_datetime, nonempty, nonnegative_number
from .validation import validate_basis, validate_evidence


COMPONENT_FIELDS = (
    "access_minutes",
    "expected_wait_minutes",
    "scheduled_rail_minutes",
    "london_last_mile_minutes",
)


def merge_rail_research(
    evidence: dict[str, Any],
    rail_research: dict[str, Any],
    *,
    destination_labels: Iterable[str] | None = None,
    performance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return evidence enriched by cited rail facts for existing candidates only.

    When the run profile names destinations, every journey must be for one of them
    so a journey cannot quietly describe a place the user never asked about. When an
    ORR performance file is supplied, journeys that name their operator take their
    punctuality and cancellation figures from it as measured evidence.
    """
    validate_evidence(evidence)
    candidate_ids = {candidate["id"] for candidate in evidence["candidates"]}
    validate_rail_research(rail_research, candidate_ids)
    if performance is not None:
        validate_performance(performance)
        rail_research = apply_performance(rail_research, performance)
        validate_rail_research(rail_research, candidate_ids)
    allowed = {label.casefold() for label in destination_labels or ()}
    if allowed:
        for journey in rail_research["journeys"]:
            if journey["destination_label"].casefold() not in allowed:
                raise ValueError(
                    f"rail journey destination is not in the run profile: "
                    f"{journey['destination_label']}"
                )

    merged = deepcopy(evidence)
    journeys = deepcopy(rail_research["journeys"])
    researched_candidates = {journey["candidate_id"] for journey in journeys}
    merged["observations"] = [
        observation
        for observation in merged["observations"]
        if not (
            observation["candidate_id"] in researched_candidates
            and observation["metric"] == "door_to_door_commute"
        )
    ]
    for journey in journeys:
        if journey["primary"]:
            merged["observations"].append(_commute_observation(journey))
    merged["rail_journeys"] = journeys
    validate_evidence(merged)
    return merged


def apply_performance(
    rail_research: dict[str, Any], performance: dict[str, Any]
) -> dict[str, Any]:
    """Fill reliability from ORR for journeys that name an operator; measured wins."""
    updated = deepcopy(rail_research)
    punctuality_source = next(
        source for source in performance["sources"] if source["kind"] == "punctuality"
    )
    cancellations_source = next(
        source for source in performance["sources"] if source["kind"] == "cancellations"
    )
    for journey in updated["journeys"]:
        operator = journey.get("operator")
        if operator is None:
            continue
        record = performance_for(performance, operator)
        journey["operator"] = record["operator"]
        journey["punctuality_percent"] = record["punctuality_time_to_3_annual_percent"]
        journey["cancellation_percent"] = record["cancellations_annual_percent"]
        journey["sources"] = [
            source for source in journey["sources"] if source["kind"] != "performance"
        ] + [{
            "kind": "performance",
            "label": (
                f"{punctuality_source['label']} and {cancellations_source['label']}, "
                f"moving annual average, {record['period']}"
            ),
            "url": punctuality_source["url"],
            "retrieved_at": performance["retrieved_at"],
            "source_date": performance["source_date"],
            "licence": performance["licence"],
        }]
        note = (
            f"Reliability: ORR moving annual average for {record['operator']}, "
            f"{record['period']} (measured); replaces any input reliability figures."
        )
        if note not in journey["confidence_notes"]:
            journey["confidence_notes"] = f"{journey['confidence_notes'].rstrip()} {note}"
    return updated


def validate_rail_research(
    rail_research: dict[str, Any], allowed_candidate_ids: set[str]
) -> None:
    if rail_research.get("schema_version") != "1":
        raise ValueError("unsupported rail research schema_version")
    nonempty(rail_research, "provider")
    journeys = rail_research.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        raise ValueError("rail research journeys must be a non-empty array")

    journey_ids: set[str] = set()
    primary_counts: dict[str, int] = {}
    destinations: set[tuple[str, str]] = set()
    for journey in journeys:
        if not isinstance(journey, dict):
            raise ValueError("rail journeys must be objects")
        journey_id = nonempty(journey, "id")
        if journey_id in journey_ids:
            raise ValueError(f"duplicate rail journey id: {journey_id}")
        journey_ids.add(journey_id)
        candidate_id = nonempty(journey, "candidate_id")
        if candidate_id not in allowed_candidate_ids:
            raise ValueError("rail journey is outside the candidate shortlist")
        destination = nonempty(journey, "destination_label")
        destination_key = (candidate_id, destination.casefold())
        if destination_key in destinations:
            raise ValueError("duplicate rail journey destination for candidate")
        destinations.add(destination_key)

        for field in (
            "origin_station", "origin_station_crs", "london_arrival_station",
            "service_window", "confidence_notes",
        ):
            nonempty(journey, field)
        if "operator" in journey:
            nonempty(journey, "operator")
        crs = journey["origin_station_crs"]
        if len(crs) != 3 or not crs.isascii() or not crs.isalpha() or crs != crs.upper():
            raise ValueError("origin_station_crs must be a three-letter uppercase CRS code")
        if not isinstance(journey.get("primary"), bool):
            raise ValueError("rail journey primary must be boolean")
        primary_counts[candidate_id] = primary_counts.get(candidate_id, 0) + int(
            journey["primary"]
        )

        for field in (*COMPONENT_FIELDS, "total_minutes", "services_per_hour"):
            nonnegative_number(journey, field)
        changes = journey.get("changes")
        if not isinstance(changes, int) or isinstance(changes, bool) or changes < 0:
            raise ValueError("rail journey changes must be a non-negative integer")
        component_total = sum(float(journey[field]) for field in COMPONENT_FIELDS)
        if abs(component_total - float(journey["total_minutes"])) > 0.01:
            raise ValueError("rail journey component times must equal total_minutes")

        last_departure = journey.get("last_useful_departure")
        if last_departure is not None:
            iso_datetime(last_departure, "last_useful_departure")
        for field in ("punctuality_percent", "cancellation_percent"):
            value = journey.get(field)
            if value is not None and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 100
            ):
                raise ValueError(f"{field} must be null or between 0 and 100")
        confidence = journey.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("rail journey confidence must be between 0 and 1")
        validate_basis(journey, float(confidence), "rail journey")
        source_kinds = _validate_sources(journey.get("sources"))
        if (
            journey["punctuality_percent"] is not None
            or journey["cancellation_percent"] is not None
        ) and "performance" not in source_kinds:
            raise ValueError("rail reliability values require a performance source")

    if any(count != 1 for count in primary_counts.values()):
        raise ValueError("each researched candidate must have exactly one primary rail journey")


def _commute_observation(journey: dict[str, Any]) -> dict[str, Any]:
    timetable = next(
        source for source in journey["sources"] if source["kind"] == "timetable"
    )
    return {
        "id": f"{journey['id']}-commute",
        "candidate_id": journey["candidate_id"],
        "metric": "door_to_door_commute",
        "value": journey["total_minutes"],
        "unit": "minutes",
        "geographic_scope": (
            f"{journey['origin_station']} to {journey['destination_label']}"
        ),
        "source": timetable["label"],
        "source_url": timetable["url"],
        "retrieved_at": timetable["retrieved_at"],
        "source_date": timetable["source_date"],
        "transformation": (
            "Door-to-door total = station access + expected wait + scheduled rail "
            "+ London last mile; imported from cited shortlist research"
        ),
        "licence": timetable["licence"],
        "confidence": journey["confidence"],
        "confidence_notes": journey["confidence_notes"],
        "basis": journey["basis"],
    }


def _validate_sources(value: Any) -> set[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("rail journey sources must be a non-empty array")
    kinds: set[str] = set()
    for source in value:
        if not isinstance(source, dict):
            raise ValueError("rail journey sources must be objects")
        kind = nonempty(source, "kind")
        if kind in kinds:
            raise ValueError(f"duplicate rail source kind: {kind}")
        kinds.add(kind)
        for field in ("label", "licence"):
            nonempty(source, field)
        http_url(nonempty(source, "url"), "rail source url")
        retrieved_at = iso_datetime(nonempty(source, "retrieved_at"), "retrieved_at")
        source_date = iso_date(nonempty(source, "source_date"), "rail source_date")
        if source_date > retrieved_at.date():
            raise ValueError("rail source_date cannot be later than retrieved_at")
    if "timetable" not in kinds:
        raise ValueError("rail journey requires a timetable source")
    return kinds
