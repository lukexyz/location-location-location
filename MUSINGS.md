# MUSINGS

## The Vision (restated 2026-09-03)

This block is the standing statement of what LOCATION³ is for. Everything below it is a dated log, and earlier entries describe the thinking of their day; where they disagree with this block, this block wins.

### The product in one paragraph

LOCATION³ is a personal place-finding instrument that you run yourself. You open the public demo, see what a finished search looks like, and are immediately offered one line to paste into your own terminal. That line boots the real app locally. Your coding agent, Claude Code or Codex, running on the subscription you already pay for, asks what matters to you: where you need to get to and by when, your housing budget, how much you care about cafés, green space, betting shops, and street care, and which limits are absolute. It then does the research, previewing every outbound call before it happens, while a research modal shows you honestly what it is doing and finding. Deterministic Python turns the evidence into scores. At the end you get your own ranked map, with a dossier per place that says why it scored what it did, how fresh the evidence is, and what is missing.

### The three parts, and what each is for

| Part | Job | Must never |
| --- | --- | --- |
| **Public demo** on GitHub Pages | The shop window. Show a real, finished result on real towns so a visitor understands the output in ten seconds, then send them to make their own with a large, unmissable call to action. | Run research, ask for credentials, or hold anyone's data. |
| **Local app** in the cloned repository | The real product. One-line bootstrap, an agent-led conversation to set criteria, preview-then-execute research, a live progress surface, and the same viewer rendering a private result bundle. | Cost money beyond the agent subscription the person already has, or send anything anywhere without previewing it first. |
| **Deterministic core** in Python | The authority. Boundaries, catchments, hard limits, curves, weights, confidence, provenance, and schemas. | Let an agent assign a score or label an estimate as measured. |

### Why "your own agent, your own subscription" is the whole idea

The research an estate-agent or a paid data product would charge for is exactly the work a coding agent already does well: reading published tables, citing sources, reconciling conflicting figures, and writing a structured file that a schema can check. So the product does not run a research service. It hands the person a skill, lets their agent do the gathering on a subscription they already own, and keeps the scoring in code that cannot be talked into a number. Free for the user, private by construction, and every figure carries a basis and a citation.

### What a first-time visitor should experience, in order

1. Land on the demo. A banner says plainly that this is a sample on real towns with synthetic evidence, and a large button says "Run your own search."
2. Click it. A modal offers Claude Code and Codex tabs, each with one copy-paste command, a sentence about what happens next, and a sentence about what stays private.
3. Paste the line. The repository is cloned, dependencies install, and the agent opens with the research skill loaded. If no routing key is present, the first run still works with a clearly labelled fallback boundary; the key is offered as an upgrade, not a gate.
4. Talk. The agent asks for an approximate origin, destinations, budget, importance, and hard limits, and shows a preview of exactly what will leave the machine.
5. Approve. Research runs while a progress modal shows real stage names, real counts, and a little whimsy on top.
6. Explore. The viewer opens on a private result bundle: ranked map, dossiers, what-if importance, and honest warnings.
7. Optionally share a redacted export, previewed first.

### Principles that have not changed

- Hard constraints remove places; weighted preferences rank the survivors.
- Every score is explainable and uncertainty stays visible; missing evidence never reads as "fine."
- No surprise costs: two live provider calls per run, previewed before they happen.
- Private by default: profiles, origins, budgets, visit audits, and results never leave the machine unless the person exports them on purpose.
- Playfulness sits on top of serious evidence, never in place of it.

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

### P4 completion note

- The single Overpass call now uses `around` filters on the discovered place nodes for amenities, green space, and the walkable highway network, which also stops it fetching every café in a large drive-time polygon. The call cap stays at two.
- `walking.py` builds an undirected graph from way geometry, densifies long segments so mid-street features snap within about 25 m, and runs a bounded Dijkstra from each place node. A feature snaps to its single nearest walkable node so every measurement reads as "network distance to that node plus the short offset".
- Fallbacks are explicit in each observation: a candidate more than 300 m from any walkable way, or a cached response without network data, keeps the straight-line proxy and says why. Network-measured counts carry a modest confidence bonus; green space keeps its bounding-box proxy.

### Demo place note

- The public demo now names three real commuter-belt towns (Welwyn Garden City, Hemel Hempstead, Maidenhead) with real coordinates and plausible stations, but every number remains synthetic and is labelled as such in the viewer, fixtures, and README. The demo must never be read as a measurement of those towns.

### P5 completion note

- Six playful readouts sit at the top of the dossier: Sourdough-to-Slots, Emergency Croissant Radius, Green Escape, Last Train Home, Rail Roulette, and Pavement Pride. They are derived in the viewer from fields already in the result, render "no evidence" instead of a value when the evidence is missing, and unit tests prove they leave the result untouched.

### P6 completion note

- `whatif.ts` reproduces the scorer's category means, weighted overall, confidence, and contribution arithmetic, including Python's round-half-to-even on exact binary ties. Parity is proven against the demo bundle at its researched weights and against a second Python scoring of the same evidence with different importance, which `build_demo.py` now emits and CI keeps reproducible.
- The register hosts a Tune importance panel. While a what-if is active the order and bright scores are the preview, rank numbers and the dossier dial remain the researched result, the footer and eyebrow say so, and one control restores the researched weights. Importing a bundle resets any preview.
- Metrics that were never observed anywhere in a bundle cannot be tuned, because their category weight is unknown; metrics missing for one place reduce that place's what-if confidence exactly as the scorer would.

### P7 completion note

- `scripts/export_run.py` previews what a shared bundle would still reveal, then writes a redacted copy: origin rounded to a chosen precision, optional removal of budget, property requirements, market evidence, and the affordability metric, and optional replacement of destination labels wherever they appear, including the prose of merged commute observations.
- Redaction is applied to the profile and evidence and the result is re-scored through `write_bundle`, so an export is always a schema-valid, internally consistent bundle rather than a hand-edited file. The route envelope, limits, and preferences are retained and the preview says so.

