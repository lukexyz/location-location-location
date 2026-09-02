"""Preview and import cited rail research into an existing private run."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

from .importer import ImportPlan, ImportSpec, read_json, run_import
from .orr_cli import OUTPUT_NAME as PERFORMANCE_FILE
from .rail import merge_rail_research


def _add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--performance", type=Path,
        help="an orr-performance.json written by fetch_orr_performance.py",
    )


def _prepare(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    rail_research: dict[str, Any],
    args: argparse.Namespace,
) -> ImportPlan:
    performance = read_json(args.performance) if args.performance else None
    merged = merge_rail_research(
        evidence,
        rail_research,
        destination_labels=[item["label"] for item in profile["search"]["destinations"]],
        performance=performance,
    )
    lines = [
        f"Rail import plan: {len(rail_research['journeys'])} journeys across "
        f"{len({item['candidate_id'] for item in rail_research['journeys']})} "
        "shortlisted candidates"
    ]
    providers = {"rail": rail_research["provider"]}
    ledger: list[dict[str, Any]] = []
    copies: tuple[str, ...] = ()
    if performance is not None:
        operators = sorted({
            journey["operator"] for journey in merged["rail_journeys"] if "operator" in journey
        })
        lines.append(
            f"ORR performance: measured reliability applied to {len(operators)} operator(s): "
            f"{', '.join(operators) or 'none named'}"
        )
        providers["rail_performance"] = performance["provider"]
        ledger = list(performance.get("request_ledger", []))
        copies = (PERFORMANCE_FILE,)
    return ImportPlan(
        profile=profile,
        evidence=merged,
        lines=lines,
        providers=providers,
        request_ledger=ledger,
        copies=copies,
    )


SPEC = ImportSpec(
    description="Preview or import cited shortlist-only London rail research",
    suffix="rail",
    label="rail",
    preview_hint="the citations",
    prepare=_prepare,
    add_arguments=_add_arguments,
)


def main(argv: Sequence[str] | None = None) -> int:
    return run_import(argv, SPEC)
