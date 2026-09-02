"""Deterministic, agent-independent scoring for validated research evidence."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .catalog import METRICS, SCORING_VERSION
from .validation import validate_evidence, validate_profile


def score_research(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    validate_profile(profile)
    validate_evidence(evidence)
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    by_candidate: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for observation in evidence["observations"]:
        metric = observation["metric"]
        candidate_id = observation["candidate_id"]
        if metric in by_candidate[candidate_id]:
            raise ValueError(f"multiple observations for {candidate_id}/{metric}")
        by_candidate[candidate_id][metric] = observation

    scored = [
        _score_candidate(candidate, by_candidate[candidate["id"]], profile)
        for candidate in evidence["candidates"]
    ]
    scored.sort(
        key=lambda item: (
            item["hard_constraints"]["passed"], item["overall_score"], item["confidence"]
        ),
        reverse=True,
    )
    for rank, candidate in enumerate(scored, start=1):
        candidate["rank"] = rank

    return {
        "schema_version": "1",
        "scoring_version": SCORING_VERSION,
        "run_id": profile["run_id"],
        "generated_at": generated_at,
        "unknown_data_policy": profile.get("unknown_data_policy", "warn"),
        "candidates": scored,
    }


def _score_candidate(
    candidate: dict[str, Any],
    observations: dict[str, dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    weights = profile["weights"]
    category_weights = profile["category_weights"]
    metric_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing: list[str] = []
    available_confidence = 0.0
    possible_confidence = sum(
        float(weight)
        for key, weight in weights.items()
        if weight > 0 and category_weights[METRICS[key].category] > 0
    )

    for key, definition in METRICS.items():
        weight = float(weights[key])
        active = weight > 0 and category_weights[definition.category] > 0
        observation = observations.get(key)
        if observation is None:
            if active:
                missing.append(key)
            continue
        normalized = definition.score(observation["value"])
        if active:
            available_confidence += weight * float(observation["confidence"])
        metric_results[definition.category].append(
            {
                "metric": key,
                "category": definition.category,
                "raw_value": observation["value"],
                "unit": observation["unit"],
                "normalized_score": normalized,
                "weight": weight,
                "active": active,
                "confidence": observation["confidence"],
                "evidence_id": observation["id"],
                "source": observation["source"],
                "source_url": observation["source_url"],
                "source_date": observation["source_date"],
                "confidence_notes": observation["confidence_notes"],
            }
        )

    categories: list[dict[str, Any]] = []
    for category in sorted(category_weights):
        active_metrics = [metric for metric in metric_results[category] if metric["active"]]
        active_weight = sum(metric["weight"] for metric in active_metrics)
        if not active_metrics or active_weight == 0:
            continue
        category_score = sum(
            metric["normalized_score"] * metric["weight"] for metric in active_metrics
        ) / active_weight
        for metric in active_metrics:
            metric["category_contribution"] = round(
                metric["normalized_score"] * metric["weight"] / active_weight, 2
            )
        categories.append(
            {
                "category": category,
                "score": round(category_score, 2),
                "weight": float(category_weights[category]),
                "metrics": active_metrics,
            }
        )

    total_category_weight = sum(category["weight"] for category in categories)
    overall = (
        sum(category["score"] * category["weight"] for category in categories)
        / total_category_weight if total_category_weight else 0.0
    )
    for category in categories:
        category["overall_contribution"] = round(
            category["score"] * category["weight"] / total_category_weight, 2
        )

    confidence = available_confidence / possible_confidence if possible_confidence else 1.0
    constraints = _evaluate_constraints(profile.get("hard_constraints", []), observations)
    warnings = [f"Missing weighted metric: {metric}" for metric in sorted(missing)]
    warnings.extend(item["warning"] for item in constraints if item.get("warning"))
    informational_metrics = [
        metric
        for category in sorted(metric_results)
        for metric in metric_results[category]
        if not metric["active"]
    ]
    for metric in informational_metrics:
        metric["category_contribution"] = 0.0
    return {
        "id": candidate["id"],
        "name": candidate["name"],
        "location": candidate["location"],
        "overall_score": round(overall, 2),
        "confidence": round(confidence * 100, 2),
        "hard_constraints": {
            "passed": all(item["passed"] for item in constraints),
            "results": constraints,
        },
        "categories": categories,
        "informational_metrics": informational_metrics,
        "missing_metrics": sorted(missing),
        "warnings": warnings,
    }


def _evaluate_constraints(
    constraints: list[dict[str, Any]], observations: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    results = []
    for constraint in constraints:
        metric = constraint["metric"]
        observation = observations.get(metric)
        if observation is None:
            results.append({
                **constraint, "actual": None, "passed": True,
                "warning": f"Unknown hard constraint: {metric}",
            })
            continue
        actual = observation["value"]
        passed = (
            actual <= constraint["value"]
            if constraint["operator"] == "<=" else actual >= constraint["value"]
        )
        results.append({**constraint, "actual": actual, "passed": passed})
    return results