### P8 completion note

- The README is now product documentation: masthead, the problem it answers, the run in seven steps, an instrument tour, a metric glossary with the exact curves from `catalog.py`, architecture and source tables, commands, cost and privacy boundaries, GL4SS attribution, and the MIT versus ODbL/OGL licence split.
- Screenshots come from a skipped-by-default Playwright spec (`CAPTURE_SCREENSHOTS=1`) that renders the synthetic demo on desktop and mobile with the attributed OpenStreetMap basemap, so they can be refreshed the same way every time.

## 2026-09-02 — Context, Learnings, and Open Work After P4–P8

### Where the project stands

The P1–P3 stabilisation is pushed as c1cdc85. The P4–P8 pass sits on `main` as six local commits (61c8544 through 903c27c) and has not been pushed. At 903c27c the tree is clean and the whole stack is green: ruff, 52 Python tests, 33 viewer tests, 28 desktop and mobile browser tests with axe, byte-identical demo fixtures, and the production build.

The audited gaps from the 2026-09-01 brief are now closed except the deferred items below. The demo shows three real towns with synthetic evidence and is labelled that way everywhere; that labelling must survive any future demo change.

### Learnings from this pass

- **Overpass `around` on a named set is the bounded-query tool.** Filtering amenities, green space, and the highway network by `(around.places:N)` on the discovered place nodes keeps one call, stops a large drive-time polygon from pulling every café in a city, and makes the pedestrian network affordable to fetch.
- **Snap to one nearest node, not the best of several.** Minimising network distance plus straight-line offset let features cut corners through the snap radius. Densifying long way segments and snapping to the single nearest node keeps every measurement explainable as "walk to that node, then the short offset".
- **Fallbacks belong in the observation text.** A cached response without network data, or a place node far from any walkable way, silently reverting to a proxy would have hidden a quality change. Each observation now states its scope, its transformation, and the reason for any proxy.
- **Cross-language parity needs a second scoring, not a re-derivation.** Testing the viewer's arithmetic only at the researched weights would have passed a scorer that ignored weights. The demo builder now emits a differently weighted Python scoring, and CI keeps it reproducible.
- **Rounding is part of the contract.** Python rounds ties to even on the exact binary value; JavaScript's `Math.round` and `toFixed` do not. Two-decimal parity failed at exactly those boundaries until the viewer mirrored Python's rule.
- **Redaction must be re-scored, not edited.** Removing housing evidence by hand would leave contributions and warnings inconsistent. Applying redactions to profile and evidence and re-running `write_bundle` keeps every export schema-valid.
- **Labels leak into prose.** The rail merge stamps destination labels into commute observations' `geographic_scope`; anonymisation has to rewrite free-text fields, not just the label field.
- **Renaming demo places by text replacement breaks identifiers.** A slug with a hyphen became a TypeScript variable name. Rename data first, then check test files separately.
- **Windows heredocs and `write_text` both bite.** Long multi-line shell heredocs failed to parse; patch scripts written to a scratch file were reliable. `Path.write_text` produced CRLF files that git then warned about; pass `newline="\n"` when generating committed text.
- **Screenshots need a repeatable capture path.** A Playwright spec skipped unless `CAPTURE_SCREENSHOTS=1` gives identical framing every time and avoids hand-cropped images drifting from the product.
- **A parent-directory `node_modules` can hide a missing dependency.** The viewer built locally because TypeScript walked up to a stray `D:\python\node_modules\@types\node`, while CI's clean `npm ci` had no Node types and the build failed on the schema-parity test. Every ambient type the code relies on now has to be an explicit, pinned devDependency named in `tsconfig.json`.

### Remaining work

Ordered by value; none is blocking a push of the current checkpoint.

1. **Official source adapters.** Land Registry price-paid data has no coordinates, so a bounded query needs candidate postcode districts or an ONS postcode-centroid extract cached locally. ORR performance tables and timetable feeds change URLs and formats; an adapter must preview, cap, cite, and fail closed like the research command. Until then rail, housing, and street-care evidence stay hand-written cited inputs.
2. **Green-space walking distance.** Green space still uses the bounding-box proxy because its 45-minute reach would need a network extract roughly nine times larger. Options: a smaller 20-minute green-space horizon measured on the network with the proxy beyond it, or per-candidate walking isochrones from the routing provider, which would raise the call cap and must be previewed.
3. **Screenshot regression baselines.** Generate Linux baselines inside CI and publish them as artifacts before committing any, so Windows renders never become the reference.
4. **Per-destination isochrones.** Each hard travel limit could be drawn as its own envelope. It costs one routing call per destination, so it belongs behind the preview with an updated cap.
5. **Category importance in the what-if panel.** Metric sliders exist; category weights are still fixed to the researched values. Adding them is small now that parity is proven.
6. **Docs polish.** Trim the screenshot PNGs, add a short "first run in five minutes" walkthrough with a redacted real run, and link the skill entry points from the README tour.

### Feature ideas

- **Visit audit form in the viewer** that emits schema-valid street-care JSON for the importer without uploading anything.
- **Run-to-run diff** showing how each place's evidence, confidence, and score changed between two bundles, with the reason attributed to a changed observation.
- **Compare mode** pinning two or three places side by side with the same dossier rows aligned.
- **"What is missing" checklist** per place listing the evidence that would most raise its confidence, derived from missing metrics and low-confidence observations.
- **Basemap toggle** between the current OpenStreetMap raster and an attributed dark or satellite layer with a policy-compliant fallback, to move closer to the intended instrument look.
- **Later metric modules** from the original brief: crime and anti-social behaviour, flood risk, air and noise, broadband, schools, EPC evidence, planning pressure, healthcare access, cycling and walkability, and third places.
- **Optional multi-run library** in the viewer that remembers imported bundles in browser storage only, with an explicit clear control.

