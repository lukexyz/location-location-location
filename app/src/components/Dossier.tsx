import { basisLabel, compactDate, label, rawValue } from "../lib/format";
import { deriveReadouts } from "../lib/readouts";
import type { WhatIfScore } from "../lib/whatif";
import type { CandidateResult, ConstraintStatus, HousingSummary, MetricResult, RailJourney, RouteBoundary, StreetCareSummary } from "../types";

const CONSTRAINT_LABEL: Record<ConstraintStatus, string> = {
  pass: "CLEAR", unknown: "UNVERIFIED", fail: "LIMIT BREACH",
};
const CONSTRAINT_TONE: Record<ConstraintStatus, "good" | "warn" | "bad"> = {
  pass: "good", unknown: "warn", fail: "bad",
};

export function Dossier({
  candidate,
  routeBoundary,
  whatIf,
}: {
  candidate: CandidateResult;
  routeBoundary?: RouteBoundary;
  whatIf?: WhatIfScore;
}) {
  const status = candidate.hard_constraints.status;
  const coverage = candidate.score_coverage_percent;
  return (
    <aside className="dossier panel-cut" aria-labelledby="dossier-heading">
      <header className="dossier-heading">
        <div>
          <span className="eyebrow">EVIDENCE DOSSIER / {String(candidate.rank).padStart(2, "0")}</span>
          <h2 id="dossier-heading">{candidate.name}</h2>
          <div className="coordinates">
            {candidate.location.latitude.toFixed(3)}N / {candidate.location.longitude.toFixed(3)}E
          </div>
        </div>
        <div
          className={`score-dial ${status === "fail" ? "failed" : status === "unknown" ? "unverified" : ""}`}
          style={{ "--score": candidate.overall_score } as React.CSSProperties}
          aria-label={`Overall suitability ${candidate.overall_score.toFixed(1)} out of 100`}
        >
          <strong>{candidate.overall_score.toFixed(1)}</strong>
          <span>FIT</span>
        </div>
      </header>

      <div className="instrument-strip">
        <Readout label="Constraint" value={CONSTRAINT_LABEL[status]} tone={CONSTRAINT_TONE[status]} />
        <Readout label="Confidence" value={`${candidate.confidence.toFixed(0)}%`} />
        <Readout label="Coverage" value={`${coverage.toFixed(0)}%`} tone={coverage < 100 ? "warn" : undefined} />
        <Readout label="Evidence" value={`${metricCount(candidate)} pts`} />
        {whatIf && (
          <Readout
            label="What-if"
            value={`${whatIf.overallScore.toFixed(1)} · ${whatIf.confidence.toFixed(0)}%`}
            tone="preview"
          />
        )}
      </div>

      <div
        className="confidence-track"
        role="progressbar"
        aria-label="Evidence confidence"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(candidate.confidence)}
      >
        <span style={{ width: `${candidate.confidence}%` }} />
      </div>

      <div className="dossier-scroll">
        <section className="readout-block" aria-labelledby={`readouts-${candidate.id}`}>
          <h3 id={`readouts-${candidate.id}`} className="visually-hidden">Playful readouts</h3>
          <ul className="readout-grid">
            {deriveReadouts(candidate).map((readout) => (
              <li key={readout.key} className={readout.available ? undefined : "is-empty"}>
                <span className="eyebrow">{readout.title.toUpperCase()}</span>
                <strong>{readout.value}</strong>
                <small>{readout.detail}</small>
              </li>
            ))}
          </ul>
          <p className="readout-footnote">Readouts restate cited evidence; they add nothing to the score.</p>
        </section>

        {routeBoundary && <RouteBoundaryReadout boundary={routeBoundary} />}

        {candidate.hard_constraints.results.length > 0 && (
          <section className="constraint-block" aria-labelledby="constraints-heading">
            <h3 id="constraints-heading">Hard limits</h3>
            {candidate.hard_constraints.results.map((constraint) => (
              <div
                className="constraint-row"
                key={`${constraint.metric}:${constraint.destination_label ?? "all"}`}
              >
                <span>
                  {label(constraint.metric)}
                  {constraint.destination_label ? ` / ${constraint.destination_label}` : ""}
                </span>
                <strong className={`text-${CONSTRAINT_TONE[constraint.status]}`}>
                  {constraint.actual ?? "no evidence"} {constraint.operator} {constraint.value}
                </strong>
              </div>
            ))}
          </section>
        )}

        {candidate.rail_summary && (
          <section className="rail-block" aria-labelledby={`rail-${candidate.id}`}>
            <header>
              <div>
                <span className="eyebrow">SHORTLIST / CITED JOURNEYS</span>
                <h3 id={`rail-${candidate.id}`}>Rail intelligence</h3>
              </div>
              <strong>{candidate.rail_summary.fastest_total_minutes} min</strong>
            </header>
            {candidate.rail_summary.journeys.map((journey) => (
              <RailJourneyReadout journey={journey} key={journey.id} />
            ))}
          </section>
        )}

        {candidate.housing_summary && (
          <HousingReadout housing={candidate.housing_summary} candidateId={candidate.id} />
        )}

        {candidate.street_care_summary && (
          <StreetCareReadout streetCare={candidate.street_care_summary} candidateId={candidate.id} />
        )}

        {candidate.categories.map((category) => (
          <section className="category-block" key={category.category}>
            <header>
              <div>
                <span className="eyebrow">CATEGORY / WEIGHT {category.weight}</span>
                <h3>{label(category.category)}</h3>
              </div>
              <div className="category-result">
                <strong>{category.score.toFixed(1)}</strong>
                <span>+{category.overall_contribution.toFixed(2)} overall</span>
              </div>
            </header>
            <div className="category-bar" aria-hidden="true">
              <span style={{ width: `${category.score}%` }} />
            </div>
            {category.metrics.map((metric) => (
              <MetricRow metric={metric} key={metric.metric} />
            ))}
          </section>
        ))}

        {candidate.unmeasured_categories.map((item) => (
          <section className="category-block unmeasured" key={item.category} aria-label={`${label(item.category)} has no evidence`}>
            <header>
              <div>
                <span className="eyebrow">CATEGORY / WEIGHT {item.weight} / NO EVIDENCE</span>
                <h3>{label(item.category)}</h3>
              </div>
              <div className="category-result">
                <strong>--</strong>
                <span>not in score</span>
              </div>
            </header>
            <p className="unmeasured-note">
              Nothing in this category was measured, so it is absent from the score rather than
              counted as average. The score covers {coverage.toFixed(0)}% of the intended category weight.
            </p>
          </section>
        ))}

        {candidate.informational_metrics.length > 0 && (
          <section className="category-block">
            <header><h3>Informational only</h3></header>
            {candidate.informational_metrics.map((metric) => (
              <MetricRow metric={metric} key={metric.metric} />
            ))}
          </section>
        )}

        {(candidate.warnings.length > 0 || candidate.missing_metrics.length > 0) && (
          <section className="warning-block" aria-labelledby="warning-heading">
            <h3 id="warning-heading">Evidence warnings</h3>
            <ul>
              {candidate.warnings.map((warning) => <li key={warning}>{warning}</li>)}
              {candidate.missing_metrics.map((metric) => <li key={metric}>Missing: {label(metric)}</li>)}
            </ul>
          </section>
        )}
      </div>
    </aside>
  );
}

