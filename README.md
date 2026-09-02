# LOCATION³

A local, user-run instrument for finding places to live.

Requires Python 3.11 or newer.

```powershell
python scripts/run_fixture.py
python -m unittest discover -s tests
```

The demo writes a private, gitignored report to `research-runs/demo/report.html`.
Public defaults live in `preferences.toml`; optional local overrides live in the
gitignored `preferences.local.toml`.

Preview a bounded café research run (no network or writes):

```powershell
python scripts/research_location.py --latitude LAT --longitude LON --minutes 30
```

Set a local `ORS_API_KEY`, review the preview, then add `--execute`.
Codex users can invoke the same workflow with `$location-research`.

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

```powershell
npm install
npm run dev
```

The viewer starts with fictional data. Importing a `results.json` reads it only
inside the current browser tab; it is not uploaded or stored. Map tiles remain an
external network request.
