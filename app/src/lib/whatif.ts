import type { CandidateResult, MetricResult, ResearchResult } from "../types";

/**
 * What-if reweighting mirrors the Python scorer's arithmetic so a person can
 * preview how importance changes reorder the researched places. It is a
 * preview only: authoritative ranks come from `results.json`, evidence is never
 * re-measured, and missing evidence stays missing.
 */

export type WeightMap = Record<string, number>;

export interface TuningBaseline {
  /** Metric importance the research run used, 0–5. */
  metricWeights: WeightMap;
  /** Category importance the research run used, 0–5. */
  categoryWeights: WeightMap;
  /** Category of every metric the bundle knows about. */
  metricCategories: Record<string, string>;
  /** Metric keys in stable display order. */
  metrics: string[];
}

export interface WhatIfCategory {
  category: string;
  score: number;
  weight: number;
  overallContribution: number;
  metrics: { metric: string; normalizedScore: number; weight: number; categoryContribution: number }[];
}

export interface WhatIfScore {
  id: string;
  overallScore: number;
  confidence: number;
  categories: WhatIfCategory[];
  missingMetrics: string[];
  passed: boolean;
}

export const MAX_WEIGHT = 5;

function presentMetrics(candidate: CandidateResult): MetricResult[] {
  return [
    ...candidate.categories.flatMap((category) => category.metrics),
    ...candidate.informational_metrics,
  ];
}

/** Recover the run's weights from the bundle; metrics never observed anywhere cannot be tuned. */
export function deriveBaseline(result: ResearchResult): TuningBaseline {
  const metricWeights: WeightMap = {};
  const categoryWeights: WeightMap = {};
  const metricCategories: Record<string, string> = {};
  for (const candidate of result.candidates) {
    for (const category of candidate.categories) {
      categoryWeights[category.category] = category.weight;
    }
    for (const metric of presentMetrics(candidate)) {
      metricCategories[metric.metric] = metric.category;
      metricWeights[metric.metric] = metric.weight;
    }
  }
  const metrics = Object.keys(metricCategories)
    .filter((metric) => metricCategories[metric] in categoryWeights)
    .sort((left, right) => {
      const byCategory = metricCategories[left].localeCompare(metricCategories[right]);
      return byCategory || left.localeCompare(right);
    });
  return { metricWeights, categoryWeights, metricCategories, metrics };
}

/**
 * Round to two decimals exactly as Python's `round(value, 2)` does: correctly
 * rounded on the exact binary value, with true ties going to the even digit.
 */
export function round2(value: number): number {
  const expansion = value.toPrecision(25); // long enough to expose an exact binary tie
  if (/^-?\d+\.\d{2}50*$/.test(expansion)) {
    const scaled = Math.trunc(Math.abs(value) * 100);
    const even = scaled % 2 === 0 ? scaled : scaled + 1;
    return (value < 0 ? -even : even) / 100;
  }
  return Number(value.toFixed(2));
}

export function scoreWhatIf(
  candidate: CandidateResult,
  weights: WeightMap,
  baseline: TuningBaseline,
): WhatIfScore {
  const byMetric = new Map(presentMetrics(candidate).map((metric) => [metric.metric, metric]));
  const grouped = new Map<string, WhatIfCategory["metrics"]>();
  const missingMetrics: string[] = [];
  let availableConfidence = 0;
  let possibleConfidence = 0;

  for (const key of baseline.metrics) {
    const weight = clampWeight(weights[key] ?? baseline.metricWeights[key] ?? 0);
    const category = baseline.metricCategories[key];
    const active = weight > 0 && (baseline.categoryWeights[category] ?? 0) > 0;
    if (!active) continue;
    possibleConfidence += weight;
    const metric = byMetric.get(key);
    if (!metric) {
      missingMetrics.push(key);
      continue;
    }
    availableConfidence += weight * metric.confidence;
    const list = grouped.get(category) ?? [];
    list.push({ metric: key, normalizedScore: metric.normalized_score, weight, categoryContribution: 0 });
    grouped.set(category, list);
  }

  const categories: WhatIfCategory[] = [];
  for (const category of Object.keys(baseline.categoryWeights).sort()) {
    const metrics = grouped.get(category);
    if (!metrics || metrics.length === 0) continue;
    const activeWeight = metrics.reduce((total, metric) => total + metric.weight, 0);
    if (activeWeight === 0) continue;
    const score = metrics.reduce((total, metric) => total + metric.normalizedScore * metric.weight, 0) / activeWeight;
    for (const metric of metrics) {
      metric.categoryContribution = round2(metric.normalizedScore * metric.weight / activeWeight);
    }
    categories.push({
      category,
      score: round2(score),
      weight: baseline.categoryWeights[category],
      overallContribution: 0,
      metrics,
    });
  }

  const totalCategoryWeight = categories.reduce((total, category) => total + category.weight, 0);
  const overall = totalCategoryWeight
    ? categories.reduce((total, category) => total + category.score * category.weight, 0) / totalCategoryWeight
    : 0;
  for (const category of categories) {
    category.overallContribution = totalCategoryWeight
      ? round2(category.score * category.weight / totalCategoryWeight)
      : 0;
  }
  const confidence = possibleConfidence ? availableConfidence / possibleConfidence : 1;

  return {
    id: candidate.id,
    overallScore: round2(overall),
    confidence: round2(confidence * 100),
    categories,
    missingMetrics: missingMetrics.sort(),
    passed: candidate.hard_constraints.passed,
  };
}

/** Order what-if scores the way the Python scorer ranks: limits, suitability, confidence. */
export function orderWhatIf(scores: WhatIfScore[]): WhatIfScore[] {
  return [...scores].sort((left, right) =>
    Number(right.passed) - Number(left.passed)
    || right.overallScore - left.overallScore
    || right.confidence - left.confidence,
  );
}

export function weightsDiffer(weights: WeightMap, baseline: TuningBaseline): boolean {
  return baseline.metrics.some((metric) => clampWeight(weights[metric] ?? baseline.metricWeights[metric]) !== baseline.metricWeights[metric]);
}

export function clampWeight(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(MAX_WEIGHT, Math.max(0, value));
}