### Decisions to keep

- The straight-line proxy is a labelled fallback, never the default; any future catchment change must keep the observation text honest about which method produced the count.
- Playful readouts remain presentation only. If a readout ever needs its own score, it must become a metric in `catalog.py` with a documented curve.
- What-if previews never write back. Making new importance authoritative always means rerunning the research command.
- Exports are re-scored bundles. No script may hand-edit a `results.json`.
- The public demo may name real places only while every number is synthetic and labelled as such in the interface, fixtures, and README.

## 2026-09-02 — Code Evaluation Against the Brief and Gameplan P9–P15

### Verdict

The project is on target with the scope-corrected vision and the build claims above hold: ruff is clean, 52 Python, 33 viewer, and 28 browser tests pass, the demo regenerates byte-identically, the production build succeeds, and `main` is fully pushed at 4b6c880. The drift is not in direction but in depth. The parts of the mission that carry the most weight are the least real.

### Where the build has drifted from the vision

- **The live run does not measure what the user weights most.** A run makes one isochrone call and one Overpass call. Door-to-door commute, housing affordability, and street care enter only through hand-written JSON that an agent "researches" without a source adapter. The schemas require hard numbers such as punctuality percent and a 2 km median price, so an agent with browsing will emit plausible figures with a URL attached. "Cited" is enforced; "measured" is not. The brief's measured / transformed / inferred / observed distinction has no field anywhere.
- **The one live amenity path is broken on real data.** The POI block ends with `out center tags`. In Overpass QL `tags` prints ids and tags without coordinates for nodes, and `center` adds a centroid only for ways and relations. Most cafés, bookmakers, and shops are nodes, so `osm.py` drops them and every count reads 0 at confidence 0.75. The tests hand-build elements with `lat`/`lon`, so the suite cannot see it.
- **Missing evidence is quietly renormalised away.** A category with no observations leaves the weight denominator, so a fresh run ranks purely on cafés and green space with confidence as the only warning. Hard constraints with no evidence count as passed and sort above genuine failures, and driving or walking destination limits can never be evaluated at all. The brief says missing is never clean.
- **The skill cannot express the acceptance scenario.** `SKILL.md` omits the destination, constraint, weight, and housing flags the CLI already has, and every run collects all five amenity categories regardless of selected metrics, contradicting "only metrics selected for that run".
- **The viewer reads as a dark dashboard rather than a machined instrument.** Two floating cards with drop shadows cover most of the map, controls are native selects and OS range sliders, all text is one Consolas voice at roughly 9 px, pins are fixed 58 px discs with no collision handling, and the score explanation and missing-data warnings sit at the bottom of the dossier. Mobile hides the "loaded in this tab only" disclosure.

### Defects found

- Export redaction is incomplete: the ledger request id is a hash of the exact ORS body, so a rounded origin can be brute-forced from an export; station names, audit notes, and lowercase label mentions survive anonymisation.
- The disclosure understates what is sent: the preview prints the origin at 4 decimals but full precision is sent, and the polygon sent to Overpass is subsampled to 80 vertices while the full one is recorded.
- The map refits on every slider tick because the bounds controller depends on the sorted candidate array.
- Green Escape asserts "no green space was found" when the metric is merely absent.
- Smaller: a 5 MB import cap rejects runs over roughly 350 candidates; all-zero sliders show 100 % confidence; coordinates render as "-0.208E"; `.env` files are not ignored; the README has no install step; the launch default weights recorded on 2026-09-01 (street care 4, betting 3, yoga 2, grocers 2) no longer match `preferences.toml` (3, 2, 1, 1) and this entry amends that decision to the file's values.
- Code debt: four copies of the validator helpers, three near-identical importer CLIs, circular-import workarounds in scoring and validation, a 545-line hand validator duplicating the JSON schema, and stale `.pyc` files for deleted modules.

### Gameplan

- **P9 — Make the live path real.** Fix the Overpass output verbosity, add a recorded live-shaped fixture with node POIs, derive the Overpass blocks from the selected metrics and constraints, print exactly the body that leaves the machine with the origin rounded before sending, and record the simplified polygon in provenance. Give the skill the full command line.
- **P10 — Missing is never clean.** Three-state hard constraints (`pass` / `fail` / `unknown`) with unknown sorted below pass; reject destination limits that no evidence path can evaluate; keep empty categories visible in the result as unmeasured with a prominent warning instead of silently renormalising.
- **P11 — Complete export redaction.** Re-hash or drop request ids, strip station names and audit prose, replace labels case-insensitively, and drop the private visit audit from exports.
- **P12 — Evidence basis.** Add a required `basis` field (`measured`, `transformed`, `agent_inferred`, `user_observed`) to observations and to rail, housing, and street-care inputs; surface it in the dossier and lower confidence for inferred values.
- **P13 — Viewer pass.** Fix map state churn, reorder the dossier so constraints, explanation, and missing-data warnings lead, show category weights and what-if missing metrics, fix the Green Escape wording, hemispheres, hidden mobile disclosure, and the import limits; move toward three typographic voices and custom controls.
- **P14 — One official adapter.** ORR station performance through the same preview, cap, ledger, and citation path, so at least one hand-written input becomes measured.
- **P15 — Hygiene.** Ignore `.env*`, add the install step to the README, consolidate validator helpers and importer CLIs, delete stale bytecode, and record completion notes here.

### P9 completion note

