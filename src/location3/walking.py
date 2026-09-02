"""Deterministic pedestrian-network catchments built from Overpass way geometry."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from typing import Any, Iterable


# Highway classes a pedestrian can normally use. Motorways and trunk roads are
# excluded; tagged foot or private access restrictions are excluded in the query.
WALKABLE_HIGHWAYS: tuple[str, ...] = (
    "footway", "path", "pedestrian", "steps", "living_street", "residential", "service",
    "unclassified", "tertiary", "tertiary_link", "secondary", "secondary_link",
    "primary", "primary_link", "track", "cycleway", "bridleway", "road",
)
WALK_METRES_PER_MINUTE = 80
CATCHMENT_MINUTES = 15
CATCHMENT_METRES = WALK_METRES_PER_MINUTE * CATCHMENT_MINUTES
# A candidate must be this close to a walkable way for its catchment to be trusted.
ORIGIN_SNAP_METRES = 300
# A feature further than this from any walkable way is measured straight-line instead.
FEATURE_SNAP_METRES = 150
# Long straight way segments get synthetic intermediate nodes so snapping stays close.
MAX_SEGMENT_METRES = 50
_CELL_DEGREES = 0.004  # roughly 450 m of latitude


@dataclass(frozen=True)
class Reach:
    """Network distances from one origin, or None when the origin could not be snapped."""

    origin_node: int | None
    origin_offset_metres: float
    distances: dict[int, float] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.origin_node is not None


class WalkingNetwork:
    """An undirected pedestrian graph with haversine edge lengths."""

    def __init__(self) -> None:
        self._nodes: dict[int, tuple[float, float]] = {}
        self._edges: dict[int, list[tuple[int, float]]] = defaultdict(list)
        self._cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self._synthetic_count = 0

    @classmethod
    def from_elements(cls, elements: Iterable[Any]) -> "WalkingNetwork":
        network = cls()
        for element in elements:
            if not isinstance(element, dict) or element.get("type") != "way":
                continue
            tags = element.get("tags")
            if not isinstance(tags, dict) or tags.get("highway") not in WALKABLE_HIGHWAYS:
                continue
            node_ids = element.get("nodes")
            geometry = element.get("geometry")
            if (
                not isinstance(node_ids, list)
                or not isinstance(geometry, list)
                or len(node_ids) != len(geometry)
                or len(node_ids) < 2
            ):
                continue
            points: list[tuple[int, float, float]] = []
            for node_id, point in zip(node_ids, geometry):
                if (
                    isinstance(node_id, bool)
                    or not isinstance(node_id, int)
                    or not isinstance(point, dict)
                ):
                    points = []
                    break
                latitude, longitude = point.get("lat"), point.get("lon")
                if not _finite_coordinate(latitude, longitude):
                    points = []
                    break
                points.append((node_id, float(latitude), float(longitude)))
            for (left_id, left_lat, left_lon), (right_id, right_lat, right_lon) in zip(
                points, points[1:]
            ):
                network._add_node(left_id, left_lat, left_lon)
                network._add_node(right_id, right_lat, right_lon)
                if left_id == right_id:
                    continue
                network._add_segment(left_id, left_lat, left_lon, right_id, right_lat, right_lon)
        return network

    def _add_segment(
        self,
        left_id: int,
        left_lat: float,
        left_lon: float,
        right_id: int,
        right_lat: float,
        right_lon: float,
    ) -> None:
        """Link two way nodes, inserting synthetic nodes so long segments snap accurately."""
        metres = distance_metres(left_lat, left_lon, right_lat, right_lon)
        pieces = int(metres // MAX_SEGMENT_METRES)
        if metres % MAX_SEGMENT_METRES or pieces == 0:
            pieces += 1
        previous_id, previous_lat, previous_lon = left_id, left_lat, left_lon
        for step in range(1, pieces + 1):
            if step == pieces:
                next_id, next_lat, next_lon = right_id, right_lat, right_lon
            else:
                fraction = step / pieces
                next_lat = left_lat + (right_lat - left_lat) * fraction
                next_lon = left_lon + (right_lon - left_lon) * fraction
                self._synthetic_count += 1
                next_id = -self._synthetic_count
                self._add_node(next_id, next_lat, next_lon)
            length = distance_metres(previous_lat, previous_lon, next_lat, next_lon)
            self._edges[previous_id].append((next_id, length))
            self._edges[next_id].append((previous_id, length))
            previous_id, previous_lat, previous_lon = next_id, next_lat, next_lon

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def nearest_node(
        self, latitude: float, longitude: float, max_metres: float
    ) -> tuple[int, float] | None:
        best: tuple[int, float] | None = None
        for node_id in self._nearby_node_ids(latitude, longitude, max_metres):
            node_lat, node_lon = self._nodes[node_id]
            metres = distance_metres(latitude, longitude, node_lat, node_lon)
            if metres <= max_metres and (best is None or metres < best[1]):
                best = (node_id, metres)
        return best

    def reach(self, latitude: float, longitude: float, cutoff_metres: float) -> Reach:
        """Dijkstra from the nearest walkable node, bounded by the catchment cutoff."""
        origin = self.nearest_node(latitude, longitude, ORIGIN_SNAP_METRES)
        if origin is None:
            return Reach(origin_node=None, origin_offset_metres=0.0)
        origin_node, offset = origin
        distances: dict[int, float] = {origin_node: offset}
        frontier: list[tuple[float, int]] = [(offset, origin_node)]
        while frontier:
            current, node_id = heappop(frontier)
            if current > distances.get(node_id, float("inf")):
                continue
            for neighbour, metres in self._edges[node_id]:
                candidate = current + metres
                if candidate > cutoff_metres or candidate >= distances.get(neighbour, float("inf")):
                    continue
                distances[neighbour] = candidate
                heappush(frontier, (candidate, neighbour))
        return Reach(origin_node=origin_node, origin_offset_metres=offset, distances=distances)

    def walking_metres(
        self, reach: Reach, latitude: float, longitude: float
    ) -> float | None:
        """Network distance via the feature's nearest walkable node, or None if unreachable.

        The feature snaps to its single nearest node so the measurement is
        explainable: walk the network to that node, then the short straight offset.
        """
        if not reach.usable:
            return None
        snapped = self.nearest_node(latitude, longitude, FEATURE_SNAP_METRES)
        if snapped is None:
            return None
        node_id, offset = snapped
        network_metres = reach.distances.get(node_id)
        if network_metres is None:
            return None
        return network_metres + offset

    def has_snappable_feature(self, latitude: float, longitude: float) -> bool:
        return self.nearest_node(latitude, longitude, FEATURE_SNAP_METRES) is not None

    def _add_node(self, node_id: int, latitude: float, longitude: float) -> None:
        if node_id in self._nodes:
            return
        self._nodes[node_id] = (latitude, longitude)
        self._cells[_cell(latitude, longitude)].append(node_id)

    def _nearby_node_ids(
        self, latitude: float, longitude: float, max_metres: float
    ) -> Iterable[int]:
        latitude_span = max(1, int(max_metres / (111_320 * _CELL_DEGREES)) + 1)
        longitude_scale = max(0.05, cos(radians(latitude)))
        longitude_span = max(
            1, int(max_metres / (111_320 * longitude_scale * _CELL_DEGREES)) + 1
        )
        row, column = _cell(latitude, longitude)
        for delta_row in range(-latitude_span, latitude_span + 1):
            for delta_column in range(-longitude_span, longitude_span + 1):
                yield from self._cells.get((row + delta_row, column + delta_column), ())


def distance_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    latitude_delta = radians(lat2 - lat1)
    longitude_delta = radians(lon2 - lon1)
    a = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(longitude_delta / 2) ** 2
    )
    return 6_371_008.8 * 2 * asin(sqrt(a))


def _cell(latitude: float, longitude: float) -> tuple[int, int]:
    return int(latitude // _CELL_DEGREES), int(longitude // _CELL_DEGREES)


def _finite_coordinate(latitude: Any, longitude: Any) -> bool:
    for value, limit in ((latitude, 90), (longitude, 180)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if not -limit <= value <= limit:
            return False
    return True
