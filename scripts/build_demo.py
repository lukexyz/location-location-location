"""Generate the public fictional viewer fixture from deterministic Python scoring."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences  # noqa: E402
from location3.scoring import score_research  # noqa: E402


def main() -> int:
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    profile["unknown_data_policy"] = preferences["scoring"]["unknown_data_policy"]
    results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
    output = ROOT / "app/src/data/demo-results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote public fictional demo to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