- The Overpass POI and green-space blocks now end with `out center body` and `out bb body`. The previous `tags` verbosity omitted node coordinates, so every café, bookmaker, or shop mapped as a node was dropped before counting. A recorded live response for Welwyn Garden City (`fixtures/overpass/`, ODbL) now proves node points of interest are counted, and a guard test shows the tags-only shape would have reported one café instead of six.
- Collection follows the selected metrics: a metric weighted 0 with no hard limit is neither queried nor measured unless `--measure METRIC` asks for it, and the manifest records what was skipped. A run with no amenity metrics still discovers settlements.
- The origin is rounded before it is sent or stored (`--origin-decimals`, default 3, about 110 m) and the profile records that precision. The preview prints the rounded origin, both provider hosts, what is measured, what is skipped, and which metrics are only ever imported from cited inputs. When the boundary is simplified for Overpass the manifest says how many vertices were sent.
- The skill now lists every research flag and forbids editing preferences or scoring files or adding runs to git. The README gained the install step and the new flags.

### P10 completion note

- Hard limits now have three states. Each constraint result and each candidate carries `status` of `pass`, `fail`, or `unknown`; unknown never counts as a pass and ranks below every pass and above every breach, in Python and in the viewer's what-if order. The map pins, register, and dossier show an amber "unverified" state, and a limit with no evidence says "no evidence" rather than a number.
- A door-to-door limit can only be attached to a public_transport destination, because the cited rail import is the only commute evidence path in v1. The CLI and the profile validator both reject a limit on a driving, cycling, or walking destination with the reason.
- A weighted category with no evidence is no longer silently renormalised away. Results carry `unmeasured_categories` and `score_coverage_percent`; the scorer warns "Unmeasured category: essentials (weight 5) has no evidence; the overall score covers 50% of the intended category weight", the dossier renders the category as a hatched no-evidence block with a Coverage readout, and the register shows the measured share. The what-if preview reports the same coverage and parity is tested.
- The result contract moved to `schema_version` 2 for these fields. The viewer rejects a version 1 bundle with a message that says to rerun the research command.

### P11 completion note

- Exports re-hash every request ledger id with a random salt. The original id was a hash of the exact provider request body, and with a rounded origin inside a known isochrone the body could be brute-forced from an export; the salted hash keeps the ledger's count, timing, and cache facts without that link.
- Destination anonymisation now rewrites every field, matches any letter case and the hyphenated slug form agents use in identifiers, and withholds London arrival stations, which named the destination terminal.
- Personal visit audits, with their notes and walking scope, are removed from exports unless `--keep-visit-audits` is given. Removal re-derives the street-care observation through the same merge so the export's score matches its components and falls back to cited proxies.

### P12 completion note

- Every observation, rail journey, housing market, and street-care place now carries a required `basis`: `measured`, `transformed`, `agent_inferred`, `user_observed`, or `synthetic`. The Overpass adapter writes `measured`; derived observations inherit the basis of the journey, market, or place they came from; a recent visit audit is `user_observed`; the public demo is `synthetic` in-band rather than only in prose.
- An `agent_inferred` record cannot claim confidence above 0.5. The JSON Schemas, the Python validators, and the browser validator all enforce it, so an estimate with a URL attached can no longer pass as a measurement.
- The dossier shows the basis for every metric, journey, market, and street-care place, flags agent-inferred metrics with an EST badge and an amber note, and the skill tells the agent how to choose the basis and never to leave it out.

### P14 completion note

- The first official source adapter is in: `scripts/fetch_orr_performance.py` fetches ORR Table 3138 (train punctuality at recorded station stops by operator) and Table 3124 (trains planned and cancellations by operator), two GET calls to public URLs cached for seven days under the same ledger and cap machinery as the research command. Nothing about the run is sent; operators are matched locally after download, case-insensitively, and an unknown name fails closed listing ORR's published operator names.
- The adapter parses the portal's `#reportTable` HTML with the standard library, picks the latest period per operator by parsing the period label, and writes `orr-performance.json` with periodic and moving-annual-average figures, both source URLs, licence OGL-3.0, basis `measured`, and its own request ledger. Column changes fail closed with a message naming the expected headers.
- A rail journey may now carry `operator`; `import_rail.py --performance` fills that journey's punctuality and cancellation from the ORR moving annual average, replaces any input figures, appends a cited performance source, notes it in the journey, records the provider, and merges the ORR ledger into the bundle's provenance. Recorded trimmed extracts of both tables with real values live under `fixtures/orr/` (OGL).
- Verified against the live portal on 2026-09-03: two calls, then cache hits, latest period Apr 2026 to Mar 2027 (Period 04).

### P13 completion note

- The map is now a stable field. It fits the whole run once per bundle and flies only to a selection the user makes; sorting the register, moving an importance slider, or loading the bundle's own top candidate never moves it, and an end-to-end test pans the map and asserts the pane transform survives every control change. Pins scale with zoom, the selected pin sits on top, and unknown limits draw a dashed ring while breaches draw a strike.
- Category importance is tunable alongside metric importance. The tune panel groups each category slider above its metrics and says how many were researched; one restore returns both. The what-if preview applies both maps and the parity test derives its weights from the Python reweighted fixture, so the browser preview and the deterministic scorer agree on category weight, contribution, and order.
- The dossier reads top-down: verdict dial, the constraint / confidence / coverage / evidence / what-if strip, the what-if preview with missing metrics and unmeasured categories, an amber collapsible warning strip with a count, hard limits with their warnings, categories, unmeasured categories, then informational metrics, rail, housing, street care, route boundary, and readouts. A unit test asserts that order.
- Readouts stop implying clean results. Green Escape says there is no green-space evidence in the run rather than that no green space exists; catchment wording is generated from the metric unit; coordinates render as hemispheres. The import limit rose to 25 MB and its message names the 1,000-candidate cap so the two limits cannot contradict each other; load state is visible at every width and the reset button appears only when the demo is not active.
- The chrome now has three voices: display, mono with tabular numerals, and a text voice for every note, caveat, warning, and citation. Sorting is a labelled segmented control with pressed state, range inputs have a custom track and thumb, and the panels use an inner-edge shadow and frame line rather than floating cards. A rail journey's ORR operator, when present, is typed, validated, and shown.
- Verified on 2026-09-03: 58 Vitest tests, a clean TypeScript build, 30 Playwright tests including axe on desktop and mobile, screenshots refreshed.

