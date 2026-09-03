"""Small runtime validators for the v1 public bundle contracts."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping
from urllib.parse import urlsplit

from .catalog import EVIDENCE_BASES, INFERRED_CONFIDENCE_CAP, METRICS, PLACE_KINDS
from .fields import http_url, iso_date, iso_datetime, nonempty, require


TRAVEL_MODES = {"public_transport", "driving", "cycling", "walking"}
BOUNDARY_TYPES = {"isochrone", "distance_proxy", "fixture_polygon"}


def validate_profile(profile: dict[str, Any]) -> None:
    if require(profile, "schema_version", str) != "1":
        raise ValueError("unsupported profile schema_version")
    require(profile, "run_id", str)
    search = require(profile, "search", dict)
    _validate_search(search)
    weights = require(profile, "weights", dict)
    category_weights = require(profile, "category_weights", dict)
    if set(weights) != set(METRICS):
        raise ValueError("profile weights do not match the metric catalogue")
    if not category_weights:
        raise ValueError("profile category_weights cannot be empty")
    for label, values in (("metric", weights), ("category", category_weights)):
        for key, value in values.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 5
            ):
                raise ValueError(f"profile {label} weight {key} must be from 0 to 5")
    constraints = profile.get("hard_constraints", [])
    if not isinstance(constraints, list):
        raise ValueError("profile hard_constraints must be an array")
    destination_modes = {
        destination["label"].casefold(): destination["travel_mode"]
        for destination in search["destinations"]
    }
    constraint_keys: list[tuple[str, str]] = []
    for constraint in constraints:
        if not isinstance(constraint, dict):
            raise ValueError("hard constraints must be objects")
        if set(constraint) - {"metric", "operator", "value", "destination_label"}:
            raise ValueError("hard constraint contains unsupported fields")
        if constraint.get("metric") not in METRICS:
            raise ValueError("hard constraint references an unknown metric")
        if constraint.get("operator") not in {"<=", ">="}:
            raise ValueError("hard constraint operator must be <= or >=")
        if isinstance(constraint.get("value"), bool) or not isinstance(
            constraint.get("value"), (int, float)
        ):
            raise ValueError("hard constraint value must be numeric")
        destination_label = constraint.get("destination_label")
        if destination_label is not None:
            if constraint["metric"] != "door_to_door_commute":
                raise ValueError("only commute constraints may name a destination")
            if not isinstance(destination_label, str) or not destination_label.strip():
                raise ValueError("hard constraint destination_label must be non-empty")
            if destination_label.casefold() not in destination_modes:
                raise ValueError("hard constraint destination is not in the search profile")
            if destination_modes[destination_label.casefold()] != "public_transport":
                raise ValueError(
                    "a door-to-door limit can only be evaluated for a public_transport "
                    "destination in v1; commute evidence comes from the cited rail import"
                )
        constraint_keys.append(
            (constraint["metric"], (destination_label or "").casefold())
        )
    if len(set(constraint_keys)) != len(constraint_keys):
        raise ValueError("each metric and destination may carry at most one hard constraint")


def _validate_search(search: dict[str, Any]) -> None:
    origin = require(search, "approximate_origin", dict)
    latitude = require(origin, "latitude", (int, float))
    longitude = require(origin, "longitude", (int, float))
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("approximate_origin is out of range")
    nonempty(origin, "precision")

    boundary = require(search, "route_boundary", dict)
    if boundary.get("type") not in BOUNDARY_TYPES:
        raise ValueError("route_boundary type is unsupported")
    nonempty(boundary, "provider")
    nonempty(boundary, "traffic_treatment")
    iso_datetime(nonempty(boundary, "retrieved_at"), "route_boundary.retrieved_at")
    if boundary.get("departure_time") is not None:
        iso_datetime(boundary["departure_time"], "route_boundary.departure_time")
    if "duration_minutes" in boundary:
        minutes = require(boundary, "duration_minutes", int)
        if not 1 <= minutes <= 300:
            raise ValueError("route_boundary duration_minutes is out of range")
    validate_polygon_geometry(require(boundary, "geometry", dict))

    housing = require(search, "housing", dict)
    if housing:
        if set(housing) != {"mode", "budget_gbp", "property_type", "bedrooms"}:
            raise ValueError("housing requirements fields do not match the schema")
        if housing["mode"] not in {"buy", "rent"}:
            raise ValueError("housing mode must be buy or rent")
        budget = require(housing, "budget_gbp", (int, float))
        if budget <= 0:
            raise ValueError("housing budget_gbp must be positive")
        nonempty(housing, "property_type")
        bedrooms = housing["bedrooms"]
        if bedrooms is not None and (
            not isinstance(bedrooms, int) or isinstance(bedrooms, bool) or bedrooms < 0
        ):
            raise ValueError("housing bedrooms must be null or a non-negative integer")

    labels: set[str] = set()
    for destination in require(search, "destinations", list):
        if not isinstance(destination, dict):
            raise ValueError("destinations must be objects")
        label = nonempty(destination, "label").casefold()
        if label in labels:
            raise ValueError("destination labels must be unique")
        labels.add(label)
        if destination.get("travel_mode") not in TRAVEL_MODES:
            raise ValueError("destination travel_mode is unsupported")
        nonempty(destination, "arrival")
        max_minutes = destination.get("max_minutes")
        if max_minutes is not None and (
            not isinstance(max_minutes, int) or isinstance(max_minutes, bool)
            or not 1 <= max_minutes <= 300
        ):
            raise ValueError("destination max_minutes must be null or 1-300")

    providers = require(search, "providers", dict)
    if any(
        not isinstance(key, str) or not key or not isinstance(value, str) or not value
        for key, value in providers.items()
    ):
        raise ValueError("providers must map names to non-empty strings")


def validate_polygon_geometry(geometry: dict[str, Any]) -> None:
    """Check a GeoJSON Polygon or MultiPolygon has well-formed, in-range rings."""
    kind = geometry.get("type")
    if kind not in {"Polygon", "MultiPolygon"}:
        raise ValueError("route boundary geometry must be a Polygon or MultiPolygon")
    coordinates = geometry.get("coordinates")
    polygons = coordinates if kind == "MultiPolygon" else [coordinates]
    if not isinstance(polygons, list) or not polygons:
        raise ValueError("route boundary geometry has no coordinates")
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("route boundary polygon has no rings")
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError("route boundary ring needs at least four positions")
            for position in ring:
                if (
                    not isinstance(position, list) or len(position) < 2
                    or any(
                        isinstance(value, bool) or not isinstance(value, (int, float))
                        for value in position[:2]
                    )
                    or not -180 <= position[0] <= 180 or not -90 <= position[1] <= 90
                ):
                    raise ValueError("route boundary contains an invalid position")
            if ring[0][:2] != ring[-1][:2]:
                raise ValueError("route boundary rings must be closed")


def validate_evidence(bundle: dict[str, Any]) -> None:
    if require(bundle, "schema_version", str) != "1":
        raise ValueError("unsupported evidence schema_version")
    candidates = require(bundle, "candidates", list)
    observations = require(bundle, "observations", list)
    candidate_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = require(candidate, "id", str)
        require(candidate, "name", str)
        location = require(candidate, "location", dict)
        latitude = require(location, "latitude", (int, float))
        longitude = require(location, "longitude", (int, float))
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("candidate location is out of range")
        if "place_kind" in candidate and candidate["place_kind"] not in PLACE_KINDS:
            raise ValueError("candidate place_kind is unsupported")
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)

    observation_ids: set[str] = set()
    for observation in observations:
        observation_id = require(observation, "id", str)
        if observation_id in observation_ids:
            raise ValueError(f"duplicate observation id: {observation_id}")
        observation_ids.add(observation_id)
        if require(observation, "candidate_id", str) not in candidate_ids:
            raise ValueError("observation references an unknown candidate")
        metric = require(observation, "metric", str)
        if metric not in METRICS:
            raise ValueError(f"unknown evidence metric: {metric}")
        require(observation, "value", (int, float))
        if require(observation, "unit", str) != METRICS[metric].unit:
            raise ValueError(f"unexpected unit for {metric}")
        confidence = require(observation, "confidence", (int, float))
        if not 0 <= confidence <= 1:
            raise ValueError("observation confidence must be between 0 and 1")
        validate_basis(observation, confidence, "observation")
        for key in (
            "geographic_scope", "source", "transformation", "licence", "confidence_notes",
        ):
            nonempty(observation, key)
        http_url(nonempty(observation, "source_url"), "source_url")
        retrieved_at = iso_datetime(nonempty(observation, "retrieved_at"), "retrieved_at")
        source_date = iso_date(nonempty(observation, "source_date"), "source_date")
        if source_date > retrieved_at.date():
            raise ValueError("source_date cannot be later than retrieved_at")

    rail_journeys = bundle.get("rail_journeys", [])
    if not isinstance(rail_journeys, list):
        raise ValueError("evidence rail_journeys must be an array")
    if rail_journeys:
        # Local import avoids coupling the base evidence validator to a provider.
        from .rail import validate_rail_research

        validate_rail_research(
            {
                "schema_version": "1",
                "provider": "evidence bundle",
                "journeys": rail_journeys,
            },
            candidate_ids,
        )

    housing_research = bundle.get("housing_research")
    if housing_research is not None:
        if not isinstance(housing_research, dict):
            raise ValueError("evidence housing_research must be an object")
        from .housing import validate_housing_research

        validate_housing_research(housing_research, candidate_ids)
        budget = housing_research["requirements"]["budget_gbp"]
        for market in housing_research["markets"]:
            matching = [
                observation
                for observation in observations
                if observation["candidate_id"] == market["candidate_id"]
                and observation["metric"] == "housing_affordability"
            ]
            if len(matching) != 1:
                raise ValueError(
                    "each housing market requires one affordability observation"
                )
            expected_ratio = market["typical_cost_gbp"] / budget
            if abs(matching[0]["value"] - expected_ratio) > 0.000001:
                raise ValueError(
                    "housing affordability observation does not match market and budget"
                )

    street_research = bundle.get("street_care_research")
    if street_research is not None:
        if not isinstance(street_research, dict):
            raise ValueError("evidence street_care_research must be an object")
        from .street_care import assess_street_care, validate_street_care_research

        validate_street_care_research(street_research, candidate_ids)
        for place in street_research["places"]:
            matching = [
                observation
                for observation in observations
                if observation["candidate_id"] == place["candidate_id"]
                and observation["metric"] == "street_care"
            ]
            if len(matching) != 1:
                raise ValueError(
                    "each street-care place requires one derived observation"
                )
            expected = assess_street_care(
                place, street_research["assessment_date"]
            )["score"]
            if abs(matching[0]["value"] - expected) > 0.000001:
                raise ValueError(
                    "street-care observation does not match its raw components"
                )


def validate_basis(record: dict[str, Any], confidence: float, label: str) -> str:
    """Require an honest evidence basis; an agent estimate cannot claim high confidence."""
    basis = record.get("basis")
    if basis not in EVIDENCE_BASES:
        raise ValueError(
            f"{label} basis must be one of {', '.join(EVIDENCE_BASES)}"
        )
    if basis == "agent_inferred" and confidence > INFERRED_CONFIDENCE_CAP:
        raise ValueError(
            f"agent-inferred {label} cannot claim confidence above {INFERRED_CONFIDENCE_CAP}"
        )
    return basis


def validate_manifest(
    manifest: dict[str, Any], artifacts: Mapping[str, bytes] | None = None
) -> None:
    if require(manifest, "schema_version", str) != "1":
        raise ValueError("unsupported manifest schema_version")
    nonempty(manifest, "run_id")
    iso_datetime(nonempty(manifest, "generated_at"), "generated_at")
    nonempty(manifest, "scoring_version")
    tool_versions = require(manifest, "tool_versions", dict)
    if not tool_versions or any(
        not isinstance(key, str) or not isinstance(value, str) or not key or not value
        for key, value in tool_versions.items()
    ):
        raise ValueError("tool_versions must contain non-empty string entries")
    require(manifest, "geographic_coverage", dict)
    ledger = require(manifest, "request_ledger", list)
    cache_used = require(manifest, "cache_used", bool)
    _string_list(manifest, "sources")
    _string_list(manifest, "licences")
    _string_list(manifest, "warnings")
    for entry in ledger:
        if not isinstance(entry, dict):
            raise ValueError("request ledger entries must be objects")
        allowed = {
            "provider", "request_id", "endpoint", "requested_at", "cache", "status",
            "cache_expires_at",
        }
        if set(entry) - allowed:
            raise ValueError("request ledger contains unapproved fields")
        nonempty(entry, "provider")
        request_id = nonempty(entry, "request_id")
        if not _checksum_value(request_id):
            raise ValueError("request_id must be a SHA-256 identifier")
        endpoint = http_url(nonempty(entry, "endpoint"), "endpoint")
        parsed_endpoint = urlsplit(endpoint)
        if parsed_endpoint.query or parsed_endpoint.fragment or parsed_endpoint.username:
            raise ValueError("request ledger endpoints must not contain sensitive URL parts")
        iso_datetime(nonempty(entry, "requested_at"), "requested_at")
        if entry.get("cache") not in {"hit", "miss"}:
            raise ValueError("request ledger cache must be hit or miss")
        status = require(entry, "status", int)
        if not 0 <= status <= 599:
            raise ValueError("request ledger status is out of range")
        if "cache_expires_at" in entry:
            iso_datetime(nonempty(entry, "cache_expires_at"), "cache_expires_at")
    if cache_used != any(entry["cache"] == "hit" for entry in ledger):
        raise ValueError("cache_used does not match the request ledger")

    checksums = require(manifest, "checksums", dict)
    expected = {"profile.json", "evidence.json", "results.json"}
    if set(checksums) != expected:
        raise ValueError("manifest checksums must cover the three bundle contracts")
    for name, checksum in checksums.items():
        if not isinstance(checksum, str) or not _checksum_value(checksum):
            raise ValueError(f"invalid checksum for {name}")
    if artifacts is not None:
        if set(artifacts) != expected:
            raise ValueError("artifact bytes must cover the three bundle contracts")
        for name, content in artifacts.items():
            actual = f"sha256:{sha256(content).hexdigest()}"
            if checksums[name] != actual:
                raise ValueError(f"checksum mismatch for {name}")


def validate_provenance(
    evidence: dict[str, Any],
    manifest: dict[str, Any],
    artifacts: Mapping[str, bytes] | None = None,
) -> None:
    validate_evidence(evidence)
    validate_manifest(manifest, artifacts)
    sources = {item["source_url"] for item in evidence["observations"]}
    licences = {item["licence"] for item in evidence["observations"]}
    for journey in evidence.get("rail_journeys", []):
        sources.update(source["url"] for source in journey["sources"])
        licences.update(source["licence"] for source in journey["sources"])
    housing_research = evidence.get("housing_research")
    if housing_research:
        for market in housing_research["markets"]:
            sources.update(source["url"] for source in market["sources"])
            licences.update(source["licence"] for source in market["sources"])
    street_research = evidence.get("street_care_research")
    if street_research:
        for place in street_research["places"]:
            sources.add(place["fly_tipping"]["source"]["url"])
            licences.add(place["fly_tipping"]["source"]["licence"])
            if place["local_reports"]:
                sources.add(place["local_reports"]["source"]["url"])
                licences.add(place["local_reports"]["source"]["licence"])
    sources = sorted(sources)
    licences = sorted(licences)
    if manifest["sources"] != sources:
        raise ValueError("manifest sources do not match evidence citations")
    if manifest["licences"] != licences:
        raise ValueError("manifest licences do not match evidence")


def _string_list(container: dict[str, Any], key: str) -> list[str]:
    values = require(container, key, list)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{key} must contain non-empty strings")
    return values


def _checksum_value(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != 71:
        return False
    try:
        int(value[7:], 16)
    except ValueError:
        return False
    return True
