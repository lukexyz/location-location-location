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
