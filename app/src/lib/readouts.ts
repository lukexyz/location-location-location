import { catchmentPhrase, catchmentShort } from "./format";
import type { CandidateResult, MetricResult, RailJourney } from "../types";

/**
 * Playful readouts are alternate presentations of evidence the result already
 * carries. They never compute a score, never feed one, and say "no evidence"
 * rather than inventing a value.
 */
export interface Readout {
  key: string;
  title: string;
  value: string;
  detail: string;
  available: boolean;
}

const NO_EVIDENCE = "no evidence";

export function deriveReadouts(candidate: CandidateResult): Readout[] {
  return [
    sourdoughToSlots(candidate),
    emergencyCroissantRadius(candidate),
    greenEscape(candidate),
    lastTrainHome(candidate),
    railRoulette(candidate),
    pavementPride(candidate),
  ];
}

export function findMetric(candidate: CandidateResult, key: string): MetricResult | undefined {
  for (const category of candidate.categories) {
    const metric = category.metrics.find((item) => item.metric === key);
    if (metric) return metric;
  }
  return candidate.informational_metrics.find((item) => item.metric === key);
}

function primaryJourney(candidate: CandidateResult): RailJourney | undefined {
  const summary = candidate.rail_summary;
  if (!summary) return undefined;
  return summary.journeys.find((journey) => journey.id === summary.primary_journey_id)
    ?? summary.journeys[0];
}

function unavailable(key: string, title: string, detail: string): Readout {
  return { key, title, value: NO_EVIDENCE, detail, available: false };
}

function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

function sourdoughToSlots(candidate: CandidateResult): Readout {
  const cafes = findMetric(candidate, "cafes");
  const betting = findMetric(candidate, "betting_shops");
  const title = "Sourdough-to-Slots";
  if (!cafes || !betting) {
    return unavailable("sourdough_to_slots", title, "Needs both café and betting-shop counts.");
  }
  const detail = `${plural(cafes.raw_value, "café")} to ${plural(betting.raw_value, "betting shop")} within ${catchmentPhrase(cafes.unit)}.`;
  if (betting.raw_value === 0) {
    return {
      key: "sourdough_to_slots", title, available: true, detail,
      value: cafes.raw_value > 0 ? "All sourdough" : "Neither",
    };
  }
  const ratio = cafes.raw_value / betting.raw_value;
  return {
    key: "sourdough_to_slots", title, available: true, detail,
    value: `${ratio.toFixed(1)} : 1`,
  };
}

function emergencyCroissantRadius(candidate: CandidateResult): Readout {
  const cafes = findMetric(candidate, "cafes");
  const title = "Emergency Croissant Radius";
  if (!cafes) return unavailable("emergency_croissant_radius", title, "No café count was researched.");
  return {
    key: "emergency_croissant_radius", title, available: true,
    value: cafes.raw_value === 0
      ? `Beyond ${catchmentShort(cafes.unit)}`
      : `${plural(cafes.raw_value, "café")} in ${catchmentShort(cafes.unit)}`,
    detail: cafes.confidence_notes,
  };
}

function greenEscape(candidate: CandidateResult): Readout {
  const green = findMetric(candidate, "green_space");
  const title = "Green Escape";
  // Absence of the metric means it was not measured, not that no green space exists.
  if (!green) return unavailable("green_escape", title, "No green-space evidence in this run.");
  return {
    key: "green_escape", title, available: true,
    value: `${green.raw_value} min walk`,
    detail: green.confidence_notes,
  };
}

function lastTrainHome(candidate: CandidateResult): Readout {
  const journey = primaryJourney(candidate);
  const title = "Last Train Home";
  if (!journey) return unavailable("last_train_home", title, "No cited rail journey for this place.");
  if (journey.last_useful_departure === null) {
    return unavailable("last_train_home", title, `Final service from ${journey.london_arrival_station} not published in the cited sources.`);
  }
  return {
    key: "last_train_home", title, available: true,
    value: journey.last_useful_departure.slice(11, 16),
    detail: `Last useful departure from ${journey.london_arrival_station} to ${journey.origin_station}.`,
  };
}

function railRoulette(candidate: CandidateResult): Readout {
  const journey = primaryJourney(candidate);
  const title = "Rail Roulette";
  if (!journey) return unavailable("rail_roulette", title, "No cited rail journey for this place.");
  const reliability = journey.punctuality_percent === null || journey.cancellation_percent === null
    ? "Reliability not published."
    : `${journey.punctuality_percent.toFixed(1)}% on time, ${journey.cancellation_percent.toFixed(1)}% cancelled.`;
  return {
    key: "rail_roulette", title, available: true,
    value: `${journey.services_per_hour}/hr · ${plural(journey.changes, "change")}`,
    detail: reliability,
  };
}

function pavementPride(candidate: CandidateResult): Readout {
  const title = "Pavement Pride";
  const summary = candidate.street_care_summary;
  if (summary) {
    return {
      key: "pavement_pride", title, available: true,
      value: `${summary.score.toFixed(0)} / 100`,
      detail: summary.basis === "recent_visit_audit"
        ? "Based on a recent personal visit audit."
        : "Cautious proxy from fly-tipping and report evidence.",
    };
  }
  const metric = findMetric(candidate, "street_care");
  if (!metric) return unavailable("pavement_pride", title, "No street-care evidence was researched.");
  return {
    key: "pavement_pride", title, available: true,
    value: `${metric.raw_value} / 100`,
    detail: metric.confidence_notes,
  };
}
