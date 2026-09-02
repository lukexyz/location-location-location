# MUSINGS

## 2026-09-01 — Initial Product Direction

### Mission

Build a place-finding instrument that helps people discover where to live by combining practical constraints—housing cost and real door-to-door journeys—with the texture of everyday life: useful amenities, green space, street care, and playful signals of neighbourhood character. The app should make personal trade-offs visible and explainable rather than claiming there is one objectively perfect place.

### Motivation

Conventional property portals are good at answering “which homes are currently advertised?” but much weaker at answering “where would everyday life suit me?” Their filters generally stop at price, bedrooms, property type, and a radius drawn around a place. They do not combine realistic journeys, access to useful amenities, environmental character, or subjective preferences into a coherent location search.

This project should recommend areas before individual listings. It should narrow a large commuter region into a defensible shortlist, explain the trade-offs behind every recommendation, and then link the user to appropriate property searches. It is a decision-support tool, not an oracle or an automated property valuer.

### Product Principles

- **Hard constraints remove places.** Examples include a maximum driving time, a maximum door-to-door commute, or a housing budget.
- **Weighted preferences rank the survivors.** Amenities, green space, street care, affordability, and similar qualities contribute according to user-selected importance.
- **Informational facts stay visible without silently changing the score.** Rail frequency, changes, reliability, last trains, and source confidence begin as facts and become scoring inputs only when the user gives them weight.
- **Every score must be explainable.** A place should say why it scored 82, which evidence helped or hurt it, how fresh that evidence is, and what is missing.
- **Uncertainty must remain visible.** Missing or low-resolution evidence is not equivalent to an average result, zero incidents, or a clean street.
- **No surprise costs.** Changing controls does not trigger chargeable requests. Network work happens only when the user deliberately resolves a search, and free-tier exhaustion fails closed.
- **Private by default.** Profiles, budgets, destinations, visit notes, and results remain in the user's browser. Sharing the app does not share a person's data.
- **Playfulness sits on top of serious evidence.** Humorous labels should make the tool enjoyable without disguising weak data or counting the same signal twice.

### Decisions Made

