"""One preview-first skeleton for every importer that enriches a private run.

Each importer reads a validated run, merges a cited local input, prints what it
would do, and only writes a sibling bundle after `--execute`. The rail, housing,
and street-care commands differ only in how they merge and what they disclose,
so that difference is expressed as an ImportSpec rather than three copies of the
same command.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from shutil import copy2
from typing import Any, Callable, Sequence

from .reporting import write_bundle
from .scoring import score_research
from .validation import validate_provenance


SIDECARS = ("route-boundary.geojson", "overpass-query.overpassql")


@dataclass
class ImportPlan:
    """What an importer will do, decided before anything is written."""

    profile: dict[str, Any]
    evidence: dict[str, Any]
    lines: list[str]
    providers: dict[str, str]
    request_ledger: list[dict[str, Any]] = field(default_factory=list)
    copies: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportSpec:
    description: str
    suffix: str
    label: str
    preview_hint: str
    prepare: Callable[[dict[str, Any], dict[str, Any], dict[str, Any], argparse.Namespace], ImportPlan]
    add_arguments: Callable[[argparse.ArgumentParser], None] | None = None


def run_import(argv: Sequence[str] | None, spec: ImportSpec) -> int:
    parser = argparse.ArgumentParser(description=spec.description)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    if spec.add_arguments is not None:
        spec.add_arguments(parser)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)

    profile = read_json(args.run_dir / "profile.json")
    evidence = read_json(args.run_dir / "evidence.json")
    manifest = read_json(args.run_dir / "provenance.json")
    research = read_json(args.input)
    artifacts = {
        name: (args.run_dir / name).read_bytes()
        for name in ("profile.json", "evidence.json", "results.json")
    }
    validate_provenance(evidence, manifest, artifacts)
    plan = spec.prepare(profile, evidence, research, args)
    output = args.output or args.run_dir.with_name(f"{args.run_dir.name}-{spec.suffix}")

    for line in plan.lines:
        print(line)
    print("Network calls: 0; only the cited local input files are read")
    print(f"Private output: {output}")
    if not args.execute:
        print(f"Preview only. Re-run with --execute after reviewing {spec.preview_hint}.")
        return 0

    plan.profile["search"]["providers"].update(plan.providers)
    generated_at = datetime.now(timezone.utc).isoformat()
    results = score_research(plan.profile, plan.evidence, generated_at)
    write_bundle(
        output,
        plan.profile,
        plan.evidence,
        results,
        request_ledger=list(manifest["request_ledger"]) + list(plan.request_ledger),
    )
    for name in (*SIDECARS, *plan.copies):
        source = args.run_dir / name
        if source.exists():
            copy2(source, output / name)
    print(f"Wrote {spec.label}-enriched bundle to {output}")
    return 0


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value
