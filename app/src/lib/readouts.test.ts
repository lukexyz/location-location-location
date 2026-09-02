import demoData from "../data/demo-results.json";
import type { CandidateResult, MetricResult } from "../types";
import { parseResultBundle } from "./validateResult";
import { deriveReadouts } from "./readouts";

function metric(key: string, rawValue: number, category = "amenities"): MetricResult {
  return {
    metric: key, category, raw_value: rawValue, unit: "count_15_min_walk",
    normalized_score: 50, weight: 2, active: true, confidence: 0.7,
    evidence_id: `${key}-evidence`, source: "test", source_url: "https://example.test/",
    source_date: "2026-08-01", confidence_notes: `${key} note`, category_contribution: 1,
    basis: "synthetic",
  };
}

function candidate(overrides: Partial<CandidateResult> = {}): CandidateResult {
  return {
    id: "place", name: "Place", location: { latitude: 51.5, longitude: -0.1 }, rank: 1,
    overall_score: 70, confidence: 80, hard_constraints: { status: "pass", results: [] },
    unmeasured_categories: [], score_coverage_percent: 100,
    categories: [{
      category: "amenities", score: 50, weight: 2, overall_contribution: 10,
      metrics: [metric("cafes", 4), metric("betting_shops", 0)],
    }],
    informational_metrics: [], missing_metrics: [], warnings: [],
    ...overrides,
  };
}

describe("playful readouts", () => {
  it("derives six readouts for every demo candidate without touching the result", () => {
    const result = parseResultBundle(demoData);
    for (const item of result.candidates) {
      const before = JSON.stringify(item);
      const readouts = deriveReadouts(item);
      expect(readouts.map((readout) => readout.key)).toEqual([
        "sourdough_to_slots", "emergency_croissant_radius", "green_escape",
        "last_train_home", "rail_roulette", "pavement_pride",
      ]);
      expect(JSON.stringify(item)).toBe(before);
      expect(item.overall_score).toBe(JSON.parse(before).overall_score);
    }
  });

  it("presents a café-only place as all sourdough", () => {
    const [sourdough, croissant] = deriveReadouts(candidate());
    expect(sourdough.value).toBe("All sourdough");
    expect(sourdough.detail).toBe("4 cafés to 0 betting shops within a 15-minute walk.");
    expect(croissant.value).toBe("4 cafés in 15 min");
  });

  it("expresses a mixed street as a ratio and a café desert honestly", () => {
    const mixed = candidate({
      categories: [{
        category: "amenities", score: 50, weight: 2, overall_contribution: 10,
        metrics: [metric("cafes", 3), metric("betting_shops", 2)],
      }],
    });
    expect(deriveReadouts(mixed)[0].value).toBe("1.5 : 1");
    const desert = candidate({
      categories: [{
        category: "amenities", score: 50, weight: 2, overall_contribution: 10,
        metrics: [metric("cafes", 0), metric("betting_shops", 0)],
      }],
    });
    expect(deriveReadouts(desert)[0].value).toBe("Neither");
    expect(deriveReadouts(desert)[1].value).toBe("Beyond 15 min");
  });

  it("reports no evidence instead of inventing rail, green, or street facts", () => {
    const readouts = deriveReadouts(candidate({ categories: [] }));
    for (const readout of readouts) {
      expect(readout.available).toBe(false);
      expect(readout.value).toBe("no evidence");
    }
  });

  it("keeps an unpublished last train explicit even when a journey exists", () => {
    const result = parseResultBundle(demoData);
    const withRail = result.candidates.find((item) => item.rail_summary);
    expect(withRail).toBeDefined();
    const journey = withRail!.rail_summary!.journeys[0];
    const modified: CandidateResult = {
      ...withRail!,
      rail_summary: {
        ...withRail!.rail_summary!,
        journeys: [{ ...journey, last_useful_departure: null, punctuality_percent: null }],
      },
    };
    const readouts = deriveReadouts(modified);
    expect(readouts[3].available).toBe(false);
    expect(readouts[3].detail).toMatch(/not published/);
    expect(readouts[4].detail).toBe("Reliability not published.");
  });
});