### P15 completion note

- The shared field validators live in one module and the three importer commands are one preview-first skeleton driven by a small spec, so a new cited input adds a merge and a disclosure rather than a fourth copy of the command. Rail keeps its `--performance` flag through that spec.
- `.env` files, the virtualenv, and the ruff cache are ignored; stale bytecode for deleted modules is gone; provenance records the Python and jsonschema versions alongside the tool version; CI pins Python 3.12 and guards the committed viewer build. The README gained the install step, the new research flags, the three-state limits, coverage, evidence basis, export flags, and the ORR source.
- Not done: the lazy imports between validation and the rail, housing, and street-care modules remain, because those modules validate their inputs through the evidence validator and the evidence validator dispatches to them. Breaking that cycle needs the sub-block validators to move out of the merge modules, which is a larger reshuffle than this pass wanted.

## 2026-09-03 — Where the Project Stands After P9–P15

### State

- The live path measures what it says it measures. One isochrone call and one Overpass call collect only the metrics a run weights or constrains, node points of interest are counted, the preview prints the rounded origin that is actually sent, and the manifest records what was skipped and how much of the polygon left the machine.
- Missing evidence is visible everywhere. Hard limits are pass, fail, or unknown; unmeasured categories stay in the result with a coverage percentage; every observation and imported record carries a basis, and agent-inferred values cannot claim confidence above 0.5.
- One hand-written input is now measured: ORR punctuality and cancellations flow into rail journeys through the same preview, cap, cache, ledger, and citation path as the research command.
- Exports are deliberate and private: salted ledger ids, case-insensitive label scrubbing, withheld terminals, and visit audits dropped by default.
- The viewer is an instrument rather than a dashboard: stable map, category and metric importance, a top-down dossier, honest readouts, three typographic voices, and custom controls, with parity tests binding it to the Python scorer.
- Verification on 2026-09-03: ruff clean, 72 Python tests, demo bundle reproduces byte-identically, 58 Vitest tests, clean build, 30 Playwright tests with axe.

### Remaining work

- Green-space distance still uses straight-line reach; a network distance to the nearest park entrance would match the walking catchments used for points of interest.
- Per-destination isochrones are still out of scope under the two-call cap; a second destination reuses the first boundary.
- Screenshot baselines are refreshed by hand; a pixel-diff gate in CI would catch layout regressions the visual-contract test does not.
- Housing is the next candidate for a measured adapter: Land Registry price paid data is open and per-postcode, which would move the housing basis from agent-inferred to measured for purchases.
- Run comparison: two runs of the same profile on different days, or of two profiles, cannot yet be diffed in the viewer or on the command line.
- The validation import cycle noted under P15.

### Decisions to keep

- The Python scorer owns every number; the viewer previews and never persists.
- Two live provider calls per run, previewed before they happen, remains the ceiling until a measured need proves otherwise.
- Every new evidence source enters through the importer skeleton with a basis, a citation, and a disclosure line, or not at all.

## 2026-09-03 — The Missing Front Door: Demo to Personal Search

### Prompt

After the P9–P15 deploy went live, Luke looked at the Pages site and put a finger on the gap: the demo shows a finished result, but nothing on it says that it is a sample, nothing invites you to make your own search with your own criteria, and there is no one-line path from the page to the real, locally running app. The core of the product is that your own agent, on your existing subscription, does the research for free while an honest progress modal shows what is happening, and you get personalised results back. The demo is only there to bring people in. The head of this file was restated on the same day to say that plainly.

### Assessment

The repository already encodes the product. It just does not tell anyone.

**Where the code already agrees with the vision**

- The skill at `skills/location-research/SKILL.md` exists, with Claude Code and Codex pointers. Its steps 6 to 10 already have the agent research rail, housing, and street-care evidence with citations, and each importer previews before it executes. That is exactly the "free research on your own subscription" mechanic.
- The viewer is deliberately a read-only renderer that never phones home. That is the right property for a shop window: the demo can never leak anything.

**Where it falls short**

1. **No front door.** The only hint in the viewer is a small status line saying demonstration data is active, plus a load-file button. Nothing says "this is a sample, go make yours." The README has the path, but a visitor arriving from the Pages link does not read the README.
2. **No one-liner.** Getting from zero to a run means clone, install uv, sync, `npm install`, get an OpenRouteService key, set it, then invoke the skill. The skill is repository-scoped, so it does nothing until all of that is done.
3. **The routing key breaks the "free" promise.** OpenRouteService is free, but it is a signup form and an email at the moment of highest drop-off. A keyless fallback for the first run matters more than any spinner.
4. **Criteria live in the terminal, not the app.** Weights and hard limits are CLI flags and a TOML file. The agent conversation is effectively the criteria UI, which is fine, but the viewer never tells the visitor that the conversation is where it happens.
5. **No progress surface.** Research runs in the terminal and the viewer only opens at the end. A live modal needs the viewer to see progress, which means a tiny local server or a progress file the run script writes and the viewer watches. That is an architectural addition, not a cosmetic one, but a contained one: localhost does not break the no-external-network rule.

### Gameplan P16–P19

Ordered by how much each unlocks per unit of work. The door comes first because without it nobody reaches anything else.

