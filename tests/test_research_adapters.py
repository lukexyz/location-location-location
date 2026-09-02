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
from location3.routing import OpenRouteServiceIsochrones, RouteBoundary
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
        self.assertNotIn("poly:", cafe_filter)
        self.assertEqual(cafe_filter.count(","), 3)
        self.assertIn(".pois out center tags qt;", query)
        self.assertIn(".green out bb tags qt;", query)

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
            for item in result.evidence["observations"]
        ))
        self.assertTrue(all(
            item["source_date"] == "2026-09-01"
            for item in result.evidence["observations"]
        ))
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


if __name__ == "__main__":
    unittest.main()
