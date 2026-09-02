"""Bounded OpenRouteService isochrone adapter."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from .net import HttpTransport, UrllibTransport
from .validation import validate_polygon_geometry


DEFAULT_ORS_ENDPOINT = "https://api.openrouteservice.org"


@dataclass(frozen=True)
class RouteBoundary:
    geometry: dict[str, Any]
    provider: str
    profile: str
    duration_minutes: int
    retrieved_at: str | None = None


class OpenRouteServiceIsochrones:
    def __init__(
        self,
        api_key: str,
        *,
        transport: HttpTransport | None = None,
        endpoint: str = DEFAULT_ORS_ENDPOINT,
        timeout: float = 30.0,
        max_duration_minutes: int = 120,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenRouteService API key is required")
        self._api_key = api_key
        self._transport = transport or UrllibTransport()
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout
        self._max_duration_minutes = max_duration_minutes

    def boundary(
        self,
        latitude: float,
        longitude: float,
        duration_minutes: int,
        *,
        profile: str = "driving-car",
    ) -> RouteBoundary:
        _coordinate(latitude, longitude)
        if not isinstance(duration_minutes, int) or isinstance(duration_minutes, bool):
            raise ValueError("duration_minutes must be a whole number")
        if not 1 <= duration_minutes <= self._max_duration_minutes:
            raise ValueError(
                f"duration_minutes must be between 1 and {self._max_duration_minutes}"
            )
        if profile not in {"driving-car", "cycling-regular", "foot-walking"}:
            raise ValueError("unsupported routing profile")

        body = json.dumps({
            "locations": [[longitude, latitude]],
            "range": [duration_minutes * 60],
            "range_type": "time",
        }, separators=(",", ":")).encode("utf-8")
        response = self._transport.request(
            "POST",
            f"{self._endpoint}/v2/isochrones/{profile}",
            headers={
                "Accept": "application/geo+json, application/json",
                "Authorization": self._api_key,
                "Content-Type": "application/json",
                "User-Agent": "location3/0.1",
            },
            body=body,
            timeout=self._timeout,
        )
        if not 200 <= response.status < 300:
            raise RuntimeError(f"OpenRouteService returned HTTP {response.status}")
        payload = _json_object(response.body, "OpenRouteService")
        features = payload.get("features")
        if not isinstance(features, list) or len(features) != 1:
            raise ValueError("OpenRouteService response must contain one isochrone feature")
        feature = features[0]
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not isinstance(geometry, dict):
            raise ValueError("OpenRouteService response has no polygon geometry")
        validate_polygon_geometry(geometry)
        return RouteBoundary(
            geometry=geometry,
            provider="openrouteservice",
            profile=profile,
            duration_minutes=duration_minutes,
            retrieved_at=response.headers.get("X-Location3-Retrieved-At"),
        )


def _coordinate(latitude: float, longitude: float) -> None:
    if isinstance(latitude, bool) or not isinstance(latitude, (int, float)):
        raise ValueError("latitude must be numeric")
    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
        raise ValueError("longitude must be numeric")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("origin coordinates are out of range")


def _json_object(body: bytes, provider: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{provider} returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{provider} response must be an object")
    return payload
