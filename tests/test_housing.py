from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences
from location3.housing import configure_housing_profile, merge_housing_research
from location3.housing_cli import main as housing_main
from location3.reporting import write_bundle
from location3.scoring import score_research
from location3.validation import validate_evidence


def fixtures():
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    housing = json.loads((ROOT / "fixtures/demo/housing.json").read_text(encoding="utf-8"))
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    profile = configure_housing_profile(profile, housing)
    return profile, evidence, housing


class HousingResearchTests(unittest.TestCase):
    def test_merge_computes_budget_ratio_and_exposes_non_inventory_summary(self):
        profile, evidence, housing = fixtures()
        merged = merge_housing_research(profile, evidence, housing)
        alder_observation = next(
            item for item in merged["observations"]
            if item["candidate_id"] == "alder-green"
            and item["metric"] == "housing_affordability"
        )
        self.assertEqual(alder_observation["value"], 0.78)

        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        alder = next(item for item in results["candidates"] if item["id"] == "alder-green")
        self.assertEqual(alder["housing_summary"]["typical_cost_gbp"], 390000)
        self.assertEqual(alder["housing_summary"]["inventory_status"], "not_checked")

    def test_rejects_outside_candidates_mode_geography_and_profile_mismatch(self):
        profile, evidence, housing = fixtures()
        outside = deepcopy(housing)
        outside["markets"][0]["candidate_id"] = "not-shortlisted"
        with self.assertRaisesRegex(ValueError, "outside the candidate shortlist"):
            merge_housing_research(profile, evidence, outside)

        rent_radius = deepcopy(housing)
        rent_radius["requirements"]["mode"] = "rent"
        rent_radius["markets"][0]["sources"][0]["kind"] = "rents"
        empty_housing_profile = deepcopy(profile)
        empty_housing_profile["search"]["housing"] = {}
        with self.assertRaisesRegex(ValueError, "published aggregate geography"):
            configure_housing_profile(empty_housing_profile, rent_radius)

        mismatch = deepcopy(profile)
        mismatch["search"]["housing"]["budget_gbp"] = 600000
        with self.assertRaisesRegex(ValueError, "do not match"):
            merge_housing_research(mismatch, evidence, housing)

    def test_rent_keeps_monthly_budget_and_coarse_published_geography(self):
        profile, evidence, housing = fixtures()
        rent = deepcopy(housing)
        rent["requirements"] = {
            "mode": "rent", "budget_gbp": 2000,
            "property_type": "flat", "bedrooms": 2,
        }
        rent["markets"] = [deepcopy(rent["markets"][0])]
        market = rent["markets"][0]
        market["typical_cost_gbp"] = 1600
        market["geography"] = {
            "kind": "local_authority", "label": "Example Borough", "radius_km": None,
        }
        market["sample_size"] = None
        market["sources"][0]["kind"] = "rents"
        profile["search"]["housing"] = {}
        profile = configure_housing_profile(profile, rent)
        merged = merge_housing_research(profile, evidence, rent)
        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        alder = next(item for item in results["candidates"] if item["id"] == "alder-green")
        self.assertEqual(alder["housing_summary"]["budget_period"], "month")
        self.assertEqual(alder["housing_summary"]["budget_ratio"], 0.8)
        self.assertIn(
            "Rent evidence uses coarse local authority geography", alder["warnings"]
        )

    def test_manifest_includes_housing_citations(self):
        profile, evidence, housing = fixtures()
        merged = merge_housing_research(profile, evidence, housing)
        results = score_research(profile, merged, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            manifest = write_bundle(Path(directory), profile, merged, results)
        self.assertIn(
            "https://github.com/lukexyz/location-location-location/blob/main/fixtures/demo/housing.json",
            manifest["sources"],
        )

    def test_evidence_contract_rejects_a_tampered_affordability_ratio(self):
        profile, evidence, housing = fixtures()
        merged = merge_housing_research(profile, evidence, housing)
        observation = next(
            item for item in merged["observations"]
            if item["candidate_id"] == "alder-green"
            and item["metric"] == "housing_affordability"
        )
        observation["value"] = 0.5
        with self.assertRaisesRegex(ValueError, "does not match market and budget"):
            validate_evidence(merged)

    def test_cli_preview_makes_no_output_and_can_configure_empty_profile(self):
        profile, evidence, housing = fixtures()
        profile["search"]["housing"] = {}
        results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            run_dir = temporary / "base"
            write_bundle(run_dir, profile, evidence, results)
            housing_path = temporary / "housing.json"
            housing_path.write_text(json.dumps(housing), encoding="utf-8")
            output = temporary / "housing-output"
            status = housing_main([
                "--run-dir", str(run_dir), "--input", str(housing_path),
                "--output", str(output),
            ])
            self.assertEqual(status, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
