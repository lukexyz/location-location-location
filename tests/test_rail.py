from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences
from location3.rail import merge_rail_research
from location3.rail_cli import main as rail_main
from location3.reporting import write_bundle
from location3.scoring import score_research


def fixtures():
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    rail = json.loads((ROOT / "fixtures/demo/rail.json").read_text(encoding="utf-8"))
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    return profile, evidence, rail


class RailResearchTests(unittest.TestCase):
    def test_merge_replaces_commute_with_component_total_and_exposes_summary(self):
        profile, evidence, rail = fixtures()
        merged = merge_rail_research(evidence, rail)
        alder_commutes = [
            item for item in merged["observations"]
            if item["candidate_id"] == "alder-green"
            and item["metric"] == "door_to_door_commute"
        ]
        self.assertEqual(len(alder_commutes), 1)
        self.assertEqual(alder_commutes[0]["value"], 58)

        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        alder = next(item for item in results["candidates"] if item["id"] == "alder-green")
        self.assertEqual(alder["rail_summary"]["fastest_total_minutes"], 58)
        self.assertEqual(
            alder["rail_summary"]["journeys"][0]["london_arrival_station"],
            "London King's Cross",
        )

    def test_rejects_candidates_outside_shortlist_and_bad_component_math(self):
        _, evidence, rail = fixtures()
        outside = deepcopy(rail)
        outside["journeys"][0]["candidate_id"] = "not-shortlisted"
        with self.assertRaisesRegex(ValueError, "outside the candidate shortlist"):
            merge_rail_research(evidence, outside)

        bad_total = deepcopy(rail)
        bad_total["journeys"][0]["total_minutes"] = 57
        with self.assertRaisesRegex(ValueError, "component times"):
            merge_rail_research(evidence, bad_total)

        uncited_reliability = deepcopy(rail)
        uncited_reliability["journeys"][0]["sources"] = [
            source for source in uncited_reliability["journeys"][0]["sources"]
            if source["kind"] != "performance"
        ]
        with self.assertRaisesRegex(ValueError, "require a performance source"):
            merge_rail_research(evidence, uncited_reliability)

    def test_manifest_includes_rail_citations(self):
        profile, evidence, rail = fixtures()
        merged = merge_rail_research(evidence, rail)
        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_bundle(Path(directory), profile, merged, results)
        self.assertIn(
            "https://github.com/lukexyz/location-location-location/blob/main/fixtures/demo/rail.json",
            manifest["sources"],
        )

    def test_cli_preview_makes_no_output(self):
        profile, evidence, rail = fixtures()
        results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            run_dir = temporary / "base"
            write_bundle(run_dir, profile, evidence, results)
            rail_path = temporary / "rail.json"
            rail_path.write_text(json.dumps(rail), encoding="utf-8")
            output = temporary / "rail-output"
            status = rail_main([
                "--run-dir", str(run_dir), "--input", str(rail_path),
                "--output", str(output),
            ])
            self.assertEqual(status, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
