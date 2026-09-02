import json
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.validation import validate_evidence, validate_profile
from location3.housing import merge_housing_research
from location3.rail import merge_rail_research
from location3.reporting import write_bundle
from location3.schema_validation import validate_schema_document
from location3.scoring import score_research
from location3.street_care import merge_street_care_research


class ContractTests(unittest.TestCase):
    def test_every_public_schema_is_valid_json(self):
        schemas = list((ROOT / "schemas").glob("*.schema.json"))
        self.assertEqual(len(schemas), 7)
        for path in schemas:
            with self.subTest(path=path.name):
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["$schema"],
                                 "https://json-schema.org/draft/2020-12/schema")
                Draft202012Validator.check_schema(
                    json.loads(path.read_text(encoding="utf-8"))
                )

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
        enriched = merge_street_care_research(enriched, street)
        validate_evidence(enriched)
        results = score_research(profile, enriched, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            write_bundle(Path(directory), profile, enriched, results)

    def test_schema_rejects_fields_the_contract_does_not_publish(self):
        profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
        profile["secret"] = "must not cross the contract boundary"
        with self.assertRaisesRegex(ValueError, r"research-profile.*Additional properties"):
            validate_schema_document(profile, "research-profile.schema.json")


if __name__ == "__main__":
    unittest.main()
