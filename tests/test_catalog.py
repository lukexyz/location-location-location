from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.catalog import METRICS


class MetricCurveTests(unittest.TestCase):
    def test_piecewise_curve_hits_documented_anchors(self):
        commute = METRICS["door_to_door_commute"]
        self.assertEqual(commute.score(20), 100)
        self.assertEqual(commute.score(45), 75)
        self.assertEqual(commute.score(120), 0)

    def test_negative_metric_rewards_lower_counts(self):
        betting = METRICS["betting_shops"]
        self.assertGreater(betting.score(0), betting.score(3))
        self.assertEqual(betting.score(0), 100)

    def test_log_curve_has_diminishing_returns(self):
        cafes = METRICS["cafes"]
        first_increment = cafes.score(2) - cafes.score(1)
        later_increment = cafes.score(8) - cafes.score(7)
        self.assertGreater(first_increment, later_increment)


if __name__ == "__main__":
    unittest.main()