function RouteBoundaryReadout({ boundary }: { boundary: RouteBoundary }) {
  return (
    <section className="route-context" aria-labelledby="route-context-heading">
      <header>
        <div>
          <span className="eyebrow">SEARCH ENVELOPE / {boundary.type.replaceAll("_", " ")}</span>
          <h3 id="route-context-heading">Route boundary</h3>
        </div>
        <strong>{boundary.duration_minutes ? `${boundary.duration_minutes} min` : "FIXTURE"}</strong>
      </header>
      <dl>
        <div><dt>Provider</dt><dd>{boundary.provider}</dd></div>
        <div><dt>Retrieved</dt><dd>{compactDate(boundary.retrieved_at)}</dd></div>
        <div><dt>Travel profile</dt><dd>{boundary.travel_profile ?? "not supplied"}</dd></div>
        <div><dt>Departure</dt><dd>{boundary.departure_time ? compactDate(boundary.departure_time) : "not supplied"}</dd></div>
      </dl>
      <p>{boundary.traffic_treatment}</p>
    </section>
  );
}

function HousingReadout({ housing, candidateId }: { housing: HousingSummary; candidateId: string }) {
  const market = housing.market;
  const basis = housing.mode === "buy" ? "purchase" : "month";
  return (
    <section className="housing-block" aria-labelledby={`housing-${candidateId}`}>
      <header>
        <div>
          <span className="eyebrow">SHORTLIST / MARKET EVIDENCE</span>
          <h3 id={`housing-${candidateId}`}>Housing affordability</h3>
        </div>
        <strong>{Math.round(housing.budget_ratio * 100)}%</strong>
      </header>
      <dl className="housing-grid">
        <div><dt>Typical {basis}</dt><dd>{gbp(housing.typical_cost_gbp)}</dd></div>
        <div><dt>Budget</dt><dd>{gbp(housing.budget_gbp)}</dd></div>
        <div><dt>Property</dt><dd>{housing.bedrooms === null ? "Any size" : `${housing.bedrooms} bed`} {housing.property_type}</dd></div>
        <div><dt>Statistic</dt><dd>{market.statistic}</dd></div>
        <div><dt>Geography</dt><dd>{market.geography.label}</dd></div>
        <div><dt>Sample</dt><dd>{market.sample_size ?? "not published"}</dd></div>
        <div><dt>Period</dt><dd>{compactDate(market.period_start)}–{compactDate(market.period_end)}</dd></div>
        <div><dt>Confidence</dt><dd>{Math.round(market.confidence * 100)}%</dd></div>
        <div><dt>Basis</dt><dd className={market.basis === "agent_inferred" ? "text-warn" : undefined}>{basisLabel(market.basis)}</dd></div>
      </dl>
      <p className="housing-note">{market.confidence_notes}</p>
      <p className="inventory-note">Market evidence only — live inventory was not checked.</p>
      {market.listing_search_url && (
        <a className="listing-action" href={market.listing_search_url} rel="noreferrer" target="_blank">
          Search current listings ↗
        </a>
      )}
      <div className="housing-sources">
        {market.sources.map((source) => (
          <a href={source.url} key={source.kind} rel="noreferrer" target="_blank">
            {source.kind}: {source.label} ({compactDate(source.source_date)})
          </a>
        ))}
      </div>
    </section>
  );
}

