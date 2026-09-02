"""Small runtime validators for the v1 public bundle contracts."""

from __future__ import annotations

from typing import Any

from .catalog import METRICS


def validate_profile(profile: dict[str, Any]) -> None:
    _require(profile, "schema_version", str)
    _require(profile, "run_id", str)
    _require(profile, "search", dict)
    weights = _require(profile, "weights", dict)
    category_weights = _require(profile, "category_weights", dict)
    if set(weights) != set(METRICS):
        raise ValueError("profile weights do not match the metric catalogue")
    if not category_weights:
        raise ValueError("profile category_weights cannot be empty")
    constraints = profile.get("hard_constraints", [])
    if not isinstance(constraints, list):
        raise ValueError("profile hard_constraints must be an array")
    for constraint in constraints:
        if constraint.get("metric") not in METRICS:
            raise ValueError("hard constraint references an unknown metric")
        if constraint.get("operator") not in {"<=", ">="}:
            raise ValueError("hard constraint operator must be <= or >=")
        if not isinstance(constraint.get("value"), (int, float)):
            raise ValueError("hard constraint value must be numeric")


def validate_evidence(bundle: dict[str, Any]) -> None:
    _require(bundle, "schema_version", str)
    candidates = _require(bundle, "candidates", list)
    observations = _require(bundle, "observations", list)
    candidate_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = _require(candidate, "id", str)
        _require(candidate, "name", str)
        location = _require(candidate, "location", dict)
        _require(location, "latitude", (int, float))
        _require(location, "longitude", (int, float))
        if candidate_id in candidate_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        candidate_ids.add(candidate_id)

    observation_ids: set[str] = set()
    for observation in observations:
        observation_id = _require(observation, "id", str)
        if observation_id in observation_ids:
            raise ValueError(f"duplicate observation id: {observation_id}")
        observation_ids.add(observation_id)
        if _require(observation, "candidate_id", str) not in candidate_ids:
            raise ValueError("observation references an unknown candidate")
        metric = _require(observation, "metric", str)
        if metric not in METRICS:
            raise ValueError(f"unknown evidence metric: {metric}")
        _require(observation, "value", (int, float))
        if _require(observation, "unit", str) != METRICS[metric].unit:
            raise ValueError(f"unexpected unit for {metric}")
        confidence = _require(observation, "confidence", (int, float))
        if not 0 <= confidence <= 1:
            raise ValueError("observation confidence must be between 0 and 1")
        for key in (
            "geographic_scope", "source", "retrieved_at", "source_date",
            "transformation", "licence", "confidence_notes",
        ):
            _require(observation, key, str)


def _require(container: dict[str, Any], key: str, expected_type: Any) -> Any:
    value = container.get(key)
    if isinstance(value, bool) and expected_type != bool:
        raise ValueError(f"{key} has the wrong type")
    if not isinstance(value, expected_type):
        raise ValueError(f"{key} has the wrong type or is missing")
    return value
