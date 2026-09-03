import { label } from "../lib/format";
import { MAX_WEIGHT, weightsDiffer } from "../lib/whatif";
import type { TuningBaseline, WeightMap } from "../lib/whatif";

interface TunePanelProps {
  baseline: TuningBaseline;
  weights: WeightMap;
  categoryWeights: WeightMap;
  onChange: (weights: WeightMap) => void;
  onCategoryChange: (weights: WeightMap) => void;
  onReset: () => void;
}

/**
 * Importance sliders for a what-if preview. The sliders never touch the
 * imported bundle; they only steer the browser-side arithmetic that is tested
 * against the Python scorer. Category importance sits above the metrics it
 * governs, exactly as the scorer combines them.
 */
export function TunePanel({ baseline, weights, categoryWeights, onChange, onCategoryChange, onReset }: TunePanelProps) {
  const active = weightsDiffer(weights, baseline, categoryWeights);
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
      <div className="tune-grid" role="group" aria-label="Category and metric importance">
        {baseline.categories.map((category) => {
          const categoryValue = categoryWeights[category] ?? baseline.categoryWeights[category];
          const categoryResearched = baseline.categoryWeights[category];
          const categoryId = `tune-category-${category}`;
          return (
            <div className="tune-group" key={category} role="group" aria-label={`${label(category)} importance`}>
              <div className="tune-row category">
                <label htmlFor={categoryId}>
                  <span>{label(category)}</span>
                  <small>Category · researched {categoryResearched}</small>
                </label>
                <input
                  id={categoryId}
                  type="range"
                  min={0}
                  max={MAX_WEIGHT}
                  step={1}
                  value={categoryValue}
                  aria-valuetext={`${categoryValue} of ${MAX_WEIGHT}`}
                  onChange={(event) => onCategoryChange({ ...categoryWeights, [category]: Number(event.currentTarget.value) })}
                />
                <output htmlFor={categoryId} className={categoryValue !== categoryResearched ? "changed" : undefined}>
                  {categoryValue}
                </output>
              </div>
              {baseline.metrics.filter((metric) => baseline.metricCategories[metric] === category).map((metric) => {
                const value = weights[metric] ?? baseline.metricWeights[metric];
                const researched = baseline.metricWeights[metric];
                const inputId = `tune-${metric}`;
                return (
                  <div className="tune-row" key={metric}>
                    <label htmlFor={inputId}>
                      <span>{label(metric)}</span>
                      <small>researched {researched}</small>
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
          );
        })}
      </div>
      <button type="button" className="utility-button" onClick={onReset} disabled={!active}>
        Restore researched importance
      </button>
    </details>
  );
}
