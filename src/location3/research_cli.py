"""Preview and execute one bounded, resumable LOCATION³ research run."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Sequence

from .cache import CachingTransport, RequestLedger
from .catalog import METRICS
from .config import brand_group, load_preferences
from .net import HttpTransport, UrllibTransport
from .osm import OverpassAmenityCollector
from .reporting import write_bundle
from .routing import OpenRouteServiceIsochrones
from .scoring import score_research
from .validation import TRAVEL_MODES, validate_profile


RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
CONSTRAINT = re.compile(r"^([a-z_]+)(<=|>=)(-?\d+(?:\.\d+)?)$")
WEIGHT = re.compile(r"^([a-z_]+)=(\d+(?:\.\d+)?)$")
MAX_DESTINATION_MINUTES = 300


def main(argv: Sequence[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = _parser(root)
    args = parser.parse_args(argv)
    if not RUN_ID.fullmatch(args.run_name):
        parser.error("run-name must use 1-64 letters, numbers, dots, dashes, or underscores")
    _validate_request(parser, args.latitude, args.longitude, args.minutes)
    output = args.output or root / "research-runs" / args.run_name

    try:
        preferences = load_preferences(root, include_local=not args.public_only)
        search = build_search_profile(
            preferences,
            destinations=args.destination,
            constraints=args.constraint,
            weights=args.weight,
            housing_mode=args.housing,
            budget_gbp=args.budget,
            property_type=args.property_type,
            bedrooms=args.bedrooms,
        )
    except ValueError as error:
        parser.error(str(error))

    grocers = brand_group(preferences, "premium_grocers")
    print(
        "Research plan: OpenRouteService isochrone + one combined Overpass query "
        "(settlements, amenities, green space, and the walkable street network)"
    )
    print(
        f"Origin sent to routing provider: {args.latitude:.4f}, {args.longitude:.4f}; "
        f"{args.minutes} minutes by {args.profile}"
    )
    print(
        "Sent to Overpass: the boundary polygon and the premium grocer patterns "
        f"{', '.join(grocers.patterns)}"
    )
    print(
        "Measured for every candidate: cafes, betting shops, yoga, and premium grocers within "
        "a 15-minute walk along the mapped pedestrian network; green space by proxy distance"
    )
    print("Maximum live provider calls: 2 (compatible cache hits reduce this)")
    for line in describe_search_profile(search):
        print(line)
    print(f"Private output: {output}")
    if not args.execute:
        print("Preview only. Re-run with --execute after reviewing this disclosure.")
        return 0

    api_key = os.environ.get("ORS_API_KEY", "")
    if not api_key:
        parser.error("ORS_API_KEY must be set in the local environment")
    execute_research(
        root=root,
        output=output,
        cache_directory=args.cache,
        run_id=args.run_name,
        latitude=args.latitude,
        longitude=args.longitude,
        duration_minutes=args.minutes,
        route_profile=args.profile,
        api_key=api_key,
        include_local_preferences=not args.public_only,
        search=search,
    )
    return 0


def _parser(root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or run bounded local location research",
        epilog=(
            "Destinations use LABEL|MODE|ARRIVAL[|MAX_MINUTES], for example "
            '"London Bridge|public_transport|Tuesday 09:00|75". A destination with '
            "MAX_MINUTES adds a door-to-door hard limit. Constraints look like "
            "betting_shops<=1; weight overrides look like cafes=3."
        ),
    )
    parser.add_argument("--latitude", required=True, type=float)
    parser.add_argument("--longitude", required=True, type=float)
    parser.add_argument("--minutes", required=True, type=int)
    parser.add_argument("--run-name", default="location-research")
    parser.add_argument(
        "--profile",
        choices=("driving-car", "cycling-regular", "foot-walking"),
        default="driving-car",
    )
    parser.add_argument("--destination", action="append", default=[], metavar="SPEC")
    parser.add_argument("--constraint", action="append", default=[], metavar="METRIC<=VALUE")
    parser.add_argument("--weight", action="append", default=[], metavar="METRIC=VALUE")
    parser.add_argument("--housing", choices=("buy", "rent"))
    parser.add_argument("--budget", type=float, help="purchase budget or monthly rent in GBP")
    parser.add_argument("--property-type", help="for example flat, terraced, semi-detached")
    parser.add_argument("--bedrooms", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache", type=Path, default=root / "cache")
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="make up to two quota-consuming provider calls; cache hits make none",
    )
    return parser


def build_search_profile(
    preferences: dict[str, Any],
    *,
    destinations: Sequence[str] = (),
    constraints: Sequence[str] = (),
    weights: Sequence[str] = (),
    housing_mode: str | None = None,
    budget_gbp: float | None = None,
    property_type: str | None = None,
    bedrooms: int | None = None,
) -> dict[str, Any]:
    """Turn command-line choices into the profile parts that steer scoring."""
    parsed_destinations = [_parse_destination(spec) for spec in destinations]
    labels = [item["label"].casefold() for item in parsed_destinations]
    if len(set(labels)) != len(labels):
        raise ValueError("destination labels must be unique")

    hard_constraints = [_parse_constraint(spec) for spec in constraints]
    for destination in parsed_destinations:
        if destination["max_minutes"] is None:
            continue
        hard_constraints.append({
            "metric": "door_to_door_commute",
            "operator": "<=",
            "value": destination["max_minutes"],
            "destination_label": destination["label"],
        })
    constraint_keys = [
        (item["metric"], item.get("destination_label", "").casefold())
        for item in hard_constraints
    ]
    if len(set(constraint_keys)) != len(constraint_keys):
        raise ValueError("each metric and destination may carry at most one hard constraint")

    merged_weights = dict(preferences["weights"])
    for spec in weights:
        match = WEIGHT.fullmatch(spec.strip())
        if not match or match.group(1) not in METRICS:
            raise ValueError(f"weight override must look like cafes=3: {spec}")
        value = float(match.group(2))
        if value > 5:
            raise ValueError(f"weight override must be from 0 to 5: {spec}")
        merged_weights[match.group(1)] = value

    housing: dict[str, Any] = {}
    if any(value is not None for value in (housing_mode, budget_gbp, property_type, bedrooms)):
        if housing_mode is None or budget_gbp is None or not property_type:
            raise ValueError("housing needs --housing, --budget, and --property-type together")
        if budget_gbp <= 0:
            raise ValueError("budget must be a positive number of pounds")
        if bedrooms is not None and bedrooms < 0:
            raise ValueError("bedrooms cannot be negative")
        housing = {
            "mode": housing_mode,
            "budget_gbp": budget_gbp,
            "property_type": property_type.strip(),
            "bedrooms": bedrooms,
        }

    return {
        "destinations": parsed_destinations,
        "hard_constraints": hard_constraints,
        "weights": merged_weights,
        "housing": housing,
    }


def describe_search_profile(search: dict[str, Any]) -> list[str]:
    lines = []
    for destination in search["destinations"]:
        limit = (
            f", at most {destination['max_minutes']} min door-to-door"
            if destination["max_minutes"] else ""
        )
        lines.append(
            f"Destination: {destination['label']} by {destination['travel_mode']} "
            f"arriving {destination['arrival']}{limit}"
        )
    for constraint in search["hard_constraints"]:
        destination = (
            f" for {constraint['destination_label']}"
            if constraint.get("destination_label") else ""
        )
        lines.append(
            f"Hard limit: {constraint['metric']}{destination} "
            f"{constraint['operator']} {constraint['value']:g}"
        )
    housing = search["housing"]
    if housing:
        period = "purchase" if housing["mode"] == "buy" else "month"
        size = "any size" if housing["bedrooms"] is None else f"{housing['bedrooms']} bed"
        lines.append(
            f"Housing: {housing['mode']} a {size} {housing['property_type']} within "
            f"GBP {housing['budget_gbp']:,.0f} per {period} (evidence imported later)"
        )
    active = ", ".join(
        f"{metric}={weight:g}" for metric, weight in search["weights"].items() if weight > 0
    )
    lines.append(f"Weighted metrics: {active or 'none'}")
    return lines


def execute_research(
    *,
    root: Path,
    output: Path,
    cache_directory: Path,
    run_id: str,
    latitude: float,
    longitude: float,
    duration_minutes: int,
    route_profile: str,
    api_key: str,
    include_local_preferences: bool,
    search: dict[str, Any] | None = None,
    transport: HttpTransport | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    preferences = load_preferences(root, include_local=include_local_preferences)
    search = search or build_search_profile(preferences)
    upstream = transport or UrllibTransport()
    ledger = RequestLedger(max_network_requests=2)
    routing_transport = CachingTransport(
        "openrouteservice",
        upstream,
        cache_directory,
        ledger,
        ttl=timedelta(days=30),
    )
    overpass_transport = CachingTransport(
        "overpass",
        upstream,
        cache_directory,
        ledger,
        ttl=timedelta(days=1),
    )
    boundary = OpenRouteServiceIsochrones(
        api_key, transport=routing_transport
    ).boundary(
        latitude, longitude, duration_minutes, profile=route_profile
    )
    collector = OverpassAmenityCollector(
        premium_grocers=brand_group(preferences, "premium_grocers"),
        transport=overpass_transport,
    )
    research = collector.collect(boundary)

    profile = {
        "schema_version": "1",
        "run_id": run_id,
        "search": {
            "approximate_origin": {
                "latitude": latitude,
                "longitude": longitude,
                "precision": "user-provided",
            },
            "route_boundary": {
                "type": "isochrone",
                "duration_minutes": duration_minutes,
                "travel_profile": route_profile,
                "provider": boundary.provider,
                "departure_time": None,
                "traffic_treatment": "provider default; departure time not supplied",
                "retrieved_at": boundary.retrieved_at or generated_at,
                "geometry_file": "route-boundary.geojson",
                "geometry": boundary.geometry,
            },
            "housing": search["housing"],
            "destinations": search["destinations"],
            "providers": {
                "routing": boundary.provider,
                "places": research.provider,
            },
        },
        "weights": search["weights"],
        "category_weights": preferences["category_weights"],
        "unknown_data_policy": preferences["scoring"]["unknown_data_policy"],
        "hard_constraints": search["hard_constraints"],
    }
    validate_profile(profile)
    results = score_research(profile, research.evidence, generated_at)
    manifest = write_bundle(
        output,
        profile,
        research.evidence,
        results,
        request_ledger=ledger.entries,
    )
    _write_json(output / "route-boundary.geojson", boundary.geometry)
    (output / "overpass-query.overpassql").write_text(
        research.query + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(results['candidates'])} candidates; "
        f"{ledger.network_requests} live calls, "
        f"{sum(entry['cache'] == 'hit' for entry in ledger.entries)} cache hits"
    )
    return manifest


def _parse_destination(spec: str) -> dict[str, Any]:
    parts = [part.strip() for part in spec.split("|")]
    if len(parts) not in (3, 4):
        raise ValueError(f"destination must be LABEL|MODE|ARRIVAL[|MAX_MINUTES]: {spec}")
    label, travel_mode, arrival = parts[:3]
    if not label or not arrival:
        raise ValueError(f"destination label and arrival cannot be empty: {spec}")
    if travel_mode not in TRAVEL_MODES:
        raise ValueError(
            f"destination mode must be one of {', '.join(sorted(TRAVEL_MODES))}: {spec}"
        )
    max_minutes: int | None = None
    if len(parts) == 4 and parts[3]:
        if not parts[3].isdigit() or not 1 <= int(parts[3]) <= MAX_DESTINATION_MINUTES:
            raise ValueError(
                f"destination max minutes must be 1-{MAX_DESTINATION_MINUTES}: {spec}"
            )
        max_minutes = int(parts[3])
    return {
        "label": label,
        "travel_mode": travel_mode,
        "arrival": arrival,
        "max_minutes": max_minutes,
    }


def _parse_constraint(spec: str) -> dict[str, Any]:
    match = CONSTRAINT.fullmatch(spec.replace(" ", ""))
    if not match or match.group(1) not in METRICS:
        raise ValueError(f"constraint must look like betting_shops<=1: {spec}")
    return {
        "metric": match.group(1),
        "operator": match.group(2),
        "value": float(match.group(3)),
    }


def _validate_request(
    parser: argparse.ArgumentParser,
    latitude: float,
    longitude: float,
    duration_minutes: int,
) -> None:
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        parser.error("origin coordinates are out of range")
    if not 1 <= duration_minutes <= 120:
        parser.error("minutes must be between 1 and 120")


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
