"""Preview and import cited rail research into an existing private run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from shutil import copy2
from typing import Any, Sequence

from .rail import merge_rail_research
from .reporting import write_bundle
from .scoring import score_research
from .validation import validate_provenance


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or import cited shortlist-only London rail research"
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    profile = _read_json(args.run_dir / "profile.json")
    evidence = _read_json(args.run_dir / "evidence.json")
    manifest = _read_json(args.run_dir / "provenance.json")
    rail_research = _read_json(args.input)
    artifacts = {
        name: (args.run_dir / name).read_bytes()
        for name in ("profile.json", "evidence.json", "results.json")
    }
    validate_provenance(evidence, manifest, artifacts)
    merged = merge_rail_research(evidence, rail_research)
    output = args.output or args.run_dir.with_name(f"{args.run_dir.name}-rail")

    print(
        f"Rail import plan: {len(rail_research['journeys'])} journeys across "
        f"{len({item['candidate_id'] for item in rail_research['journeys']})} "
        "shortlisted candidates"
    )
    print("Network calls: 0; only the cited local input file is read")
    print(f"Private output: {output}")
    if not args.execute:
        print("Preview only. Re-run with --execute after reviewing the citations.")
        return 0

    profile["search"]["providers"]["rail"] = rail_research["provider"]
    generated_at = datetime.now(timezone.utc).isoformat()
    results = score_research(profile, merged, generated_at)
    write_bundle(
        output,
        profile,
        merged,
        results,
        request_ledger=manifest["request_ledger"],
    )
    for name in ("route-boundary.geojson", "overpass-query.overpassql"):
        source = args.run_dir / name
        if source.exists():
            copy2(source, output / name)
    print(f"Wrote rail-enriched bundle to {output}")
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value
