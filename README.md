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

```powershell
npm install
npm run dev
```

The viewer starts with fictional data. Importing a `results.json` reads it only
inside the current browser tab; it is not uploaded or stored. Map tiles remain an
external network request.