function gbp(value: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency", currency: "GBP", maximumFractionDigits: 0,
  }).format(value);
}

function StreetCareReadout({ streetCare, candidateId }: { streetCare: StreetCareSummary; candidateId: string }) {
  const place = streetCare.place;
  const reports = place.local_reports;
  const audit = place.visit_audit;
  const basis = streetCare.basis === "recent_visit_audit" ? "Recent visit audit" : "Cautious proxy";
  return (
    <section className="street-care-block" aria-labelledby={`street-care-${candidateId}`}>
      <header>
        <div>
          <span className="eyebrow">PAVEMENT PRIDE / {basis}</span>
          <h3 id={`street-care-${candidateId}`}>Street care</h3>
        </div>
        <strong>{streetCare.score.toFixed(1)}</strong>
      </header>
      <dl className="street-care-grid">
        <div><dt>Local authority</dt><dd>{place.local_authority}</dd></div>
        <div><dt>Confidence</dt><dd>{Math.round(streetCare.confidence * 100)}%</dd></div>
        <div><dt>Basis</dt><dd className={place.basis === "agent_inferred" ? "text-warn" : undefined}>{streetCare.basis === "recent_visit_audit" ? "User-observed" : basisLabel(place.basis)}</dd></div>
        <div><dt>Fly-tipping</dt><dd>{place.fly_tipping.current_incidents_per_1000}/1k</dd></div>
        <div><dt>Prior period</dt><dd>{place.fly_tipping.previous_incidents_per_1000}/1k</dd></div>
        <div><dt>Reporting basis</dt><dd>{place.fly_tipping.reporting_basis}</dd></div>
        <div><dt>Report density</dt><dd>{reports?.reports_per_1000 == null ? "unavailable" : `${reports.reports_per_1000}/1k`}</dd></div>
        <div><dt>Unresolved</dt><dd>{reports?.unresolved_percent == null ? "unavailable" : `${reports.unresolved_percent}%`}</dd></div>
        <div><dt>Median resolution</dt><dd>{reports?.median_resolution_days == null ? "unavailable" : `${reports.median_resolution_days} days`}</dd></div>
      </dl>
      <div className="street-components">
        {streetCare.components.map((component) => (
          <div key={component.key}>
            <span>{label(component.key)}</span>
            <b>{component.included ? component.normalized_score?.toFixed(1) : "info only"}</b>
          </div>
        ))}
      </div>
      {audit && (
        <p className="street-note">
          Visit {compactDate(audit.audited_at)}: {audit.notes}
          {streetCare.basis === "proxy" ? " This audit is too old to override the proxy." : ""}
        </p>
      )}
      {streetCare.basis === "proxy" && (
        <p className="proxy-note">Low-resolution proxy — incident volume also reflects reporting practice. A recent visit audit is recommended.</p>
      )}
      <div className="street-sources">
        <a href={place.fly_tipping.source.url} rel="noreferrer" target="_blank">
          Fly-tipping: {place.fly_tipping.source.label} ({compactDate(place.fly_tipping.source.source_date)})
        </a>
        {reports && (
          <a href={reports.source.url} rel="noreferrer" target="_blank">
            Local reports: {reports.source.label} ({compactDate(reports.source.source_date)})
          </a>
        )}
      </div>
    </section>
  );
}

