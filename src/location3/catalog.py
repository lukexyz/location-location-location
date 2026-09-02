"""The versioned launch metric catalogue and its deterministic score curves."""

from __future__ import annotations

from dataclasses import dataclass
from math import log1p


SCORING_VERSION = "1"


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    category: str
    unit: str
    curve: str
    anchors: tuple[tuple[float, float], ...] = ()
    saturation: float | None = None
    negative: bool = False

    def score(self, raw_value: float) -> float:
        """Map a raw observation onto an inspectable 0–100 desirability scale."""
        value = float(raw_value)
        if self.curve == "piecewise":
            result = _piecewise(value, self.anchors)
        elif self.curve == "log_saturation":
            if self.saturation is None or self.saturation <= 0:
                raise ValueError(f"{self.key} has an invalid saturation point")
            result = 100.0 * log1p(max(0.0, value)) / log1p(self.saturation)
            result = min(100.0, result)
        elif self.curve == "identity":
            result = value
        else:
            raise ValueError(f"Unsupported curve: {self.curve}")

        if self.negative:
            result = 100.0 - result
        return round(max(0.0, min(100.0, result)), 2)


def _piecewise(value: float, anchors: tuple[tuple[float, float], ...]) -> float:
    if len(anchors) < 2:
        raise ValueError("A piecewise curve needs at least two anchors")
    if value <= anchors[0][0]:
        return anchors[0][1]
    if value >= anchors[-1][0]:
        return anchors[-1][1]
    for (left_x, left_y), (right_x, right_y) in zip(anchors, anchors[1:]):
        if left_x <= value <= right_x:
            fraction = (value - left_x) / (right_x - left_x)
            return left_y + fraction * (right_y - left_y)
    raise AssertionError("unreachable")


METRICS: dict[str, MetricDefinition] = {
    "door_to_door_commute": MetricDefinition(
        "door_to_door_commute", "essentials", "minutes", "piecewise",
        ((20, 100), (45, 75), (75, 40), (120, 0)),
    ),
    "housing_affordability": MetricDefinition(
        "housing_affordability", "essentials", "budget_ratio", "piecewise",
        ((0.65, 100), (0.85, 85), (1.0, 60), (1.2, 20), (1.5, 0)),
    ),
    "street_care": MetricDefinition(
        "street_care", "environment", "desirability_score", "identity"
    ),
    "green_space": MetricDefinition(
        "green_space", "environment", "walk_minutes", "piecewise",
        ((0, 100), (5, 95), (15, 70), (30, 25), (45, 0)),
    ),
    "betting_shops": MetricDefinition(
        "betting_shops", "amenities", "count_15_min_walk", "log_saturation",
        saturation=5, negative=True,
    ),
    "cafes": MetricDefinition(
        "cafes", "amenities", "count_15_min_walk", "log_saturation", saturation=12
    ),
    "yoga_studios": MetricDefinition(
        "yoga_studios", "amenities", "count_15_min_walk", "log_saturation", saturation=5
    ),
    "premium_grocers": MetricDefinition(
        "premium_grocers", "amenities", "count_15_min_walk", "log_saturation", saturation=4
    ),
}

CATEGORIES = {definition.category for definition in METRICS.values()}
