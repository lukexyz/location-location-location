"""Field-level checks shared by every contract validator and importer.

These helpers raise ValueError with the offending field name so a failed import
tells the person exactly which value to fix. Keeping one copy means the rail,
housing, street-care, and bundle validators cannot drift apart.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable
from urllib.parse import urlsplit


def require(container: dict[str, Any], key: str, expected_type: Any) -> Any:
    value = container.get(key)
    if isinstance(value, bool) and expected_type is not bool:
        raise ValueError(f"{key} has the wrong type")
    if not isinstance(value, expected_type):
        raise ValueError(f"{key} has the wrong type or is missing")
    return value


def nonempty(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def exact_keys(container: dict[str, Any], expected: Iterable[str], label: str) -> None:
    if set(container) != set(expected):
        raise ValueError(f"{label} fields do not match the schema")


def nonnegative_number(container: dict[str, Any], key: str) -> float:
    value = container.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be a non-negative number")
    return float(value)


def positive_number(container: dict[str, Any], key: str) -> float:
    value = container.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{key} must be a positive number")
    return float(value)


def nullable_nonnegative(container: dict[str, Any], key: str) -> None:
    if container.get(key) is not None:
        nonnegative_number(container, key)


def http_url(value: str, field: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be an HTTP URL")
    return value


def iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO 8601 date") from error


def iso_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def piecewise(value: float, anchors: tuple[tuple[float, float], ...]) -> float:
    """Linear interpolation between documented anchors, clamped at both ends."""
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
