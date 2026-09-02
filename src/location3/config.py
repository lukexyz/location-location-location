"""Layer public preferences with optional private local overrides."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import tomllib

from .catalog import CATEGORIES, METRICS


def load_preferences(root: Path, include_local: bool = True) -> dict[str, Any]:
    preferences = _read_toml(root / "preferences.toml")
    local_path = root / "preferences.local.toml"
    if include_local and local_path.exists():
        preferences = _deep_merge(preferences, _read_toml(local_path))
    validate_preferences(preferences)
    return preferences


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Missing preferences file: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def validate_preferences(preferences: dict[str, Any]) -> None:
    if preferences.get("version") != 1:
        raise ValueError("preferences.version must be 1")
    weights = preferences.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise ValueError("preferences.weights must be a non-empty table")
    unknown_metrics = set(weights) - set(METRICS)
    if unknown_metrics:
        raise ValueError(f"Unknown metric weights: {', '.join(sorted(unknown_metrics))}")
    missing_metrics = set(METRICS) - set(weights)
    if missing_metrics:
        raise ValueError(f"Missing metric weights: {', '.join(sorted(missing_metrics))}")
    _validate_weights(weights, "metric")

    category_weights = preferences.get("category_weights")
    if not isinstance(category_weights, dict) or set(category_weights) != CATEGORIES:
        raise ValueError("category_weights must define essentials, environment, and amenities")
    _validate_weights(category_weights, "category")

    policy = preferences.get("scoring", {}).get("unknown_data_policy")
    if policy != "warn":
        raise ValueError('Only unknown_data_policy = "warn" is supported in v1')


def _validate_weights(weights: dict[str, Any], label: str) -> None:
    for key, value in weights.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{label} weight {key} must be a non-negative number")
