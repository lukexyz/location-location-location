import type { ResearchResult } from "../types";

const MAX_CANDIDATES = 1_000;

export class ResultValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResultValidationError";
  }
}

export function parseResultBundle(input: unknown): ResearchResult {
  const result = record(input, "result bundle");
  if (result.schema_version !== "1") {
    throw new ResultValidationError(
      `Incompatible schema ${String(result.schema_version)}. This viewer requires schema 1.`,
    );
  }
  string(result.scoring_version, "scoring_version");
  string(result.run_id, "run_id");
  string(result.generated_at, "generated_at");
  if (result.unknown_data_policy !== "warn") {
    throw new ResultValidationError("unknown_data_policy must be warn");
  }
  const candidates = array(result.candidates, "candidates");
  if (candidates.length === 0) {
    throw new ResultValidationError("The bundle contains no candidates.");
  }
  if (candidates.length > MAX_CANDIDATES) {
    throw new ResultValidationError(`The bundle exceeds the ${MAX_CANDIDATES}-candidate limit.`);
  }

  const ids = new Set<string>();
  for (const [index, value] of candidates.entries()) {
    validateCandidate(value, index, ids);
  }
  return input as ResearchResult;
}

function validateCandidate(value: unknown, index: number, ids: Set<string>): void {
  const path = `candidates[${index}]`;
  const candidate = record(value, path);
  const id = string(candidate.id, `${path}.id`);
  if (ids.has(id)) throw new ResultValidationError(`Duplicate candidate id: ${id}`);
  ids.add(id);
  string(candidate.name, `${path}.name`);
  finite(candidate.rank, `${path}.rank`);
  range(candidate.overall_score, `${path}.overall_score`, 0, 100);
  range(candidate.confidence, `${path}.confidence`, 0, 100);
  const location = record(candidate.location, `${path}.location`);
  range(location.latitude, `${path}.location.latitude`, -90, 90);
  range(location.longitude, `${path}.location.longitude`, -180, 180);

  const constraints = record(candidate.hard_constraints, `${path}.hard_constraints`);
  boolean(constraints.passed, `${path}.hard_constraints.passed`);
  array(constraints.results, `${path}.hard_constraints.results`).forEach((item, itemIndex) => {
    const constraint = record(item, `${path}.hard_constraints.results[${itemIndex}]`);
    string(constraint.metric, `${path}.constraint.metric`);
    boolean(constraint.passed, `${path}.constraint.passed`);
  });

  array(candidate.categories, `${path}.categories`).forEach((item, categoryIndex) => {
    const category = record(item, `${path}.categories[${categoryIndex}]`);
    string(category.category, `${path}.category.name`);
    range(category.score, `${path}.category.score`, 0, 100);
    finite(category.weight, `${path}.category.weight`);
    array(category.metrics, `${path}.category.metrics`).forEach((metric, metricIndex) =>
      validateMetric(metric, `${path}.categories[${categoryIndex}].metrics[${metricIndex}]`),
    );
  });
  array(candidate.informational_metrics, `${path}.informational_metrics`).forEach(
    (metric, metricIndex) => validateMetric(metric, `${path}.informational_metrics[${metricIndex}]`),
  );
  if (candidate.rail_summary !== undefined) {
    validateRailSummary(candidate.rail_summary, `${path}.rail_summary`, id);
  }
  if (candidate.housing_summary !== undefined) {
    validateHousingSummary(candidate.housing_summary, `${path}.housing_summary`, id);
  }
  stringArray(candidate.missing_metrics, `${path}.missing_metrics`);
  stringArray(candidate.warnings, `${path}.warnings`);
}

