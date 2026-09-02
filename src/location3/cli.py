"""Command-line entry point for the first fixture-powered research slice."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import load_preferences
from .reporting import write_bundle
from .scoring import score_research


def main(argv: Sequence[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Score the LOCATION³ demonstration fixture")
    parser.add_argument("--profile", type=Path, default=root / "fixtures/demo/profile.json")
    parser.add_argument("--evidence", type=Path, default=root / "fixtures/demo/evidence.json")
    parser.add_argument("--output", type=Path, default=root / "research-runs/demo")
    parser.add_argument(
        "--public-only", action="store_true",
        help="ignore preferences.local.toml and use public defaults only",
    )
    args = parser.parse_args(argv)

    preferences = load_preferences(root, include_local=not args.public_only)
    profile = _read_json(args.profile)
    evidence = _read_json(args.evidence)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    profile["unknown_data_policy"] = preferences["scoring"]["unknown_data_policy"]
    results = score_research(profile, evidence)
    write_bundle(args.output, profile, evidence, results)
    print(f"Wrote {len(results['candidates'])} candidates to {args.output}")
    print(
        f"Top result: {results['candidates'][0]['name']} "
        f"({results['candidates'][0]['overall_score']:.2f})"
    )
    return 0


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
