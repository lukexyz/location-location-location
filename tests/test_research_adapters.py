import json
from math import cos, pi, sin
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.net import HttpResponse
from location3.osm import BrandGroup, OverpassAmenityCollector
from location3.routing import (
    DistanceProxyBoundary, OpenRouteServiceIsochrones, RouteBoundary, proxy_radius_km,
)
from location3.validation import validate_evidence


GROCERS = BrandGroup(
    patterns=("Waitrose", "Marks & Spencer", "M&S"),
    shop_types=("supermarket", "convenience", "food", "deli", "department_store"),
)


class RecordingTransport:
    def __init__(self, payload, status=200, headers=None):
        self.response = HttpResponse(
            status, json.dumps(payload).encode("utf-8"), headers or {}
        )
        self.calls = []

    def request(self, method, url, *, headers, body, timeout):
        self.calls.append({
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
            "timeout": timeout,
        })
        return self.response


def simple_boundary():
    return RouteBoundary(
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-0.2, 51.45],
                [0.0, 51.45],
                [0.0, 51.60],
                [-0.2, 51.60],
                [-0.2, 51.45],
            ]],
        },
        provider="openrouteservice",
        profile="driving-car",
        duration_minutes=30,
    )


def node(osm_id, latitude, longitude, **tags):
    return {"type": "node", "id": osm_id, "lat": latitude, "lon": longitude, "tags": tags}


class RoutingAdapterTests(unittest.TestCase):
    def test_openrouteservice_request_is_bounded_and_uses_lon_lat_order(self):
        transport = RecordingTransport(
            {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": simple_boundary().geometry}],
            },
            headers={"X-Location3-Retrieved-At": "2026-09-02T09:00:00+00:00"},
        )
        adapter = OpenRouteServiceIsochrones("local-secret", transport=transport)

        boundary = adapter.boundary(51.5, -0.1, 30)

        self.assertEqual(boundary.duration_minutes, 30)
        self.assertEqual(boundary.retrieved_at, "2026-09-02T09:00:00+00:00")
        self.assertEqual(len(transport.calls), 1)
        call = transport.calls[0]
        self.assertEqual(call["url"], "https://api.openrouteservice.org/v2/isochrones/driving-car")
        self.assertEqual(call["headers"]["Authorization"], "local-secret")
        self.assertEqual(json.loads(call["body"]), {
            "locations": [[-0.1, 51.5]],
            "range": [1800],
            "range_type": "time",
        })

    def test_openrouteservice_rejects_an_unbounded_duration_before_network_use(self):
        transport = RecordingTransport({})
        adapter = OpenRouteServiceIsochrones("local-secret", transport=transport)

        with self.assertRaisesRegex(ValueError, "between 1 and 120"):
            adapter.boundary(51.5, -0.1, 121)

        self.assertEqual(transport.calls, [])


