"""Preview and write a deliberately redacted copy of a private research run."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from secrets import token_hex
from shutil import copy2
from typing import Any, Sequence

from .reporting import write_bundle
from .scoring import score_research
from .street_care import merge_street_care_research
from .validation import validate_provenance


ORIGIN_DECIMALS_KM = {0: 111.0, 1: 11.0, 2: 1.1, 3: 0.11, 4: 0.011}
SHARING_WARNING = (
    "Warning: an exported bundle still reveals the route envelope around your origin, "
    "your travel limits, and your preferences. Nothing is uploaded by this command; "
    "sharing the export is a separate, deliberate action."
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or write a redacted export of a private research run"
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--origin-decimals", type=int, default=2, choices=sorted(ORIGIN_DECIMALS_KM),
        help="decimal places kept for the approximate origin (2 is about 1 km)",
    )
    parser.add_argument(
        "--strip-housing", action="store_true",
        help="remove budget, property requirements, market evidence, and the affordability metric",
    )
    parser.add_argument(
        "--anonymise-destinations", action="store_true",
        help="replace private destination labels with Destination 1, 2, ...",
    )
    parser.add_argument(
        "--keep-visit-audits", action="store_true",
        help="retain personal visit audits, their notes, and their walking scope",
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    profile = _read_json(args.run_dir / "profile.json")
    evidence = _read_json(args.run_dir / "evidence.json")
    manifest = _read_json(args.run_dir / "provenance.json")
    results = _read_json(args.run_dir / "results.json")
    artifacts = {
        name: (args.run_dir / name).read_bytes()
        for name in ("profile.json", "evidence.json", "results.json")
    }
    validate_provenance(evidence, manifest, artifacts)
    output = args.output or args.run_dir.with_name(f"{args.run_dir.name}-export")

    redacted_profile, redacted_evidence, notes = redact_bundle(
        profile,
        evidence,
        origin_decimals=args.origin_decimals,
        strip_housing=args.strip_housing,
        anonymise_destinations=args.anonymise_destinations,
        keep_visit_audits=args.keep_visit_audits,
    )
    print(f"Export plan: {profile['run_id']} -> {output}")
    for note in notes:
        print(note)
    print("Route boundary: retained; an isochrone still reveals the approximate origin area")
    print("Preferences and hard limits: retained")
    print(
        "Request ledger: request ids re-hashed with a random salt so the exact request "
        "bodies, including the origin, cannot be matched by brute force"
    )
    print("Network calls: 0; only the private run directory is read")
    print(SHARING_WARNING)
    if not args.execute:
        print("Preview only. Re-run with --execute after reviewing what the export reveals.")
        return 0

    rescored = score_research(redacted_profile, redacted_evidence, results["generated_at"])
    write_bundle(
        output,
        redacted_profile,
        redacted_evidence,
        rescored,
        request_ledger=rehash_ledger(manifest.get("request_ledger", [])),
    )
    boundary = args.run_dir / "route-boundary.geojson"
    if boundary.exists():
        copy2(boundary, output / "route-boundary.geojson")
    print(f"Wrote redacted export to {output}")
    return 0


def redact_bundle(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    *,
    origin_decimals: int = 2,
    strip_housing: bool = False,
    anonymise_destinations: bool = False,
    keep_visit_audits: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Return redacted copies plus human-readable notes on what changed and what remains."""
    if origin_decimals not in ORIGIN_DECIMALS_KM:
        raise ValueError("origin_decimals must be between 0 and 4")
    profile = deepcopy(profile)
    evidence = deepcopy(evidence)
    notes: list[str] = []

    origin = profile["search"]["approximate_origin"]
    origin["latitude"] = round(float(origin["latitude"]), origin_decimals)
    origin["longitude"] = round(float(origin["longitude"]), origin_decimals)
    origin["precision"] = (
        f"rounded to {origin_decimals} decimal places "
        f"(about {ORIGIN_DECIMALS_KM[origin_decimals]:g} km)"
    )
    notes.append(f"Origin: {origin['precision']}")

    housing = profile["search"].get("housing") or {}
    if strip_housing:
        profile["search"]["housing"] = {}
        profile["search"]["providers"].pop("housing", None)
        evidence.pop("housing_research", None)
        evidence["observations"] = [
            observation for observation in evidence["observations"]
            if observation["metric"] != "housing_affordability"
        ]
        notes.append(
            "Housing: removed budget, property requirements, market evidence, and the "
            "affordability metric; the export will report that metric as missing"
        )
    elif housing:
        period = "purchase" if housing["mode"] == "buy" else "month"
        notes.append(
            f"Housing: retained; the export reveals a GBP {housing['budget_gbp']:,.0f} per "
            f"{period} budget for a {housing['property_type']}"
        )
    else:
        notes.append("Housing: no requirements recorded")

    street = evidence.get("street_care_research")
    audits = sum(
        1 for place in (street["places"] if street else []) if place.get("visit_audit")
    )
    if audits and not keep_visit_audits:
        research = deepcopy(street)
        for place in research["places"]:
            place["visit_audit"] = None
        base = deepcopy(evidence)
        base.pop("street_care_research")
        base["observations"] = [
            observation for observation in base["observations"]
            if observation["metric"] != "street_care"
        ]
        # Re-derive rather than edit so the street-care score matches its components.
        evidence = merge_street_care_research(base, research)
        notes.append(
            f"Visit audits: removed {audits} personal audit(s) with their notes and walking "
            "scope; street care falls back to cited proxies (--keep-visit-audits retains them)"
        )
    elif audits:
        notes.append(
            f"Visit audits: retained {audits} personal audit(s) including notes and walking scope"
        )

    destinations = profile["search"]["destinations"]
    if anonymise_destinations and destinations:
        original_labels = [destination["label"] for destination in destinations]
        mapping = {
            destination["label"].casefold(): f"Destination {index}"
            for index, destination in enumerate(destinations, start=1)
        }
        for destination in destinations:
            destination["label"] = mapping[destination["label"].casefold()]
        for constraint in profile.get("hard_constraints", []):
            label = constraint.get("destination_label")
            if label is not None:
                constraint["destination_label"] = mapping[label.casefold()]
        for journey in evidence.get("rail_journeys", []):
            journey["destination_label"] = mapping[journey["destination_label"].casefold()]
        # Merged commute observations, journey notes, and identifiers repeat the label
        # in prose or slug form, in any letter case.
        replacements = []
        for destination_label in original_labels:
            new_label = mapping[destination_label.casefold()]
            replacements.append((_label_pattern(destination_label), new_label))
            replacements.append((
                _label_pattern(destination_label.casefold().replace(" ", "-")),
                new_label.casefold().replace(" ", "-"),
            ))
        for record in (*evidence["observations"], *evidence.get("rail_journeys", [])):
            for field in (
                "id", "geographic_scope", "transformation", "confidence_notes", "service_window",
            ):
                if isinstance(record.get(field), str):
                    record[field] = _scrub(record[field], replacements)
        for journey in evidence.get("rail_journeys", []):
            journey["london_arrival_station"] = "London terminal withheld"
        notes.append(
            f"Destinations: {len(destinations)} label(s) replaced with "
            f"{', '.join(mapping.values())} in every field, and London arrival stations "
            "withheld; arrival rules are retained"
        )
    elif destinations:
        labels = ", ".join(destination["label"] for destination in destinations)
        notes.append(f"Destinations: retained; the export names {labels}")
    else:
        notes.append("Destinations: none recorded")

    return profile, evidence, notes


def rehash_ledger(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace request ids with salted hashes so the fingerprints cannot be replayed."""
    salt = token_hex(16)
    return [
        {
            **entry,
            "request_id": "sha256:" + sha256(f"{salt}:{entry['request_id']}".encode()).hexdigest(),
        }
        for entry in entries
    ]


def _label_pattern(label: str) -> re.Pattern[str]:
    return re.compile(re.escape(label), re.IGNORECASE)


def _scrub(text: str, replacements: list[tuple[re.Pattern[str], str]]) -> str:
    for pattern, replacement in replacements:
        text = pattern.sub(replacement, text)
    return text


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value
