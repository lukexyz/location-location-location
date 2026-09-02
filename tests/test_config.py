from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import brand_group, load_preferences


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
[brand_groups.premium_grocers]
patterns = ["Waitrose", "M&S"]
shop_types = ["supermarket", "convenience"]
"""

LOCAL_BRANDS = """version = 1
[brand_groups.premium_grocers]
patterns = {patterns}
shop_types = ["supermarket"]
"""


class PreferenceTests(unittest.TestCase):
    def test_local_preferences_overlay_public_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.toml").write_text(PUBLIC, encoding="utf-8")
            (root / "preferences.local.toml").write_text(
                "version = 1\n[weights]\ncafes = 4\n", encoding="utf-8"
            )
            preferences = load_preferences(root)
            self.assertEqual(preferences["weights"]["cafes"], 4)
            self.assertEqual(preferences["weights"]["housing_affordability"], 5)

    def test_local_preferences_can_redefine_brand_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.toml").write_text(PUBLIC, encoding="utf-8")
            (root / "preferences.local.toml").write_text(
                LOCAL_BRANDS.format(patterns='["Booths"]'), encoding="utf-8"
            )
            group = brand_group(load_preferences(root), "premium_grocers")
            self.assertEqual(group.patterns, ("Booths",))
            (root / "preferences.local.toml").write_text(
                LOCAL_BRANDS.format(patterns='["Booths\\"]"]'), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "brand_groups.premium_grocers is invalid"):
                load_preferences(root)

    def test_public_only_ignores_local_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.toml").write_text(PUBLIC, encoding="utf-8")
            (root / "preferences.local.toml").write_text(
                "version = 1\n[weights]\ncafes = 9\n", encoding="utf-8"
            )
            preferences = load_preferences(root, include_local=False)
            self.assertEqual(preferences["weights"]["cafes"], 2)

    def test_importance_is_limited_to_zero_through_five(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "preferences.toml").write_text(PUBLIC, encoding="utf-8")
            (root / "preferences.local.toml").write_text(
                "version = 1\n[weights]\ncafes = 6\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "0 to 5"):
                load_preferences(root)


if __name__ == "__main__":
    unittest.main()