function RailJourneyReadout({ journey }: { journey: RailJourney }) {
  const lastTrain = journey.last_useful_departure
    ? journey.last_useful_departure.slice(11, 16)
    : "unknown";
  return (
    <details className="rail-journey" open={journey.primary}>
      <summary>
        <span><strong>{journey.origin_station}</strong> → {journey.london_arrival_station}</span>
        <b>{journey.total_minutes} min</b>
      </summary>
      <p className="rail-window">{journey.destination_label} / {journey.service_window}</p>
      <dl className="rail-grid">
        <div><dt>Station access</dt><dd>{journey.access_minutes} min</dd></div>
        <div><dt>Expected wait</dt><dd>{journey.expected_wait_minutes} min</dd></div>
        <div><dt>Scheduled rail</dt><dd>{journey.scheduled_rail_minutes} min</dd></div>
        <div><dt>London last mile</dt><dd>{journey.london_last_mile_minutes} min</dd></div>
        <div><dt>Changes</dt><dd>{journey.changes}</dd></div>
        <div><dt>Frequency</dt><dd>{journey.services_per_hour}/hr</dd></div>
        <div><dt>Last useful train</dt><dd>{lastTrain}</dd></div>
        <div><dt>Time to 3</dt><dd>{railPercent(journey.punctuality_percent)}</dd></div>
        <div><dt>Cancellations</dt><dd>{railPercent(journey.cancellation_percent)}</dd></div>
        <div><dt>Confidence</dt><dd>{Math.round(journey.confidence * 100)}%</dd></div>
        <div><dt>Basis</dt><dd className={journey.basis === "agent_inferred" ? "text-warn" : undefined}>{basisLabel(journey.basis)}</dd></div>
      </dl>
      <p className="rail-note">{journey.confidence_notes}</p>
      <div className="rail-sources">
        {journey.sources.map((source) => (
          <a href={source.url} key={source.kind} rel="noreferrer" target="_blank">
            {source.kind}: {source.label} ({compactDate(source.source_date)})
          </a>
        ))}
      </div>
    </details>
  );
}

function railPercent(value: number | null): string {
  return value === null ? "unknown" : `${value.toFixed(1)}%`;
}

function MetricRow({ metric }: { metric: MetricResult }) {
  const favorableObservation = metric.metric === "betting_shops" && metric.raw_value === 0;
  return (
    <details className="metric-row">
      <summary>
        <span className="metric-name">{label(metric.metric)}</span>
        <span className="metric-raw">
          {favorableObservation ? (
            <><span className="favorable-observation">0</span> in 15 min</>
          ) : rawValue(metric.raw_value, metric.unit)}
        </span>
        <span className="metric-score">
          {metric.basis === "agent_inferred" && <i className="basis-flag" title="Agent-inferred">EST</i>}
          {metric.normalized_score.toFixed(1)}
        </span>
      </summary>
      <div className="metric-detail">
        <div className="metric-track"><span style={{ width: `${metric.normalized_score}%` }} /></div>
        <dl>
          <div><dt>Weight</dt><dd>{metric.active ? metric.weight : "informational"}</dd></div>
          <div><dt>Category points</dt><dd>{metric.category_contribution.toFixed(2)}</dd></div>
          <div><dt>Confidence</dt><dd>{Math.round(metric.confidence * 100)}%</dd></div>
          <div><dt>Basis</dt><dd className={metric.basis === "agent_inferred" ? "text-warn" : undefined}>{basisLabel(metric.basis)}</dd></div>
          <div><dt>Source date</dt><dd>{compactDate(metric.source_date)}</dd></div>
          <div><dt>Evidence</dt><dd><a href={metric.source_url} rel="noreferrer" target="_blank">{metric.source}</a></dd></div>
        </dl>
        <p>{metric.confidence_notes}</p>
        {metric.basis === "agent_inferred" && (
          <p className="basis-note">Agent-inferred value: an estimate, not a measurement. Verify before relying on it.</p>
        )}
      </div>
    </details>
  );
}

function Readout({ label: title, value, tone }: { label: string; value: string; tone?: "good" | "warn" | "bad" | "preview" }) {
  return <div className={`readout ${tone ?? ""}`}><span>{title}</span><strong>{value}</strong></div>;
}

function metricCount(candidate: CandidateResult): number {
  return candidate.categories.reduce((total, category) => total + category.metrics.length, 0)
    + candidate.informational_metrics.length
    + (candidate.rail_summary?.journeys.length ?? 0)
    + (candidate.housing_summary ? 1 : 0)
    + (candidate.street_care_summary ? 1 : 0);
}
