import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences
from location3.net import HttpResponse
from location3.orr import (
    OrrPerformanceAdapter, latest_rows, parse_report_table, performance_for, TABLES,
)
from location3.orr_cli import fetch_performance, main as orr_main
from location3.rail import merge_rail_research
from location3.rail_cli import main as rail_main
from location3.reporting import write_bundle
from location3.scoring import score_research


FIXTURES = ROOT / "fixtures" / "orr"
PAGES = {
    TABLES["punctuality"]["path"]: (FIXTURES / "table-3138-sample.html").read_text(encoding="utf-8"),
    TABLES["cancellations"]["path"]: (FIXTURES / "table-3124-sample.html").read_text(encoding="utf-8"),
}


class PageTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, url, *, headers, body, timeout):
        self.calls.append({"method": method, "url": url, "body": body, "headers": headers})
        path = url.replace("https://dataportal.orr.gov.uk", "")
        return HttpResponse(200, PAGES[path].encode("utf-8"), {})


class FailingTransport:
    def request(self, method, url, *, headers, body, timeout):
        raise AssertionError("a cache hit must not use the network")


def demo_run(directory: Path) -> Path:
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
    run = directory / "run"
    write_bundle(run, profile, evidence, results)
    return run


class OrrParsingTests(unittest.TestCase):
    def test_recorded_pages_parse_and_the_latest_period_wins(self):
        headers, rows = parse_report_table(PAGES[TABLES["punctuality"]["path"]])
        self.assertEqual(headers[:2], ["Time Period", "Operator"])
        self.assertIn("Time to 3 maa", headers)
        latest = latest_rows(headers, rows, TABLES["punctuality"])
        chiltern = latest["chiltern railways"]
        self.assertEqual(chiltern["Time Period"], "Apr 2026 to Mar 2027 (Period 04)")
        self.assertEqual(chiltern["Time to 3 maa"], "88.68")
        self.assertEqual(chiltern["Time to 3"], "84.17")

    def test_changed_columns_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "columns changed"):
            latest_rows(["Something", "Else"], [["a", "b"]], TABLES["punctuality"])
        with self.assertRaisesRegex(ValueError, "did not contain a report table"):
            parse_report_table("<html><body><p>moved</p></body></html>")


class OrrAdapterTests(unittest.TestCase):
    def test_two_get_requests_carry_no_run_data_and_match_operators_case_insensitively(self):
        transport = PageTransport()
        performance = OrrPerformanceAdapter(transport=transport).fetch(
            ["chiltern railways", "Great Britain"], retrieved_at="2026-09-03T00:00:00+00:00"
        )

        self.assertEqual(len(transport.calls), 2)
        for call in transport.calls:
            self.assertEqual(call["method"], "GET")
            self.assertEqual(call["body"], b"")
            self.assertTrue(call["url"].startswith("https://dataportal.orr.gov.uk/statistics/"))
        self.assertEqual(performance["basis"], "measured")
        self.assertEqual(performance["licence"], "OGL-3.0")
        self.assertEqual(
            [item["operator"] for item in performance["operators"]],
            ["Chiltern Railways", "Great Britain"],
        )
        chiltern = performance_for(performance, "Chiltern Railways")
        self.assertEqual(chiltern, {
            "operator": "Chiltern Railways",
            "period": "Apr 2026 to Mar 2027 (Period 04)",
            "punctuality_time_to_3_percent": 84.17,
            "punctuality_time_to_3_annual_percent": 88.68,
            "cancellations_percent": 2.03,
            "cancellations_annual_percent": 1.78,
        })
        self.assertEqual(
            {source["kind"] for source in performance["sources"]},
            {"punctuality", "cancellations"},
        )

    def test_unknown_operators_fail_closed_with_the_published_names(self):
        with self.assertRaisesRegex(ValueError, "does not list an operator named 'Thameslink'; available: "):
            OrrPerformanceAdapter(transport=PageTransport()).fetch(["Thameslink"])
        with self.assertRaisesRegex(ValueError, "at most 6 operators"):
            OrrPerformanceAdapter(transport=PageTransport()).fetch(
                [f"Operator {index}" for index in range(7)]
            )

    def test_fetch_writes_a_validated_file_and_reuses_the_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            run = demo_run(temporary)
            first = fetch_performance(
                run, ["Chiltern Railways"], cache_directory=temporary / "cache",
                transport=PageTransport(), retrieved_at="2026-09-03T00:00:00+00:00",
            )
            self.assertEqual(first["request_ledger_summary"], {"network_requests": 2, "cache_hits": 0})
            written = json.loads((run / "orr-performance.json").read_text(encoding="utf-8"))
            self.assertEqual(written["operators"], first["operators"])
            self.assertEqual(len(written["request_ledger"]), 2)
            self.assertNotIn("Chiltern", json.dumps(written["request_ledger"]))

            second = fetch_performance(
                run, ["Chiltern Railways"], cache_directory=temporary / "cache",
                transport=FailingTransport(),
            )
            self.assertEqual(second["request_ledger_summary"], {"network_requests": 0, "cache_hits": 2})

    def test_cli_preview_discloses_urls_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            run = demo_run(Path(directory))
            with patch("builtins.print") as printed:
                status = orr_main(["--run-dir", str(run), "--operator", "Chiltern Railways"])
            lines = [call.args[0] for call in printed.call_args_list]
            self.assertEqual(status, 0)
            self.assertFalse((run / "orr-performance.json").exists())
        self.assertTrue(any(line.startswith("Fetched from ORR (punctuality): https://dataportal.orr.gov.uk/") for line in lines))
        self.assertIn("Maximum live provider calls: 2 (a seven-day cache hit makes none)", lines)
        self.assertTrue(any("no run data, origin, or operator names leave the machine" in line for line in lines))


class RailPerformanceMergeTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
        self.evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
        self.rail = json.loads((ROOT / "fixtures/demo/rail.json").read_text(encoding="utf-8"))
        preferences = load_preferences(ROOT, include_local=False)
        self.profile["weights"] = preferences["weights"]
        self.profile["category_weights"] = preferences["category_weights"]
        self.performance = OrrPerformanceAdapter(transport=PageTransport()).fetch(
            ["Chiltern Railways"], retrieved_at="2026-09-03T00:00:00+00:00"
        )

    def test_measured_reliability_replaces_input_figures_for_journeys_with_an_operator(self):
        journey = self.rail["journeys"][0]
        journey["operator"] = "chiltern railways"
        journey["punctuality_percent"] = None
        journey["cancellation_percent"] = None
        journey["sources"] = [
            source for source in journey["sources"] if source["kind"] != "performance"
        ]
        untouched = self.rail["journeys"][1]

        merged = merge_rail_research(self.evidence, self.rail, performance=self.performance)

        enriched = next(item for item in merged["rail_journeys"] if item["id"] == journey["id"])
        self.assertEqual(enriched["operator"], "Chiltern Railways")
        self.assertEqual(enriched["punctuality_percent"], 88.68)
        self.assertEqual(enriched["cancellation_percent"], 1.78)
        performance_source = next(
            source for source in enriched["sources"] if source["kind"] == "performance"
        )
        self.assertEqual(performance_source["licence"], "OGL-3.0")
        self.assertIn("dataportal.orr.gov.uk", performance_source["url"])
        self.assertIn(
            "Reliability: ORR moving annual average for Chiltern Railways, "
            "Apr 2026 to Mar 2027 (Period 04) (measured)",
            enriched["confidence_notes"],
        )
        other = next(item for item in merged["rail_journeys"] if item["id"] == untouched["id"])
        self.assertEqual(other["punctuality_percent"], untouched["punctuality_percent"])
        self.assertNotIn("operator", other)

    def test_an_operator_missing_from_the_performance_file_fails_closed(self):
        self.rail["journeys"][0]["operator"] = "Southeastern"
        with self.assertRaisesRegex(ValueError, "no entry for operator 'Southeastern'"):
            merge_rail_research(self.evidence, self.rail, performance=self.performance)

    def test_rail_cli_accepts_a_performance_file_and_extends_the_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            run = demo_run(temporary)
            fetch_performance(
                run, ["Chiltern Railways"], cache_directory=temporary / "cache",
                transport=PageTransport(), retrieved_at="2026-09-03T00:00:00+00:00",
            )
            self.rail["journeys"][0]["operator"] = "Chiltern Railways"
            rail_path = temporary / "rail.json"
            rail_path.write_text(json.dumps(self.rail), encoding="utf-8")
            output = temporary / "rail-output"
            with patch("builtins.print"):
                status = rail_main([
                    "--run-dir", str(run), "--input", str(rail_path),
                    "--performance", str(run / "orr-performance.json"),
                    "--output", str(output), "--execute",
                ])
            self.assertEqual(status, 0)
            manifest = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
            profile = json.loads((output / "profile.json").read_text(encoding="utf-8"))
            results = json.loads((output / "results.json").read_text(encoding="utf-8"))
        self.assertEqual([entry["provider"] for entry in manifest["request_ledger"]], ["orr", "orr"])
        self.assertEqual(profile["search"]["providers"]["rail_performance"], "orr")
        welwyn = next(item for item in results["candidates"] if item["id"] == "welwyn-garden-city")
        self.assertEqual(welwyn["rail_summary"]["journeys"][0]["punctuality_percent"], 88.68)
        self.assertIn("https://dataportal.orr.gov.uk/statistics/performance/passenger-rail-performance/table-3138-train-punctuality-at-recorded-station-stops-by-operator-periodic/", manifest["sources"])


if __name__ == "__main__":
    unittest.main()
