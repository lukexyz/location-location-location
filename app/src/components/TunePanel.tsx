import { label } from "../lib/format";
import { MAX_WEIGHT, weightsDiffer } from "../lib/whatif";
import type { TuningBaseline, WeightMap } from "../lib/whatif";

interface TunePanelProps {
  baseline: TuningBaseline;
  weights: WeightMap;
  onChange: (weights: WeightMap) => void;
  onReset: () => void;
}

/**
 * Importance sliders for a what-if preview. The sliders never touch the
 * imported bundle; they only steer the browser-side arithmetic that is tested
 * against the Python scorer.
 */
export function TunePanel({ baseline, weights, onChange, onReset }: TunePanelProps) {
  const active = weightsDiffer(weights, baseline);
  return (
    <details className={`tune-panel${active ? " active" : ""}`}>
      <summary>
        <span>Tune importance</span>
        <b>{active ? "WHAT-IF ACTIVE" : "RESEARCHED WEIGHTS"}</b>
      </summary>
      <p className="tune-note">
        Preview only. Evidence is not re-measured and the researched rank numbers stay
        in place; rerun the research to make new importance authoritative.
      </p>
      <div className="tune-grid" role="group" aria-label="Metric importance">
        {baseline.metrics.map((metric) => {
          const value = weights[metric] ?? baseline.metricWeights[metric];
          const researched = baseline.metricWeights[metric];
          const inputId = `tune-${metric}`;
          return (
            <div className="tune-row" key={metric}>
              <label htmlFor={inputId}>
                <span>{label(metric)}</span>
                <small>{label(baseline.metricCategories[metric])} · researched {researched}</small>
              </label>
              <input
                id={inputId}
                type="range"
                min={0}
                max={MAX_WEIGHT}
                step={1}
                value={value}
                aria-valuetext={`${value} of ${MAX_WEIGHT}`}
                onChange={(event) => onChange({ ...weights, [metric]: Number(event.currentTarget.value) })}
              />
              <output htmlFor={inputId} className={value !== researched ? "changed" : undefined}>{value}</output>
            </div>
          );
        })}
      </div>
      <button type="button" className="utility-button" onClick={onReset} disabled={!active}>
        RESTORE RESEARCHED IMPORTANCE
      </button>
    </details>
  );
}
