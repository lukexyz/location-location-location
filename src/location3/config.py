"""Layer public preferences with optional private local overrides."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import tomllib

from .catalog import CATEGORIES, METRICS
from .osm import BrandGroup


BRAND_GROUPS = {"premium_grocers"}


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

    brand_groups = preferences.get("brand_groups")
    if not isinstance(brand_groups, dict) or set(brand_groups) != BRAND_GROUPS:
        raise ValueError("brand_groups must define exactly: " + ", ".join(sorted(BRAND_GROUPS)))
    for name in BRAND_GROUPS:
        try:
            brand_group(preferences, name)
        except (TypeError, ValueError) as error:
            raise ValueError(f"brand_groups.{name} is invalid: {error}") from error


def brand_group(preferences: dict[str, Any], name: str) -> BrandGroup:
    """Build the named editable brand group from validated preferences."""
    group = preferences["brand_groups"][name]
    if not isinstance(group, dict) or set(group) != {"patterns", "shop_types"}:
        raise ValueError("expected patterns and shop_types")
    patterns, shop_types = group["patterns"], group["shop_types"]
    if not isinstance(patterns, list) or not isinstance(shop_types, list):
        raise ValueError("patterns and shop_types must be arrays of strings")
    return BrandGroup(patterns=tuple(patterns), shop_types=tuple(shop_types))


def _validate_weights(weights: dict[str, Any], label: str) -> None:
    for key, value in weights.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0 <= value <= 5
        ):
            raise ValueError(f"{label} weight {key} must be a number from 0 to 5")