class OverpassAdapterTests(unittest.TestCase):
    def test_one_request_discovers_candidates_and_measures_every_amenity_metric(self):
        transport = RecordingTransport({
            "osm3s": {"timestamp_osm_base": "2026-09-01T18:22:00Z"},
            "elements": [
                node(10, 51.5, -0.1, place="town", name="Alpha"),
                node(20, 51.53, -0.1, place="village", name="Beta"),
                node(30, 51.501, -0.1, amenity="cafe", name="Alpha Cup"),
                node(30, 51.501, -0.1, amenity="cafe", name="Alpha Cup"),
                {"type": "way", "id": 40, "center": {"lat": 51.531, "lon": -0.1},
                 "tags": {"amenity": "cafe", "name": "Beta Brew"}},
                {"type": "relation", "id": 50,
                 "tags": {"amenity": "cafe", "name": "No Geometry"}},
                node(60, 51.502, -0.1, shop="bookmaker", name="Odds"),
                node(61, 51.503, -0.1, amenity="gambling", name="Slots"),
                node(70, 51.504, -0.1, leisure="fitness_centre", sport="yoga;pilates"),
                node(80, 51.505, -0.1, shop="supermarket", brand="Waitrose", name="Waitrose Alpha"),
                node(81, 51.506, -0.1, shop="convenience", name="M&S Simply Food"),
                node(82, 51.507, -0.1, shop="clothes", name="Marks & Spencer"),
                node(83, 51.508, -0.1, shop="supermarket", brand="Tesco"),
                {"type": "way", "id": 90, "bounds": {
                    "minlat": 51.508, "minlon": -0.12, "maxlat": 51.515, "maxlon": -0.10},
                 "tags": {"leisure": "park", "name": "Alpha Park"}},
                {"type": "way", "id": 91, "bounds": {
                    "minlat": 51.49, "minlon": -0.12, "maxlat": 51.495, "maxlon": -0.10},
                 "tags": {"leisure": "park", "access": "private"}},
            ],
        })
        collector = OverpassAmenityCollector(premium_grocers=GROCERS, transport=transport)

        result = collector.collect(
            simple_boundary(), retrieved_at="2026-09-02T09:00:00+00:00"
        )

        self.assertEqual(len(transport.calls), 1)
        query = parse_qs(transport.calls[0]["body"].decode("utf-8"))["data"][0]
        self.assertIn('node["place"~"^(city|town|suburb|village|neighbourhood)$"]', query)
        for clause in (
            'nwr["amenity"="cafe"]', 'nwr["shop"="bookmaker"]', 'nwr["amenity"="gambling"]',
            'nwr["sport"~"(^|;)yoga(;|$)",i]',
            '["brand"~"(Waitrose|Marks & Spencer|M&S)",i]',
            '["name"~"(Waitrose|Marks & Spencer|M&S)",i]',
            'nwr["leisure"~"^(park|nature_reserve|recreation_ground|common|dog_park)$"]["access"!="private"]',
        ):
            self.assertIn(clause, query)
        cafe_filter = query.split('nwr["amenity"="cafe"]', 1)[1].split(";", 1)[0]
        self.assertEqual(cafe_filter, "(around.places:1200)")
        self.assertIn('["name"](poly:"', query.split("->.places;", 1)[0])
        self.assertIn(".places out qt;", query)
        self.assertIn("(around.places:3600)", query)
        self.assertIn(".pois out center body qt;", query)
        self.assertIn(".green out bb body qt;", query)
        self.assertIn('way["highway"~"^(footway|path|pedestrian|', query)
        self.assertIn('["foot"!~"^(no|private)$"]["access"!="private"](around.places:1300)', query)
        self.assertIn(".network out geom qt;", query)
        self.assertEqual(query.count("out "), 4, "one call, four output statements")

        candidates = result.evidence["candidates"]
        self.assertEqual([item["name"] for item in candidates], ["Alpha", "Beta"])
        self.assertEqual([item["place_kind"] for item in candidates], ["town", "village"])
        alpha = {
            item["metric"]: item["value"]
            for item in result.evidence["observations"]
            if item["candidate_id"] == "osm-node-10"
        }
        self.assertEqual(alpha, {
            "cafes": 1,
            "betting_shops": 2,
            "yoga_studios": 1,
            "premium_grocers": 2,
            "green_space": 11.1,
        })
        beta = {
            item["metric"]: item["value"]
            for item in result.evidence["observations"]
            if item["candidate_id"] == "osm-node-20"
        }
        self.assertEqual(beta["cafes"], 1)
        self.assertEqual(beta["premium_grocers"], 0)
        self.assertEqual(beta["green_space"], 20.8)
        self.assertTrue(all(
            "not a pedestrian-network" in item["transformation"]
            and "carried no pedestrian network" in item["transformation"]
            for item in result.evidence["observations"]
            if item["metric"] != "green_space"
        ))
        self.assertTrue(all(
            item["source_date"] == "2026-09-01"
            for item in result.evidence["observations"]
        ))
        validate_evidence(result.evidence)

    def test_network_catchment_counts_walking_distance_not_straight_line(self):
        def offset(north_metres, east_metres):
            return 51.5 + north_metres / 111_320, -0.1 + east_metres / 69_300

        def way(way_id, points):
            return {
                "type": "way", "id": way_id, "tags": {"highway": "residential"},
                "nodes": [node_id for node_id, _, _ in points],
                "geometry": [{"lat": lat, "lon": lon} for _, lat, lon in points],
            }

        # A road runs 800 m east, 800 m north, then 800 m back west from the town node.
        road = way(500, [
            (501, 51.5, -0.1), (502, *offset(0, 800)),
            (503, *offset(800, 800)), (504, *offset(800, 0)),
        ])
        transport = RecordingTransport({
            "osm3s": {"timestamp_osm_base": "2026-09-01T18:22:00Z"},
            "elements": [
                node(10, 51.5, -0.1, place="town", name="Alpha"),
                node(11, 51.53, -0.1, place="village", name="Remote"),
                road,
                # Beside the street 600 m along: reachable on the network.
                node(20, *offset(40, 600), amenity="cafe", name="Kerbside"),
                # 800 m away as the crow flies but 2,400 m by road: excluded.
                node(21, *offset(800, 0), amenity="cafe", name="Across the fields"),
                node(22, *offset(800, 0), shop="bookmaker", name="Far Odds"),
                # No walkable way within 150 m: measured straight-line as a fallback.
                node(23, *offset(600, 500), amenity="cafe", name="Off grid"),
                node(24, *offset(200, 100), shop="bookmaker", name="Near Odds"),
            ],
        })
        collector = OverpassAmenityCollector(premium_grocers=GROCERS, transport=transport)

        result = collector.collect(
            simple_boundary(), retrieved_at="2026-09-02T09:00:00+00:00"
        )

        by_candidate = {}
        for item in result.evidence["observations"]:
            by_candidate.setdefault(item["candidate_id"], {})[item["metric"]] = item
        alpha = by_candidate["osm-node-10"]
        self.assertEqual(alpha["cafes"]["value"], 2)
        self.assertEqual(alpha["betting_shops"]["value"], 1)
        self.assertIn("pedestrian-network catchment", alpha["cafes"]["geographic_scope"])
        self.assertIn("walking distance along the OSM pedestrian network", alpha["cafes"]["transformation"])
        self.assertAlmostEqual(alpha["cafes"]["confidence"], 0.75)
        remote = by_candidate["osm-node-11"]
        self.assertIn("straight-line catchment", remote["cafes"]["geographic_scope"])
        self.assertIn("no walkable way was mapped within 300 m", remote["cafes"]["transformation"])
        self.assertAlmostEqual(remote["cafes"]["confidence"], 0.65)
        validate_evidence(result.evidence)

    def test_nearby_anchors_are_deduplicated_keeping_the_most_significant_kind(self):
        transport = RecordingTransport({
            "elements": [
                node(1, 51.50, -0.10, place="neighbourhood", name="Old Quarter"),
                node(2, 51.502, -0.10, place="city", name="Alpha"),
                node(3, 51.55, -0.10, place="suburb", name="Northfield"),
                node(4, 51.5501, -0.10, place="village", name="Northfield Village"),
            ],
        })
        result = OverpassAmenityCollector(
            premium_grocers=GROCERS, transport=transport
        ).collect(simple_boundary(), retrieved_at="2026-09-02T09:00:00+00:00")

        self.assertEqual(
            [(item["name"], item["place_kind"]) for item in result.evidence["candidates"]],
            [("Alpha", "city"), ("Northfield", "suburb")],
        )
        self.assertFalse(
            any(item["metric"] == "green_space" for item in result.evidence["observations"]),
            "no green space in the response means no fabricated distance",
        )

    def test_large_provider_polygon_is_capped_in_the_overpass_query(self):
        points = [
            [-0.1 + 0.1 * cos(index * 2 * pi / 120),
             51.5 + 0.1 * sin(index * 2 * pi / 120)]
            for index in range(120)
        ]
        points.append(points[0])
        boundary = RouteBoundary(
            geometry={"type": "Polygon", "coordinates": [points]},
            provider="openrouteservice",
            profile="driving-car",
            duration_minutes=30,
        )
        transport = RecordingTransport({"elements": []})

        result = OverpassAmenityCollector(
            premium_grocers=GROCERS, transport=transport, max_polygon_vertices=20
        ).collect(boundary, retrieved_at="2026-09-02T09:00:00+00:00")

        polygon = result.query.split('poly:"', 1)[1].split('"', 1)[0]
        self.assertEqual(len(polygon.split()), 40)
        self.assertEqual(result.polygon_vertices, (19, 120))
        self.assertEqual(result.evidence, {
            "schema_version": "1", "candidates": [], "observations": []
        })

    def test_brand_groups_reject_query_injection_characters(self):
        with self.assertRaisesRegex(ValueError, "unsafe"):
            BrandGroup(patterns=('Waitrose"]',), shop_types=("supermarket",))
        with self.assertRaisesRegex(ValueError, "single OSM shop"):
            BrandGroup(patterns=("Waitrose",), shop_types=("super market",))
        self.assertTrue(GROCERS.matches({"shop": "supermarket", "name": "little waitrose"}))
        self.assertFalse(GROCERS.matches({"shop": "clothes", "brand": "Marks & Spencer"}))
        dotted = BrandGroup(patterns=("Co.op",), shop_types=("food.store",))
        self.assertEqual(dotted.overpass_regex(), r"(Co\.op)")
        self.assertEqual(dotted.shop_regex(), r"^(food\.store)$")


