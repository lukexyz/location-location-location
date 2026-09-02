"""Preview and import cited housing research into an existing private run."""

from __future__ import annotations

import argparse
from typing import Any, Sequence

from .housing import configure_housing_profile, merge_housing_research
from .importer import ImportPlan, ImportSpec, run_import


def _prepare(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    housing_research: dict[str, Any],
    args: argparse.Namespace,
) -> ImportPlan:
    profile = configure_housing_profile(profile, housing_research)
    merged = merge_housing_research(profile, evidence, housing_research)
    requirements = housing_research["requirements"]
    period = "purchase" if requirements["mode"] == "buy" else "month"
    return ImportPlan(
        profile=profile,
        evidence=merged,
        lines=[
            f"Housing import plan: {len(housing_research['markets'])} "
            f"{requirements['mode']} markets for shortlisted candidates",
            f"Budget basis: GBP {requirements['budget_gbp']:g} per {period}",
            "Live inventory: not checked; listing links are external search actions",
        ],
        providers={"housing": housing_research["provider"]},
    )


SPEC = ImportSpec(
    description="Preview or import cited shortlist-only housing research",
    suffix="housing",
    label="housing",
    preview_hint="the citations",
    prepare=_prepare,
)


def main(argv: Sequence[str] | None = None) -> int:
    return run_import(argv, SPEC)
