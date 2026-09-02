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
  stringArray(candidate.missing_metrics, `${path}.missing_metrics`);
  stringArray(candidate.warnings, `${path}.warnings`);
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

function stringArray(value: unknown, path: string): void {
  array(value, path).forEach((item, index) => string(item, `${path}[${index}]`));
}
