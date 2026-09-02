"""Generate the public fictional viewer fixture from deterministic Python scoring."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from location3.config import load_preferences  # noqa: E402
from location3.housing import merge_housing_research  # noqa: E402
from location3.rail import merge_rail_research  # noqa: E402
from location3.scoring import score_research  # noqa: E402
from location3.street_care import merge_street_care_research  # noqa: E402


# Importance used for the what-if parity fixture: a café-led, commute-light profile that
# demotes betting shops to an informational metric.
REWEIGHTED_IMPORTANCE = {
    "cafes": 5,
    "door_to_door_commute": 1,
    "betting_shops": 0,
    "yoga_studios": 4,
    "premium_grocers": 3,
}
# Category importance for the same parity fixture, so the viewer's category sliders
# are proven against Python too.
REWEIGHTED_CATEGORY_IMPORTANCE = {"essentials": 3, "environment": 5, "amenities": 4}


def main() -> int:
    profile = json.loads((ROOT / "fixtures/demo/profile.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT / "fixtures/demo/evidence.json").read_text(encoding="utf-8"))
    rail_research = json.loads((ROOT / "fixtures/demo/rail.json").read_text(encoding="utf-8"))
    housing_research = json.loads((ROOT / "fixtures/demo/housing.json").read_text(encoding="utf-8"))
    street_research = json.loads((ROOT / "fixtures/demo/street-care.json").read_text(encoding="utf-8"))
    evidence = merge_rail_research(evidence, rail_research)
    evidence = merge_housing_research(profile, evidence, housing_research)
    evidence = merge_street_care_research(evidence, street_research)
    preferences = load_preferences(ROOT, include_local=False)
    profile["weights"] = preferences["weights"]
    profile["category_weights"] = preferences["category_weights"]
    profile["unknown_data_policy"] = preferences["scoring"]["unknown_data_policy"]
    results = score_research(profile, evidence, "2026-08-01T12:00:00+00:00")
    output = ROOT / "app/src/data/demo-results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    _write(output, results)
    print(f"Wrote public demo to {output}")

    # A second scoring of the same evidence with different importance. The viewer's
    # what-if reweighting is tested against it so the browser arithmetic cannot
    # drift from this scorer.
    reweighted_profile = json.loads(json.dumps(profile))
    reweighted_profile["weights"].update(REWEIGHTED_IMPORTANCE)
    reweighted_profile["category_weights"].update(REWEIGHTED_CATEGORY_IMPORTANCE)
    reweighted = score_research(reweighted_profile, evidence, "2026-08-01T12:00:00+00:00")
    reweighted_output = ROOT / "app/src/data/demo-results.reweighted.json"
    _write(reweighted_output, reweighted)
    print(f"Wrote reweighted parity fixture to {reweighted_output}")
    return 0


def _write(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
