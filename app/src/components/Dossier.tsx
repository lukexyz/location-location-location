import { compactDate, label, rawValue } from "../lib/format";
import type { CandidateResult, MetricResult } from "../types";

export function Dossier({ candidate }: { candidate: CandidateResult }) {
  const constraintStatus = candidate.hard_constraints.passed ? "CLEAR" : "LIMIT BREACH";
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
          className={`score-dial ${candidate.hard_constraints.passed ? "" : "failed"}`}
          style={{ "--score": candidate.overall_score } as React.CSSProperties}
          aria-label={`Overall suitability ${candidate.overall_score.toFixed(1)} out of 100`}
        >
          <strong>{candidate.overall_score.toFixed(1)}</strong>
          <span>FIT</span>
        </div>
      </header>

      <div className="instrument-strip">
        <Readout label="Constraint" value={constraintStatus} tone={candidate.hard_constraints.passed ? "good" : "bad"} />
        <Readout label="Confidence" value={`${candidate.confidence.toFixed(0)}%`} />
        <Readout label="Evidence" value={`${metricCount(candidate)} pts`} />
      </div>

      <div className="confidence-track" aria-label={`Evidence confidence ${candidate.confidence.toFixed(0)} percent`}>
        <span style={{ width: `${candidate.confidence}%` }} />
      </div>

      <div className="dossier-scroll">
        {candidate.hard_constraints.results.length > 0 && (
          <section className="constraint-block" aria-labelledby="constraints-heading">
            <h3 id="constraints-heading">Hard limits</h3>
            {candidate.hard_constraints.results.map((constraint) => (
              <div className="constraint-row" key={constraint.metric}>
                <span>{label(constraint.metric)}</span>
                <strong className={constraint.passed ? "text-good" : "text-bad"}>
                  {constraint.actual ?? "unknown"} {constraint.operator} {constraint.value}
                </strong>
              </div>
            ))}
          </section>
        )}

        {candidate.categories.map((category) => (
          <section className="category-block" key={category.category}>
            <header>
              <div>
                <span className="eyebrow">CATEGORY / WEIGHT {category.weight}</span>
                <h3>{label(category.category)}</h3>
              </div>
              <strong>{category.score.toFixed(1)}</strong>
            </header>
            <div className="category-bar" aria-hidden="true">
              <span style={{ width: `${category.score}%` }} />
            </div>
            {category.metrics.map((metric) => (
              <MetricRow metric={metric} key={metric.metric} />
            ))}
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
        <span className="metric-score">{metric.normalized_score.toFixed(1)}</span>
      </summary>
      <div className="metric-detail">
        <div className="metric-track"><span style={{ width: `${metric.normalized_score}%` }} /></div>
        <dl>
          <div><dt>Weight</dt><dd>{metric.active ? metric.weight : "informational"}</dd></div>
          <div><dt>Confidence</dt><dd>{Math.round(metric.confidence * 100)}%</dd></div>
          <div><dt>Source date</dt><dd>{compactDate(metric.source_date)}</dd></div>
          <div><dt>Evidence</dt><dd><a href={metric.source_url} rel="noreferrer" target="_blank">{metric.source}</a></dd></div>
        </dl>
        <p>{metric.confidence_notes}</p>
      </div>
    </details>
  );
}

function Readout({ label: title, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  return <div className={`readout ${tone ?? ""}`}><span>{title}</span><strong>{value}</strong></div>;
}

function metricCount(candidate: CandidateResult): number {
  return candidate.categories.reduce((total, category) => total + category.metrics.length, 0)
    + candidate.informational_metrics.length;
}