function validateHousingSummary(value: unknown, path: string, candidateId: string): void {
  const summary = record(value, path);
  const mode = string(summary.mode, `${path}.mode`);
  if (mode !== "buy" && mode !== "rent") {
    throw new ResultValidationError(`${path}.mode must be buy or rent`);
  }
  const budget = range(summary.budget_gbp, `${path}.budget_gbp`, Number.EPSILON, Infinity);
  const period = string(summary.budget_period, `${path}.budget_period`);
  if (period !== (mode === "buy" ? "purchase" : "month")) {
    throw new ResultValidationError(`${path}.budget_period does not match mode`);
  }
  string(summary.property_type, `${path}.property_type`);
  if (summary.bedrooms !== null) integer(summary.bedrooms, `${path}.bedrooms`, 0);
  const typical = range(summary.typical_cost_gbp, `${path}.typical_cost_gbp`, Number.EPSILON, Infinity);
  const ratio = range(summary.budget_ratio, `${path}.budget_ratio`, Number.EPSILON, Infinity);
  if (Math.abs(ratio - typical / budget) > 0.000001) {
    throw new ResultValidationError(`${path}.budget_ratio is inconsistent`);
  }
  if (summary.inventory_status !== "not_checked") {
    throw new ResultValidationError(`${path}.inventory_status must be not_checked`);
  }

  const market = record(summary.market, `${path}.market`);
  string(market.id, `${path}.market.id`);
  if (string(market.candidate_id, `${path}.market.candidate_id`) !== candidateId) {
    throw new ResultValidationError(`${path}.market references another candidate`);
  }
  if (finite(market.typical_cost_gbp, `${path}.market.typical_cost_gbp`) !== typical) {
    throw new ResultValidationError(`${path}.market typical cost is inconsistent`);
  }
  const statistic = string(market.statistic, `${path}.market.statistic`);
  if (statistic !== "median" && statistic !== "mean") {
    throw new ResultValidationError(`${path}.market.statistic must be median or mean`);
  }
  const geography = record(market.geography, `${path}.market.geography`);
  const geographyKind = string(geography.kind, `${path}.market.geography.kind`);
  string(geography.label, `${path}.market.geography.label`);
  if (mode === "buy") {
    if (geographyKind !== "radius") {
      throw new ResultValidationError(`${path}.market purchase geography must be a radius`);
    }
    range(geography.radius_km, `${path}.market.geography.radius_km`, Number.EPSILON, 5);
  } else {
    if (!["local_authority", "broad_rental_market_area", "region"].includes(geographyKind)) {
      throw new ResultValidationError(`${path}.market rent geography is invalid`);
    }
    if (geography.radius_km !== null) {
      throw new ResultValidationError(`${path}.market rent geography cannot use a radius`);
    }
  }
  string(market.period_start, `${path}.market.period_start`);
  string(market.period_end, `${path}.market.period_end`);
  if (market.sample_size !== null) integer(market.sample_size, `${path}.market.sample_size`, 1);
  if (mode === "buy" && market.sample_size === null) {
    throw new ResultValidationError(`${path}.market purchase sample cannot be unknown`);
  }
  if (market.listing_search_url !== null) url(market.listing_search_url, `${path}.market.listing_search_url`);
  range(market.confidence, `${path}.market.confidence`, 0, 1);
  string(market.confidence_notes, `${path}.market.confidence_notes`);
  const sources = array(market.sources, `${path}.market.sources`);
  if (sources.length === 0) throw new ResultValidationError(`${path}.market.sources cannot be empty`);
  const sourceKinds = new Set<string>();
  sources.forEach((value, index) => {
    const sourcePath = `${path}.market.sources[${index}]`;
    const source = record(value, sourcePath);
    const kind = string(source.kind, `${sourcePath}.kind`);
    if (sourceKinds.has(kind)) throw new ResultValidationError(`${path}.market has duplicate source kinds`);
    sourceKinds.add(kind);
    ["label", "retrieved_at", "source_date", "licence"]
      .forEach((field) => string(source[field], `${sourcePath}.${field}`));
    url(source.url, `${sourcePath}.url`);
  });
  const requiredSource = mode === "buy" ? "transactions" : "rents";
  if (!sourceKinds.has(requiredSource)) {
    throw new ResultValidationError(`${path}.market requires a ${requiredSource} source`);
  }
}

