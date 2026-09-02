---
name: location-research
description: Research and score bounded UK location candidates with LOCATION³ when the user wants a local, cited comparison of places to live. Do not use for an unbounded national data build or for merely viewing an existing result bundle.
---

# Location research

Run the repository's deterministic workflow; do not invent measurements or assign scores directly.

1. Confirm the approximate origin, route duration/profile, run name, and selected local preferences. Never ask for or print `ORS_API_KEY`.
2. Run `python scripts/research_location.py --latitude LAT --longitude LON --minutes MINUTES --run-name NAME` without `--execute`.
3. Show the preview to the user and wait for explicit approval before adding `--execute`. Do not call providers directly or exceed the command's two-call cap.
4. On approval, run the same command with `--execute`. Compatible cached responses are reused automatically; rerun the identical command to resume after a provider failure.
5. Check `research-runs/NAME/provenance.json` and report cache use, unavailable evidence, confidence limits, and provider failures. Treat café reach as a 1.2 km straight-line proxy, not a walking-network isochrone.
6. Point the user to `research-runs/NAME/results.json` for the viewer. Keep the run, cache, profile, origin, and credentials private unless the user explicitly requests publication.

If required network access, credentials, or provider availability are missing, preserve any cache progress and explain exactly what can be resumed. Do not replace missing evidence with uncited inference.
