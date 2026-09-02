"""Validate and merge cited, shortlist-only housing market research."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .validation import validate_basis, validate_evidence, validate_profile
from .fields import exact_keys, http_url, iso_date, iso_datetime, nonempty, positive_number


MODES = {"buy", "rent"}
RENT_GEOGRAPHIES = {"local_authority", "broad_rental_market_area", "region"}


def configure_housing_profile(
    profile: dict[str, Any], housing_research: dict[str, Any]
) -> dict[str, Any]:
    """Return a profile whose housing requirements match the private input."""
    configured = deepcopy(profile)
    requirements = deepcopy(housing_research.get("requirements"))
    validate_housing_research(housing_research, set(), allow_unknown_candidates=True)
    current = configured["search"].get("housing", {})
    if current:
        for key, value in requirements.items():
            if current.get(key) != value:
                raise ValueError(f"housing research {key} does not match the run profile")
    configured["search"]["housing"] = requirements
    validate_profile(configured)
    return configured


def merge_housing_research(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    housing_research: dict[str, Any],
) -> dict[str, Any]:
    """Return evidence enriched by cited market facts for existing candidates only."""
    validate_profile(profile)
    validate_evidence(evidence)
    candidate_ids = {candidate["id"] for candidate in evidence["candidates"]}
    validate_housing_research(housing_research, candidate_ids)
    if profile["search"].get("housing") != housing_research["requirements"]:
        raise ValueError("housing research requirements do not match the run profile")

    merged = deepcopy(evidence)
    researched_candidates = {
        market["candidate_id"] for market in housing_research["markets"]
    }
    merged["observations"] = [
        observation
        for observation in merged["observations"]
        if not (
            observation["candidate_id"] in researched_candidates
            and observation["metric"] == "housing_affordability"
        )
    ]
    for market in housing_research["markets"]:
        merged["observations"].append(
            _affordability_observation(market, housing_research["requirements"])
        )
    merged["housing_research"] = deepcopy(housing_research)
    validate_evidence(merged)
    return merged


def validate_housing_research(
    housing_research: dict[str, Any],
    allowed_candidate_ids: set[str],
    *,
    allow_unknown_candidates: bool = False,
) -> None:
    exact_keys(
        housing_research,
        {"schema_version", "provider", "requirements", "markets"},
        "housing research",
    )
    if housing_research.get("schema_version") != "1":
        raise ValueError("unsupported housing research schema_version")
    nonempty(housing_research, "provider")
    requirements = housing_research.get("requirements")
    if not isinstance(requirements, dict):
        raise ValueError("housing research requirements must be an object")
    exact_keys(
        requirements,
        {"mode", "budget_gbp", "property_type", "bedrooms"},
        "housing requirements",
    )
    mode = requirements.get("mode")
    if mode not in MODES:
        raise ValueError("housing mode must be buy or rent")
    positive_number(requirements, "budget_gbp")
    nonempty(requirements, "property_type")
    bedrooms = requirements.get("bedrooms")
    if bedrooms is not None and (
        not isinstance(bedrooms, int) or isinstance(bedrooms, bool) or bedrooms < 0
    ):
        raise ValueError("housing bedrooms must be null or a non-negative integer")

    markets = housing_research.get("markets")
    if not isinstance(markets, list) or not markets:
        raise ValueError("housing research markets must be a non-empty array")
    market_ids: set[str] = set()
    candidate_ids: set[str] = set()
    required_source_kind = "transactions" if mode == "buy" else "rents"
    for market in markets:
        if not isinstance(market, dict):
            raise ValueError("housing markets must be objects")
        exact_keys(
            market,
            {
                "id", "candidate_id", "typical_cost_gbp", "statistic",
                "geography", "period_start", "period_end", "sample_size",
                "listing_search_url", "confidence", "confidence_notes", "sources",
                "basis",
            },
            "housing market",
        )
        market_id = nonempty(market, "id")
        if market_id in market_ids:
            raise ValueError(f"duplicate housing market id: {market_id}")
        market_ids.add(market_id)
        candidate_id = nonempty(market, "candidate_id")
        if not allow_unknown_candidates and candidate_id not in allowed_candidate_ids:
            raise ValueError("housing market is outside the candidate shortlist")
        if candidate_id in candidate_ids:
            raise ValueError("each researched candidate must have one housing market")
        candidate_ids.add(candidate_id)
        positive_number(market, "typical_cost_gbp")
        if market.get("statistic") not in {"median", "mean"}:
            raise ValueError("housing statistic must be median or mean")
        start = iso_date(nonempty(market, "period_start"), "period_start")
        end = iso_date(nonempty(market, "period_end"), "period_end")
        if end < start:
            raise ValueError("housing period_end cannot precede period_start")
        sample_size = market.get("sample_size")
        if sample_size is not None and (
            not isinstance(sample_size, int)
            or isinstance(sample_size, bool)
            or sample_size < 1
        ):
            raise ValueError("housing sample_size must be null or a positive integer")
        if mode == "buy" and sample_size is None:
            raise ValueError("purchase evidence requires a sample_size")
        listing_url = market.get("listing_search_url")
        if listing_url is not None:
            http_url(listing_url, "listing_search_url")
        confidence = market.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("housing confidence must be between 0 and 1")
        validate_basis(market, float(confidence), "housing market")
        nonempty(market, "confidence_notes")
        _validate_geography(market.get("geography"), mode)
        source_kinds = _validate_sources(market.get("sources"))
        if required_source_kind not in source_kinds:
            raise ValueError(
                f"{mode} housing evidence requires a {required_source_kind} source"
            )


def _affordability_observation(
    market: dict[str, Any], requirements: dict[str, Any]
) -> dict[str, Any]:
    required_kind = "transactions" if requirements["mode"] == "buy" else "rents"
    source = next(item for item in market["sources"] if item["kind"] == required_kind)
    ratio = float(market["typical_cost_gbp"]) / float(requirements["budget_gbp"])
    basis = "purchase price" if requirements["mode"] == "buy" else "monthly rent"
    return {
        "id": f"{market['id']}-affordability",
        "candidate_id": market["candidate_id"],
        "metric": "housing_affordability",
        "value": ratio,
        "unit": "budget_ratio",
        "geographic_scope": market["geography"]["label"],
        "source": source["label"],
        "source_url": source["url"],
        "retrieved_at": source["retrieved_at"],
        "source_date": source["source_date"],
        "transformation": (
            f"Typical {basis} divided by the configured {basis} budget; "
            "market evidence does not establish live inventory"
        ),
        "licence": source["licence"],
        "confidence": market["confidence"],
        "confidence_notes": market["confidence_notes"],
        "basis": market["basis"],
    }


def _validate_geography(value: Any, mode: str) -> None:
    if not isinstance(value, dict):
        raise ValueError("housing geography must be an object")
    exact_keys(value, {"kind", "label", "radius_km"}, "housing geography")
    kind = value.get("kind")
    nonempty(value, "label")
    radius = value.get("radius_km")
    if mode == "buy":
        if kind != "radius":
            raise ValueError("purchase evidence geography must be a radius")
        if (
            not isinstance(radius, (int, float))
            or isinstance(radius, bool)
            or not 0 < radius <= 5
        ):
            raise ValueError("purchase evidence radius_km must be above 0 and at most 5")
    else:
        if kind not in RENT_GEOGRAPHIES:
            raise ValueError("rent evidence must use a published aggregate geography")
        if radius is not None:
            raise ValueError("rent evidence cannot imply a radius-level estimate")


def _validate_sources(value: Any) -> set[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("housing sources must be a non-empty array")
    kinds: set[str] = set()
    for source in value:
        if not isinstance(source, dict):
            raise ValueError("housing sources must be objects")
        exact_keys(
            source,
            {"kind", "label", "url", "retrieved_at", "source_date", "licence"},
            "housing source",
        )
        kind = nonempty(source, "kind")
        if kind in kinds:
            raise ValueError(f"duplicate housing source kind: {kind}")
        kinds.add(kind)
        for field in ("label", "licence"):
            nonempty(source, field)
        http_url(nonempty(source, "url"), "source url")
        retrieved_at = iso_datetime(nonempty(source, "retrieved_at"), "retrieved_at")
        source_date = iso_date(nonempty(source, "source_date"), "source_date")
        if source_date > retrieved_at.date():
            raise ValueError("housing source_date cannot be later than retrieved_at")
    return kinds
