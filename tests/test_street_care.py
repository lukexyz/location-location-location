from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences
from location3.reporting import write_bundle
from location3.scoring import score_research
from location3.street_care import assess_street_care, merge_street_care_research
from location3.street_care_cli import main as street_care_main
from location3.validation import validate_evidence


def fixtures():
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    street = json.loads((ROOT / "fixtures/demo/street-care.json").read_text(encoding="utf-8"))
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    return profile, evidence, street


class StreetCareResearchTests(unittest.TestCase):
    def test_recent_structured_audit_overrides_but_preserves_proxy_facts(self):
        profile, evidence, street = fixtures()
        merged = merge_street_care_research(evidence, street)
        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        alder = next(item for item in results["candidates"] if item["id"] == "welwyn-garden-city")
        summary = alder["street_care_summary"]
        self.assertEqual(summary["basis"], "recent_visit_audit")
        self.assertEqual(summary["score"], 87.5)
        self.assertEqual(summary["place"]["fly_tipping"]["current_incidents_per_1000"], 12)
        self.assertNotIn("visit audit recommended", " ".join(alder["warnings"]))

    def test_proxy_scores_resolution_but_not_raw_report_density(self):
        _, _, street = fixtures()
        north = street["places"][1]
        assessment = assess_street_care(north, street["assessment_date"])
        density = next(item for item in assessment["components"] if item["key"] == "report_density")
        self.assertEqual(assessment["basis"], "proxy")
        self.assertFalse(density["included"])
        self.assertEqual(density["weight"], 0)
        self.assertEqual(assessment["confidence"], 0.5)

    def test_stale_audit_and_partial_reporting_remain_prominent_warnings(self):
        profile, evidence, street = fixtures()
        merged = merge_street_care_research(evidence, street)
        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        mere = next(item for item in results["candidates"] if item["id"] == "maidenhead")
        self.assertEqual(mere["street_care_summary"]["basis"], "proxy")
        warnings = " ".join(mere["warnings"])
        self.assertIn("stale", warnings)
        self.assertIn("does not report all incidents", warnings)
        self.assertIn("resolution evidence unavailable", warnings)

    def test_rejects_outside_future_and_tampered_research(self):
        _, evidence, street = fixtures()
        outside = deepcopy(street)
        outside["places"][0]["candidate_id"] = "not-shortlisted"
        with self.assertRaisesRegex(ValueError, "outside the candidate shortlist"):
            merge_street_care_research(evidence, outside)

        future = deepcopy(street)
        future["places"][0]["visit_audit"]["audited_at"] = "2026-08-02"
        with self.assertRaisesRegex(ValueError, "later than assessment_date"):
            merge_street_care_research(evidence, future)

        merged = merge_street_care_research(evidence, street)
        observation = next(
            item for item in merged["observations"]
            if item["candidate_id"] == "welwyn-garden-city" and item["metric"] == "street_care"
        )
        observation["value"] = 100
        with self.assertRaisesRegex(ValueError, "does not match its raw components"):
            validate_evidence(merged)

    def test_manifest_and_cli_preview_preserve_citations_without_output(self):
        profile, evidence, street = fixtures()
        merged = merge_street_care_research(evidence, street)
        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            manifest = write_bundle(temporary / "enriched", profile, merged, results)
            self.assertIn(
                "https://github.com/lukexyz/location-location-location/blob/main/fixtures/demo/street-care.json",
                manifest["sources"],
            )
            base_results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
            run_dir = temporary / "base"
            write_bundle(run_dir, profile, evidence, base_results)
            input_path = temporary / "street-care.json"
            input_path.write_text(json.dumps(street), encoding="utf-8")
            output = temporary / "street-output"
            status = street_care_main([
                "--run-dir", str(run_dir), "--input", str(input_path),
                "--output", str(output),
            ])
            self.assertEqual(status, 0)
            self.assertFalse(output.exists())
            status = street_care_main([
                "--run-dir", str(run_dir), "--input", str(input_path),
                "--output", str(output), "--execute",
            ])
            self.assertEqual(status, 0)
            written = json.loads((output / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(written["candidates"][0]["street_care_summary"]["basis"], "recent_visit_audit")


if __name__ == "__main__":
    unittest.main()
