# LOCATION³

A local, user-run instrument for finding places to live.

Requires Python 3.11 or newer.

```powershell
python scripts/run_fixture.py
python -m unittest discover -s tests
uvx ruff@0.15.0 check src scripts tests
```

The demo writes a private, gitignored report to `research-runs/demo/report.html`.
Public defaults live in `preferences.toml`; optional local overrides live in the
gitignored `preferences.local.toml`.

Preview a bounded location research run (no network or writes):

```powershell
python scripts/research_location.py --latitude LAT --longitude LON --minutes 30
```

Optional repeatable flags include `--destination
"LABEL|MODE|ARRIVAL|MAX_MINUTES"`, `--constraint "METRIC<=VALUE"`, and `--weight
"METRIC=VALUE"`; housing flags are also available. The preview discloses those
choices, the configurable premium-grocer fragments, and the two-call ceiling.
Set a local `ORS_API_KEY`, review the preview, then add `--execute`.
Codex users can invoke the same workflow with `$location-research`; Claude Code
users can invoke it with `/location-research`. Both entry points defer to the
single workflow in `skills/location-research/SKILL.md`.

Preview a cited rail import for that run (no network or writes), then add
`--execute` after review:

```powershell
python scripts/import_rail.py --run-dir research-runs/NAME --input rail.json
```

The input must match `schemas/rail-research.schema.json` and may reference only
candidates already in the run.

Preview a cited housing import (also zero-network), then add `--execute` after
reviewing its requirements, geographic resolution, and citations:

```powershell
python scripts/import_housing.py --run-dir research-runs/NAME-rail --input housing.json
```

The private input must match `schemas/housing-research.schema.json`. It supplies
the buy or monthly-rent budget, property requirements, and one market estimate
per researched shortlist candidate. The importer computes affordability; it
does not check live inventory, and any property-portal URL remains an external
search action.

Preview cited street-care evidence for the latest enriched run, then add
`--execute` after reviewing its limitations:

```powershell
python scripts/import_street_care.py --run-dir research-runs/NAME-rail-housing --input street-care.json
```

The private input must match `schemas/street-care-research.schema.json`.
Fly-tipping remains a low-confidence local-authority prior, raw report volume is
informational, and only a structured visit audit no more than 180 days old
overrides the proxy score.

```powershell
npm install
npm run dev
```

The viewer starts with fictional data. Importing a `results.json` reads it only
inside the current browser tab; it is not uploaded or stored. Map tiles remain an
external network request. Compatible results include their route boundary and
provider assumptions; the viewer draws that boundary, exposes weighted score
contributions, and can sort the register without changing authoritative ranks.

Every generated profile, evidence bundle, result, and provenance manifest is
validated against the Draft 2020-12 contracts in `schemas/` before it is written.
Python retains the cross-file and mathematical checks that JSON Schema cannot
express. Browser contract-parity tests use AJV only during development; it is not
included in the public viewer bundle.

Run the viewer checks with:

```powershell
npm run test:web
npm run test:e2e
npm run build
```

Pushes and pull requests to `main` run the **Verify** workflow: Python lint and
unit tests, demo reproducibility, viewer unit tests, browser and accessibility
tests, and the production build.

The Pages deployment is deliberately manual. After selecting **GitHub Actions**
as the repository's Pages source, run **Deploy viewer to Pages** from the Actions
tab. The workflow tests the viewer and deploys only `app/dist`, which contains
the fictional public demo—not ignored preferences or private research runs.
