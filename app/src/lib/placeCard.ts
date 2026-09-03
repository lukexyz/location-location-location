import { label, rawValue } from "./format";
import type { CandidateResult, ConstraintStatus, MetricResult, PlacePhoto } from "../types";

/** A short fact for the place card: a label and a value, both already formatted. */
export interface CardFact {
  key: string;
  label: string;
  value: string;
}

export const STATUS_BADGE: Record<ConstraintStatus, string> = {
  pass: "Within limits",
  unknown: "Limit unverified",
  fail: "Outside limit",
};

/**
 * Where a bundle's photos live. The demo ships them under the site; a run served
 * by the local command exposes them beside its results; a file picked from disk
 * has no reachable folder, so it has no photos and the card shows a gradient.
 */
export function photoUrl(assetBase: string | undefined, photo: PlacePhoto | undefined): string | undefined {
  if (!assetBase || !photo) return undefined;
  return `${assetBase}${photo.file}`;
}

/** The folder a served result was fetched from, for resolving its photos. */
export function assetBaseFor(resultUrl: string): string {
  const cut = resultUrl.lastIndexOf("/");
  return cut === -1 ? "" : resultUrl.slice(0, cut + 1);
}

function allMetrics(candidate: CandidateResult): MetricResult[] {
  return [...candidate.categories.flatMap((category) => category.metrics), ...candidate.informational_metrics];
}

function poundsCompact(value: number): string {
  if (value >= 1_000_000) return `£${(value / 1_000_000).toFixed(value >= 10_000_000 ? 0 : 1)}m`;
  if (value >= 1_000) return `£${Math.round(value / 1_000)}k`;
  return `£${Math.round(value)}`;
}

/**
 * Up to three small details for the card, in a fixed order so the same kind of
 * fact sits in the same slot from place to place: the commute, then housing,
 * then the strongest everyday-life signal. Every value comes from the bundle;
 * nothing here is computed beyond formatting.
 */
export function cardFacts(candidate: CandidateResult): CardFact[] {
  const facts: CardFact[] = [];
  const commute = candidate.hard_constraints.results.find(
    (item) => item.metric === "door_to_door_commute" && item.actual !== null,
  );
  const commuteMetric = allMetrics(candidate).find((metric) => metric.metric === "door_to_door_commute");
  if (commute && commute.actual !== null) {
    facts.push({ key: "commute", label: commute.destination_label ?? "Commute", value: `${Math.round(commute.actual)} min` });
  } else if (commuteMetric) {
    facts.push({ key: "commute", label: "Commute", value: rawValue(commuteMetric.raw_value, commuteMetric.unit) });
  }
  const housing = candidate.housing_summary;
  if (housing) {
    const period = housing.budget_period === "month" ? " pcm" : "";
    facts.push({
      key: "housing",
      label: housing.mode === "rent" ? "Typical rent" : "Typical price",
      value: `${poundsCompact(housing.typical_cost_gbp)}${period}`,
    });
  }
  // The strongest everyday signal, preferring something that is there over something that is absent:
  // "4 cafés in 15 min" is a highlight, "0 betting shops" is a relief but not a postcard.
  const everyday = allMetrics(candidate)
    .filter((metric) => metric.active && !["door_to_door_commute", "housing_affordability"].includes(metric.metric))
    .sort((left, right) =>
      Number(right.raw_value > 0) - Number(left.raw_value > 0)
      || right.normalized_score - left.normalized_score
      || left.metric.localeCompare(right.metric));
  for (const metric of everyday) {
    if (facts.length >= 3) break;
    facts.push({ key: metric.metric, label: label(metric.metric), value: rawValue(metric.raw_value, metric.unit) });
  }
  return facts.slice(0, 3);
}
