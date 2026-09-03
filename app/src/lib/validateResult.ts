import type { ResearchResult } from "../types";

export const MAX_CANDIDATES = 1_000;
const SUPPORTED_SCHEMA = "2";
const CONSTRAINT_STATUSES = ["pass", "fail", "unknown"] as const;
const EVIDENCE_BASES = ["measured", "transformed", "agent_inferred", "user_observed", "synthetic"] as const;
const INFERRED_CONFIDENCE_CAP = 0.5;

export class ResultValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResultValidationError";
  }
}

export function parseResultBundle(input: unknown): ResearchResult {
  const result = record(input, "result bundle");
  exactKeys(
    result,
    ["schema_version", "scoring_version", "run_id", "generated_at", "unknown_data_policy", "route_boundary", "candidates"],
    "result bundle",
  );
  if (result.schema_version !== SUPPORTED_SCHEMA) {
    throw new ResultValidationError(
      `Incompatible schema ${String(result.schema_version)}. This viewer requires schema ${SUPPORTED_SCHEMA}; rerun the research command to regenerate the bundle.`,
    );
  }
  string(result.scoring_version, "scoring_version");
  string(result.run_id, "run_id");
  dateTime(result.generated_at, "generated_at");
  if (result.unknown_data_policy !== "warn") {
    throw new ResultValidationError("unknown_data_policy must be warn");
  }
  if (result.route_boundary !== undefined) {
    validateRouteBoundary(result.route_boundary, "route_boundary");
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
  exactKeys(
    candidate,
    [
      "id", "name", "place_kind", "location", "rank", "overall_score", "confidence",
      "hard_constraints", "categories", "unmeasured_categories", "score_coverage_percent",
      "informational_metrics", "rail_summary", "housing_summary", "street_care_summary",
      "photo", "missing_metrics", "warnings",
    ],
    path,
  );
  const id = string(candidate.id, `${path}.id`);
  if (ids.has(id)) throw new ResultValidationError(`Duplicate candidate id: ${id}`);
  ids.add(id);
  string(candidate.name, `${path}.name`);
  if (candidate.place_kind !== undefined) {
    oneOf(
      candidate.place_kind,
      ["city", "town", "suburb", "village", "neighbourhood"],
      `${path}.place_kind`,
    );
  }
  integer(candidate.rank, `${path}.rank`, 1);
  range(candidate.overall_score, `${path}.overall_score`, 0, 100);
  range(candidate.confidence, `${path}.confidence`, 0, 100);
  const location = record(candidate.location, `${path}.location`);
  range(location.latitude, `${path}.location.latitude`, -90, 90);
  range(location.longitude, `${path}.location.longitude`, -180, 180);

  const constraints = record(candidate.hard_constraints, `${path}.hard_constraints`);
  exactKeys(constraints, ["status", "results"], `${path}.hard_constraints`);
  const declaredStatus = oneOf(constraints.status, CONSTRAINT_STATUSES, `${path}.hard_constraints.status`);
  const statuses = new Set<string>();
  array(constraints.results, `${path}.hard_constraints.results`).forEach((item, itemIndex) => {
    const constraint = record(item, `${path}.hard_constraints.results[${itemIndex}]`);
    exactKeys(
      constraint,
      ["metric", "destination_label", "operator", "value", "actual", "status", "warning"],
      `${path}.hard_constraints.results[${itemIndex}]`,
    );
    string(constraint.metric, `${path}.constraint.metric`);
    if (constraint.destination_label !== undefined) {
      string(constraint.destination_label, `${path}.constraint.destination_label`);
    }
    oneOf(constraint.operator, ["<=", ">="], `${path}.constraint.operator`);
    finite(constraint.value, `${path}.constraint.value`);
    if (constraint.actual !== null) finite(constraint.actual, `${path}.constraint.actual`);
    const status = oneOf(constraint.status, CONSTRAINT_STATUSES, `${path}.constraint.status`);
    if ((constraint.actual === null) !== (status === "unknown")) {
      throw new ResultValidationError(`${path}.constraint status does not match its evidence`);
    }
    statuses.add(status);
    if (constraint.warning !== undefined) string(constraint.warning, `${path}.constraint.warning`);
  });
  const expectedStatus = statuses.has("fail") ? "fail" : statuses.has("unknown") ? "unknown" : "pass";
  if (declaredStatus !== expectedStatus) {
    throw new ResultValidationError(`${path}.hard_constraints.status does not match its results`);
  }

  array(candidate.categories, `${path}.categories`).forEach((item, categoryIndex) => {
    const category = record(item, `${path}.categories[${categoryIndex}]`);
    exactKeys(
      category,
      ["category", "score", "weight", "overall_contribution", "metrics"],
      `${path}.categories[${categoryIndex}]`,
    );
    string(category.category, `${path}.category.name`);
    range(category.score, `${path}.category.score`, 0, 100);
    range(category.weight, `${path}.category.weight`, 0, 5);
    range(category.overall_contribution, `${path}.category.overall_contribution`, 0, 100);
    array(category.metrics, `${path}.category.metrics`).forEach((metric, metricIndex) =>
      validateMetric(metric, `${path}.categories[${categoryIndex}].metrics[${metricIndex}]`),
    );
  });
  const measured = new Set<string>();
  for (const item of candidate.categories as Array<{ category: string }>) measured.add(item.category);
  array(candidate.unmeasured_categories, `${path}.unmeasured_categories`).forEach((item, itemIndex) => {
    const unmeasured = record(item, `${path}.unmeasured_categories[${itemIndex}]`);
    exactKeys(unmeasured, ["category", "weight"], `${path}.unmeasured_categories[${itemIndex}]`);
    const name = string(unmeasured.category, `${path}.unmeasured_categories.category`);
    if (measured.has(name)) {
      throw new ResultValidationError(`${path}.unmeasured_categories lists a measured category`);
    }
    range(unmeasured.weight, `${path}.unmeasured_categories.weight`, Number.EPSILON, 5);
  });
  range(candidate.score_coverage_percent, `${path}.score_coverage_percent`, 0, 100);
  array(candidate.informational_metrics, `${path}.informational_metrics`).forEach(
    (metric, metricIndex) => validateMetric(metric, `${path}.informational_metrics[${metricIndex}]`),
  );
  if (candidate.rail_summary !== undefined) {
    validateRailSummary(candidate.rail_summary, `${path}.rail_summary`, id);
  }
  if (candidate.housing_summary !== undefined) {
    validateHousingSummary(candidate.housing_summary, `${path}.housing_summary`, id);
  }
  if (candidate.street_care_summary !== undefined) {
    validateStreetCareSummary(candidate.street_care_summary, `${path}.street_care_summary`, id);
  }
  if (candidate.photo !== undefined) {
    validatePhoto(candidate.photo, `${path}.photo`, id);
  }
  stringArray(candidate.missing_metrics, `${path}.missing_metrics`);
  stringArray(candidate.warnings, `${path}.warnings`);
}

const PHOTO_FILE = /^photos\/[a-z0-9][a-z0-9-]{0,79}\.(jpg|png)$/;

function validatePhoto(value: unknown, path: string, candidateId: string): void {
  const photo = record(value, path);
  exactKeys(photo, ["candidate_id", "file", "width", "height", "title", "author", "licence", "licence_url", "source_url", "page_title"], path);
  if (string(photo.candidate_id, `${path}.candidate_id`) !== candidateId) {
    throw new ResultValidationError(`${path}.candidate_id does not match its candidate`);
  }
  if (!PHOTO_FILE.test(string(photo.file, `${path}.file`))) {
    throw new ResultValidationError(`${path}.file must be photos/<slug>.jpg or .png`);
  }
  integer(photo.width, `${path}.width`, 1);
  integer(photo.height, `${path}.height`, 1);
  string(photo.title, `${path}.title`);
  string(photo.author, `${path}.author`);
  string(photo.licence, `${path}.licence`);
  if (photo.licence_url !== null) url(photo.licence_url, `${path}.licence_url`);
  url(photo.source_url, `${path}.source_url`);
  string(photo.page_title, `${path}.page_title`);
}

function validateStreetCareSummary(value: unknown, path: string, candidateId: string): void {
  const summary = record(value, path);
  const assessmentDate = dateValue(summary.assessment_date, `${path}.assessment_date`);
  const score = range(summary.score, `${path}.score`, 0, 100);
  const basis = string(summary.basis, `${path}.basis`);
  if (basis !== "proxy" && basis !== "recent_visit_audit") {
    throw new ResultValidationError(`${path}.basis is invalid`);
  }
  range(summary.confidence, `${path}.confidence`, 0, 1);
  if (summary.audit_age_days !== null) integer(summary.audit_age_days, `${path}.audit_age_days`, 0);

  const components = array(summary.components, `${path}.components`);
  if (components.length < 2) throw new ResultValidationError(`${path}.components needs at least two items`);
  const componentKeys = new Set<string>();
  let totalWeight = 0;
  let weightedScore = 0;
  components.forEach((value, index) => {
    const componentPath = `${path}.components[${index}]`;
    const component = record(value, componentPath);
    const key = string(component.key, `${componentPath}.key`);
    if (componentKeys.has(key)) throw new ResultValidationError(`${path} has duplicate component keys`);
    componentKeys.add(key);
    if (component.raw_value !== null) finite(component.raw_value, `${componentPath}.raw_value`);
    string(component.unit, `${componentPath}.unit`);
    const normalized = component.normalized_score === null
      ? null
      : range(component.normalized_score, `${componentPath}.normalized_score`, 0, 100);
    const weight = range(component.weight, `${componentPath}.weight`, 0, 1);
    const included = boolean(component.included, `${componentPath}.included`);
    if (included) {
      if (normalized === null || weight === 0) {
        throw new ResultValidationError(`${componentPath} included components need score and weight`);
      }
      totalWeight += weight;
      weightedScore += normalized * weight;
    } else if (weight !== 0) {
      throw new ResultValidationError(`${componentPath} informational components must have zero weight`);
    }
  });
  if (Math.abs(totalWeight - 1) > 0.00001 || Math.abs(weightedScore - score) > 0.02) {
    throw new ResultValidationError(`${path} component weights do not reproduce its score`);
  }

  const place = record(summary.place, `${path}.place`);
  string(place.id, `${path}.place.id`);
  if (string(place.candidate_id, `${path}.place.candidate_id`) !== candidateId) {
    throw new ResultValidationError(`${path}.place references another candidate`);
  }
  string(place.local_authority, `${path}.place.local_authority`);
  evidenceBasis(place.basis, 0, `${path}.place.basis`);
  const fly = record(place.fly_tipping, `${path}.place.fly_tipping`);
  range(fly.current_incidents_per_1000, `${path}.place.fly_tipping.current_incidents_per_1000`, 0, Infinity);
  range(fly.previous_incidents_per_1000, `${path}.place.fly_tipping.previous_incidents_per_1000`, 0, Infinity);
  ["current_period", "previous_period", "reporting_basis"]
    .forEach((field) => string(fly[field], `${path}.place.fly_tipping.${field}`));
  validateStreetSource(fly.source, `${path}.place.fly_tipping.source`);

  if (place.local_reports !== null) {
    const reports = record(place.local_reports, `${path}.place.local_reports`);
    const scope = string(reports.scope_kind, `${path}.place.local_reports.scope_kind`);
    if (!["lsoa", "local_authority", "other_small_area"].includes(scope)) {
      throw new ResultValidationError(`${path}.place.local_reports.scope_kind is invalid`);
    }
    string(reports.geographic_scope, `${path}.place.local_reports.geographic_scope`);
    nullableRange(reports.reports_per_1000, `${path}.place.local_reports.reports_per_1000`, 0, Infinity);
    nullableRange(reports.unresolved_percent, `${path}.place.local_reports.unresolved_percent`, 0, 100);
    nullableRange(reports.median_resolution_days, `${path}.place.local_reports.median_resolution_days`, 0, Infinity);
    dateValue(reports.period_start, `${path}.place.local_reports.period_start`);
    dateValue(reports.period_end, `${path}.place.local_reports.period_end`);
    validateStreetSource(reports.source, `${path}.place.local_reports.source`);
  }

  let expectedAge: number | null = null;
  if (place.visit_audit !== null) {
    const audit = record(place.visit_audit, `${path}.place.visit_audit`);
    const auditedAt = dateValue(audit.audited_at, `${path}.place.visit_audit.audited_at`);
    expectedAge = Math.round((assessmentDate.valueOf() - auditedAt.valueOf()) / 86_400_000);
    if (expectedAge < 0) throw new ResultValidationError(`${path}.place.visit_audit is in the future`);
    string(audit.geographic_scope, `${path}.place.visit_audit.geographic_scope`);
    string(audit.notes, `${path}.place.visit_audit.notes`);
    const ratings = record(audit.ratings, `${path}.place.visit_audit.ratings`);
    ["litter", "dog_fouling", "graffiti", "weeds_and_detritus", "overflowing_bins", "overall_upkeep"]
      .forEach((field) => {
        const rating = integer(ratings[field], `${path}.place.visit_audit.ratings.${field}`, 0);
        if (rating > 4) throw new ResultValidationError(`${path}.place.visit_audit rating exceeds 4`);
      });
  }
  if (summary.audit_age_days !== expectedAge) {
    throw new ResultValidationError(`${path}.audit_age_days is inconsistent`);
  }
  const expectedBasis = expectedAge !== null && expectedAge <= 180 ? "recent_visit_audit" : "proxy";
  if (basis !== expectedBasis) {
    throw new ResultValidationError(`${path}.basis does not match audit recency`);
  }
}

function validateStreetSource(value: unknown, path: string): void {
  const source = record(value, path);
  ["label", "retrieved_at", "source_date", "licence"]
    .forEach((field) => string(source[field], `${path}.${field}`));
  url(source.url, `${path}.url`);
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
  const marketConfidence = range(market.confidence, `${path}.market.confidence`, 0, 1);
  evidenceBasis(market.basis, marketConfidence, `${path}.market.basis`);
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
    if (journey.operator !== undefined) string(journey.operator, `${journeyPath}.operator`);
    const journeyConfidence = range(journey.confidence, `${journeyPath}.confidence`, 0, 1);
    evidenceBasis(journey.basis, journeyConfidence, `${journeyPath}.basis`);
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
  exactKeys(
    metric,
    [
      "metric", "category", "raw_value", "unit", "normalized_score", "weight", "active",
      "confidence", "evidence_id", "source", "source_url", "source_date",
      "confidence_notes", "category_contribution", "basis",
    ],
    path,
  );
  string(metric.metric, `${path}.metric`);
  string(metric.category, `${path}.category`);
  finite(metric.raw_value, `${path}.raw_value`);
  string(metric.unit, `${path}.unit`);
  range(metric.normalized_score, `${path}.normalized_score`, 0, 100);
  range(metric.weight, `${path}.weight`, 0, 5);
  boolean(metric.active, `${path}.active`);
  range(metric.confidence, `${path}.confidence`, 0, 1);
  string(metric.evidence_id, `${path}.evidence_id`);
  string(metric.source, `${path}.source`);
  url(metric.source_url, `${path}.source_url`);
  string(metric.source_date, `${path}.source_date`);
  string(metric.confidence_notes, `${path}.confidence_notes`);
  range(metric.category_contribution, `${path}.category_contribution`, 0, 100);
  evidenceBasis(metric.basis, metric.confidence as number, `${path}.basis`);
}

function evidenceBasis(value: unknown, confidence: number, path: string): string {
  const text = oneOf(value, EVIDENCE_BASES, path);
  if (text === "agent_inferred" && confidence > INFERRED_CONFIDENCE_CAP) {
    throw new ResultValidationError(`${path} is agent-inferred but claims confidence above ${INFERRED_CONFIDENCE_CAP}`);
  }
  return text;
}

function validateRouteBoundary(value: unknown, path: string): void {
  const boundary = record(value, path);
  exactKeys(
    boundary,
    [
      "type", "description", "duration_minutes", "travel_profile", "provider",
      "departure_time", "traffic_treatment", "retrieved_at", "geometry_file", "geometry",
    ],
    path,
  );
  oneOf(boundary.type, ["isochrone", "distance_proxy", "fixture_polygon"], `${path}.type`);
  if (boundary.description !== undefined) string(boundary.description, `${path}.description`);
  if (boundary.duration_minutes !== undefined) {
    const minutes = integer(boundary.duration_minutes, `${path}.duration_minutes`, 1);
    if (minutes > 300) throw new ResultValidationError(`${path}.duration_minutes must be at most 300`);
  }
  if (boundary.travel_profile !== undefined) string(boundary.travel_profile, `${path}.travel_profile`);
  string(boundary.provider, `${path}.provider`);
  if (boundary.departure_time !== null) dateTime(boundary.departure_time, `${path}.departure_time`);
  string(boundary.traffic_treatment, `${path}.traffic_treatment`);
  dateTime(boundary.retrieved_at, `${path}.retrieved_at`);
  if (boundary.geometry_file !== undefined) string(boundary.geometry_file, `${path}.geometry_file`);
  validateBoundaryGeometry(boundary.geometry, `${path}.geometry`);
}

function validateBoundaryGeometry(value: unknown, path: string): void {
  const geometry = record(value, path);
  exactKeys(geometry, ["type", "coordinates"], path);
  const kind = oneOf(geometry.type, ["Polygon", "MultiPolygon"], `${path}.type`);
  const polygons = kind === "Polygon" ? [array(geometry.coordinates, `${path}.coordinates`)]
    : array(geometry.coordinates, `${path}.coordinates`);
  if (polygons.length === 0) throw new ResultValidationError(`${path} has no polygons`);
  polygons.forEach((polygonValue, polygonIndex) => {
    const polygon = array(polygonValue, `${path}.coordinates[${polygonIndex}]`);
    if (polygon.length === 0) throw new ResultValidationError(`${path} polygon has no rings`);
    polygon.forEach((ringValue, ringIndex) => {
      const ring = array(ringValue, `${path}.ring[${ringIndex}]`);
      if (ring.length < 4) throw new ResultValidationError(`${path} ring needs four positions`);
      ring.forEach((positionValue, positionIndex) => {
        const position = array(positionValue, `${path}.position[${positionIndex}]`);
        if (position.length < 2) throw new ResultValidationError(`${path} position needs two numbers`);
        range(position[0], `${path}.longitude`, -180, 180);
        range(position[1], `${path}.latitude`, -90, 90);
      });
    });
  });
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ResultValidationError(`${path} must be an object`);
  }
  return value as Record<string, unknown>;
}

