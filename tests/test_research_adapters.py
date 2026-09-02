import json
from math import cos, pi, sin
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.net import HttpResponse
from location3.discovery_cli import main as discovery_main
from location3.osm import OsmCafeResearch, OverpassCafeCollector
from location3.routing import OpenRouteServiceIsochrones, RouteBoundary
from location3.validation import validate_evidence


class RecordingTransport:
    def __init__(self, payload, status=200):
        self.response = HttpResponse(status, json.dumps(payload).encode("utf-8"), {})
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


class RoutingAdapterTests(unittest.TestCase):
    def test_openrouteservice_request_is_bounded_and_uses_lon_lat_order(self):
        transport = RecordingTransport({
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": simple_boundary().geometry}],
        })
        adapter = OpenRouteServiceIsochrones("local-secret", transport=transport)

        boundary = adapter.boundary(51.5, -0.1, 30)

        self.assertEqual(boundary.duration_minutes, 30)
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
    def test_one_request_discovers_candidates_and_builds_cafe_evidence(self):
        transport = RecordingTransport({
            "osm3s": {"timestamp_osm_base": "2026-09-01T18:22:00Z"},
            "elements": [
                {"type": "node", "id": 10, "lat": 51.5, "lon": -0.1,
                 "tags": {"place": "town", "name": "Alpha"}},
                {"type": "node", "id": 20, "lat": 51.53, "lon": -0.1,
                 "tags": {"place": "village", "name": "Beta"}},
                {"type": "node", "id": 30, "lat": 51.501, "lon": -0.1,
                 "tags": {"amenity": "cafe", "name": "Alpha Cup"}},
                {"type": "node", "id": 30, "lat": 51.501, "lon": -0.1,
                 "tags": {"amenity": "cafe", "name": "Alpha Cup"}},
                {"type": "way", "id": 40, "center": {"lat": 51.531, "lon": -0.1},
                 "tags": {"amenity": "cafe", "name": "Beta Brew"}},
                {"type": "relation", "id": 50,
                 "tags": {"amenity": "cafe", "name": "No Geometry"}},
            ],
        })
        collector = OverpassCafeCollector(transport=transport)

        result = collector.collect(
            simple_boundary(), retrieved_at="2026-09-02T09:00:00+00:00"
        )

        self.assertEqual(len(transport.calls), 1)
        query = parse_qs(transport.calls[0]["body"].decode("utf-8"))["data"][0]
        self.assertIn('node["place"~"^(town|village)$"]', query)
        self.assertIn('nwr["amenity"="cafe"]', query)
        cafe_filter = query.split('nwr["amenity"="cafe"]', 1)[1].split(";", 1)[0]
        self.assertNotIn("poly:", cafe_filter)
        self.assertEqual(cafe_filter.count(","), 3)
        self.assertIn("out center tags qt;", query)
        self.assertEqual([item["name"] for item in result.evidence["candidates"]], [
            "Alpha", "Beta"
        ])
        self.assertEqual([item["value"] for item in result.evidence["observations"]], [1, 1])
        self.assertTrue(all(
            "not a pedestrian-network isochrone" in item["transformation"]
            for item in result.evidence["observations"]
        ))
        self.assertTrue(all(
            item["source_date"] == "2026-09-01"
            for item in result.evidence["observations"]
        ))
        validate_evidence(result.evidence)

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

        result = OverpassCafeCollector(
            transport=transport, max_polygon_vertices=20
        ).collect(boundary, retrieved_at="2026-09-02T09:00:00+00:00")

        polygon = result.query.split('poly:"', 1)[1].split('"', 1)[0]
        self.assertEqual(len(polygon.split()), 40)
        self.assertEqual(result.evidence, {
            "schema_version": "1", "candidates": [], "observations": []
        })


class DiscoveryCliTests(unittest.TestCase):
    def test_explicit_command_writes_only_the_private_discovery_artifacts(self):
        research = OsmCafeResearch(
            evidence={"schema_version": "1", "candidates": [], "observations": []},
            query="[out:json];node(0,0,1,1);out;",
            provider="overpass",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "private-run"
            with (
                patch.dict(os.environ, {"ORS_API_KEY": "local-secret"}),
                patch("location3.discovery_cli.OpenRouteServiceIsochrones") as routing,
                patch("location3.discovery_cli.OverpassCafeCollector") as places,
            ):
                routing.return_value.boundary.return_value = simple_boundary()
                places.return_value.collect.return_value = research
                status = discovery_main([
                    "--latitude", "51.5",
                    "--longitude", "-0.1",
                    "--minutes", "30",
                    "--output", str(output),
                ])

            self.assertEqual(status, 0)
            self.assertEqual({path.name for path in output.iterdir()}, {
                "evidence.json", "overpass-query.overpassql", "route-boundary.geojson"
            })
            routing.assert_called_once_with("local-secret")
            routing.return_value.boundary.assert_called_once_with(
                51.5, -0.1, 30, profile="driving-car"
            )


if __name__ == "__main__":
    unittest.main()
