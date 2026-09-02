import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.validation import validate_evidence, validate_profile
from location3.housing import merge_housing_research
from location3.rail import merge_rail_research
from location3.street_care import merge_street_care_research


class ContractTests(unittest.TestCase):
    def test_every_public_schema_is_valid_json(self):
        schemas = list((ROOT / "schemas").glob("*.schema.json"))
        self.assertEqual(len(schemas), 7)
        for path in schemas:
            with self.subTest(path=path.name):
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["$schema"],
                                 "https://json-schema.org/draft/2020-12/schema")

    def test_fixture_matches_runtime_contracts(self):
        profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
        validate_profile(profile)
        validate_evidence(evidence)
        rail = json.loads((ROOT / "fixtures/demo/rail.json").read_text(encoding="utf-8"))
        enriched = merge_rail_research(evidence, rail)
        housing = json.loads((ROOT / "fixtures/demo/housing.json").read_text(encoding="utf-8"))
        enriched = merge_housing_research(profile, enriched, housing)
        street = json.loads((ROOT / "fixtures/demo/street-care.json").read_text(encoding="utf-8"))
        validate_evidence(merge_street_care_research(enriched, street))


if __name__ == "__main__":
    unittest.main()
