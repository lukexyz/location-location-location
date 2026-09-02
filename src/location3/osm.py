"""One-pass bounded OpenStreetMap candidate and café collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
import json
from typing import Any, Iterable
from urllib.parse import urlencode

from .net import HttpTransport, UrllibTransport
from .routing import RouteBoundary
from .validation import validate_evidence


DEFAULT_OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"


@dataclass(frozen=True)
class OsmCafeResearch:
    evidence: dict[str, Any]
    query: str
    provider: str


class OverpassCafeCollector:
    """Discover settlements and count nearby cafés from one Overpass response."""

    def __init__(
        self,
        *,
        transport: HttpTransport | None = None,
        endpoint: str = DEFAULT_OVERPASS_ENDPOINT,
        timeout: float = 45.0,
        query_timeout_seconds: int = 25,
        cafe_radius_metres: int = 1200,
        max_polygon_vertices: int = 80,
    ) -> None:
        if not 100 <= cafe_radius_metres <= 5000:
            raise ValueError("cafe_radius_metres must be between 100 and 5000")
        if not 8 <= max_polygon_vertices <= 200:
            raise ValueError("max_polygon_vertices must be between 8 and 200")
        self._transport = transport or UrllibTransport()
        self._endpoint = endpoint
        self._timeout = timeout
        self._query_timeout_seconds = query_timeout_seconds
        self._cafe_radius_metres = cafe_radius_metres
        self._max_polygon_vertices = max_polygon_vertices

    def collect(
        self,
        boundary: RouteBoundary,
        *,
        retrieved_at: str | None = None,
    ) -> OsmCafeResearch:
        requested_retrieval_time = retrieved_at
        retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
        ring = _outer_ring(boundary.geometry)
        ring = _limit_vertices(ring, self._max_polygon_vertices)
        polygon = " ".join(f"{latitude:.6f} {longitude:.6f}" for longitude, latitude in ring)
        south, west, north, east = _buffered_bounds(ring, self._cafe_radius_metres)
        query = (
            f"[out:json][timeout:{self._query_timeout_seconds}];\n"
            "(\n"
            f'  node["place"~"^(town|village)$"]["name"](poly:"{polygon}");\n'
            f'  nwr["amenity"="cafe"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});\n'
            ");\n"
            "out center tags qt;"
        )
        response = self._transport.request(
            "POST",
            self._endpoint,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                "User-Agent": "location3/0.1",
            },
            body=urlencode({"data": query}).encode("utf-8"),
            timeout=self._timeout,
        )
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Overpass returned HTTP {response.status}")
        if requested_retrieval_time is None:
            retrieved_at = response.headers.get("X-Location3-Retrieved-At", retrieved_at)
        payload = _json_object(response.body)
        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise ValueError("Overpass response has no elements array")

        candidates = _candidates(elements)
        cafes = _cafes(elements)
        source_date = _source_date(payload, retrieved_at)
        observations = [
            _cafe_observation(
                candidate,
                cafes,
                radius_metres=self._cafe_radius_metres,
                retrieved_at=retrieved_at,
                source_date=source_date,
            )
            for candidate in candidates
        ]
        evidence = {
            "schema_version": "1",
            "candidates": candidates,
            "observations": observations,
        }
        validate_evidence(evidence)
        return OsmCafeResearch(evidence=evidence, query=query, provider="overpass")


def _outer_ring(geometry: dict[str, Any]) -> list[list[float]]:
    coordinates = geometry.get("coordinates")
    polygons = coordinates if geometry.get("type") == "MultiPolygon" else [coordinates]
    try:
        rings = [polygon[0] for polygon in polygons if polygon and polygon[0]]
        ring = max(rings, key=len)
    except (TypeError, ValueError) as error:
        raise ValueError("route boundary has no usable exterior ring") from error
    clean: list[list[float]] = []
    for coordinate in ring:
        if (
            not isinstance(coordinate, list)
            or len(coordinate) < 2
            or isinstance(coordinate[0], bool)
            or isinstance(coordinate[1], bool)
            or not isinstance(coordinate[0], (int, float))
            or not isinstance(coordinate[1], (int, float))
        ):
            raise ValueError("route boundary contains an invalid coordinate")
        longitude, latitude = float(coordinate[0]), float(coordinate[1])
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError("route boundary coordinate is out of range")
        clean.append([longitude, latitude])
    if len(clean) < 4:
        raise ValueError("route boundary exterior ring is too small")
    if clean[0] != clean[-1]:
        clean.append(clean[0])
    return clean


def _limit_vertices(ring: list[list[float]], maximum: int) -> list[list[float]]:
    points = ring[:-1]
    if len(points) <= maximum - 1:
        return ring
    selected = [
        points[round(index * (len(points) - 1) / (maximum - 2))]
        for index in range(maximum - 1)
    ]
    return selected + [selected[0]]


def _buffered_bounds(
    ring: list[list[float]], radius_metres: int
) -> tuple[float, float, float, float]:
    latitudes = [coordinate[1] for coordinate in ring]
    longitudes = [coordinate[0] for coordinate in ring]
    latitude_delta = radius_metres / 111_320
    furthest_latitude = max(abs(min(latitudes)), abs(max(latitudes)))
    longitude_scale = max(0.01, cos(radians(furthest_latitude)))
    longitude_delta = radius_metres / (111_320 * longitude_scale)
    return (
        max(-90.0, min(latitudes) - latitude_delta),
        max(-180.0, min(longitudes) - longitude_delta),
        min(90.0, max(latitudes) + latitude_delta),
        min(180.0, max(longitudes) + longitude_delta),
    )


def _candidates(elements: Iterable[Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for element in elements:
        if not isinstance(element, dict) or element.get("type") != "node":
            continue
        tags = element.get("tags")
        if not isinstance(tags, dict) or tags.get("place") not in {"town", "village"}:
            continue
        name = tags.get("name")
        osm_id = element.get("id")
        point = _element_point(element)
        if not isinstance(name, str) or not name.strip() or point is None or not _osm_id(osm_id):
            continue
        latitude, longitude = point
        found.append({
            "id": f"osm-node-{osm_id}",
            "name": name.strip(),
            "location": {"latitude": latitude, "longitude": longitude},
        })
    return sorted(found, key=lambda candidate: (candidate["name"].casefold(), candidate["id"]))


def _cafes(elements: Iterable[Any]) -> list[tuple[str, float, float]]:
    found: dict[str, tuple[str, float, float]] = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags")
        osm_type = element.get("type")
        osm_id = element.get("id")
        if (
            not isinstance(tags, dict)
            or tags.get("amenity") != "cafe"
            or osm_type not in {"node", "way", "relation"}
            or not _osm_id(osm_id)
        ):
            continue
        point = _element_point(element)
        if point is not None:
            latitude, longitude = point
            key = f"{osm_type}/{osm_id}"
            found[key] = (key, latitude, longitude)
    return list(found.values())


def _element_point(element: dict[str, Any]) -> tuple[float, float] | None:
    source = element if element.get("type") == "node" else element.get("center")
    if not isinstance(source, dict):
        return None
    latitude, longitude = source.get("lat"), source.get("lon")
    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None
    return float(latitude), float(longitude)


def _osm_id(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _cafe_observation(
    candidate: dict[str, Any],
    cafes: Iterable[tuple[str, float, float]],
    *,
    radius_metres: int,
    retrieved_at: str,
    source_date: str,
) -> dict[str, Any]:
    location = candidate["location"]
    count = sum(
        _distance_metres(location["latitude"], location["longitude"], latitude, longitude)
        <= radius_metres
        for _, latitude, longitude in cafes
    )
    return {
        "id": f'{candidate["id"]}-cafes',
        "candidate_id": candidate["id"],
        "metric": "cafes",
        "value": count,
        "unit": "count_15_min_walk",
        "geographic_scope": f"{radius_metres} m straight-line catchment around OSM place node",
        "source": "OpenStreetMap contributors via Overpass API",
        "source_url": "https://www.openstreetmap.org/copyright",
        "retrieved_at": retrieved_at,
        "source_date": source_date,
        "transformation": (
            "Distinct OSM amenity=cafe features within a straight-line radius; "
            "a bounded proxy, not a pedestrian-network isochrone"
        ),
        "licence": "ODbL-1.0",
        "confidence": 0.65,
        "confidence_notes": (
            "OSM completeness varies by area; catchment uses a straight-line proxy for a "
            "15-minute walk"
        ),
    }


def _distance_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    latitude_delta = radians(lat2 - lat1)
    longitude_delta = radians(lon2 - lon1)
    a = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(longitude_delta / 2) ** 2
    )
    return 6_371_008.8 * 2 * asin(sqrt(a))


def _json_object(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Overpass returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("Overpass response must be an object")
    return payload


def _source_date(payload: dict[str, Any], retrieved_at: str) -> str:
    metadata = payload.get("osm3s")
    timestamp = metadata.get("timestamp_osm_base") if isinstance(metadata, dict) else None
    if isinstance(timestamp, str) and len(timestamp) >= 10:
        return timestamp[:10]
    return retrieved_at[:10]
