"""Explicit local entry point for the first live discovery slice."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from .osm import OverpassCafeCollector
from .routing import OpenRouteServiceIsochrones


def main(argv: Sequence[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run one private, bounded settlement and cafe discovery"
    )
    parser.add_argument("--latitude", required=True, type=float)
    parser.add_argument("--longitude", required=True, type=float)
    parser.add_argument("--minutes", required=True, type=int)
    parser.add_argument(
        "--profile",
        choices=("driving-car", "cycling-regular", "foot-walking"),
        default="driving-car",
    )
    parser.add_argument(
        "--output", type=Path, default=root / "research-runs/cafe-discovery"
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("ORS_API_KEY", "")
    if not api_key:
        parser.error("ORS_API_KEY must be set in the local environment")

    boundary = OpenRouteServiceIsochrones(api_key).boundary(
        args.latitude, args.longitude, args.minutes, profile=args.profile
    )
    research = OverpassCafeCollector().collect(boundary)
    args.output.mkdir(parents=True, exist_ok=True)
    _write_json(args.output / "route-boundary.geojson", boundary.geometry)
    _write_json(args.output / "evidence.json", research.evidence)
    (args.output / "overpass-query.overpassql").write_text(
        research.query + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(research.evidence['candidates'])} candidates "
        f"from 2 provider calls to {args.output}"
    )
    return 0


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