| Decision | Agreed direction |
| --- | --- |
| Initial geography | The London commuter belt in England |
| Primary result | Recommend areas first, then link to external property searches |
| Housing modes | Buy and Rent, selected with a mode switch |
| Destinations | Several saved places, each with mode, arrival time, maximum duration, and importance |
| Main map result | Numbered, colour-coded score pins plus a ranked list |
| Secondary map result | Optional suitability surface and hard-constraint isochrones |
| Scoring controls | Importance from 0–5 plus an optional hard-requirement toggle |
| Visual direction | Strong but legible [GL4SS-inspired](https://github.com/elder-plinius/GL4SS) instrument aesthetic |
| GL4SS relationship | Key aesthetic reference, implemented independently with no direct source adaptation |
| Shared deployment | GitHub Pages frontend plus a free-tier routing proxy |
| Private tooling | Localhost companion for data rebuilding and audits |
| Agent role | Optional data steward; agents never calculate authoritative scores |
| Accounts and telemetry | No accounts and no product analytics in v1 |
| Personal data | Browser-local only; never committed or placed in public snapshots |

### Metric Catalogue

#### Launch metrics and default importance

| Metric | Default importance | Behaviour |
| --- | ---: | --- |
| Door-to-door commute | 5 | Positive for shorter, dependable journeys; may also be a hard maximum |
| Housing affordability | 5 | Positive when local evidence fits the selected mode, budget, and property type |
| Street care | 4 | Negative for evidence of litter, fly-tipping, graffiti, overflowing bins, and slow resolution |
| Green space | 3 | Positive for useful green space reachable on foot |
| Betting shops | 3 | Negative walking-access/density signal |
| Cafés | 2 | Positive walking-access signal with diminishing returns |
| Yoga studios | 2 | Positive walking-access signal with diminishing returns |
| Premium grocers | 2 | Positive access to a configurable group such as M&S Foodhall and Waitrose |

Weights are defaults, not value judgements imposed on every user. A weight of zero makes a metric informational. A hard requirement is evaluated before scoring.

#### Street care and cleanliness

There is no sufficiently current, granular, consistent national cleanliness dataset for neighbourhood ranking. The former official NI195 measure covered litter, detritus, graffiti, and fly-posting, but the nationally published data is historical. Later Keep Britain Tidy national survey results cannot be analysed reliably at regional or local level. Current LG Inform street-cleansing metrics are voluntary, and participation is incomplete.

The launch score should therefore combine evidence cautiously:

- Current Defra fly-tipping trends per 1,000 residents at local-authority level, treated as a low-resolution prior.
- FixMyStreet category counts at LSOA/local-authority level where licensing and release quality permit.
- Council-specific Open311 or open-data adapters for litter, fly-tipping, overflowing bins, graffiti, abandoned vehicles, and street-cleaning reports where available.
- Unresolved-report density and median resolution time, normalised within the same council to reduce differences in reporting policy.
- A structured personal visit audit covering litter, dog fouling, graffiti, weeds/detritus, overflowing bins, and overall upkeep. A recent personal audit overrides the proxy for that user only.

High incident counts can indicate active residents and good reporting systems rather than a dirtier place. Missing reports never mean “clean.” Places with uncertain evidence remain in results but receive a prominent confidence warning and a suggested visit audit.

#### Playful derived readouts

- **Sourdough-to-Slots:** positive food/coffee signals compared with betting-shop exposure.
- **Pavement Pride:** the presentation of street-care evidence and personal audit results.
- **Last Train Home:** the practical usefulness of the final evening service.
- **Rail Roulette:** service frequency, changes, punctuality, and cancellations.
- **Emergency Croissant Radius:** walking access to cafés and bakeries.
- **Green Escape:** useful green space reachable without driving.

Derived readouts are alternate presentations of underlying metrics. They must not contribute additional score when their component metrics are already active.

#### Later metric modules

- Crime and anti-social behaviour, with population and visitor-footfall context.
- River, sea, and surface-water flood risk.
- Air quality, road/rail/aircraft noise, and distance from major roads.
- Fixed broadband and mobile coverage.
- Schools and childcare for users who choose to include them.
- EPC evidence, likely heating costs, and energy efficiency.
- Planning applications, development pressure, and conservation constraints.
- GP, pharmacy, dentist, hospital, and veterinary access.
- Cycling infrastructure, walkability, gradients, and car dependence.
- Pubs, bakeries, independent shops, bookshops, cinemas, theatres, and other cultural “third places.”
- Station parking, accessibility, and line/operator resilience where dependable data exists.
- Optional street-imagery cleanliness analysis only after coverage, licensing, staleness, and model accuracy have been measured.

### Research Findings

#### GL4SS inspiration and licensing

[GL4SS](https://github.com/elder-plinius/GL4SS) is a React application whose map uses Leaflet and Esri World Imagery. Its appeal comes less from novel map mechanics than from treating the whole interface as one deliberate instrument: a full-bleed view, restrained controls, technical typography, physical-feeling dials and levers, and clear feedback about actions that cost money.

GL4SS is licensed AGPL-3.0-or-later. Directly adapting its source for a networked application would require offering the corresponding source to users. This project will instead implement the map and interface independently, borrowing broad interaction and art-direction principles without copying code, prose, shaders, or distinctive assets.

#### Aesthetic brief from GL4SS

[GL4SS is the key aesthetic and interaction reference](https://github.com/elder-plinius/GL4SS), not a passing visual influence. LOCATION³ should translate its underlying design discipline into a different kind of instrument:

- Treat the map as the full-bleed visual field rather than a widget inside a conventional dashboard.
- Make the surrounding interface feel like one machined object with a coherent material, edge treatment, light direction, and depth system.
- Keep permanent chrome sparse. Controls earn their place by steering the search or reporting something the system genuinely knows.
- Use distinct typographic voices for machine labels and tabular numbers, readable evidence, and occasional editorial explanation.
- Give the primary actions physical clarity: tuning preferences prepares the search, while pulling **RESOLVE** deliberately performs routing work.
- Let motion communicate state. A scan, sweep, pulse, or change in instrument lighting should explain calculation, selection, confidence, or failure rather than decorate idle screens.
- Preserve the tension between technical precision and a slightly mysterious, cinematic atmosphere, while keeping scores, rankings, caveats, and source evidence immediately legible.
- Avoid generic SaaS conventions such as floating white cards, interchangeable pill controls, gratuitous gradients, and a dense wall of filters.
- Design mobile as the same instrument reconfigured for a smaller viewport, not as a visually unrelated secondary interface.

The translation should remain original. GL4SS's time dial becomes preference and commute tuning; its explicit spending lever inspires the quota-safe **RESOLVE** action; its status language becomes source freshness, confidence, cache, and routing-state feedback. LOCATION³ must develop its own name, symbols, animation, copy, layout, and visual assets.

#### Property data boundary

There is no suitable free, general-purpose read API for current Rightmove or Zoopla inventory. Their documented integrations primarily serve members, agents, data partners, or commercial products. Scraping listings would be brittle and create contractual and operational risk.

The first release will rank areas, use official sold-price and rent evidence for affordability, and generate deep links to listing searches. It will not claim that a currently available property exists merely because an area appears affordable.

Useful official sources include:

- [HM Land Registry Price Paid Data](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads), updated monthly and reusable under the Open Government Licence subject to its address-data conditions.
- ONS private-rent publications for current local-authority and bedroom-category evidence, acknowledging their coarser geography.
- Energy Performance of Buildings data as a possible later property-quality source, subject to its account and licensing requirements.

#### Maps, POIs, and routing

- OpenStreetMap extracts can supply cafés, yoga/fitness facilities, bookmakers, supermarkets, green space, roads, paths, and brand tags. Production data should come from regional extracts such as Geofabrik rather than burdening public Overpass services. ODbL attribution and derived-database obligations must be preserved.
- [Esri's basemap service](https://developers.arcgis.com/rest/basemap-styles/) currently includes a free monthly tile allowance suitable for a private or small shared app. It requires a token, correct attribution, quota monitoring, and a swappable fallback.
- [TravelTime](https://docs.traveltime.com/api/overview/key-concepts) supports UK driving and public-transport time maps and matrices, arrival searches, walking limits, and door-to-door journeys. Its restricted free access is suitable for a small cached deployment, not unlimited public traffic.
- The routing key cannot safely live in a static Pages bundle. A small Cloudflare Worker will hold it as an encrypted secret and impose validation, caching, and rate limits. The [Workers Free plan](https://developers.cloudflare.com/workers/platform/pricing/) currently fails after its daily allowance rather than billing an overage.

#### Rail information

- [Network Rail open feeds](https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds/) provide daily schedules in CIF/JSON and related infrastructure feeds subject to registration and terms.
- The Rail Data Marketplace and National Rail Darwin provide timetable and real-time information for registered users.
- NaPTAN supplies public-transport access nodes and station locations.
- [ORR station performance](https://dataportal.orr.gov.uk/performance) supplies station/operator punctuality and cancellation evidence.
- TfL's open Unified API can provide London journey information if a later implementation needs to supplement the primary routing provider.

Door-to-door commute time should include access to the departure station, expected waiting, scheduled rail/transfers, and the London last mile. Marketing-style “X minutes to London” figures are insufficient on their own.

#### Cleanliness evidence

- [Defra's current fly-tipping statistics](https://www.gov.uk/government/statistics/fly-tipping-statistics-for-england/fly-tipping-statistics-for-england-2024-to-2025) cover English local authorities but warn strongly against simplistic comparisons because authorities identify and record incidents differently.
- The [historical NI195 dataset](https://www.data.gov.uk/dataset/8883b252-7800-4652-b1b3-f72d814f20e4/ni-195-improved-street-and-environmental-cleanliness) describes a useful measurement framework but is too old to rank current places.
- [FixMyStreet geographic counts](https://data.mysociety.org/datasets/fms-geographic/) offer report counts by LSOA and local authority; coordinate-level research data requires a separate request.

This evidence justifies a meaningful but explicitly lower-confidence street-care score, not a fabricated nationwide cleanliness heatmap.

---

### Agreed Initial Implementation Plan: LOCATION³

#### Product experience

Build an original, GL4SS-inspired application that ranks places to rent or buy within the London commuter belt. The working title is **LOCATION³ — The Place-Finding Instrument**.

The public experience will be a full-screen satellite map with dark, machined-looking chrome, angular technical typography, restrained colour, circular 0–100 pins, a ranked shortlist, and an evidence dossier for each place. It should feel theatrical without making ordinary tasks difficult to understand.

Onboarding collects:

- Buy or Rent mode.
- Budget and property type.
- One or more destinations with travel mode, arrival day/time, importance, and an optional maximum journey duration.
- Metric importance and optional hard requirements.

The main result is a set of named town/neighbourhood pins and a sortable side panel. Selecting a place shows:

- Overall score, category scores, confidence, and hard-constraint status.
- Every metric's raw observation, normalised score, weighted contribution, source date, and caveats.
- Door-to-door journeys to each saved destination.
- Nearest useful station, fastest London journey, frequency, changes, last useful train, punctuality, and cancellations.
- Buy/rent affordability evidence and an external listing-search action.

An optional suitability surface reveals the broader spatial pattern. Hard travel limits appear as isochrone masks or intersections. Changing filters only prepares a new query; pulling the **RESOLVE** lever performs network work and consumes quota.

#### Geography and candidates

Define the initial commuter belt as populated English areas reachable within approximately 120 scheduled minutes of at least one principal central London terminal, including reasonable station access. The terminal set should cover the major radial networks rather than using a simple circle around central London.

Use H3 resolution 8 cells for neighbourhood evidence, with resolution 6 and 7 aggregates at lower zooms. Generate recognisable candidate anchors from OS/ONS populated places and railway stations, deduplicate nearby anchors, and label each with its locality and most useful station.

The browser ranks named anchors. Multi-resolution H3 chunks are loaded only for the visible map when the suitability surface is enabled.

#### Scoring model

Each `MetricDefinition` maps a raw observation to a 0–100 desirability value using documented monotonic piecewise curves. Negative metrics reverse their curve. Counts such as cafés use logarithmic saturation so the tenth nearby café matters less than the first few.

POI accessibility is based on a fifteen-minute pedestrian-network catchment, not a circular as-the-crow-flies radius. Brand groups, including premium grocers, live in editable data configuration rather than application code.

Calculate a weighted mean inside each category, then combine category scores using their active importance. This prevents several related amenity counts from overwhelming commute or affordability. Hard constraints are evaluated first.

Missing metrics are omitted from score arithmetic and reduce the separate confidence value. Rank by hard-constraint status, suitability, and then confidence. The default unknown-data policy keeps uncertain places but warns; a future advanced option may explicitly exclude unknown hard requirements.

Buying affordability uses comparable HM Land Registry transactions of the same property type from the latest 36 months within 2 km, expanding to 5 km until at least 20 comparables exist. Sample size, distance, and age determine confidence. Rent mode uses the latest official bedroom-category rent evidence available for the containing local authority and is labelled as coarser.

#### Application architecture

Use an npm-workspace monorepo with:

- A React, TypeScript, and Vite web application.
- Direct Leaflet integration with custom Canvas/GeoJSON layers and accessible HTML controls.
- A TypeScript Cloudflare routing Worker.
- A Python FastAPI localhost companion.
- A `uv`-managed Python ETL package using Parquet and DuckDB staging.

GitHub Pages hosts the static application and versioned public data snapshots. It must work correctly under the repository base path.

The Pages build uses a domain-restricted maintainer Esri token. Attribution is always visible. The map provider remains replaceable, and a policy-compliant non-satellite fallback handles unavailable or exhausted imagery.

The Cloudflare Worker stores TravelTime credentials as secrets. It must:

- Allowlist the deployed application origin.
- Validate request and response schemas and cap payload sizes.
- Rate-limit requests by a privacy-preserving client identifier.
- Cache equivalent geocoding, isochrone, and matrix requests.
- Restrict outbound requests to configured provider hosts.
- Avoid logging coordinates or request bodies.
- Fail closed when free quotas are exhausted.

Profiles, destinations, budgets, visit audits, preferences, and personal route caches live in IndexedDB. The app has no account system or analytics in v1.

#### Routing flow

Use arrival/departure isochrones to mask the candidate region for hard drive or public-transport limits. Request exact matrix durations only for surviving named candidates, batching within provider limits. Lazily request detailed route legs for a selected place rather than every pin.

Cache keys include rounded destination coordinates, mode, arrival/departure window, catalogue version, and routing-model version. Several destinations may be combined by intersecting hard masks and applying their individual importance to surviving results.

When routing is unavailable, retain non-route evidence and precomputed rail facts, clearly mark live commute results as unavailable, and never substitute straight-line distance without saying so.

#### Data pipeline

Download raw inputs into an ignored local cache. Normalise them into Parquet/DuckDB staging tables, run source-specific validation, and publish only compact aggregates:

- Candidate point data for ranking.
- Viewport-loadable H3 metric chunks.
- Rail/station summaries.
- Source and licence metadata.
- A versioned manifest with checksums.

Primary inputs are:

- Geofabrik OpenStreetMap extracts for POIs, walking networks, roads, paths, and green space.
- OS/ONS names, population, administrative geography, and built-up-area data.
- HM Land Registry Price Paid Data and current ONS rental evidence.
- Network Rail schedules, NaPTAN, Rail Data Marketplace data, and ORR performance tables.
- Defra fly-tipping data, FixMyStreet geographic counts, and optional council-specific civic-report feeds.

Refresh jobs write to a staging snapshot, validate row counts, coordinate systems, freshness, licences, and checksums, and only then atomically promote the snapshot. Raw source files and personal overlays are never committed.

#### Public interfaces and shared types

`UserProfile` contains housing mode, budget, property type, destinations, metric weights, hard constraints, and unknown-data policy.

`DestinationPreference` contains an identifier, private label, coordinates, travel mode, arrival/departure rule, maximum minutes, and importance.

`MetricDefinition` contains identifier, category, polarity, unit, curve anchors, default importance, hard-filter eligibility, source requirements, and display metadata.

`PlaceScore` contains candidate identity, overall/category/metric scores, hard-constraint results, confidence, evidence references, affordability summary, and rail summary.

`DataManifest` contains catalogue and scoring versions, generation time, geographic coverage, source dates, licences, checksums, and compatibility requirements.

The routing Worker exposes:

- `GET /v1/status`
- `POST /v1/geocode`
- `POST /v1/commutes`
- `POST /v1/isochrones`

The local companion exposes:

- `GET /health`
- `POST /jobs/refresh`
- `POST /jobs/audit`
- `GET /jobs/{id}/events` using server-sent events
- `GET /snapshots/{id}`

All request, response, profile, and snapshot schemas are runtime-validated. Imports with incompatible catalogue or scoring versions fail with a helpful message rather than being partially loaded.

#### Local companion and agent stewardship

The companion binds exclusively to `127.0.0.1`, requires a random per-launch token, allowlists configured origins, and exposes fixed operations rather than a shell or arbitrary prompt endpoint.

Add a narrow repo skill named `location-data-steward`. Its purpose is to audit source freshness, licensing, schema drift, and failed importers and to emit a structured audit manifest. Deterministic Python jobs remain responsible for downloads, transformations, calculations, validation, and publishing.

Support two optional authenticated CLI adapters:

- Codex runs non-interactively with JSONL progress, an enforced output schema, an ephemeral session, an explicit working directory, and a read-only sandbox.
- Claude runs in non-interactive print mode with streaming JSON, a turn limit, plan/read-only permissions, and mutation tools disabled.

Agent output is always validated. An audit may recommend an importer repair but cannot silently edit source, change a score, publish a snapshot, or expand its own permissions. Manual repair work proceeds through the CLI's normal review and approval flow.

#### README and visual language

Create an original README after the application takes shape. It should use a distinctive ASCII masthead, a short product story, an “instrument” tour, metric glossary, architecture and source tables, screenshots, run commands, cost boundaries, privacy promises, and complete attribution.

Use [GL4SS](https://github.com/elder-plinius/GL4SS) as the key inspiration for full-bleed composition, technical typography, physical-feeling controls, purposeful animation, and explicit cost consent. Apply the dedicated aesthetic brief above, while not copying its code, prose, shaders, names, or assets.

Release application code under MIT. Keep generated data under the licences required by each source, with ODbL-derived database material and OGL material identified separately rather than implying that MIT covers everything.

#### Test plan

- Unit-test every score curve at its anchors and boundaries, including negative metrics and logarithmic saturation.
- Test category balancing, zero weights, hard constraints, missing evidence, confidence, cleanliness overrides, and derived-index non-duplication.
- Use fixed commute fixtures for several destinations, arrival searches, driving limits, transfers, no-service periods, overnight/last-train cases, batching, caching, and exhausted quotas.
- Validate ETL schemas, coordinate reference systems, sample-size rules, row-count changes, source freshness, licences, and deterministic snapshot checksums.
- Test that high civic-report counts do not become a simplistic cross-council cleanliness comparison and that missing reports never produce a “clean” claim.
- Security-test Worker origin enforcement, rate limits, body caps, upstream allowlists, secret handling, and log redaction.
- Security-test companion loopback binding, launch tokens, fixed CLI arguments, read-only agent modes, event streaming, cancellation, and rejection of invalid output.
- Use Playwright for GitHub Pages base paths, Buy/Rent switching, map/list synchronisation, keyboard use, responsive layouts, accessibility, fallback states, and profile/snapshot import-export.
- Include visual regression tests for the score pins, selected-place dossier, control deck, isochrones, heat surface, and provider-error states.

The central acceptance scenario is:

> A user requires less than 30 minutes' driving to one place and less than 75 minutes' door-to-door travel to another, values affordability, cafés, yoga, premium grocers, green space, and clean streets, and dislikes betting-shop density. After deliberately resolving the search, only valid places rank normally; every pin explains its score and confidence; rail details remain visible; and no preference or destination is sent anywhere except when strictly needed for routing.

A second acceptance scenario covers sharing:

> A new person opens the GitHub Pages URL, creates an independent profile, calculates custom commutes without supplying API keys, and cannot see or retrieve another person's destinations, budget, audits, or results.

#### Delivery sequence

1. Scaffold the web application, shared schemas, static mock catalogue, Leaflet map, pins, ranked list, profile editor, dossier, and GL4SS-inspired design system.
2. Implement deterministic scoring and the OSM/housing/rail/street-care ETL pipeline with manifests and fixtures.
3. Add TravelTime routing, the Cloudflare Worker, isochrone masks, caching, quotas, and failure states.
4. Add the localhost companion, refresh/audit jobs, the portable data-steward skill, and Codex/Claude adapters.
5. Complete accessibility, security tests, visual regression coverage, attribution, documentation, and GitHub Pages deployment.

### Open Risks and Assumptions

- V1 recommends areas and deep-links to property portals. It does not ingest, scrape, or republish current listings.
- The initial audience is personal use and a small number of people sharing the public app, not an unrestricted high-traffic commercial service.
- Only the maintainer configures Esri and TravelTime credentials. People using the shared app do not need their own keys.
- Esri, TravelTime, Cloudflare, and other free-tier terms or quotas may change. Providers remain replaceable, quota state is visible, and the app fails closed instead of enabling paid overage silently.
- Public map imagery is the most likely shared quota pressure; the routing provider is likely the tighter limit for complex searches. Caching and the deliberate RESOLVE action are required from the beginning.
- Official purchase evidence is more granular than official rental evidence. Rent results must not imply address-level precision.
- OSM amenity and brand coverage varies. Every place dossier exposes source coverage and update dates.
- Civic-report density is influenced by population, reporting propensity, council software, and clearance practice. Street care therefore carries a lower confidence grade and invites verification.
- Saved profiles and exact destinations are not included in the public dataset, source repository, telemetry, server storage, or shared links by default.
- The Pages application remains useful if the routing proxy is unavailable: users can explore the snapshot, inspect place evidence, and see precomputed rail information, but live custom-commute results are explicitly unavailable.
- Crime, flood risk, air/noise, broadband, schools, EPCs, planning, healthcare, cycling, culture, and imagery-based cleanliness are later modules, not launch blockers.
- This dated entry records the agreed starting point. Future discoveries should be added as new dated sections that explicitly amend individual decisions rather than rewriting this history.

## 2026-09-01 — Scope Correction: User-Run, Bounded Research

This entry supersedes the national catalogue, bulk ETL, hosted routing-proxy, localhost-companion, and passive public-app assumptions in the initial plan. All earlier product, metric, scoring, evidence, privacy, and visual-design decisions remain in force unless amended below.

### Why the Scope Changed

The useful question is personal and geographically bounded: which places inside a chosen travel-time limit fit this particular set of preferences? Building and maintaining nationwide café, yoga, betting-shop, grocer, housing, rail, and cleanliness datasets would solve a much larger problem than necessary.

V1 will therefore be a user-triggered research instrument. Each person runs a Codex or Claude workflow locally, for a deliberately limited area and selected metrics, then explores the resulting private research bundle in the included map application. There is no national scoring run or central store of personal searches.

### Revised Decisions

| Concern | Revised direction |
| --- | --- |
| Distribution unit | One GitHub repository containing the research skill, deterministic scripts, schemas, and GL4SS-inspired frontend |
| Research trigger | The user explicitly invokes a local `research-location` skill; opening the viewer never starts research |
| Geographic scope | A route-time polygon chosen for the current run, such as places within a 30-minute drive of an approximate origin |
| Metric scope | Only metrics selected for that run and only evidence relevant to candidate places inside the boundary |
| Data strategy | Query, validate, cache, and cite small area-specific slices; do not build a national warehouse |
| Agent choice | Codex or Claude, not both; thin provider-specific instructions call the same scripts and schemas |
| Authority | Agents gather and reconcile evidence; deterministic code applies boundaries, density calculations, hard constraints, and scores |
| Result | A private, portable, versioned `results.json` research bundle with evidence and confidence metadata |
| App runtime | Local static application or development server reading the generated bundle; no AI dependency after generation |
| Public sharing | Optional GitHub Pages read-only viewer with demonstration data and local file import |
| Credentials and quotas | Any research or routing credentials are supplied and held locally by the person running the skill |
| Accounts and central service | None in v1 |

### Repository-Shaped Product

The repository, rather than a hosted service, is the product:

```text
location-location-location/
├── skills/
│   └── location-research/
│       └── SKILL.md
├── app/                         # React, TypeScript, Vite and Leaflet viewer
├── scripts/                     # routing, collection, validation and scoring
├── schemas/                     # profile, evidence and result contracts
├── fixtures/                    # small synthetic and recorded test cases
├── research-runs/               # private generated work; always gitignored
│   └── <run-name>/
│       ├── profile.json
│       ├── evidence.json
│       ├── provenance.json
│       └── results.json
└── README.md
```

The skill and frontend ship together, but have separate responsibilities. The skill conducts and documents a research run. Scripts perform repeatable calculations. The frontend renders a completed result and remains useful without an agent, model API, routing key, or internet connection except for externally hosted map tiles.

OpenAI skills can be distributed as directory or ZIP file bundles through the [Skills API](https://developers.openai.com/api/reference/go/resources/skills). Repository installation instructions should make the local Codex route simple, while a thin Claude-compatible adapter may be supplied without duplicating the research logic.

### User-Run Research Flow

1. The user invokes `research-location` from the cloned repository.
2. The skill collects an approximate origin, travel mode and hard limit, housing mode and budget, destinations, selected metrics, weights, and optional hard requirements. An approximate postcode or map point is sufficient; an exact home address is neither required nor encouraged.
3. A deterministic routing adapter calculates the travel-time polygon after showing the provider, data that will leave the computer, expected request count, and quota status.
4. Candidate towns or neighbourhood anchors are discovered only inside that polygon. The hard boundary answers *where to consider*; each amenity metric then measures the immediate walkable context around each candidate, rather than counting everything across the entire polygon.
5. The skill makes a combined or carefully batched POI request for the selected amenity categories. It researches housing, rail, cleanliness, and other expensive evidence only for surviving candidates, with a shortlist stage when necessary.
6. Every observation is saved with its source URL, retrieval date, geographic resolution, transformation, licence note, and confidence. Conflicting or weak evidence remains visible rather than being silently averaged into certainty.
7. Validated scripts apply the agreed hard constraints and scoring curves and produce `results.json`. The agent may explain or challenge evidence but may not invent measurements or directly assign authoritative scores.
8. The skill starts or points to the local viewer. The map displays colour-coded pins, the ranked list, route-time boundary, evidence dossiers, rail facts, missing-data warnings, and score explanations.
9. A later run reuses compatible cached evidence and requests confirmation before making new quota-consuming calls.

### Bounded Data Collection

- Use a routing isochrone rather than a crude radius for constraints such as “within 30 minutes' drive.” Request matrices or detailed legs only for candidates that survive the broad boundary.
- Query OpenStreetMap POIs within the research extent in one combined request where practical. Avoid repeated per-category calls and respect service limits, attribution, caching, and ODbL obligations.
- Calculate amenity access using the candidate's defined neighbourhood or pedestrian catchment. Report both the raw count and denominator or catchment so “density” remains inspectable.
- Research London rail journeys only for shortlisted candidates. Preserve access time, waiting, transfers, London last mile, service frequency, final useful service, and reliability as separate facts.
- Retrieve housing evidence only for relevant candidates and property parameters. Where no suitable free structured source exists, use cited official aggregates, clearly labelled manual research, or user-provided property-search links; do not scrape property portals.
- Retrieve council, FixMyStreet, Defra, and visit-audit evidence only for relevant authorities and small areas. Preserve the cleanliness limitations recorded above.
- Cache reusable raw responses locally with source timestamps and expiry rules. A cache is an efficiency aid, not a growing public national dataset.

Some sources are released only as national bulk files. V1 should prefer bounded APIs or published local extracts. If a bulk source is uniquely valuable, the research script may download it temporarily and extract only the required records into the private run cache; it must not require publishing or continuously maintaining a transformed national catalogue.

### Skill and Agent Contract

The earlier `location-data-steward` concept is replaced in v1 by the user-facing `location-research` skill. Stewardship checks become part of each run:

- Confirm that each configured source is still available, permitted, appropriately licensed, and fresh enough for its claim.
- Plan the smallest set of requests needed for the selected boundary and metrics.
- Prefer primary and official sources, while recognising that OpenStreetMap is the practical POI source.
- Record citations and distinguish measured facts, transformations, agent inferences, and user observations.
- Validate all generated files against repository schemas before scoring or display.
- Stop when credentials, licence permission, quota, geographic coverage, or evidence quality is insufficient; do not fill gaps with plausible-looking values.
- Never edit the scoring model, expand permissions, publish a run, or commit personal files as a side effect of research.

Codex and Claude integrations are optional front doors over the same workflow. Provider-neutral scripts own routing adapters, POI queries, normalisation, scoring, caching, and output generation so switching agent does not change the mathematical result.

### Revised Interfaces

`ResearchProfile` contains the approximate origin, route boundary, housing requirements, destinations, selected metrics, weights, hard constraints, and explicit provider choices.

`EvidenceObservation` contains the candidate, metric, raw value, unit, geographic scope, source, retrieval time, source date, transformation, licence, and confidence notes.

`ResearchManifest` contains the run identifier, schema and scoring versions, tool versions, geographic coverage, request ledger, cache use, sources, licences, warnings, and checksums. It contains no secret credentials.

`ResearchResult` contains candidate identities, constraint outcomes, category and overall scores, confidence, evidence references, affordability and rail summaries, and map geometry references.

The frontend imports a compatible result bundle through a local run selector, development server, or browser file picker. An incompatible schema fails with a useful migration message. A GitHub Pages build may display bundled fictional demonstration data and allow local file import, but it cannot invoke a skill running on the user's computer.

### Privacy and Cost Safeguards

- `research-runs/`, caches, profiles, destinations, visit audits, and credentials are gitignored and never included in the Pages build.
- Before routing or geocoding, show which coordinates and parameters will be sent to which provider. Support an approximate origin and coordinate rounding where accuracy permits.
- Require an explicit research action, estimate calls before execution, cap calls per run, cache equivalent requests, and stop at free-tier limits. Never opt into automatic paid overage.
- Keep provider keys in local environment configuration or a local secret store, never in result bundles, browser storage, source control, or the static application.
- Importing a result into the viewer processes it locally. Sharing the repository or Pages URL does not upload, publish, or transfer that result.
- Exporting or committing a research run is a separate, deliberate user action with a warning that the bundle may reveal approximate origins, destinations, budgets, and preferences.

### Revised Testing and Acceptance

- Test polygon inclusion and exclusion at boundaries, coordinate rounding, candidate discovery, route batching, cache keys, quota caps, and provider failures.
- Test POI deduplication, brand/category configuration, catchment denominators, logarithmic saturation, negative metrics, and repeatable scores independent of the chosen agent.
- Validate evidence, manifest, profile, and result schemas plus source dates, citations, licences, confidence, and checksums.
- Use recorded small-area fixtures; tests must not require nationwide downloads or live chargeable calls.
- Test that personal paths and run files are excluded from Git and production builds and that imported result files never leave the browser.
- Use Playwright for file import, map/list synchronisation, route-time polygons, score explanations, missing evidence, responsive layouts, keyboard operation, accessibility, and the complete GL4SS-inspired visual states.

The revised central acceptance scenario is:

> A person clones the repository, invokes one supported research skill, supplies an approximate origin and a 30-minute driving limit, and chooses coffee-shop density as the only weighted lifestyle metric. The workflow researches only candidate places inside the resulting travel-time polygon, records inspectable sources and confidence, computes scores deterministically, and opens the private result in the map application without constructing or publishing a national dataset.

A second scenario adds several destinations, a maximum door-to-door London commute, housing evidence, and more lifestyle metrics. Expensive evidence is collected only after the broad route constraint has reduced the candidate set.

### Revised Delivery Sequence

1. Define the profile, evidence, manifest, and result schemas; create small fixtures and deterministic scoring tests.
2. Build the React/Leaflet viewer around imported local result bundles and the GL4SS-inspired instrument design system.
3. Implement one bounded routing adapter, candidate discovery, and combined OpenStreetMap POI collection for a single metric such as café density.
4. Add the `location-research` skill, local cache, request ledger, provenance validation, and Codex entry point.
5. Add shortlist-only London rail and housing research, then street-care evidence with its existing confidence constraints.
6. Add an optional Claude adapter, further metric modules, accessibility and visual regression coverage, and a GitHub Pages demonstration viewer.

Do not introduce a national ETL warehouse, published H3 catalogue, Cloudflare routing proxy, FastAPI companion, or centrally stored search results unless later usage demonstrates a concrete need. Those are scale-up options, not launch foundations.

### Revised Risks and Assumptions

- A user must be willing to clone the repository, run an agent workflow, and configure any required free data-provider credentials; v1 is not a zero-setup consumer website.
- Agent browsing and source access vary by environment. The skill must report unavailable capabilities and permit resuming a partially completed run.
- Public Overpass and free routing services have usage policies and uneven availability. Queries must be bounded and cached, and provider adapters must remain replaceable.
- On-demand research may take minutes and evidence can vary between runs as sources change. The manifest makes each result reproducible and comparable where possible.
- A drive-time polygon is provider- and traffic-model-dependent. Display the assumed departure time, traffic treatment, model, retrieval date, and uncertainty.
- The user-run approach reduces central infrastructure and privacy risk but does not eliminate data work: robust schemas, source adapters, validation, scoring tests, and graceful failure remain essential.
- The public viewer is a demonstration and local-result renderer. It neither conducts research nor exposes a bridge to a skill running on someone's computer.

## 2026-09-02 — V1 Build Learnings

- The contract boundary works: deterministic Python owns scoring and emits versioned bundles; React remains a read-only renderer. Generate public demo results from the same scorer to prevent drift.
- Public defaults layer beneath an ignored local profile. Research runs, caches, build output, and imported personal results stay untracked; browser imports remain in memory, with remote map tiles disclosed separately.
- Raw observations and desirability scores have different semantics. Keep normalized scores visually consistent; use contextual colour on the observation itself (for example, zero betting shops is positive).
- The first live slice uses one bounded OpenRouteService isochrone and one combined Overpass query. Café reach is explicitly lower-confidence until the 1.2 km proxy is replaced by walking-network catchments.
- Research now previews before execution, caps live calls at two, reuses an ignored expiring cache, and validates redacted request provenance, citations, licences, dates, and checksums.
- Rail enrichment is a separate zero-network shortlist step: component times must equal the door-to-door total, reliability may remain unknown, and every displayed fact retains its citation.
- Housing enrichment follows the same boundary: code derives cost-to-budget ratios from cited shortlist evidence, buy comparables retain radius and sample size, rent retains its coarser published geography, and aggregate evidence never becomes a live-inventory claim.
- Street care is now derived rather than agent-scored: report volume stays informational, resolution evidence can strengthen a cautious proxy, and only a structured audit no more than 180 days old overrides it.
- Accessibility now has axe and keyboard coverage; stable visual contracts check responsive geometry, theme tokens, and reduced motion. Pages deployment remains a manual, public-demo-only action.
- Real desktop/mobile browser tests caught issues unit tests did not, including hidden import errors, obscured map state, fixed chrome covering evidence, and accidental reuse of another project's Vite port.
- `experiments/MUSINGS.md` is a frozen clean-room brief for an independent rebuild and should not inherit this implementation's output or later notes.

## 2026-09-02 — Development Gameplan After Build Audit

The public `main` branch remains a verified working checkpoint. A later local pass began the next bounded-research milestone but stopped mid-refactor, leaving a large uncommitted change set and one failing Python assertion. Preserve that work, but stabilise and review it before starting another feature or publishing it.

### P1 — Make a real bounded run useful

- Complete the single combined Overpass collection for cafés, betting shops, yoga, configurable premium grocers, and nearby green space without increasing the two-call cap.
- Widen candidate discovery to city, town, suburb, village, and neighbourhood anchors, with deterministic nearby-anchor deduplication.
- Make destinations, door-to-door limits, housing requirements, metric weights, and hard constraints reachable through the research CLI and visible in its pre-execution disclosure.
- Resolve the remaining green-space distance contract, review brand matching and query-safety semantics, and deliberately retire or retain the superseded café-only entry points.
- Run the complete Python, viewer, browser, accessibility, production-build, and deterministic-demo checks before making a milestone commit.

### P2 — Close contract and explanation gaps

- Make the repository JSON Schemas authoritative. Validate generated profile, evidence, manifest, and result files with `jsonschema`; keep cross-file and mathematical invariants in deterministic Python; prevent the browser validator from drifting from the same contracts.
- Carry route-boundary geometry and its provider, retrieval time, departure-time, and traffic assumptions into the result contract the viewer actually imports, then render them on the map and in the dossier.
- Show weighted contributions, add useful result sorting, and preserve missing-data and confidence explanations without requiring mental arithmetic.

### P3 — Finish the product surface and project hygiene

- Replace idle looping motion with state-driven feedback, improve very small evidence text, and keep reset/import recovery available on mobile.
- Add Python tests and linting to CI, add the optional Claude skill pointer, and update documentation after the behaviour settles.
- Commit by coherent milestone. Routine local progress need not be pushed; suggest a push at a substantial working checkpoint and otherwise wait for an explicit request.

### Definition of done and deferred work

Each milestone must leave the tree clean, generated demo output reproducible, private research artifacts untracked, provider calls previewed and capped, and the public viewer unable to upload imported results. Walking-network catchments, further playful readouts, and official-source adapters remain later modules. Do not revive the superseded national warehouse, hosted routing proxy, FastAPI companion, or central result store without evidence that the bounded local workflow needs them.

### P1 completion note

- The combined two-call run now discovers five settlement kinds and measures cafés, betting shops, yoga, configurable premium grocers, and green-space proximity in one bounded Overpass request. Straight-line catchments and green-space bounding-box distance remain explicit lower-confidence proxies.
- Premium-grocer patterns are safe literal fragments matched within configured OSM shop types; yoga is matched as a semicolon-delimited OSM sport value. Nearby anchors are deduplicated deterministically by place significance.
- CLI destinations, housing requirements, 0–5 metric importance, and hard limits now reach the validated profile. Each destination commute limit is checked against its matching researched journey rather than being collapsed into a misleading global minimum; missing journey evidence remains unknown with a warning under the v1 policy.
- The older café-only command has been retired in favour of the preview-first research command. The fictional demo remains byte-identical after regeneration, and the milestone passes the complete Python, viewer, production-build, desktop/mobile browser, and accessibility checks.

### P2 completion note

- Draft 2020-12 JSON Schemas now gate every profile, evidence bundle, result, and provenance manifest before files are written. Local `$ref` resolution and date/URI format checks are deterministic; Python still owns cross-file provenance and mathematical invariants.
- AJV runs only in the test toolchain to keep the browser's lightweight import validator aligned with the result schema. Parity coverage includes integer ranks, constraint operators, place kinds, contribution fields, and rejection of unexpected candidate data; AJV is absent from the production bundle.
- Results now carry the route boundary that the viewer imports. The map draws it, fits it with the candidates, and the dossier exposes its provider, retrieval date, travel profile, departure assumption, and traffic treatment.
- Category and metric contribution points are visible alongside scores. The register can be sorted by authoritative rank, suitability, confidence, or name while retaining the original rank numbers and hard-limit status.

### P3 completion note

- Idle motion is gone: the map scan line now runs once when the selected candidate or route boundary changes, stays invisible otherwise, and remains covered by the reduced-motion and single-pulse browser checks. Evidence, rail, housing, and street-care text no longer drops below roughly 0.6 rem, and the reset/import recovery control stays visible and clickable at mobile widths with a browser test for the recovery outcome.
- A `Verify` workflow now runs on pushes and pull requests to `main`: ruff lint, the unittest suite, byte-identical demo regeneration, viewer unit tests, Playwright browser and accessibility tests, and the production build. Pages deployment stays manual and separate.
- Ruff runs with its default rule set. Tests and entry-point scripts keep their intentional `sys.path` imports through per-file ignores, and formatting is deliberately not enforced because it would reformat most Python files without changing behaviour; adopt it as its own change if wanted.
- Claude Code gets the same thin pointer as Codex at `.claude/skills/location-research/SKILL.md`; both defer to `skills/location-research/SKILL.md` so the research logic exists once.
- Verified at this checkpoint: 43 Python tests, 23 viewer tests, 24 desktop and mobile browser tests, clean lint, reproducible demo, and the production build.

## 2026-09-02 — Development Gameplan After the Brief Audit

The P1–P3 gameplan is complete and pushed as c1cdc85. An audit against the 2026-09-01 brief and its scope correction found the bounded workflow, contracts, privacy and cost safeguards, and viewer largely delivered, with these gaps: straight-line amenity catchments instead of pedestrian-network reach, only one of the six playful readouts, no preference tuning without rerunning Python, hand-written rail and housing evidence, no deliberate export path, no screenshot regression, and a README that documents commands rather than the product. Work proceeds in the order below; each milestone is committed locally and not pushed unless asked.

### P4 — Pedestrian-network catchments without moving the call cap

- Fetch the walkable highway network in the same combined Overpass query using `around` filters on the discovered place nodes, so the run still makes at most one routing call and one Overpass call.
- Build a walking graph in deterministic Python, snap each candidate and point of interest to it, and count amenities within a 15-minute (1,200 m at 80 m per minute) network distance.
- Keep the straight-line proxy as an explicit, labelled fallback when the network is absent from a cached response or a candidate sits too far from any walkable way. Green-space distance keeps its bounding-box proxy for now because its 45-minute reach would need a much larger network extract.

### P5 — Derived readouts as presentation only

- Add Sourdough-to-Slots, Emergency Croissant Radius, Green Escape, Last Train Home, and Rail Roulette alongside Pavement Pride in the dossier.
- Readouts derive only from fields already in the result, render "no evidence" rather than inventing values, and are covered by tests showing they never change a score.

### P6 — What-if reweighting in the viewer

- Port the category-mean and weighted-overall arithmetic to TypeScript and prove parity against the Python-scored demo bundle.
- Let the viewer tune metric importance from 0 to 5 and preview the resulting order, clearly labelled as a what-if. Authoritative Python ranks, hard-limit status, and confidence stay visible; the authoritative bundle is never modified.

### P7 — Deliberate export with redaction

- Add a preview-first export command that copies a run with the origin rounded, optional budget removal, and the privacy warning the brief specified. Sharing remains a separate, explicit action.

### P8 — README as product documentation

- Masthead, product story, instrument tour, metric glossary, architecture and source tables, screenshots captured from the demo, cost and privacy boundaries, attribution, and the MIT versus ODbL/OGL licence split.

### Deferred and conditional

- Screenshot baselines need Linux-rendered references generated in CI; adopt them once a CI run can publish baselines rather than committing Windows renders that would fail there.
- Official source adapters for Land Registry price-paid and ORR performance follow the same preview, cap, and citation rules and are attempted only after a bounded live query is verified.
- Later metric modules, per-destination isochrone overlays, compare mode, and run diffing remain future ideas.
