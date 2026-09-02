"""Validate and merge cited, shortlist-only London rail research."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit

from .validation import validate_evidence


COMPONENT_FIELDS = (
    "access_minutes",
    "expected_wait_minutes",
    "scheduled_rail_minutes",
    "london_last_mile_minutes",
)


def merge_rail_research(
    evidence: dict[str, Any], rail_research: dict[str, Any]
) -> dict[str, Any]:
    """Return evidence enriched by cited rail facts for existing candidates only."""
    validate_evidence(evidence)
    candidate_ids = {candidate["id"] for candidate in evidence["candidates"]}
    validate_rail_research(rail_research, candidate_ids)

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


def validate_rail_research(
    rail_research: dict[str, Any], allowed_candidate_ids: set[str]
) -> None:
    if rail_research.get("schema_version") != "1":
        raise ValueError("unsupported rail research schema_version")
    _nonempty(rail_research, "provider")
    journeys = rail_research.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        raise ValueError("rail research journeys must be a non-empty array")

    journey_ids: set[str] = set()
    primary_counts: dict[str, int] = {}
    destinations: set[tuple[str, str]] = set()
    for journey in journeys:
        if not isinstance(journey, dict):
            raise ValueError("rail journeys must be objects")
        journey_id = _nonempty(journey, "id")
        if journey_id in journey_ids:
            raise ValueError(f"duplicate rail journey id: {journey_id}")
        journey_ids.add(journey_id)
        candidate_id = _nonempty(journey, "candidate_id")
        if candidate_id not in allowed_candidate_ids:
            raise ValueError("rail journey is outside the candidate shortlist")
        destination = _nonempty(journey, "destination_label")
        destination_key = (candidate_id, destination.casefold())
        if destination_key in destinations:
            raise ValueError("duplicate rail journey destination for candidate")
        destinations.add(destination_key)

        for field in (
            "origin_station", "origin_station_crs", "london_arrival_station",
            "service_window", "confidence_notes",
        ):
            _nonempty(journey, field)
        crs = journey["origin_station_crs"]
        if len(crs) != 3 or not crs.isascii() or not crs.isalpha() or crs != crs.upper():
            raise ValueError("origin_station_crs must be a three-letter uppercase CRS code")
        if not isinstance(journey.get("primary"), bool):
            raise ValueError("rail journey primary must be boolean")
        primary_counts[candidate_id] = primary_counts.get(candidate_id, 0) + int(
            journey["primary"]
        )

        for field in (*COMPONENT_FIELDS, "total_minutes", "services_per_hour"):
            _nonnegative_number(journey, field)
        changes = journey.get("changes")
        if not isinstance(changes, int) or isinstance(changes, bool) or changes < 0:
            raise ValueError("rail journey changes must be a non-negative integer")
        component_total = sum(float(journey[field]) for field in COMPONENT_FIELDS)
        if abs(component_total - float(journey["total_minutes"])) > 0.01:
            raise ValueError("rail journey component times must equal total_minutes")

        last_departure = journey.get("last_useful_departure")
        if last_departure is not None:
            _datetime(last_departure, "last_useful_departure")
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
    }


def _validate_sources(value: Any) -> set[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("rail journey sources must be a non-empty array")
    kinds: set[str] = set()
    for source in value:
        if not isinstance(source, dict):
            raise ValueError("rail journey sources must be objects")
        kind = _nonempty(source, "kind")
        if kind in kinds:
            raise ValueError(f"duplicate rail source kind: {kind}")
        kinds.add(kind)
        for field in ("label", "licence"):
            _nonempty(source, field)
        parsed = urlsplit(_nonempty(source, "url"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("rail source url must be an HTTP URL")
        retrieved_at = _datetime(_nonempty(source, "retrieved_at"), "retrieved_at")
        try:
            source_date = date.fromisoformat(_nonempty(source, "source_date"))
        except ValueError as error:
            raise ValueError("rail source_date must be an ISO 8601 date") from error
        if source_date > retrieved_at.date():
            raise ValueError("rail source_date cannot be later than retrieved_at")
    if "timetable" not in kinds:
        raise ValueError("rail journey requires a timetable source")
    return kinds


def _nonempty(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _nonnegative_number(container: dict[str, Any], key: str) -> float:
    value = container.get(key)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < 0
    ):
        raise ValueError(f"{key} must be a non-negative number")
    return float(value)


def _datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed
