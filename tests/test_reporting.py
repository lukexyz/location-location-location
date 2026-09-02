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


class ReportingTests(unittest.TestCase):
    def test_bundle_contains_contract_files_and_standalone_report(self):
        profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
        preferences = load_preferences(ROOT, include_local=False)
        profile["weights"] = preferences["weights"]
        profile["category_weights"] = preferences["category_weights"]
        results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = write_bundle(output, profile, evidence, results)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"profile.json", "evidence.json", "results.json", "provenance.json", "report.html"},
            )
            self.assertIn("Welwyn Garden City", (output / "report.html").read_text(encoding="utf-8"))
            self.assertTrue(manifest["checksums"]["results.json"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
