import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences
from location3.export_cli import main as export_main, redact_bundle
from location3.housing import configure_housing_profile, merge_housing_research
from location3.rail import merge_rail_research
from location3.reporting import write_bundle
from location3.scoring import score_research
from location3.street_care import merge_street_care_research


LEDGER = [{
    "provider": "openrouteservice",
    "request_id": "sha256:" + "a" * 64,
    "endpoint": "https://api.openrouteservice.org/v2/isochrones/driving-car",
    "requested_at": "2026-08-01T11:00:00+00:00",
    "cache": "miss",
    "status": 200,
}]


def demo_run(directory: Path) -> Path:
    """Write a private run from the demo fixtures, including rail and housing evidence."""
    fixtures = ROOT / "fixtures/demo"
    profile = json.loads((fixtures / "profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((fixtures / "evidence.json").read_text(encoding="utf-8"))
    rail = json.loads((fixtures / "rail.json").read_text(encoding="utf-8"))
    housing = json.loads((fixtures / "housing.json").read_text(encoding="utf-8"))
    street = json.loads((fixtures / "street-care.json").read_text(encoding="utf-8"))
    # A lowercase mention and a slug form of the label, as agents tend to write them.
    rail["journeys"][0]["confidence_notes"] += " Timed for a central destination arrival."
    rail["journeys"][0]["id"] = "welwyn-central-destination-rail"
    profile["search"]["approximate_origin"] = {
        "latitude": 51.51234, "longitude": -0.12345, "precision": "user-provided",
    }
    profile["hard_constraints"] = [{
        "metric": "door_to_door_commute", "operator": "<=", "value": 65,
        "destination_label": "Central destination",
    }]
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    profile["unknown_data_policy"] = "warn"
    profile = configure_housing_profile(profile, housing)
    evidence = merge_rail_research(evidence, rail)
    evidence = merge_housing_research(profile, evidence, housing)
    evidence = merge_street_care_research(evidence, street)
    results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
    run = directory / "run"
    write_bundle(run, profile, evidence, results, request_ledger=LEDGER)
    (run / "route-boundary.geojson").write_text("{}", encoding="utf-8")
    return run


def bundle_text(directory: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.json"))
    )


class ExportTests(unittest.TestCase):
    def test_preview_discloses_what_remains_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            run = demo_run(Path(directory))
            output = Path(directory) / "export"
            with patch("builtins.print") as printed:
                status = export_main(["--run-dir", str(run), "--output", str(output)])
            lines = [call.args[0] for call in printed.call_args_list]

        self.assertEqual(status, 0)
        self.assertFalse(output.exists())
        self.assertIn("Origin: rounded to 2 decimal places (about 1.1 km)", lines)
        self.assertTrue(any(line.startswith("Housing: retained; the export reveals a GBP 500,000") for line in lines))
        self.assertTrue(any("names Central destination" in line for line in lines))
        self.assertTrue(any(line.startswith("Warning: an exported bundle still reveals") for line in lines))
        self.assertTrue(any("Nothing is uploaded" in line for line in lines))
        self.assertTrue(any(line.startswith("Visit audits: removed 2 personal audit(s)") for line in lines))
        self.assertTrue(any(line.startswith("Request ledger: request ids re-hashed") for line in lines))

    def test_execute_rounds_origin_strips_housing_and_anonymises_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            run = demo_run(Path(directory))
            output = Path(directory) / "export"
            with patch("builtins.print"):
                status = export_main([
                    "--run-dir", str(run), "--output", str(output),
                    "--origin-decimals", "1", "--strip-housing",
                    "--anonymise-destinations", "--execute",
                ])
            self.assertEqual(status, 0)
            exported = bundle_text(output)
            profile = json.loads((output / "profile.json").read_text(encoding="utf-8"))
            results = json.loads((output / "results.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
            original = bundle_text(run)
            self.assertTrue((output / "route-boundary.geojson").exists())

        self.assertIn("500000", original)
        self.assertNotIn("500000", exported)
        self.assertIn("central destination", original.casefold())
        self.assertNotIn("central destination", exported.casefold())
        self.assertNotIn("central-destination", exported.casefold())
        self.assertIn("London King's Cross", original)
        self.assertNotIn("London King's Cross", exported)
        self.assertIn("Synthetic recent visit audit", original)
        self.assertNotIn("Synthetic recent visit audit", exported)
        self.assertNotIn("walking loop", exported)
        self.assertNotIn("51.51234", exported)
        self.assertEqual(len(manifest["request_ledger"]), 1)
        self.assertNotEqual(manifest["request_ledger"][0]["request_id"], LEDGER[0]["request_id"])
        self.assertRegex(manifest["request_ledger"][0]["request_id"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(manifest["request_ledger"][0]["endpoint"], LEDGER[0]["endpoint"])
        self.assertEqual(profile["search"]["approximate_origin"], {
            "latitude": 51.5, "longitude": -0.1,
            "precision": "rounded to 1 decimal places (about 11 km)",
        })
        self.assertEqual(profile["search"]["housing"], {})
        self.assertNotIn("housing", profile["search"]["providers"])
        self.assertEqual(profile["hard_constraints"][0]["destination_label"], "Destination 1")
        for candidate in results["candidates"]:
            self.assertNotIn("housing_summary", candidate)
            self.assertIn("housing_affordability", candidate["missing_metrics"])
            self.assertEqual(
                candidate["hard_constraints"]["results"][0]["destination_label"], "Destination 1"
            )
            self.assertIsNotNone(candidate["hard_constraints"]["results"][0]["actual"])
            self.assertEqual(
                candidate["rail_summary"]["journeys"][0]["destination_label"], "Destination 1"
            )
            self.assertEqual(
                candidate["rail_summary"]["journeys"][0]["london_arrival_station"],
                "London terminal withheld",
            )
            if "street_care_summary" in candidate:
                self.assertEqual(candidate["street_care_summary"]["basis"], "proxy")
                self.assertIsNone(candidate["street_care_summary"]["place"]["visit_audit"])
        welwyn = next(item for item in results["candidates"] if item["id"] == "welwyn-garden-city")
        self.assertEqual(
            welwyn["rail_summary"]["journeys"][0]["id"], "welwyn-destination-1-rail"
        )

    def test_visit_audits_can_be_kept_deliberately(self):
        with tempfile.TemporaryDirectory() as directory:
            run = demo_run(Path(directory))
            output = Path(directory) / "export"
            with patch("builtins.print") as printed:
                status = export_main([
                    "--run-dir", str(run), "--output", str(output),
                    "--keep-visit-audits", "--execute",
                ])
            lines = [call.args[0] for call in printed.call_args_list]
            self.assertEqual(status, 0)
            results = json.loads((output / "results.json").read_text(encoding="utf-8"))
        self.assertTrue(any(line.startswith("Visit audits: retained 2 personal audit(s)") for line in lines))
        welwyn = next(item for item in results["candidates"] if item["id"] == "welwyn-garden-city")
        self.assertEqual(welwyn["street_care_summary"]["basis"], "recent_visit_audit")

    def test_redaction_helper_is_pure_and_bounded(self):
        profile = {
            "search": {
                "approximate_origin": {"latitude": 51.5123, "longitude": -0.987654, "precision": "x"},
                "housing": {}, "destinations": [], "providers": {},
            },
            "hard_constraints": [],
        }
        evidence = {"observations": []}
        redacted, _, notes = redact_bundle(profile, evidence, origin_decimals=2)

        self.assertEqual(profile["search"]["approximate_origin"]["latitude"], 51.5123)
        self.assertEqual(redacted["search"]["approximate_origin"]["latitude"], 51.51)
        self.assertEqual(redacted["search"]["approximate_origin"]["longitude"], -0.99)
        self.assertIn("Housing: no requirements recorded", notes)
        self.assertIn("Destinations: none recorded", notes)
        with self.assertRaisesRegex(ValueError, "between 0 and 4"):
            redact_bundle(profile, evidence, origin_decimals=6)


if __name__ == "__main__":
    unittest.main()
