"""One-pass bounded OpenStreetMap candidate discovery and amenity collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any, Iterable, Sequence
from urllib.parse import urlencode

from .catalog import PLACE_KINDS
from .net import HttpTransport, UrllibTransport
from .routing import RouteBoundary
from .validation import validate_evidence
from .walking import (
    CATCHMENT_METRES,
    CATCHMENT_MINUTES,
    FEATURE_SNAP_METRES,
    ORIGIN_SNAP_METRES,
    WALK_METRES_PER_MINUTE,
    WALKABLE_HIGHWAYS,
    Reach,
    WalkingNetwork,
    distance_metres,
)


DEFAULT_OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
OSM_SOURCE = "OpenStreetMap contributors via Overpass API"
OSM_SOURCE_URL = "https://www.openstreetmap.org/copyright"
OSM_LICENCE = "ODbL-1.0"

# When two anchors sit within `dedupe_metres` of each other the more significant
# PLACE_KINDS entry is kept.
GREEN_SPACE_CUTOFF_MINUTES = 45
# The network is fetched slightly beyond the catchment so edge features can snap.
NETWORK_MARGIN_METRES = 100
GREEN_SPACE_TAGS = {
    "leisure": ("park", "nature_reserve", "recreation_ground", "common", "dog_park"),
    "landuse": ("recreation_ground", "village_green"),
}
COUNT_METRICS: tuple[str, ...] = ("cafes", "betting_shops", "yoga_studios", "premium_grocers")
_SAFE_PATTERN = re.compile(r"^[A-Za-z0-9 &'._\-]+$")
_ERE_SPECIALS = set(".^$*+?()[]{}|\\")


@dataclass(frozen=True)
class BrandGroup:
    """Literal brand/name fragments matched case-insensitively within shop types."""

    patterns: tuple[str, ...]
    shop_types: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.patterns or not self.shop_types:
            raise ValueError("brand group needs patterns and shop_types")
        for value in (*self.patterns, *self.shop_types):
            if not isinstance(value, str) or not _SAFE_PATTERN.fullmatch(value):
                raise ValueError(f"unsafe brand configuration value: {value!r}")
        if any(" " in shop_type for shop_type in self.shop_types):
            raise ValueError("shop_types must be single OSM shop values")

    def overpass_regex(self) -> str:
        return "(" + "|".join(_ere_escape(pattern) for pattern in self.patterns) + ")"

    def shop_regex(self) -> str:
        return "^(" + "|".join(_ere_escape(value) for value in self.shop_types) + ")$"

    def matches(self, tags: dict[str, Any]) -> bool:
        if tags.get("shop") not in self.shop_types:
            return False
        names = [tags.get("brand"), tags.get("name")]
        return any(
            isinstance(name, str)
            and any(pattern.casefold() in name.casefold() for pattern in self.patterns)
            for name in names
        )


def _ere_escape(value: str) -> str:
    """Escape POSIX ERE metacharacters only; spaces and & stay literal."""
    return "".join(f"\\{char}" if char in _ERE_SPECIALS else char for char in value)


@dataclass(frozen=True)
class OsmResearch:
    evidence: dict[str, Any]
    query: str
    provider: str
    measured_metrics: tuple[str, ...] = ()
    # (vertices sent to Overpass, vertices in the provider boundary)
    polygon_vertices: tuple[int, int] = (0, 0)


class OverpassAmenityCollector:
    """Discover settlements and measure walkable amenities from one Overpass call."""

    def __init__(
        self,
        *,
        premium_grocers: BrandGroup,
        transport: HttpTransport | None = None,
        endpoint: str = DEFAULT_OVERPASS_ENDPOINT,
        timeout: float = 90.0,
        query_timeout_seconds: int = 60,
        walk_radius_metres: int = CATCHMENT_METRES,
        max_polygon_vertices: int = 80,
        dedupe_metres: int = 400,
        place_kinds: Sequence[str] = PLACE_KINDS,
    ) -> None:
        if not 100 <= walk_radius_metres <= 5000:
            raise ValueError("walk_radius_metres must be between 100 and 5000")
        if not 8 <= max_polygon_vertices <= 200:
            raise ValueError("max_polygon_vertices must be between 8 and 200")
        if not 0 <= dedupe_metres <= 2000:
            raise ValueError("dedupe_metres must be between 0 and 2000")
        if not place_kinds or any(kind not in PLACE_KINDS for kind in place_kinds):
            raise ValueError("place_kinds must be drawn from the supported OSM place kinds")
        self._premium_grocers = premium_grocers
        self._transport = transport or UrllibTransport()
        self._endpoint = endpoint
        self._timeout = timeout
        self._query_timeout_seconds = query_timeout_seconds
        self._walk_radius_metres = walk_radius_metres
        self._max_polygon_vertices = max_polygon_vertices
        self._dedupe_metres = dedupe_metres
        self._place_kinds = tuple(kind for kind in PLACE_KINDS if kind in place_kinds)

    @property
    def metrics(self) -> tuple[str, ...]:
        return COUNT_METRICS + ("green_space",)

    def select_metrics(self, metrics: Iterable[str] | None) -> tuple[str, ...]:
        """Restrict collection to the requested subset of this collector's metrics."""
        if metrics is None:
            return self.metrics
        chosen = set(metrics)
        return tuple(metric for metric in self.metrics if metric in chosen)

    def build_query(
        self, boundary: RouteBoundary, metrics: Iterable[str] | None = None
    ) -> str:
        selected = self.select_metrics(metrics)
        ring = _limit_vertices(_outer_ring(boundary.geometry), self._max_polygon_vertices)
        polygon = " ".join(f"{latitude:.6f} {longitude:.6f}" for longitude, latitude in ring)
        poi_reach = self._walk_radius_metres
        kinds = "|".join(self._place_kinds)
        lines = [
            f"[out:json][timeout:{self._query_timeout_seconds}];",
            f'node["place"~"^({kinds})$"]["name"](poly:"{polygon}")->.places;',
            ".places out qt;",
        ]
        poi_clauses: list[str] = []
        if "cafes" in selected:
            poi_clauses.append(f'  nwr["amenity"="cafe"](around.places:{poi_reach});')
        if "betting_shops" in selected:
            poi_clauses.append(f'  nwr["shop"="bookmaker"](around.places:{poi_reach});')
            poi_clauses.append(f'  nwr["amenity"="gambling"](around.places:{poi_reach});')
        if "yoga_studios" in selected:
            poi_clauses.append(
                f'  nwr["sport"~"(^|;)yoga(;|$)",i](around.places:{poi_reach});'
            )
        if "premium_grocers" in selected:
            grocers = self._premium_grocers
            shop_filter = f'["shop"~"{grocers.shop_regex()}"]'
            poi_clauses.append(
                f'  nwr{shop_filter}["brand"~"{grocers.overpass_regex()}",i]'
                f"(around.places:{poi_reach});"
            )
            poi_clauses.append(
                f'  nwr{shop_filter}["name"~"{grocers.overpass_regex()}",i]'
                f"(around.places:{poi_reach});"
            )
        if poi_clauses:
            # `body` keeps node coordinates. `tags` verbosity would omit them and
            # silently drop every point of interest mapped as a node.
            lines += ["(", *poi_clauses, ")->.pois;", ".pois out center body qt;"]
        if "green_space" in selected:
            green_reach = GREEN_SPACE_CUTOFF_MINUTES * WALK_METRES_PER_MINUTE
            leisure = "|".join(GREEN_SPACE_TAGS["leisure"])
            landuse = "|".join(GREEN_SPACE_TAGS["landuse"])
            lines += [
                "(",
                f'  nwr["leisure"~"^({leisure})$"]["access"!="private"]'
                f"(around.places:{green_reach});",
                f'  nwr["landuse"~"^({landuse})$"]["access"!="private"]'
                f"(around.places:{green_reach});",
                ")->.green;",
                ".green out bb body qt;",
            ]
        if poi_clauses:
            network_reach = self._walk_radius_metres + NETWORK_MARGIN_METRES
            highways = "|".join(WALKABLE_HIGHWAYS)
            lines += [
                f'way["highway"~"^({highways})$"]["foot"!~"^(no|private)$"]'
                f'["access"!="private"](around.places:{network_reach})->.network;',
                ".network out geom qt;",
            ]
        return "\n".join(lines)

    def collect(
        self,
        boundary: RouteBoundary,
        *,
        metrics: Iterable[str] | None = None,
        retrieved_at: str | None = None,
    ) -> OsmResearch:
        selected = self.select_metrics(metrics)
        requested_retrieval_time = retrieved_at
        retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
        outer_ring = _outer_ring(boundary.geometry)
        sent_ring = _limit_vertices(outer_ring, self._max_polygon_vertices)
        query = self.build_query(boundary, selected)
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

        candidates = _dedupe_candidates(
            _candidates(elements, self._place_kinds), self._dedupe_metres
        )
        features = _classify(elements, self._premium_grocers)
        count_metrics = tuple(metric for metric in COUNT_METRICS if metric in selected)
        network = WalkingNetwork.from_elements(elements) if count_metrics else None
        source_date = _source_date(payload, retrieved_at)
        observations: list[dict[str, Any]] = []
        for candidate in candidates:
            location = candidate["location"]
            reach = (
                network.reach(
                    location["latitude"], location["longitude"], self._walk_radius_metres
                )
                if network is not None else None
            )
            for metric in count_metrics:
                observations.append(
                    _count_observation(
                        candidate,
                        metric,
                        features[metric],
                        radius_metres=self._walk_radius_metres,
                        retrieved_at=retrieved_at,
                        source_date=source_date,
                        network=network,
                        reach=reach,
                    )
                )
            if "green_space" in selected:
                green = _green_space_observation(
                    candidate, features["green_space"], retrieved_at, source_date
                )
                if green is not None:
                    observations.append(green)
        evidence = {
            "schema_version": "1",
            "candidates": candidates,
            "observations": observations,
        }
        validate_evidence(evidence)
        return OsmResearch(
            evidence=evidence,
            query=query,
            provider="overpass",
            measured_metrics=selected,
            polygon_vertices=(len(sent_ring) - 1, len(outer_ring) - 1),
        )


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


def _candidates(elements: Iterable[Any], kinds: Sequence[str]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for element in elements:
        if not isinstance(element, dict) or element.get("type") != "node":
            continue
        tags = element.get("tags")
        if not isinstance(tags, dict) or tags.get("place") not in kinds:
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
            "place_kind": tags["place"],
            "location": {"latitude": latitude, "longitude": longitude},
        })
    return sorted(found, key=lambda candidate: (candidate["name"].casefold(), candidate["id"]))


def _dedupe_candidates(
    candidates: list[dict[str, Any]], dedupe_metres: int
) -> list[dict[str, Any]]:
    """Keep the most significant anchor when several sit within dedupe_metres."""
    by_significance = sorted(
        candidates,
        key=lambda item: (
            PLACE_KINDS.index(item["place_kind"]), item["name"].casefold(), item["id"]
        ),
    )
    kept: list[dict[str, Any]] = []
    for candidate in by_significance:
        location = candidate["location"]
        if any(
            distance_metres(
                location["latitude"], location["longitude"],
                other["location"]["latitude"], other["location"]["longitude"],
            ) < dedupe_metres
            for other in kept
        ):
            continue
        kept.append(candidate)
    return sorted(kept, key=lambda candidate: (candidate["name"].casefold(), candidate["id"]))


def _classify(
    elements: Iterable[Any], premium_grocers: BrandGroup
) -> dict[str, list[tuple[str, dict[str, float]]]]:
    """Group returned features by metric, deduplicated by OSM type/id."""
    groups: dict[str, dict[str, dict[str, float]]] = {
        "cafes": {},
        "betting_shops": {},
        "yoga_studios": {},
        "premium_grocers": {},
        "green_space": {},
    }
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags")
        osm_type = element.get("type")
        osm_id = element.get("id")
        if (
            not isinstance(tags, dict)
            or osm_type not in {"node", "way", "relation"}
            or not _osm_id(osm_id)
        ):
            continue
        key = f"{osm_type}/{osm_id}"
        extent = _element_extent(element)
        if extent is None:
            continue
        if tags.get("amenity") == "cafe":
            groups["cafes"][key] = extent
        if tags.get("shop") == "bookmaker" or tags.get("amenity") == "gambling":
            groups["betting_shops"][key] = extent
        sport = tags.get("sport")
        if isinstance(sport, str) and "yoga" in {
            value.strip().casefold() for value in sport.split(";")
        }:
            groups["yoga_studios"][key] = extent
        if premium_grocers.matches(tags):
            groups["premium_grocers"][key] = extent
        if _is_green_space(tags):
            groups["green_space"][key] = extent
    return {metric: list(found.items()) for metric, found in groups.items()}


def _is_green_space(tags: dict[str, Any]) -> bool:
    if tags.get("access") == "private":
        return False
    return any(
        tags.get(tag) in values for tag, values in GREEN_SPACE_TAGS.items()
    )


def _element_extent(element: dict[str, Any]) -> dict[str, float] | None:
    """Return a point or a bounding box usable for distance measurement."""
    bounds = element.get("bounds")
    if isinstance(bounds, dict):
        values = [bounds.get(key) for key in ("minlat", "minlon", "maxlat", "maxlon")]
        if all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in values
        ):
            box = dict(zip(("minlat", "minlon", "maxlat", "maxlon"), map(float, values)))
            if (
                -90 <= box["minlat"] <= box["maxlat"] <= 90
                and -180 <= box["minlon"] <= box["maxlon"] <= 180
            ):
                return box
    point = _element_point(element)
    if point is None:
        return None
    latitude, longitude = point
    return {"minlat": latitude, "minlon": longitude, "maxlat": latitude, "maxlon": longitude}


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


def _extentdistance_metres(
    latitude: float, longitude: float, extent: dict[str, float]
) -> float:
    """Distance to the nearest point of a bounding box (zero when inside)."""
    nearest_latitude = min(max(latitude, extent["minlat"]), extent["maxlat"])
    nearest_longitude = min(max(longitude, extent["minlon"]), extent["maxlon"])
    return distance_metres(latitude, longitude, nearest_latitude, nearest_longitude)


_COUNT_METRIC_NOTES = {
    "cafes": ("OSM amenity=cafe", 0.65, "café completeness varies by area"),
    "betting_shops": (
        "OSM shop=bookmaker or amenity=gambling", 0.6,
        "bookmakers are usually mapped; adult gaming centres less consistently",
    ),
    "yoga_studios": (
        "OSM features tagged sport=yoga", 0.5,
        "yoga classes inside gyms or halls are often untagged",
    ),
    "premium_grocers": (
        "OSM shops whose brand or name matches the configured premium grocer group", 0.7,
        "brand tags are usually present for national chains",
    ),
}
# Network catchments remove the straight-line guess, so the same coverage earns more trust.
NETWORK_CONFIDENCE_BONUS = 0.1


def _count_observation(
    candidate: dict[str, Any],
    metric: str,
    features: list[tuple[str, dict[str, float]]],
    *,
    radius_metres: int,
    retrieved_at: str,
    source_date: str,
    network: WalkingNetwork | None = None,
    reach: Reach | None = None,
) -> dict[str, Any]:
    location = candidate["location"]
    description, confidence, coverage_note = _COUNT_METRIC_NOTES[metric]
    minutes = radius_metres / WALK_METRES_PER_MINUTE
    if network is not None and reach is not None and reach.usable:
        count = sum(
            _walking_reachable(network, reach, location, extent, radius_metres)
            for _, extent in features
        )
        scope = (
            f"{minutes:g}-minute pedestrian-network catchment ({radius_metres} m at "
            f"{WALK_METRES_PER_MINUTE} m/min) from the OSM place node"
        )
        transformation = (
            f"Distinct {description} within {radius_metres} m walking distance along the "
            "OSM pedestrian network from the nearest walkable way to the place node; a "
            f"feature more than {FEATURE_SNAP_METRES} m from any walkable way is measured "
            "straight-line instead"
        )
        confidence = round(min(0.95, confidence + NETWORK_CONFIDENCE_BONUS), 2)
        notes = (
            f"OSM {coverage_note}; the catchment follows mapped footways and streets, so "
            "unmapped paths or shortcuts are not counted"
        )
    else:
        count = sum(
            _extentdistance_metres(location["latitude"], location["longitude"], extent)
            <= radius_metres
            for _, extent in features
        )
        reason = (
            "no walkable way was mapped within "
            f"{ORIGIN_SNAP_METRES} m of the place node"
            if network is not None and network.node_count
            else "the response carried no pedestrian network"
        )
        scope = f"{radius_metres} m straight-line catchment around OSM place node"
        transformation = (
            f"Distinct {description} within a straight-line radius; "
            f"a bounded proxy, not a pedestrian-network isochrone, because {reason}"
        )
        notes = (
            f"OSM {coverage_note}; catchment uses a straight-line proxy for a "
            f"{CATCHMENT_MINUTES}-minute walk"
        )
    return {
        "id": f'{candidate["id"]}-{metric.replace("_", "-")}',
        "candidate_id": candidate["id"],
        "metric": metric,
        "value": count,
        "unit": "count_15_min_walk",
        "geographic_scope": scope,
        "source": OSM_SOURCE,
        "source_url": OSM_SOURCE_URL,
        "retrieved_at": retrieved_at,
        "source_date": source_date,
        "transformation": transformation,
        "licence": OSM_LICENCE,
        "confidence": confidence,
        "confidence_notes": notes,
        "basis": "measured",
    }


def _walking_reachable(
    network: WalkingNetwork,
    reach: Reach,
    location: dict[str, float],
    extent: dict[str, float],
    radius_metres: int,
) -> bool:
    latitude = (extent["minlat"] + extent["maxlat"]) / 2
    longitude = (extent["minlon"] + extent["maxlon"]) / 2
    if not network.has_snappable_feature(latitude, longitude):
        return _extentdistance_metres(
            location["latitude"], location["longitude"], extent
        ) <= radius_metres
    metres = network.walking_metres(reach, latitude, longitude)
    return metres is not None and metres <= radius_metres


def _green_space_observation(
    candidate: dict[str, Any],
    features: list[tuple[str, dict[str, float]]],
    retrieved_at: str,
    source_date: str,
) -> dict[str, Any] | None:
    location = candidate["location"]
    distances = [
        _extentdistance_metres(location["latitude"], location["longitude"], extent)
        for _, extent in features
    ]
    if not distances:
        return None
    nearest_metres = min(distances)
    walk_minutes = round(nearest_metres / WALK_METRES_PER_MINUTE, 1)
    if walk_minutes > GREEN_SPACE_CUTOFF_MINUTES:
        # The query extent only guarantees coverage up to the cutoff distance.
        return None
    return {
        "id": f'{candidate["id"]}-green-space',
        "candidate_id": candidate["id"],
        "metric": "green_space",
        "value": walk_minutes,
        "unit": "walk_minutes",
        "geographic_scope": (
            f"Nearest public green space within {GREEN_SPACE_CUTOFF_MINUTES} walking minutes "
            "of the OSM place node"
        ),
        "source": OSM_SOURCE,
        "source_url": OSM_SOURCE_URL,
        "retrieved_at": retrieved_at,
        "source_date": source_date,
        "transformation": (
            "Straight-line distance to the nearest edge of the bounding box of an OSM park, "
            f"nature reserve, recreation ground, common, or village green, at "
            f"{WALK_METRES_PER_MINUTE} m per minute; a proxy, not a pedestrian-network route"
        ),
        "licence": OSM_LICENCE,
        "basis": "measured",
        "confidence": 0.6,
        "confidence_notes": (
            "Bounding-box distance can understate the walk to a park entrance; informal "
            "countryside access and footpaths are not counted"
        ),
    }


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
