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
5. If London rail evidence is requested, research only candidates already present in the run. Write a private input matching `schemas/rail-research.schema.json`; preserve station access, expected wait, scheduled rail, London last mile, changes, frequency, last useful departure, punctuality, and cancellations as separate facts. Use current primary/official timetable and performance sources or clearly labelled cited manual research. Use `null` for unavailable reliability or last-service facts; never substitute marketing journey times or invented values.
6. Run `python scripts/import_rail.py --run-dir research-runs/NAME --input RAIL.json` without `--execute`. Show the preview and citations, wait for explicit approval, then rerun with `--execute`. This importer makes no network calls and writes a sibling `NAME-rail` bundle by default.
7. If housing evidence is requested, research only candidates already present in the run. Write a private input matching `schemas/housing-research.schema.json`. For buying, use cited HM Land Registry transactions for the requested property type and retain period, radius, and sample size; expand from 2 km toward 5 km only when the smaller sample is inadequate. For renting, use current cited ONS rent evidence and preserve its published local-authority or broader geography. Keep unavailable facts explicit, do not scrape property portals, and never infer current availability from sold-price or rent aggregates.
8. Run `python scripts/import_housing.py --run-dir research-runs/NAME --input HOUSING.json` without `--execute`. Show the preview, requirements, geography, and citations; wait for explicit approval, then rerun with `--execute`. This importer makes no network calls, computes the cost-to-budget ratio deterministically, and writes a sibling `NAME-housing` bundle by default. Treat any listing URL only as an external search action.
9. If street-care evidence is requested, research only candidates already present in the run and write a private input matching `schemas/street-care-research.schema.json`. Use current cited Defra fly-tipping level, prior-period level, and reporting basis only as a low-resolution prior. Add FixMyStreet or council report density, unresolved share, and resolution time only where the licence and geography are clear. Preserve report volume but do not interpret high or missing counts as cleanliness. A personal visit audit must use all six structured ratings; only one no more than 180 days old overrides the proxy.
10. Run `python scripts/import_street_care.py --run-dir research-runs/NAME --input STREET-CARE.json` without `--execute`. Show the preview, proxy limitations, stale audits, reporting-basis warnings, and citations; wait for explicit approval, then rerun with `--execute`. The importer makes no network calls and writes a sibling `NAME-street-care` bundle by default.
11. Check the final `provenance.json` and report cache use, unavailable evidence, confidence limits, and provider failures. Treat café reach as a 1.2 km straight-line proxy, not a walking-network isochrone.
12. Point the user to the final `results.json` for the viewer. Keep the run, cache, profile, origin, rail, housing and street-care inputs, visit audits, budgets, and credentials private unless the user explicitly requests publication.

If required network access, credentials, or provider availability are missing, preserve any cache progress and explain exactly what can be resumed. Do not replace missing evidence with uncited inference.
