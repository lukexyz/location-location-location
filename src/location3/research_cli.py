"""Preview and execute one bounded, resumable LOCATION³ research run."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from typing import Sequence

from .cache import CachingTransport, RequestLedger
from .config import load_preferences
from .net import HttpTransport, UrllibTransport
from .osm import OverpassCafeCollector
from .reporting import write_bundle
from .routing import OpenRouteServiceIsochrones
from .scoring import score_research


RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def main(argv: Sequence[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Preview or run bounded local location research"
    )
    parser.add_argument("--latitude", required=True, type=float)
    parser.add_argument("--longitude", required=True, type=float)
    parser.add_argument("--minutes", required=True, type=int)
    parser.add_argument("--run-name", default="cafe-discovery")
    parser.add_argument(
        "--profile",
        choices=("driving-car", "cycling-regular", "foot-walking"),
        default="driving-car",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache", type=Path, default=root / "cache")
    parser.add_argument("--public-only", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="make up to two quota-consuming provider calls; cache hits make none",
    )
    args = parser.parse_args(argv)
    if not RUN_ID.fullmatch(args.run_name):
        parser.error("run-name must use 1-64 letters, numbers, dots, dashes, or underscores")
    _validate_request(parser, args.latitude, args.longitude, args.minutes)
    output = args.output or root / "research-runs" / args.run_name

    print("Research plan: OpenRouteService isochrone + one combined Overpass query")
    print(
        f"Origin sent to routing provider: {args.latitude:.4f}, {args.longitude:.4f}; "
        f"{args.minutes} minutes by {args.profile}"
    )
    print("Maximum live provider calls: 2 (compatible cache hits reduce this)")
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
    )
    return 0


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
    transport: HttpTransport | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
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
    research = OverpassCafeCollector(transport=overpass_transport).collect(boundary)

    preferences = load_preferences(root, include_local=include_local_preferences)
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
                "geometry_file": "route-boundary.geojson",
            },
            "housing": {},
            "destinations": [],
            "providers": {
                "routing": boundary.provider,
                "places": research.provider,
            },
        },
        "weights": preferences["weights"],
        "category_weights": preferences["category_weights"],
        "unknown_data_policy": preferences["scoring"]["unknown_data_policy"],
        "hard_constraints": [],
    }
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
