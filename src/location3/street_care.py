"""Deterministic, cautious street-care assessment for shortlisted places."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from .validation import validate_basis, validate_evidence
from .fields import (
    exact_keys, http_url, iso_date, iso_datetime, nonempty, nonnegative_number,
    nullable_nonnegative, piecewise,
)


AUDIT_FIELDS = (
    "litter",
    "dog_fouling",
    "graffiti",
    "weeds_and_detritus",
    "overflowing_bins",
    "overall_upkeep",
)
REPORT_SCOPES = {"lsoa", "local_authority", "other_small_area"}
AUDIT_MAX_AGE_DAYS = 180
AUDIT_METHOD_URL = (
    "https://github.com/lukexyz/location-location-location/blob/main/"
    "schemas/street-care-research.schema.json"
)


def merge_street_care_research(
    evidence: dict[str, Any], street_research: dict[str, Any]
) -> dict[str, Any]:
    """Return evidence enriched by derived street-care scores for the shortlist."""
    validate_evidence(evidence)
    candidate_ids = {candidate["id"] for candidate in evidence["candidates"]}
    validate_street_care_research(street_research, candidate_ids)
    merged = deepcopy(evidence)
    researched_candidates = {
        place["candidate_id"] for place in street_research["places"]
    }
    merged["observations"] = [
        observation
        for observation in merged["observations"]
        if not (
            observation["candidate_id"] in researched_candidates
            and observation["metric"] == "street_care"
        )
    ]
    for place in street_research["places"]:
        assessment = assess_street_care(place, street_research["assessment_date"])
        merged["observations"].append(_street_observation(place, assessment))
    merged["street_care_research"] = deepcopy(street_research)
    validate_evidence(merged)
    return merged


def validate_street_care_research(
    street_research: dict[str, Any], allowed_candidate_ids: set[str]
) -> None:
    exact_keys(
        street_research,
        {"schema_version", "provider", "assessment_date", "places"},
        "street-care research",
    )
    if street_research.get("schema_version") != "1":
        raise ValueError("unsupported street-care research schema_version")
    nonempty(street_research, "provider")
    assessment_date = iso_date(
        nonempty(street_research, "assessment_date"), "assessment_date"
    )
    places = street_research.get("places")
    if not isinstance(places, list) or not places:
        raise ValueError("street-care places must be a non-empty array")

    place_ids: set[str] = set()
    candidate_ids: set[str] = set()
    for place in places:
        if not isinstance(place, dict):
            raise ValueError("street-care places must be objects")
        exact_keys(
            place,
            {
                "id", "candidate_id", "local_authority", "fly_tipping", "local_reports",
                "visit_audit", "basis",
            },
            "street-care place",
        )
        place_id = nonempty(place, "id")
        if place_id in place_ids:
            raise ValueError(f"duplicate street-care place id: {place_id}")
        place_ids.add(place_id)
        candidate_id = nonempty(place, "candidate_id")
        if candidate_id not in allowed_candidate_ids:
            raise ValueError("street-care place is outside the candidate shortlist")
        if candidate_id in candidate_ids:
            raise ValueError("each researched candidate must have one street-care place")
        candidate_ids.add(candidate_id)
        nonempty(place, "local_authority")
        # Proxy evidence is capped at 0.55 by the assessment, so the inferred cap applies
        # to the basis label itself rather than to a stated confidence.
        validate_basis(place, 0.0, "street-care place")
        _validate_fly_tipping(place.get("fly_tipping"))
        _validate_local_reports(place.get("local_reports"))
        _validate_visit_audit(place.get("visit_audit"), assessment_date)
        sources = [place["fly_tipping"]["source"]]
        if place["local_reports"]:
            sources.append(place["local_reports"]["source"])
        if any(
            iso_date(source["source_date"], "source_date") > assessment_date
            for source in sources
        ):
            raise ValueError("street-care sources cannot be later than assessment_date")


def assess_street_care(place: dict[str, Any], assessment_date: str) -> dict[str, Any]:
    """Derive the score, basis, confidence, and inspectable components."""
    assessed = iso_date(assessment_date, "assessment_date")
    audit = place["visit_audit"]
    if audit is not None:
        age_days = (assessed - iso_date(audit["audited_at"], "audited_at")).days
        if age_days <= AUDIT_MAX_AGE_DAYS:
            components = [
                {
                    "key": key,
                    "raw_value": audit["ratings"][key],
                    "unit": "rating_0_to_4",
                    "normalized_score": audit["ratings"][key] * 25,
                    "weight": round(1 / len(AUDIT_FIELDS), 6),
                    "included": True,
                }
                for key in AUDIT_FIELDS
            ]
            score = sum(item["normalized_score"] for item in components) / len(components)
            confidence = 0.9 - (age_days / AUDIT_MAX_AGE_DAYS) * 0.2
            return {
                "score": round(score, 2),
                "basis": "recent_visit_audit",
                "confidence": round(confidence, 4),
                "audit_age_days": age_days,
                "components": components,
            }

    fly = place["fly_tipping"]
    report = place["local_reports"]
    has_resolution_evidence = report is not None and (
        report["unresolved_percent"] is not None
        or report["median_resolution_days"] is not None
    )
    rate_component = _component(
        "fly_tipping_rate",
        fly["current_incidents_per_1000"],
        "incidents_per_1000",
        piecewise(
            fly["current_incidents_per_1000"],
            ((0, 90), (10, 80), (25, 65), (50, 45), (100, 20), (200, 0)),
        ),
        0.2 if has_resolution_evidence else 0.4,
    )
    trend_percent = _percent_change(
        fly["previous_incidents_per_1000"], fly["current_incidents_per_1000"]
    )
    trend_component = _component(
        "fly_tipping_trend",
        trend_percent,
        "percent_change",
        piecewise(
            trend_percent,
            ((-50, 90), (-20, 75), (0, 60), (20, 40), (50, 20), (100, 0)),
        ),
        0.2 if has_resolution_evidence else 0.6,
    )
    components = [rate_component, trend_component]
    confidence = 0.3
    if report is not None:
        unresolved = report["unresolved_percent"]
        resolution = report["median_resolution_days"]
        components.append(
            _component(
                "report_density",
                report["reports_per_1000"],
                "reports_per_1000",
                None,
                0,
                included=False,
            )
        )
        if unresolved is not None:
            components.append(
                _component(
                    "unresolved_reports", unresolved, "percent", 100 - unresolved, 0.3
                )
            )
        if resolution is not None:
            components.append(
                _component(
                    "median_resolution_time",
                    resolution,
                    "days",
                    piecewise(
                        resolution,
                        ((0, 100), (2, 90), (7, 70), (14, 50), (30, 20), (60, 0)),
                    ),
                    0.3,
                )
            )
        usable_report_components = int(unresolved is not None) + int(resolution is not None)
        if usable_report_components:
            confidence += 0.1 if report["scope_kind"] == "local_authority" else 0.15
            if usable_report_components == 2:
                confidence += 0.1

    included = [item for item in components if item["included"]]
    total_weight = sum(item["weight"] for item in included)
    score = sum(item["normalized_score"] * item["weight"] for item in included) / total_weight
    for item in included:
        item["weight"] = round(item["weight"] / total_weight, 6)
    return {
        "score": round(score, 2),
        "basis": "proxy",
        "confidence": round(min(confidence, 0.55), 4),
        "audit_age_days": (
            None
            if audit is None
            else (assessed - iso_date(audit["audited_at"], "audited_at")).days
        ),
        "components": components,
    }


def _street_observation(
    place: dict[str, Any], assessment: dict[str, Any]
) -> dict[str, Any]:
    evidence_basis = "user_observed"
    if assessment["basis"] == "recent_visit_audit":
        audit = place["visit_audit"]
        source = {
            "label": "Private structured visit audit",
            "url": AUDIT_METHOD_URL,
            "retrieved_at": f"{audit['audited_at']}T12:00:00+00:00",
            "source_date": audit["audited_at"],
            "licence": "Private user observation; not for redistribution",
        }
        scope = audit["geographic_scope"]
        transformation = (
            "Mean of six structured 0–4 visit ratings; recent audit overrides proxy"
        )
        notes = f"Personal audit is {assessment['audit_age_days']} days old"
    else:
        evidence_basis = place["basis"]
        source = place["fly_tipping"]["source"]
        scope = f"{place['local_authority']} proxy applied to candidate"
        transformation = (
            "Documented weighted proxy from fly-tipping level/trend and available "
            "local report resolution; report density is informational only"
        )
        notes = (
            "Low-resolution proxy; incident volume is affected by reporting practice "
            "and does not directly measure neighbourhood cleanliness"
        )
    return {
        "id": f"{place['id']}-score",
        "candidate_id": place["candidate_id"],
        "metric": "street_care",
        "value": assessment["score"],
        "unit": "desirability_score",
        "geographic_scope": scope,
        "source": source["label"],
        "source_url": source["url"],
        "retrieved_at": source["retrieved_at"],
        "source_date": source["source_date"],
        "transformation": transformation,
        "licence": source["licence"],
        "confidence": (
            min(assessment["confidence"], 0.5)
            if evidence_basis == "agent_inferred" else assessment["confidence"]
        ),
        "confidence_notes": notes,
        "basis": evidence_basis,
    }


def _validate_fly_tipping(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("fly_tipping must be an object")
    exact_keys(
        value,
        {"current_incidents_per_1000", "previous_incidents_per_1000", "current_period", "previous_period", "reporting_basis", "source"},
        "fly_tipping",
    )
    for field in ("current_incidents_per_1000", "previous_incidents_per_1000"):
        nonnegative_number(value, field)
    nonempty(value, "current_period")
    nonempty(value, "previous_period")
    nonempty(value, "reporting_basis")
    _validate_source(value.get("source"), "fly-tipping source")


def _validate_local_reports(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError("local_reports must be null or an object")
    exact_keys(
        value,
        {"scope_kind", "geographic_scope", "reports_per_1000", "unresolved_percent", "median_resolution_days", "period_start", "period_end", "source"},
        "local_reports",
    )
    if value.get("scope_kind") not in REPORT_SCOPES:
        raise ValueError("local report scope_kind is unsupported")
    nonempty(value, "geographic_scope")
    nullable_nonnegative(value, "reports_per_1000")
    unresolved = value.get("unresolved_percent")
    if unresolved is not None and (
        not isinstance(unresolved, (int, float))
        or isinstance(unresolved, bool)
        or not 0 <= unresolved <= 100
    ):
        raise ValueError("unresolved_percent must be null or between 0 and 100")
    nullable_nonnegative(value, "median_resolution_days")
    start = iso_date(nonempty(value, "period_start"), "period_start")
    end = iso_date(nonempty(value, "period_end"), "period_end")
    if end < start:
        raise ValueError("local report period_end cannot precede period_start")
    if all(
        value[field] is None
        for field in ("reports_per_1000", "unresolved_percent", "median_resolution_days")
    ):
        raise ValueError("local_reports must contain at least one measured value")
    _validate_source(value.get("source"), "local report source")


def _validate_visit_audit(value: Any, assessment_date: date) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError("visit_audit must be null or an object")
    exact_keys(
        value,
        {"audited_at", "geographic_scope", "ratings", "notes"},
        "visit_audit",
    )
    audited_at = iso_date(nonempty(value, "audited_at"), "audited_at")
    if audited_at > assessment_date:
        raise ValueError("visit audit cannot be later than assessment_date")
    nonempty(value, "geographic_scope")
    nonempty(value, "notes")
    ratings = value.get("ratings")
    if not isinstance(ratings, dict):
        raise ValueError("visit audit ratings must be an object")
    exact_keys(ratings, set(AUDIT_FIELDS), "visit audit ratings")
    for field in AUDIT_FIELDS:
        rating = ratings[field]
        if not isinstance(rating, int) or isinstance(rating, bool) or not 0 <= rating <= 4:
            raise ValueError("visit audit ratings must be integers from 0 to 4")


def _validate_source(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    exact_keys(
        value,
        {"label", "url", "retrieved_at", "source_date", "licence"},
        label,
    )
    nonempty(value, "label")
    http_url(nonempty(value, "url"), "source url")
    retrieved = iso_datetime(nonempty(value, "retrieved_at"), "retrieved_at")
    source_date = iso_date(nonempty(value, "source_date"), "source_date")
    if source_date > retrieved.date():
        raise ValueError("street-care source_date cannot be later than retrieved_at")
    nonempty(value, "licence")


def _component(
    key: str,
    raw_value: float | None,
    unit: str,
    normalized_score: float | None,
    weight: float,
    *,
    included: bool = True,
) -> dict[str, Any]:
    return {
        "key": key,
        "raw_value": raw_value,
        "unit": unit,
        "normalized_score": (
            None if normalized_score is None else round(normalized_score, 2)
        ),
        "weight": weight,
        "included": included,
    }


def _percent_change(previous: float, current: float) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return ((current - previous) / previous) * 100
