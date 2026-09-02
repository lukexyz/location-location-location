"""Preview and import cited street-care research into a private run."""

from __future__ import annotations

import argparse
from typing import Any, Sequence

from .importer import ImportPlan, ImportSpec, run_import
from .street_care import assess_street_care, merge_street_care_research


def _prepare(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    street_research: dict[str, Any],
    args: argparse.Namespace,
) -> ImportPlan:
    merged = merge_street_care_research(evidence, street_research)
    audited = [
        place for place in street_research["places"] if place["visit_audit"] is not None
    ]
    fresh = sum(
        assess_street_care(place, street_research["assessment_date"])["basis"]
        == "recent_visit_audit"
        for place in audited
    )
    return ImportPlan(
        profile=profile,
        evidence=merged,
        lines=[
            f"Street-care import plan: {len(street_research['places'])} shortlisted "
            f"places; {len(audited)} include personal audits",
            f"Audit recency: {fresh} override proxies; {len(audited) - fresh} are stale",
            "Fly-tipping is treated as a low-resolution prior, not a council league table",
        ],
        providers={"street_care": street_research["provider"]},
    )


SPEC = ImportSpec(
    description="Preview or import cited shortlist-only street-care research",
    suffix="street-care",
    label="street-care",
    preview_hint="the limitations",
    prepare=_prepare,
)


def main(argv: Sequence[str] | None = None) -> int:
    return run_import(argv, SPEC)