function validateRailSummary(value: unknown, path: string, candidateId: string): void {
  const summary = record(value, path);
  const primaryId = string(summary.primary_journey_id, `${path}.primary_journey_id`);
  const fastest = range(summary.fastest_total_minutes, `${path}.fastest_total_minutes`, 0, Infinity);
  const journeys = array(summary.journeys, `${path}.journeys`);
  if (journeys.length === 0) throw new ResultValidationError(`${path}.journeys cannot be empty`);
  const ids = new Set<string>();
  let primaryCount = 0;
  let actualFastest = Infinity;
  journeys.forEach((value, index) => {
    const journeyPath = `${path}.journeys[${index}]`;
    const journey = record(value, journeyPath);
    const journeyId = string(journey.id, `${journeyPath}.id`);
    if (ids.has(journeyId)) throw new ResultValidationError(`Duplicate rail journey id: ${journeyId}`);
    ids.add(journeyId);
    if (string(journey.candidate_id, `${journeyPath}.candidate_id`) !== candidateId) {
      throw new ResultValidationError(`${journeyPath} references another candidate`);
    }
    ["destination_label", "origin_station", "origin_station_crs", "london_arrival_station", "service_window", "confidence_notes"]
      .forEach((field) => string(journey[field], `${journeyPath}.${field}`));
    const primary = boolean(journey.primary, `${journeyPath}.primary`);
    primaryCount += primary ? 1 : 0;
    const components = ["access_minutes", "expected_wait_minutes", "scheduled_rail_minutes", "london_last_mile_minutes"]
      .map((field) => range(journey[field], `${journeyPath}.${field}`, 0, Infinity));
    const total = range(journey.total_minutes, `${journeyPath}.total_minutes`, 0, Infinity);
    if (Math.abs(components.reduce((sum, item) => sum + item, 0) - total) > 0.01) {
      throw new ResultValidationError(`${journeyPath} component times do not equal total_minutes`);
    }
    actualFastest = Math.min(actualFastest, total);
    integer(journey.changes, `${journeyPath}.changes`, 0);
    range(journey.services_per_hour, `${journeyPath}.services_per_hour`, 0, Infinity);
    nullableString(journey.last_useful_departure, `${journeyPath}.last_useful_departure`);
    nullableRange(journey.punctuality_percent, `${journeyPath}.punctuality_percent`, 0, 100);
    nullableRange(journey.cancellation_percent, `${journeyPath}.cancellation_percent`, 0, 100);
    range(journey.confidence, `${journeyPath}.confidence`, 0, 1);
    const sources = array(journey.sources, `${journeyPath}.sources`);
    if (sources.length === 0) throw new ResultValidationError(`${journeyPath}.sources cannot be empty`);
    sources.forEach((value, sourceIndex) => {
      const sourcePath = `${journeyPath}.sources[${sourceIndex}]`;
      const source = record(value, sourcePath);
      ["kind", "label", "retrieved_at", "source_date", "licence"]
        .forEach((field) => string(source[field], `${sourcePath}.${field}`));
      url(source.url, `${sourcePath}.url`);
    });
  });
  if (primaryCount !== 1 || !ids.has(primaryId)) {
    throw new ResultValidationError(`${path} must identify exactly one primary journey`);
  }
  if (Math.abs(fastest - actualFastest) > 0.01) {
    throw new ResultValidationError(`${path}.fastest_total_minutes is inconsistent`);
  }
}

function validateMetric(value: unknown, path: string): void {
  const metric = record(value, path);
  string(metric.metric, `${path}.metric`);
  string(metric.category, `${path}.category`);
  finite(metric.raw_value, `${path}.raw_value`);
  string(metric.unit, `${path}.unit`);
  range(metric.normalized_score, `${path}.normalized_score`, 0, 100);
  finite(metric.weight, `${path}.weight`);
  boolean(metric.active, `${path}.active`);
  range(metric.confidence, `${path}.confidence`, 0, 1);
  string(metric.evidence_id, `${path}.evidence_id`);
  string(metric.source, `${path}.source`);
  url(metric.source_url, `${path}.source_url`);
  string(metric.source_date, `${path}.source_date`);
  string(metric.confidence_notes, `${path}.confidence_notes`);
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ResultValidationError(`${path} must be an object`);
  }
  return value as Record<string, unknown>;
}

function array(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new ResultValidationError(`${path} must be an array`);
  return value;
}

function string(value: unknown, path: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new ResultValidationError(`${path} must be a non-empty string`);
  }
  return value;
}

function url(value: unknown, path: string): string {
  const text = string(value, path);
  try {
    const parsed = new URL(text);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") throw new Error();
  } catch {
    throw new ResultValidationError(`${path} must be an HTTP URL`);
  }
  return text;
}

function boolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") throw new ResultValidationError(`${path} must be boolean`);
  return value;
}

function finite(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ResultValidationError(`${path} must be a finite number`);
  }
  return value;
}

function range(value: unknown, path: string, minimum: number, maximum: number): number {
  const number = finite(value, path);
  if (number < minimum || number > maximum) {
    throw new ResultValidationError(`${path} must be between ${minimum} and ${maximum}`);
  }
  return number;
}

function integer(value: unknown, path: string, minimum: number): number {
  const number = finite(value, path);
  if (!Number.isInteger(number) || number < minimum) {
    throw new ResultValidationError(`${path} must be an integer of at least ${minimum}`);
  }
  return number;
}

function nullableString(value: unknown, path: string): void {
  if (value !== null) string(value, path);
}

function nullableRange(value: unknown, path: string, minimum: number, maximum: number): void {
  if (value !== null) range(value, path, minimum, maximum);
}

function stringArray(value: unknown, path: string): void {
  array(value, path).forEach((item, index) => string(item, `${path}[${index}]`));
}
