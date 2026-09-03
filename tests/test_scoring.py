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
    profile = json.loads((ROOT / "fixtures/synthetic/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/synthetic/evidence.json").read_text(encoding="utf-8"))
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
            "Welwyn Garden City", "Hemel Hempstead", "Maidenhead"
        ])
        self.assertEqual(first["candidates"][0]["hard_constraints"]["status"], "pass")
        self.assertEqual(first["candidates"][2]["hard_constraints"]["status"], "fail")
        self.assertEqual(first["schema_version"], "2")
        for candidate in first["candidates"]:
            self.assertEqual(candidate["unmeasured_categories"], [])
            self.assertEqual(candidate["score_coverage_percent"], 100.0)

    def test_missing_metric_is_omitted_and_reduces_confidence(self):
        profile, evidence = fixture_data()
        complete = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        changed = deepcopy(evidence)
        changed["observations"] = [
            item for item in changed["observations"] if item["id"] != "welwyn-cafes"
        ]
        incomplete = score_research(profile, changed, "2026-08-01T12:00:00+00:00")
        complete_alder = next(item for item in complete["candidates"] if item["id"] == "welwyn-garden-city")
        incomplete_alder = next(item for item in incomplete["candidates"] if item["id"] == "welwyn-garden-city")
        self.assertIn("cafes", incomplete_alder["missing_metrics"])
        self.assertLess(incomplete_alder["confidence"], complete_alder["confidence"])

    def test_unknown_limits_rank_below_passes_and_above_failures(self):
        profile, evidence = fixture_data()
        changed = deepcopy(evidence)
        changed["observations"] = [
            item for item in changed["observations"] if item["id"] != "hemel-commute"
        ]
        results = score_research(profile, changed, "2026-08-01T12:00:00+00:00")
        by_name = {item["name"]: item for item in results["candidates"]}
        hemel = by_name["Hemel Hempstead"]
        self.assertEqual(hemel["hard_constraints"]["status"], "unknown")
        self.assertEqual(hemel["hard_constraints"]["results"][0]["status"], "unknown")
        self.assertIsNone(hemel["hard_constraints"]["results"][0]["actual"])
        self.assertIn(
            "Unknown hard constraint: door_to_door_commute; no evidence was measured",
            hemel["warnings"],
        )
        self.assertEqual(
            [item["name"] for item in results["candidates"]],
            ["Welwyn Garden City", "Hemel Hempstead", "Maidenhead"],
        )
        self.assertEqual(
            [item["hard_constraints"]["status"] for item in results["candidates"]],
            ["pass", "unknown", "fail"],
        )

    def test_unmeasured_category_stays_visible_with_coverage(self):
        profile, evidence = fixture_data()
        changed = deepcopy(evidence)
        changed["observations"] = [
            item for item in changed["observations"]
            if item["id"] not in {"welwyn-commute", "welwyn-housing"}
        ]
        results = score_research(profile, changed, "2026-08-01T12:00:00+00:00")
        welwyn = next(item for item in results["candidates"] if item["id"] == "welwyn-garden-city")
        self.assertEqual(
            welwyn["unmeasured_categories"], [{"category": "essentials", "weight": 5.0}]
        )
        self.assertEqual(welwyn["score_coverage_percent"], 50.0)
        self.assertEqual(
            [category["category"] for category in welwyn["categories"]],
            ["amenities", "environment"],
        )
        self.assertEqual(
            welwyn["warnings"][0],
            "Unmeasured category: essentials (weight 5) has no evidence; the overall "
            "score covers 50% of the intended category weight",
        )
        self.assertEqual(
            welwyn["missing_metrics"], ["door_to_door_commute", "housing_affordability"]
        )
        self.assertLess(welwyn["confidence"], 100)

    def test_zero_weighted_categories_are_not_reported_as_unmeasured(self):
        profile, evidence = fixture_data()
        profile["weights"]["door_to_door_commute"] = 0
        profile["weights"]["housing_affordability"] = 0
        changed = deepcopy(evidence)
        changed["observations"] = [
            item for item in changed["observations"]
            if item["metric"] not in {"door_to_door_commute", "housing_affordability"}
        ]
        results = score_research(profile, changed, "2026-08-01T12:00:00+00:00")
        for candidate in results["candidates"]:
            self.assertEqual(candidate["unmeasured_categories"], [])
            self.assertEqual(candidate["score_coverage_percent"], 100.0)

    def test_zero_weight_metric_remains_visible_but_does_not_contribute(self):
        profile, evidence = fixture_data()
        profile["weights"]["cafes"] = 0
        results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        alder = next(item for item in results["candidates"] if item["id"] == "welwyn-garden-city")
        cafes = next(
            item for item in alder["informational_metrics"] if item["metric"] == "cafes"
        )
        self.assertFalse(cafes["active"])
        self.assertEqual(cafes["category_contribution"], 0)


if __name__ == "__main__":
    unittest.main()
