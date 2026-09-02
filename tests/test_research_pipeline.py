import json
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.net import HttpResponse
from location3.cache import CachingTransport, RequestLedger
from location3.config import load_preferences
from location3.research_cli import (
    build_search_profile, execute_research, main as research_main,
)
from location3.validation import validate_manifest


BOUNDARY = {
    "type": "Polygon",
    "coordinates": [[
        [-0.2, 51.45], [0.0, 51.45], [0.0, 51.60],
        [-0.2, 51.60], [-0.2, 51.45],
    ]],
}


class ProviderTransport:
    def __init__(self, boundary=BOUNDARY):
        self.calls = []
        self.boundary = boundary

    def request(self, method, url, *, headers, body, timeout):
        self.calls.append({"url": url, "headers": headers, "body": body})
        if "openrouteservice" in url:
            payload = {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": self.boundary}],
            }
        else:
            payload = {
                "osm3s": {"timestamp_osm_base": "2026-09-01T18:22:00Z"},
                "elements": [
                    {"type": "node", "id": 10, "lat": 51.5, "lon": -0.1,
                     "tags": {"place": "town", "name": "Alpha"}},
                    {"type": "node", "id": 20, "lat": 51.501, "lon": -0.1,
                     "tags": {"amenity": "cafe", "name": "Alpha Cup"}},
                    {"type": "way", "id": 30, "bounds": {
                        "minlat": 51.502, "minlon": -0.11, "maxlat": 51.51, "maxlon": -0.09},
                     "tags": {"leisure": "park"}},
                ],
            }
        return HttpResponse(200, json.dumps(payload).encode("utf-8"), {})


class FailingTransport:
    def request(self, method, url, *, headers, body, timeout):
        raise AssertionError("a compatible cache hit must not use the network")


class StaticTransport:
    def __init__(self):
        self.calls = 0

    def request(self, method, url, *, headers, body, timeout):
        self.calls += 1
        return HttpResponse(200, b"{}", {})


