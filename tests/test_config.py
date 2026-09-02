from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences


PUBLIC = """version = 1
[scoring]
unknown_data_policy = "warn"
[category_weights]
essentials = 5
environment = 3
amenities = 2
[weights]
door_to_door_commute = 5
housing_affordability = 5
street_care = 3
green_space = 3
betting_shops = 2
cafes = 2
yoga_studios = 1
premium_grocers = 1
"""


class PreferenceTests(unittest.TestCase):
    def test_local_preferences_overlay_public_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.toml").write_text(PUBLIC, encoding="utf-8")
            (root / "preferences.local.toml").write_text(
                "version = 1\n[weights]\ncafes = 9\n", encoding="utf-8"
            )
            preferences = load_preferences(root)
            self.assertEqual(preferences["weights"]["cafes"], 9)
            self.assertEqual(preferences["weights"]["housing_affordability"], 5)

    def test_public_only_ignores_local_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.toml").write_text(PUBLIC, encoding="utf-8")
            (root / "preferences.local.toml").write_text(
                "version = 1\n[weights]\ncafes = 9\n", encoding="utf-8"
            )
            preferences = load_preferences(root, include_local=False)
            self.assertEqual(preferences["weights"]["cafes"], 2)


if __name__ == "__main__":
    unittest.main()