function exactKeys(value: Record<string, unknown>, allowed: readonly string[], path: string): void {
  const extras = Object.keys(value).filter((key) => !allowed.includes(key));
  if (extras.length) {
    throw new ResultValidationError(`${path} contains unsupported fields: ${extras.join(", ")}`);
  }
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

function oneOf(value: unknown, choices: readonly string[], path: string): string {
  const text = string(value, path);
  if (!choices.includes(text)) {
    throw new ResultValidationError(`${path} must be one of ${choices.join(", ")}`);
  }
  return text;
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

function dateTime(value: unknown, path: string): string {
  const text = string(value, path);
  if (
    !/(Z|[+-]\d{2}:\d{2})$/.test(text)
    || Number.isNaN(Date.parse(text))
  ) {
    throw new ResultValidationError(`${path} must be an ISO date-time with a timezone`);
  }
  return text;
}

function dateValue(value: unknown, path: string): Date {
  const text = string(value, path);
  const parsed = new Date(`${text}T00:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(text)
    || Number.isNaN(parsed.valueOf())
    || parsed.toISOString().slice(0, 10) !== text
  ) {
    throw new ResultValidationError(`${path} must be an ISO date`);
  }
  return parsed;
}

function stringArray(value: unknown, path: string): void {
  array(value, path).forEach((item, index) => string(item, `${path}[${index}]`));
}