class ResearchPipelineTests(unittest.TestCase):
    def test_cache_expiry_refetches_and_network_cap_stops_extra_requests(self):
        now = [datetime(2026, 9, 2, 9, tzinfo=timezone.utc)]
        upstream = StaticTransport()
        with tempfile.TemporaryDirectory() as directory:
            ledger = RequestLedger(max_network_requests=2)
            transport = CachingTransport(
                "example", upstream, Path(directory), ledger,
                ttl=timedelta(hours=1), clock=lambda: now[0],
            )
            request = {
                "headers": {"Content-Type": "application/json"},
                "body": b'{"place":"alpha"}',
                "timeout": 1,
            }
            transport.request("POST", "https://example.com/data", **request)
            transport.request("POST", "https://example.com/data", **request)
            now[0] += timedelta(hours=2)
            transport.request("POST", "https://example.com/data", **request)
            with self.assertRaisesRegex(RuntimeError, "call cap"):
                transport.request(
                    "POST", "https://example.com/data", **{**request, "body": b"different"}
                )

        self.assertEqual(upstream.calls, 2)
        self.assertEqual([entry["cache"] for entry in ledger.entries], [
            "miss", "hit", "miss"
        ])

    def test_preview_requires_no_key_network_or_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview"
            with (
                patch.dict(os.environ, {}, clear=True),
                patch("location3.research_cli.execute_research") as execute,
            ):
                status = research_main([
                    "--latitude", "51.5", "--longitude", "-0.1",
                    "--minutes", "30", "--output", str(output),
                ])
            self.assertEqual(status, 0)
            execute.assert_not_called()
            self.assertFalse(output.exists())

    def test_complete_run_is_cached_and_provenance_is_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            first_transport = ProviderTransport()
            first = execute_research(
                root=ROOT,
                output=temporary / "run",
                cache_directory=temporary / "cache",
                run_id="bounded-test",
                latitude=51.50049,
                longitude=-0.10049,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="local-secret",
                include_local_preferences=False,
                transport=first_transport,
                generated_at="2026-09-02T09:00:00+00:00",
            )
            self.assertEqual(len(first_transport.calls), 2)
            self.assertEqual(
                json.loads(first_transport.calls[0]["body"])["locations"], [[-0.1, 51.5]],
                "the origin is rounded before it leaves the machine",
            )
            self.assertEqual([entry["cache"] for entry in first["request_ledger"]], [
                "miss", "miss"
            ])
            self.assertFalse(first["cache_used"])
            self.assertEqual(first["sources"], [
                "https://www.openstreetmap.org/copyright"
            ])

            second = execute_research(
                root=ROOT,
                output=temporary / "run",
                cache_directory=temporary / "cache",
                run_id="bounded-test",
                latitude=51.50049,
                longitude=-0.10049,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="different-secret",
                include_local_preferences=False,
                transport=FailingTransport(),
                generated_at="2026-09-02T10:00:00+00:00",
            )
            self.assertEqual([entry["cache"] for entry in second["request_ledger"]], [
                "hit", "hit"
            ])
            self.assertTrue(second["cache_used"])
            provenance = (temporary / "run" / "provenance.json").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("local-secret", provenance)
            self.assertNotIn("different-secret", provenance)
            self.assertNotIn('"latitude"', provenance)
            self.assertNotIn('"body"', provenance)
            results = json.loads(
                (temporary / "run" / "results.json").read_text(encoding="utf-8")
            )
            alpha = results["candidates"][0]
            self.assertEqual(alpha["name"], "Alpha")
            self.assertEqual(alpha["place_kind"], "town")
            measured = {
                metric["metric"]
                for category in alpha["categories"]
                for metric in category["metrics"]
            }
            self.assertEqual(measured, {
                "cafes", "betting_shops", "yoga_studios", "premium_grocers", "green_space",
            })
            self.assertEqual(alpha["missing_metrics"], [
                "door_to_door_commute", "housing_affordability", "street_care",
            ])
            self.assertEqual(results["schema_version"], "2")
            self.assertTrue(all(
                metric["basis"] == "measured"
                for category in alpha["categories"] for metric in category["metrics"]
            ))
            self.assertEqual(alpha["hard_constraints"], {"status": "pass", "results": []})
            self.assertEqual(
                alpha["unmeasured_categories"], [{"category": "essentials", "weight": 5.0}],
                "a fresh run has no commute or housing evidence and must say so",
            )
            self.assertEqual(alpha["score_coverage_percent"], 50.0)
            self.assertTrue(
                any(warning.startswith("Unmeasured category: essentials") for warning in alpha["warnings"])
            )
            profile_text = (temporary / "run" / "profile.json").read_text(encoding="utf-8")
            self.assertNotIn("51.50049", profile_text)
            profile = json.loads(profile_text)
            self.assertEqual(profile["search"]["approximate_origin"], {
                "latitude": 51.5, "longitude": -0.1,
                "precision": "rounded to 3 decimal places, about 111 m",
            })
            boundary = profile["search"]["route_boundary"]
            self.assertEqual(boundary["geometry"], BOUNDARY)
            # The boundary is stamped by the caching layer when it was fetched live.
            self.assertEqual(
                boundary["retrieved_at"],
                first["request_ledger"][0]["requested_at"],
            )
            self.assertIn("openrouteservice", boundary["provider"])

    def test_zero_weight_metrics_are_not_collected_unless_measured(self):
        preferences = load_preferences(ROOT, include_local=False)
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            transport = ProviderTransport()
            manifest = execute_research(
                root=ROOT,
                output=temporary / "run",
                cache_directory=temporary / "cache",
                run_id="selection-test",
                latitude=51.5,
                longitude=-0.1,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="local-secret",
                include_local_preferences=False,
                search=build_search_profile(preferences, weights=["yoga_studios=0"]),
                transport=transport,
                generated_at="2026-09-02T09:00:00+00:00",
            )
            overpass_body = transport.calls[1]["body"].decode("utf-8")
            self.assertNotIn("yoga", overpass_body)
            self.assertIn(
                "Not collected in this run (weight 0 and no hard limit): yoga_studios",
                manifest["warnings"],
            )
            results = json.loads(
                (temporary / "run" / "results.json").read_text(encoding="utf-8")
            )
            alpha = results["candidates"][0]
            self.assertNotIn("yoga_studios", alpha["missing_metrics"])
            self.assertEqual(alpha["informational_metrics"], [])

            measured = ProviderTransport()
            manifest = execute_research(
                root=ROOT,
                output=temporary / "measured",
                cache_directory=temporary / "cache-measured",
                run_id="selection-test",
                latitude=51.5,
                longitude=-0.1,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="local-secret",
                include_local_preferences=False,
                search=build_search_profile(preferences, weights=["yoga_studios=0"]),
                transport=measured,
                generated_at="2026-09-02T09:00:00+00:00",
                measure=["yoga_studios"],
            )
            self.assertIn("yoga", measured.calls[1]["body"].decode("utf-8"))
            self.assertFalse(any("Not collected" in item for item in manifest["warnings"]))
            results = json.loads(
                (temporary / "measured" / "results.json").read_text(encoding="utf-8")
            )
            informational = results["candidates"][0]["informational_metrics"]
            self.assertEqual([item["metric"] for item in informational], ["yoga_studios"])

    def test_simplified_discovery_polygon_is_recorded_in_provenance(self):
        from math import cos, pi, sin

        points = [
            [-0.1 + 0.1 * cos(index * 2 * pi / 120), 51.5 + 0.1 * sin(index * 2 * pi / 120)]
            for index in range(120)
        ]
        points.append(points[0])
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            manifest = execute_research(
                root=ROOT,
                output=temporary / "run",
                cache_directory=temporary / "cache",
                run_id="polygon-test",
                latitude=51.5,
                longitude=-0.1,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="local-secret",
                include_local_preferences=False,
                transport=ProviderTransport({"type": "Polygon", "coordinates": [points]}),
                generated_at="2026-09-02T09:00:00+00:00",
            )
        self.assertIn(
            "Overpass discovery used the route boundary simplified from 120 to 79 vertices; "
            "places near a concave edge may differ from the drawn boundary",
            manifest["warnings"],
        )

    def test_search_profile_expresses_destinations_limits_housing_and_weights(self):
        preferences = load_preferences(ROOT, include_local=False)
        search = build_search_profile(
            preferences,
            destinations=[
                "London Bridge|public_transport|Tuesday 09:00|75",
                "Client office|driving|Friday 10:00",
            ],
            constraints=["betting_shops<=1"],
            weights=["cafes=3", "yoga_studios=0"],
            housing_mode="rent",
            budget_gbp=1800,
            property_type="flat",
            bedrooms=2,
        )
        self.assertEqual(search["destinations"][0], {
            "label": "London Bridge", "travel_mode": "public_transport",
            "arrival": "Tuesday 09:00", "max_minutes": 75,
        })
        self.assertIsNone(search["destinations"][1]["max_minutes"])
        self.assertEqual(search["hard_constraints"], [
            {"metric": "betting_shops", "operator": "<=", "value": 1.0},
            {
                "metric": "door_to_door_commute", "operator": "<=", "value": 75,
                "destination_label": "London Bridge",
            },
        ])
        self.assertEqual(search["weights"]["cafes"], 3.0)
        self.assertEqual(search["weights"]["yoga_studios"], 0.0)
        self.assertEqual(search["weights"]["street_care"], preferences["weights"]["street_care"])
        self.assertEqual(search["housing"], {
            "mode": "rent", "budget_gbp": 1800, "property_type": "flat", "bedrooms": 2,
        })

    def test_search_profile_rejects_ambiguous_or_partial_input(self):
        preferences = load_preferences(ROOT, include_local=False)
        with self.assertRaisesRegex(ValueError, r"LABEL\|MODE\|ARRIVAL"):
            build_search_profile(preferences, destinations=["London Bridge"])
        with self.assertRaisesRegex(ValueError, "mode must be one of"):
            build_search_profile(preferences, destinations=["A|teleport|Monday 09:00"])
        with self.assertRaisesRegex(ValueError, "at most one hard constraint"):
            build_search_profile(
                preferences, constraints=["cafes<=5", "cafes>=1"],
            )
        with self.assertRaisesRegex(ValueError, "cafes=3"):
            build_search_profile(preferences, weights=["unknown=2"])
        with self.assertRaisesRegex(ValueError, "0 to 5"):
            build_search_profile(preferences, weights=["cafes=6"])
        with self.assertRaisesRegex(ValueError, "together"):
            build_search_profile(preferences, budget_gbp=400000)
        with self.assertRaisesRegex(ValueError, "cannot be evaluated for a driving destination"):
            build_search_profile(
                preferences, destinations=["Client office|driving|Friday 10:00|30"]
            )

    def test_preview_prints_the_disclosure_without_a_key(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview"
            with (
                patch.dict(os.environ, {}, clear=True),
                patch("location3.research_cli.execute_research") as execute,
                patch("builtins.print") as printed,
            ):
                status = research_main([
                    "--latitude", "51.5", "--longitude", "-0.1", "--minutes", "30",
                    "--destination", "London Bridge|public_transport|Tuesday 09:00|75",
                    "--housing", "buy", "--budget", "450000", "--property-type", "flat",
                    "--weight", "yoga_studios=0",
                    "--output", str(output),
                ])
            self.assertEqual(status, 0)
            execute.assert_not_called()
            lines = [call.args[0] for call in printed.call_args_list]
            self.assertIn(
                "Origin sent to routing provider: 51.500, -0.100 (rounded to 3 decimal "
                "places, about 111 m; the exact value you typed is neither sent nor stored)",
                lines,
            )
            self.assertIn(
                "Research plan: OpenRouteService isochrone (https://api.openrouteservice.org) "
                "+ one combined Overpass query (https://overpass-api.de)",
                lines,
            )
            self.assertIn(
                "Not collected (weight 0 and no hard limit): yoga_studios; "
                "add --measure METRIC to record one for information",
                lines,
            )
            self.assertIn(
                "Imported later from cited inputs, never fetched here: door_to_door_commute, "
                "housing_affordability, street_care",
                lines,
            )
            self.assertIn(
                "Hard limit: door_to_door_commute for London Bridge <= 75", lines
            )
            self.assertTrue(any(line.startswith("Housing: buy a any size flat") for line in lines))
            self.assertTrue(any("Waitrose" in line for line in lines))

    def test_manifest_rejects_request_payload_fields(self):
        manifest = {
            "schema_version": "1",
            "run_id": "test",
            "generated_at": "2026-09-02T09:00:00+00:00",
            "scoring_version": "1",
            "tool_versions": {"location3": "0.1.0"},
            "geographic_coverage": {},
            "request_ledger": [{
                "provider": "example",
                "request_id": "sha256:" + "a" * 64,
                "endpoint": "https://example.com/research",
                "requested_at": "2026-09-02T09:00:00+00:00",
                "cache": "miss",
                "status": 200,
                "body": {"latitude": 51.5},
            }],
            "cache_used": False,
            "sources": [],
            "licences": [],
            "warnings": [],
            "checksums": {
                "profile.json": "sha256:" + "a" * 64,
                "evidence.json": "sha256:" + "b" * 64,
                "results.json": "sha256:" + "c" * 64,
            },
        }
        with self.assertRaisesRegex(ValueError, "unapproved fields"):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
