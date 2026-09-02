from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences
from location3.scoring import score_research


def fixture_data():
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    return profile, evidence


class ScoringTests(unittest.TestCase):
    def test_fixture_ranking_is_repeatable_and_constraints_rank_first(self):
        profile, evidence = fixture_data()
        first = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        second = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        self.assertEqual(first, second)
        self.assertEqual([item["name"] for item in first["candidates"]], [
            "Alder Green", "Northbridge", "Mereford"
        ])
        self.assertTrue(first["candidates"][0]["hard_constraints"]["passed"])
        self.assertFalse(first["candidates"][2]["hard_constraints"]["passed"])

    def test_missing_metric_is_omitted_and_reduces_confidence(self):
        profile, evidence = fixture_data()
        complete = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        changed = deepcopy(evidence)
        changed["observations"] = [
            item for item in changed["observations"] if item["id"] != "alder-cafes"
        ]
        incomplete = score_research(profile, changed, "2026-08-01T12:00:00+00:00")
        complete_alder = next(item for item in complete["candidates"] if item["id"] == "alder-green")
        incomplete_alder = next(item for item in incomplete["candidates"] if item["id"] == "alder-green")
        self.assertIn("cafes", incomplete_alder["missing_metrics"])
        self.assertLess(incomplete_alder["confidence"], complete_alder["confidence"])

    def test_zero_weight_metric_remains_visible_but_does_not_contribute(self):
        profile, evidence = fixture_data()
        profile["weights"]["cafes"] = 0
        results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        alder = next(item for item in results["candidates"] if item["id"] == "alder-green")
        cafes = next(
            item for item in alder["informational_metrics"] if item["metric"] == "cafes"
        )
        self.assertFalse(cafes["active"])
        self.assertEqual(cafes["category_contribution"], 0)


if __name__ == "__main__":
    unittest.main()