RECORDED_RESPONSE = ROOT / "fixtures" / "overpass" / "welwyn-garden-city-sample.json"


def welwyn_boundary():
    return RouteBoundary(
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-0.215, 51.797], [-0.199, 51.797], [-0.199, 51.809],
                [-0.215, 51.809], [-0.215, 51.797],
            ]],
        },
        provider="openrouteservice",
        profile="driving-car",
        duration_minutes=30,
    )


class RecordedOverpassResponseTests(unittest.TestCase):
    """The recorded response carries the element shapes the live query returns."""

    def setUp(self):
        self.payload = json.loads(RECORDED_RESPONSE.read_text(encoding="utf-8"))
        self.retrieved_at = "2026-09-03T00:00:00+00:00"

    def collector(self, payload):
        # The sample was recorded at a 600 m walk radius to keep the file small.
        return OverpassAmenityCollector(
            premium_grocers=GROCERS,
            transport=RecordingTransport(payload),
            walk_radius_metres=600,
        )

    def test_recorded_live_response_counts_node_points_of_interest(self):
        result = self.collector(self.payload).collect(
            welwyn_boundary(), retrieved_at=self.retrieved_at
        )

        self.assertEqual(
            [item["name"] for item in result.evidence["candidates"]], ["Welwyn Garden City"]
        )
        values = {item["metric"]: item["value"] for item in result.evidence["observations"]}
        self.assertEqual(values, {
            "cafes": 6, "betting_shops": 1, "yoga_studios": 0, "premium_grocers": 1,
            "green_space": 0.0,
        })
        for item in result.evidence["observations"]:
            self.assertEqual(item["source_date"], "2026-09-02")
            if item["metric"] != "green_space":
                self.assertIn("pedestrian-network catchment", item["geographic_scope"])
        self.assertEqual(result.polygon_vertices, (4, 4))
        validate_evidence(result.evidence)

    def test_tags_only_verbosity_would_silently_drop_node_points_of_interest(self):
        # `out tags` omits node coordinates. Guard the query so this never returns.
        without_coordinates = {
            **self.payload,
            "elements": [
                {key: value for key, value in element.items() if key not in ("lat", "lon")}
                if element["type"] == "node" and "place" not in element.get("tags", {})
                else element
                for element in self.payload["elements"]
            ],
        }
        collector = self.collector(without_coordinates)

        result = collector.collect(welwyn_boundary(), retrieved_at=self.retrieved_at)

        values = {item["metric"]: item["value"] for item in result.evidence["observations"]}
        self.assertEqual(values["cafes"], 1, "only the café mapped as a way survives")
        self.assertEqual(values["betting_shops"], 0)
        query = collector.build_query(welwyn_boundary())
        self.assertIn(".pois out center body qt;", query)
        self.assertIn(".green out bb body qt;", query)
        self.assertNotIn("out center tags", query)
        self.assertNotIn("out bb tags", query)

    def test_query_and_measurement_follow_the_selected_metrics(self):
        collector = self.collector(self.payload)

        cafes_only = collector.collect(
            welwyn_boundary(),
            metrics=("cafes", "door_to_door_commute"),
            retrieved_at=self.retrieved_at,
        )
        self.assertIn('nwr["amenity"="cafe"]', cafes_only.query)
        for absent in ("bookmaker", "gambling", "yoga", "Waitrose", '"leisure"', ".green"):
            self.assertNotIn(absent, cafes_only.query)
        self.assertIn(".network out geom qt;", cafes_only.query)
        self.assertEqual(cafes_only.query.count("out "), 3)
        self.assertEqual(
            [item["metric"] for item in cafes_only.evidence["observations"]], ["cafes"]
        )
        self.assertEqual(cafes_only.measured_metrics, ("cafes",))

        green_only = collector.collect(
            welwyn_boundary(), metrics=("green_space",), retrieved_at=self.retrieved_at
        )
        self.assertNotIn(".pois", green_only.query)
        self.assertNotIn(".network", green_only.query)
        self.assertEqual(
            [item["metric"] for item in green_only.evidence["observations"]], ["green_space"]
        )

        discovery_only = collector.collect(
            welwyn_boundary(), metrics=(), retrieved_at=self.retrieved_at
        )
        self.assertEqual(discovery_only.query.count("out "), 1)
        self.assertEqual(discovery_only.evidence["observations"], [])
        self.assertEqual(len(discovery_only.evidence["candidates"]), 1)


