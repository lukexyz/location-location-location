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

```powershell
npm install
npm run dev
```

The viewer starts with fictional data. Importing a `results.json` reads it only
inside the current browser tab; it is not uploaded or stored. Map tiles remain an
external network request.
