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
from location3.research_cli import execute_research, main as research_main
from location3.validation import validate_manifest


BOUNDARY = {
    "type": "Polygon",
    "coordinates": [[
        [-0.2, 51.45], [0.0, 51.45], [0.0, 51.60],
        [-0.2, 51.60], [-0.2, 51.45],
    ]],
}


class ProviderTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, url, *, headers, body, timeout):
        self.calls.append({"url": url, "headers": headers, "body": body})
        if "openrouteservice" in url:
            payload = {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": BOUNDARY}],
            }
        else:
            payload = {
                "osm3s": {"timestamp_osm_base": "2026-09-01T18:22:00Z"},
                "elements": [
                    {"type": "node", "id": 10, "lat": 51.5, "lon": -0.1,
                     "tags": {"place": "town", "name": "Alpha"}},
                    {"type": "node", "id": 20, "lat": 51.501, "lon": -0.1,
                     "tags": {"amenity": "cafe", "name": "Alpha Cup"}},
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
                latitude=51.5,
                longitude=-0.1,
                duration_minutes=30,
                route_profile="driving-car",
                api_key="local-secret",
                include_local_preferences=False,
                transport=first_transport,
                generated_at="2026-09-02T09:00:00+00:00",
            )
            self.assertEqual(len(first_transport.calls), 2)
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
                latitude=51.5,
                longitude=-0.1,
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
            self.assertEqual(
                json.loads((temporary / "run" / "results.json").read_text(
                    encoding="utf-8"
                ))["candidates"][0]["name"],
                "Alpha",
            )

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