if __name__ == "__main__":
    unittest.main()


class DistanceProxyTests(unittest.TestCase):
    def test_proxy_is_a_closed_ring_of_the_stated_radius_and_says_what_it_is(self):
        from math import asin, sqrt

        boundary = DistanceProxyBoundary().boundary(51.5, -0.1, 30, profile="driving-car")
        self.assertEqual(boundary.provider, "distance-proxy")
        self.assertIsNone(boundary.retrieved_at)
        self.assertEqual(proxy_radius_km(30, "driving-car"), 14.0)
        self.assertIn("14.0 km straight-line radius", boundary.description)
        self.assertIn("not a routed isochrone", boundary.description)
        ring = boundary.geometry["coordinates"][0]
        self.assertEqual(len(ring), 65)
        self.assertEqual(ring[0], ring[-1])

        def haversine_km(lon, lat):
            phi1, phi2 = 51.5 * pi / 180, lat * pi / 180
            dphi, dlambda = (lat - 51.5) * pi / 180, (lon + 0.1) * pi / 180
            a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
            return 2 * 6371 * asin(sqrt(a))

        for lon, lat in ring:
            self.assertAlmostEqual(haversine_km(lon, lat), 14.0, delta=0.05)

    def test_proxy_rejects_the_same_bad_input_as_the_routed_adapter(self):
        proxy = DistanceProxyBoundary()
        with self.assertRaisesRegex(ValueError, "profile"):
            proxy.boundary(51.5, -0.1, 30, profile="rocket")
        with self.assertRaisesRegex(ValueError, "duration_minutes"):
            proxy.boundary(51.5, -0.1, 0)
        with self.assertRaisesRegex(ValueError, "out of range"):
            proxy.boundary(95.0, -0.1, 30)