#### P16 — Hero call to action on the demo

- A banner above the map, visible at every width: "This is a sample on real towns with synthetic evidence. Run your own search."
- Clicking opens a modal with Claude Code and Codex tabs. Each tab shows a single copy-paste command with a copy button, one sentence on what happens next, and one sentence on what stays private.
- The modal is static content; no network, no analytics, no external scripts. It disappears when a private bundle is loaded and returns with the demo.
- Vitest covers the modal's content and the copy action; Playwright and axe cover it on desktop and mobile.

#### P17 — Make the one-liner true

- A bootstrap script, `scripts/bootstrap.ps1` and `scripts/bootstrap.sh`, that clones the repository, runs `uv sync` and `npm install`, checks for a routing key, prints what was and was not found, and starts the chosen agent in the repository so the skill is loaded from `.claude/skills` or `.agents/skills`.
- The command in the P16 modal is the command this script makes work. Test it from an empty directory on Windows and on a POSIX shell.
- The README's "Running it" section points at the bootstrap first and keeps the manual steps as the long form.

#### P18 — Keyless first run

- When no `ORS_API_KEY` is present, the research command falls back to a plain distance boundary around the origin, sized from the requested minutes and a stated speed assumption, and labels the boundary basis `proxy` in the manifest, the result, and the viewer's route-boundary panel.
- The preview says clearly which boundary will be used and that a key upgrades it to a real isochrone. The skill's first step offers the key as an upgrade, never as a gate.
- Python tests cover the fallback geometry and the manifest label; the viewer test covers the proxy wording.

#### P19 — Progress modal on a local serve

- A `serve` command that hosts the built viewer and a `progress.json` on localhost only. The research and import commands append stage events to that file: stage name, counts so far, cache hits, provider host, and any warning.
- The viewer polls the local progress feed only when served from localhost, never on Pages, and shows a modal with real stage names and real counts, with the whimsical copy layered on top. When the run finishes, the modal offers to load the new bundle.
- The rule that the viewer makes no external network request beyond OSM tiles is unchanged; localhost is the machine itself.
- Tests: Python covers the event writer; Vitest covers the modal's rendering of a fixture feed; Playwright drives a fake feed end to end.

### P16 completion note

- The demo now has a front door. While the sample bundle is active a bezel sits over the map between the register and the dossier (below the map on a phone) saying "Sample run / real towns, synthetic evidence" with a large acid button, "Run your own search". It disappears when a private bundle is imported and returns with the demo.
- The button opens a modal, not a page. Tabs choose Claude Code or Codex; a segmented control chooses Windows PowerShell or macOS/Linux, defaulting from the visitor's platform. The one line is rendered from a pure function in `app/src/lib/onboarding.ts`, copied with one button, and followed by the skill's invocation, the prerequisites, five "what happens next" steps, three "what stays private" notes, and links to the workflow and the source. The modal is a plain `role="dialog"` with its own focus handling because jsdom has no native dialog methods; the heading takes focus on open, Tab is trapped, Escape and the backdrop close it, and focus returns to the door.
- Nothing about the modal touches the network: the unit test stubs `fetch` and asserts it is never called; the copy button uses the clipboard only.
- Verified on 2026-09-03: 63 Vitest tests (three new: door visibility, the modal end to end, and the command strings), 34 Playwright tests passing with axe clean on desktop and mobile including the open modal (the command block wraps rather than scrolls so it needs no focusable scroll region), clean build.
- Known nit: on a 1280px desktop the banner covers the top-most demo pin; the map is still fitted and the pin is reachable once the banner is dismissed by loading a bundle. Left as is because the banner is the point while the sample is active.

### P17 completion note

- The one-liner is true. `scripts/bootstrap.sh` (POSIX sh) and `scripts/bootstrap.ps1` (PowerShell, designed for `irm | iex`) take the agent name, report git, uv, Node 22+, npm, the agent CLI, and whether `ORS_API_KEY` is set without ever printing it, then clone or reuse the repository, run `uv sync` and `npm install`, and open the agent inside the clone with a prompt that names the research skill. Python is not a prerequisite because uv installs it. When the shell script arrives through a pipe it hands the agent `/dev/tty` so the terminal still works. `LOCATION3_DIR`, `LOCATION3_REPO`, and `LOCATION3_LAUNCH=0` exist for tests and for people who want to stop before launch.
- Tested three ways on 2026-09-03: unit tests drive both scripts with shimmed `uv` and `npm` against a clone of this working tree (the test alone marks the source safe for git through `GIT_CONFIG_*`, because on this machine the checkout is owned by another account); a real run of each script in a scratch directory cloned, synced, installed 133 packages, and printed the launch line; and a static check asserts neither script ever echoes the key.
- The README opens "Running it" with the two lines; the manual install remains below. The modal's lines and the README's lines are the same strings.
- Verified: ruff clean, 76 Python tests (four new), viewer suites unchanged from P16.

### P18 completion note

