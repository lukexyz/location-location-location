"""Deterministic, agent-independent scoring for validated research evidence."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
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

    rail_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for journey in evidence.get("rail_journeys", []):
        rail_by_candidate[journey["candidate_id"]].append(journey)

    housing_by_candidate: dict[str, dict[str, Any]] = {}
    housing_research = evidence.get("housing_research")
    if housing_research:
        housing_by_candidate = {
            market["candidate_id"]: market for market in housing_research["markets"]
        }

    street_by_candidate: dict[str, dict[str, Any]] = {}
    street_research = evidence.get("street_care_research")
    if street_research:
        street_by_candidate = {
            place["candidate_id"]: place for place in street_research["places"]
        }

    scored = [
        _score_candidate(
            candidate,
            by_candidate[candidate["id"]],
            rail_by_candidate[candidate["id"]],
            housing_by_candidate.get(candidate["id"]),
            street_by_candidate.get(candidate["id"]),
            street_research["assessment_date"] if street_research else None,
            profile,
        )
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
    rail_journeys: list[dict[str, Any]],
    housing_market: dict[str, Any] | None,
    street_place: dict[str, Any] | None,
    street_assessment_date: str | None,
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
    constraints = _evaluate_constraints(
        profile.get("hard_constraints", []), observations, rail_journeys
    )
    warnings = [f"Missing weighted metric: {metric}" for metric in sorted(missing)]
    warnings.extend(item["warning"] for item in constraints if item.get("warning"))
    for journey in rail_journeys:
        if journey["last_useful_departure"] is None:
            warnings.append(
                f"Last useful rail service unavailable: {journey['destination_label']}"
            )
        if (
            journey["punctuality_percent"] is None
            or journey["cancellation_percent"] is None
        ):
            warnings.append(
                f"Rail reliability incomplete: {journey['destination_label']}"
            )
    if housing_market:
        mode = profile["search"]["housing"]["mode"]
        warnings.append("Housing affordability is market evidence, not live inventory")
        if mode == "buy" and housing_market["sample_size"] < 20:
            warnings.append("Purchase comparable sample has fewer than 20 transactions")
        if mode == "rent":
            geography = housing_market["geography"]["kind"].replace("_", " ")
            warnings.append(f"Rent evidence uses coarse {geography} geography")
    street_assessment = None
    if street_place and street_assessment_date:
        from .street_care import AUDIT_MAX_AGE_DAYS, assess_street_care

        street_assessment = assess_street_care(
            street_place, street_assessment_date
        )
        if street_assessment["basis"] == "proxy":
            warnings.append(
                "Street-care score uses low-resolution proxies; visit audit recommended"
            )
            local_reports = street_place["local_reports"]
            if local_reports is None or (
                local_reports["unresolved_percent"] is None
                and local_reports["median_resolution_days"] is None
            ):
                warnings.append("Local report resolution evidence unavailable")
            if street_place["fly_tipping"]["reporting_basis"].casefold() != "all incidents":
                warnings.append("Fly-tipping source does not report all incidents")
            if (
                street_assessment["audit_age_days"] is not None
                and street_assessment["audit_age_days"] > AUDIT_MAX_AGE_DAYS
            ):
                warnings.append(
                    "Personal street-care audit is stale and does not override proxies"
                )
    informational_metrics = [
        metric
        for category in sorted(metric_results)
        for metric in metric_results[category]
        if not metric["active"]
    ]
    for metric in informational_metrics:
        metric["category_contribution"] = 0.0
    result = {
        "id": candidate["id"],
        "name": candidate["name"],
        **({"place_kind": candidate["place_kind"]} if "place_kind" in candidate else {}),
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
    if rail_journeys:
        result["rail_summary"] = {
            "primary_journey_id": next(
                journey["id"] for journey in rail_journeys if journey["primary"]
            ),
            "fastest_total_minutes": min(
                journey["total_minutes"] for journey in rail_journeys
            ),
            "journeys": deepcopy(rail_journeys),
        }
    if housing_market:
        requirements = profile["search"]["housing"]
        result["housing_summary"] = {
            "mode": requirements["mode"],
            "budget_gbp": requirements["budget_gbp"],
            "budget_period": (
                "purchase" if requirements["mode"] == "buy" else "month"
            ),
            "property_type": requirements["property_type"],
            "bedrooms": requirements["bedrooms"],
            "typical_cost_gbp": housing_market["typical_cost_gbp"],
            "budget_ratio": (
                housing_market["typical_cost_gbp"] / requirements["budget_gbp"]
            ),
            "inventory_status": "not_checked",
            "market": deepcopy(housing_market),
        }
    if street_place and street_assessment_date and street_assessment:
        result["street_care_summary"] = {
            "assessment_date": street_assessment_date,
            "score": street_assessment["score"],
            "basis": street_assessment["basis"],
            "confidence": street_assessment["confidence"],
            "audit_age_days": street_assessment["audit_age_days"],
            "components": deepcopy(street_assessment["components"]),
            "place": deepcopy(street_place),
        }
    return result


def _evaluate_constraints(
    constraints: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
    rail_journeys: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for constraint in constraints:
        metric = constraint["metric"]
        destination_label = constraint.get("destination_label")
        if destination_label:
            journey = next(
                (
                    item for item in rail_journeys
                    if item["destination_label"].casefold() == destination_label.casefold()
                ),
                None,
            )
            actual = journey["total_minutes"] if journey else None
        else:
            observation = observations.get(metric)
            actual = observation["value"] if observation else None
        if actual is None:
            subject = f"{metric} for {destination_label}" if destination_label else metric
            results.append({
                **constraint, "actual": None, "passed": True,
                "warning": f"Unknown hard constraint: {subject}",
            })
            continue
        passed = (
            actual <= constraint["value"]
            if constraint["operator"] == "<=" else actual >= constraint["value"]
        )
        results.append({**constraint, "actual": actual, "passed": passed})
    return results
