import demoData from "../data/demo-results.json";
import reweightedData from "../data/demo-results.reweighted.json";
import { parseResultBundle } from "./validateResult";
import { deriveBaseline, orderWhatIf, scoreWhatIf, weightsDiffer } from "./whatif";

const demo = parseResultBundle(demoData);
const reweighted = parseResultBundle(reweightedData);
const baseline = deriveBaseline(demo);

describe("what-if reweighting", () => {
  it("reproduces the Python scorer exactly at the researched weights", () => {
    for (const candidate of demo.candidates) {
      const preview = scoreWhatIf(candidate, baseline.metricWeights, baseline);
      expect(preview.overallScore).toBeCloseTo(candidate.overall_score, 2);
      expect(preview.confidence).toBeCloseTo(candidate.confidence, 2);
      expect(preview.missingMetrics).toEqual(candidate.missing_metrics);
      expect(preview.coveragePercent).toBe(candidate.score_coverage_percent);
      expect(preview.unmeasuredCategories).toEqual(candidate.unmeasured_categories.map((item) => item.category));
      expect(preview.constraintStatus).toBe(candidate.hard_constraints.status);
      expect(preview.categories.map((category) => [category.category, category.score, category.overallContribution]))
        .toEqual(candidate.categories.map((category) => [category.category, category.score, category.overall_contribution]));
      for (const category of preview.categories) {
        const original = candidate.categories.find((item) => item.category === category.category)!;
        for (const metric of category.metrics) {
          const originalMetric = original.metrics.find((item) => item.metric === metric.metric)!;
          expect(metric.categoryContribution).toBeCloseTo(originalMetric.category_contribution, 2);
        }
      }
    }
    const ordered = orderWhatIf(demo.candidates.map((candidate) => scoreWhatIf(candidate, baseline.metricWeights, baseline)));
    expect(ordered.map((score) => score.id)).toEqual(
      [...demo.candidates].sort((left, right) => left.rank - right.rank).map((candidate) => candidate.id),
    );
    expect(weightsDiffer(baseline.metricWeights, baseline)).toBe(false);
  });

  it("matches a Python rerun with different metric and category importance, including a metric demoted to informational", () => {
    const rerun = deriveBaseline(reweighted);
    const altered = rerun.metricWeights;
    const alteredCategories = rerun.categoryWeights;
    expect(altered).not.toEqual(baseline.metricWeights);
    expect(alteredCategories).toEqual({ essentials: 3, environment: 5, amenities: 4 });
    expect(weightsDiffer(altered, baseline, alteredCategories)).toBe(true);
    for (const candidate of demo.candidates) {
      const expected = reweighted.candidates.find((item) => item.id === candidate.id)!;
      const preview = scoreWhatIf(candidate, altered, baseline, alteredCategories);
      expect(preview.overallScore).toBeCloseTo(expected.overall_score, 2);
      expect(preview.confidence).toBeCloseTo(expected.confidence, 2);
      expect(preview.categories.map((category) => [category.category, category.score, category.weight, category.overallContribution]))
        .toEqual(expected.categories.map((category) => [category.category, category.score, category.weight, category.overall_contribution]));
    }
    const ordered = orderWhatIf(demo.candidates.map((candidate) => scoreWhatIf(candidate, altered, baseline, alteredCategories)));
    expect(ordered.map((score) => score.id)).toEqual(
      [...reweighted.candidates].sort((left, right) => left.rank - right.rank).map((candidate) => candidate.id),
    );
  });

  it("treats a changed category weight alone as an active what-if", () => {
    expect(weightsDiffer(baseline.metricWeights, baseline, baseline.categoryWeights)).toBe(false);
    expect(weightsDiffer({}, baseline, { amenities: baseline.categoryWeights.amenities + 1 })).toBe(true);
    const preview = scoreWhatIf(demo.candidates[0], {}, baseline, { amenities: 0 });
    expect(preview.categories.map((category) => category.category)).toEqual(["environment", "essentials"]);
    expect(preview.unmeasuredCategories).toEqual([]);
    expect(preview.coveragePercent).toBe(100);
  });

  it("reports no evidence weight rather than full confidence when every weight is zero", () => {
    const none = Object.fromEntries(baseline.metrics.map((metric) => [metric, 0]));
    const preview = scoreWhatIf(demo.candidates[0], none, baseline);
    expect(preview.evidenceWeight).toBe(0);
    expect(preview.overallScore).toBe(0);
    expect(preview.categories).toEqual([]);
    const zeroCategories = Object.fromEntries(baseline.categories.map((category) => [category, 0]));
    expect(scoreWhatIf(demo.candidates[0], baseline.metricWeights, baseline, zeroCategories).evidenceWeight).toBe(0);
    expect(scoreWhatIf(demo.candidates[0], baseline.metricWeights, baseline).evidenceWeight).toBeGreaterThan(0);
  });

  it("never edits the authoritative bundle and clamps weights to 0–5", () => {
    const before = JSON.stringify(demo);
    const wild = Object.fromEntries(baseline.metrics.map((metric) => [metric, 99]));
    const preview = scoreWhatIf(demo.candidates[0], wild, baseline);
    expect(JSON.stringify(demo)).toBe(before);
    const equalWeights = Object.fromEntries(baseline.metrics.map((metric) => [metric, 5]));
    expect(preview.overallScore).toBe(scoreWhatIf(demo.candidates[0], equalWeights, baseline).overallScore);
  });

  it("turns a single-metric preference into that metric's normalized score", () => {
    const only = Object.fromEntries(baseline.metrics.map((metric) => [metric, metric === "cafes" ? 5 : 0]));
    for (const candidate of demo.candidates) {
      const cafes = candidate.categories.flatMap((category) => category.metrics).find((metric) => metric.metric === "cafes")!;
      const preview = scoreWhatIf(candidate, only, baseline);
      expect(preview.overallScore).toBeCloseTo(cafes.normalized_score, 2);
      expect(preview.categories).toHaveLength(1);
      expect(preview.confidence).toBeCloseTo(cafes.confidence * 100, 2);
      expect(preview.unmeasuredCategories).toEqual([]);
      expect(preview.coveragePercent).toBe(100);
    }
  });

  it("keeps a weighted category visible as unmeasured instead of renormalising it away", () => {
    const stripped = structuredClone(demo);
    const candidate = stripped.candidates[0];
    candidate.categories = candidate.categories.filter((category) => category.category !== "essentials");
    const preview = scoreWhatIf(candidate, baseline.metricWeights, baseline);
    expect(preview.unmeasuredCategories).toEqual(["essentials"]);
    expect(preview.coveragePercent).toBe(50);
    expect(preview.categories.map((category) => category.category)).toEqual(["amenities", "environment"]);
    const withoutEssentials = Object.fromEntries(
      baseline.metrics.map((metric) => [metric, baseline.metricCategories[metric] === "essentials" ? 0 : baseline.metricWeights[metric]]),
    );
    expect(scoreWhatIf(candidate, withoutEssentials, baseline).unmeasuredCategories).toEqual([]);
  });

  it("orders unverified limits below passes and above breaches", () => {
    const scores = demo.candidates.map((candidate) => scoreWhatIf(candidate, baseline.metricWeights, baseline));
    const unverified = { ...scores[0], constraintStatus: "unknown" as const, overallScore: 99 };
    const breach = { ...scores[1], constraintStatus: "fail" as const, overallScore: 99 };
    const clear = { ...scores[2], constraintStatus: "pass" as const, overallScore: 1 };
    expect(orderWhatIf([breach, unverified, clear]).map((score) => score.constraintStatus)).toEqual(["pass", "unknown", "fail"]);
  });
});