- A first run needs no signup. When `ORS_API_KEY` is absent the research command builds a distance-proxy boundary locally: a 64-vertex circle whose radius is the requested minutes at an assumed speed per travel profile (40 km/h driving, 15 cycling, 4.5 walking) times a 0.7 straight-line detour factor, so 30 minutes by car is a 14.0 km radius. Nothing about the origin leaves the machine for it; the only live call is Overpass, and the preview says "Maximum live provider calls: 1".
- The proxy is labelled everywhere it can be seen. The boundary type `distance_proxy` joins `isochrone` and `fixture_polygon` in the Python validator, the JSON Schema, the viewer's hand validator, and its types; the profile and provenance carry a `description` stating the assumptions; the manifest gains a warning that starts "Route boundary is a distance proxy"; and the dossier's route-boundary block reads "SEARCH ENVELOPE / distance proxy", "30 min · PROXY", and the assumptions in the text voice.
- The preview's wording changes with the key: keyed runs still say what origin is sent to the routing provider; keyless runs say the origin is used locally and that a free key upgrades the boundary. The key itself is tested for presence once and never printed; the keyed preview test asserts that.
- The skill's first step now tells the agent to mention the upgrade once and carry on; the README says the same in the run-flow summary and the research section.
- Verified on 2026-09-03: ruff clean, 80 Python tests (four new: proxy geometry and input checks, keyless execution, and the two previews), 65 Vitest tests (two new: schema parity for the boundary type in both validators, and the dossier's proxy wording), 34 Playwright tests, clean build, demo bundle reproduces byte-identically.

### P19 completion note

- The run can be watched. `location3.progress.ProgressLog` appends stage events to `research-runs/progress.json` atomically: the research command records the boundary (isochrone with its cache state, or the locally computed proxy), discovery with candidate and observation counts and the Overpass cache state, measured counts per metric, ranked places by limit status, and the written bundle; the importers record the merge and the write. A failure marks the feed failed with the exception text and re-raises. A log with no path is a silent no-op, which is what library callers and every existing test get.
- `python scripts/serve_viewer.py` hosts `app/dist`, the feed, and `research-runs/<name>/results.json` on 127.0.0.1 only, with no-store JSON, nosniff, and no referrer. Profiles, evidence, provenance, anything nested, and any path outside those three routes are 404; a test walks the traversal attempts.
- The viewer polls `./progress.json` every two seconds only when its page is served from a loopback address, and never inside unit tests. A 404, a dev server's HTML fallback, or an unparsable document all mean "no run in progress". The modal shows the real events in the text voice with the whimsy on top: a stage caption ("Knocking on doors" for discovery), a rotating quip line, a plumbob spinner that respects reduced motion, and when the run finishes a "Load this result" button that fetches the served bundle through the same validator as a file import. Dismissing hides the modal until a new run starts.
- Confirmed against the real serve command on 2026-09-03: built the viewer, started the server, dropped the running fixture into the feed, saw the modal, swapped in the finished fixture, saw the load button, and confirmed a missing run returns 404. Screenshots were reviewed at 1280px.
- Verified: ruff clean, 86 Python tests (six new across the log, the research stages and failure path, and the server's routes), 78 Vitest tests (13 new across the feed parser, the modal, and captions), 38 Playwright tests with axe clean on both modals, clean build, the CI private-material grep passes on the fresh `app/dist`.

### Decisions

- The demo stays a static, read-only renderer. The call to action is content, not a feature.
- The agent conversation remains the criteria interface for v1. A criteria form in the viewer is deferred until P16–P19 show whether people get stuck before or after the conversation starts.
- Criteria, previews, execution, and the two-call ceiling all stay in the deterministic Python core; the bootstrap and the serve command only wrap it.

## 2026-09-03 — Where the Project Stands After P16–P19

### State

- The front door exists. The public demo says it is a sample and offers one pasted line per agent and shell; the bootstrap scripts behind those lines clone, install, report, and open the agent with the research skill loaded. The lines point at `main` on GitHub, so they work the moment this branch is pushed and not before.
- A first run needs no signup. Without a routing key the boundary is a labelled distance proxy computed locally, one live call is made, and the profile, provenance, dossier, and preview all say so. A free key upgrades it and nothing else changes.
- A run can be watched. The research and import commands write a progress feed beside the private runs; a loopback-only serve command hosts the built viewer with that feed and finished bundles; the viewer shows real stage events under a little whimsy and offers to load the result. The public demo never polls.
- Verification on 2026-09-03: ruff clean, 86 Python tests, demo bundle reproduces byte-identically, 78 Vitest tests, 38 Playwright tests with axe clean on both modals, clean build, the CI private-material grep passes on `app/dist`. Both bootstrap scripts were also run for real against a local clone.

### Not yet exercised

- The bootstrap scripts' final step, handing the terminal to `claude` or `codex` with the skill prompt, was tested only up to the launch line (`LOCATION3_LAUNCH=0`). The first real end-to-end run from a pasted line on a clean machine is the next thing to watch.
- The Pages site still serves the P15 build; the front door reaches visitors only after the manual **Deploy viewer to Pages** run.

### Remaining work

- Everything listed under P9–P15 still stands: green-space network distance, per-destination isochrones, a screenshot diff gate in CI, a measured Land Registry housing adapter, run comparison, and the validation import cycle.
- A criteria form in the viewer stays deferred until the front door shows where people stall.
- The progress feed could carry the importers' preview lines too, so the modal explains what an import is about to do before `--execute`.

### Decisions to keep

- The demo is content plus a renderer; every capability that touches a person's data runs on their machine behind a preview.
- Anything that stands in for a measurement carries a label everywhere it can be seen, the distance proxy included.
- Localhost is the machine itself; the viewer's no-external-network rule is unchanged.

## 2026-09-03 — Giving the Viewer Some Life

### Prompt

Luke looked at the live front door and said it was a bit ugly, and that the aesthetic may not match the app's utility. My read, after screenshots at 1440, 1280, and 390: the layout is sound, the tone is wrong. Every surface is dressed as an ops console (chamfers, bezels, glow, a map filtered to a dim green ghost, and nouns like "instrument", "register", and "dossier") for a tool whose job is helping someone find a lovely place to live. Luke agreed: "give it a bit more life", "make the map nice and colourful for a start", then the rest; commit first so it can be reverted. The revert point is 0f4bb4d.

### Gameplan

- **P20 — A real map.** Serve OpenStreetMap tiles in colour with only a gentle tone, drop the vignette, the grid, the scan line, and the "MAP FEED" label, and fit the field with top padding so the front door never covers a pin. Nothing animates while idle.
- **P21 — Flat, warm panels.** One border, a soft radius, a soft shadow, no chamfer, no inner hairline, no glow. A lifted background, a friendlier lime accent, coral and sun for the other two states. Uppercase letter-spaced mono is reserved for eyebrows and tiny labels; names, headings, metrics, and controls go to sentence case.
- **P22 — Plain words.** "Shortlist" and "Evidence" instead of "Candidate register" and "Evidence dossier"; a tagline that says what the tool is for; a status rail that says where the data went in words. Class names and ARIA contracts stay put so the tests keep meaning.
- **P23 — A lighter front door.** A compact invite strip, a modal whose two toggle rows are labelled, whose command block is the hero with the copy button inside it, and whose "what happens next" is three steps.
- **P24 — Evidence.** Refresh the README screenshots, adjust the README wording, and record what changed.

### P20 completion note

- OpenStreetMap tiles now render in colour with only a slight tone; the vignette, the grid, the scan line, its keyframes, and the "MAP FEED" label are gone, and the boundary is a mid-green dash with a faint fill so it reads on a light map. The Leaflet attribution went light to match.
- The field fits into the visible part of the map: on a wide screen the fit pads for the two side panels, the header, and the front door, so no pin starts under a panel; on a phone it pads evenly. A new Playwright check asserts that nothing on the page animates while idle, replacing the two scan-line checks.
- Verified: typecheck and build clean, 78 Vitest tests, screenshots at 1280 and 390 reviewed with live tiles.

### P21 completion note

- Every panel is now one flat card: a border, a 12px radius, and a soft drop shadow, with the chamfer, the inner hairline, the gradient, and the viewport frame line removed. Inner blocks share a 7px radius. Every glow (status lights, buttons, the score dial, the bars, the pins, the slider thumb) is gone; the plumbob keeps its bounce and nothing else.
- The palette lifted off pure black: background `#11171a`, panels `rgba(20, 26, 29, 0.94)`, accent `#b4f36b`, sun `#ffcd6b`, coral `#ff8577`. The visual contract test pins the new tokens.
- Uppercase letter-spaced mono is now reserved for eyebrows, readout labels, definition terms, and the status rail; panel headings, place names, category and metric names, sort keys, buttons, links, and the tune rows read in sentence case at a slightly larger size.
- One regression caught in review: giving the readout strip `overflow: hidden` let the evidence column's flex layout squash it to ten pixels. It is `flex: 0 0 auto` now.

### P22 completion note

- The header now says what the tool is for ("Where to live, with receipts") over a run title made from the run id; the load state reads "Sample data: real towns, synthetic evidence"; the panels are "Shortlist" and "Evidence / place 01"; the buttons read "Reset demo", "Import result.json", and "Restore researched importance"; the status rail says "Ready", "Researched 01 Aug 2026", and "Runs in your browser · nothing uploaded · map tiles from OpenStreetMap".
- The page title and description say the same, and the README's part table and captions use the new names. Class names, ids, and ARIA labels did not move, so every test that changed did so only for the words it matches.
- Verified: typecheck and build clean, 78 Vitest tests, screenshots reviewed at 1280.

### P23 completion note

- The invite is one short line ("Want this for your own criteria?") beside the button, capped at 600px and centred between the cards, so it covers far less map. The button reads "Run your own search" in sentence case with the "one line · your agent · free" strap underneath.
- The modal's two choices are labelled rows ("Your agent", "Your shell") of segmented keys, the command block is the hero with a lime "Copy" button in its header that flips to "Copied", and "What happens next" is three steps that still say the agent never assigns a score and there are at most two provider calls. The close button and the copy button lost their shouting.
- Verified: typecheck and build clean, 78 Vitest tests, 38 Playwright tests (36 passed, the 2 screenshot captures skipped) with axe clean on both modals, screenshots at 1440, 1280, and 390 with the modal open and closed.

### P24 completion note

- The four README screenshots were recaptured from the new build with live tiles, and the README's captions and part table now use "viewer", "shortlist", and "evidence". No file under `README.md`, the skill, or `AGENTS.md` still says "instrument", "register", or "dossier" as a product noun; class names and the `chromium-dossier.png` filename stay so links and tests do not move.
- Verified on 2026-09-03: typecheck and build clean, 78 Vitest tests, 38 Playwright tests (36 passed plus the two screenshot captures, which ran for real this time) with axe clean on both modals, the CI private-material grep passes on the fresh `app/dist`, and no JSON is shipped in it. Nothing in Python changed.

### Decisions

- Dark stays: the panels float over a light, colourful map, so the score colours and the map both read. A paper reskin was the other route and is a rewrite of every panel.
- The plumbob, the quips, and the "knocking on doors" captions stay; they finally fit the room.
- The viewer still makes no request beyond OpenStreetMap tiles; the reskin uses system fonts only.

## 2026-09-03 — Where the Project Stands After the Reskin

### State

- The viewer looks like what it is: a colourful OpenStreetMap map with three dark cards floating over it, a shortlist, the evidence for one place, and a short invite to run your own search. The chamfers, glows, grid, scan line, and console nouns are gone; the plumbob and the quips stay.
- Five commits after 0f4bb4d (plan, map, panels, words, front door, evidence). Reverting to 0f4bb4d restores the old look in one step.
- Nothing in Python changed. The viewer still makes no request beyond map tiles, uses system fonts only, and the CI private-material grep passes on the fresh build.

### Not yet done

- Not pushed. The live demo still serves the console look until `main` is pushed and **Deploy viewer to Pages** is run.
- The first real end-to-end run from a pasted line on a clean machine is still the next thing to watch.
- The README screenshots were recaptured; the phone screenshot's header still overlaps the top of the map, which is by design but worth a look on a real phone.
