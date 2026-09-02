export interface LocationPoint {
  latitude: number;
  longitude: number;
}

export interface ConstraintResult {
  metric: string;
  operator: "<=" | ">=";
  value: number;
  actual: number | null;
  passed: boolean;
  warning?: string;
}

export interface MetricResult {
  metric: string;
  category: string;
  raw_value: number;
  unit: string;
  normalized_score: number;
  weight: number;
  active: boolean;
  confidence: number;
  evidence_id: string;
  source: string;
  source_url: string;
  source_date: string;
  confidence_notes: string;
  category_contribution: number;
}

export interface CategoryResult {
  category: string;
  score: number;
  weight: number;
  overall_contribution: number;
  metrics: MetricResult[];
}

export interface CandidateResult {
  id: string;
  name: string;
  location: LocationPoint;
  rank: number;
  overall_score: number;
  confidence: number;
  hard_constraints: {
    passed: boolean;
    results: ConstraintResult[];
  };
  categories: CategoryResult[];
  informational_metrics: MetricResult[];
  missing_metrics: string[];
  warnings: string[];
}

export interface ResearchResult {
  schema_version: "1";
  scoring_version: string;
  run_id: string;
  generated_at: string;
  unknown_data_policy: "warn";
  candidates: CandidateResult[];
}

export type LoadState =
  | { kind: "demo"; message: string }
  | { kind: "loaded"; message: string }
  | { kind: "error"; message: string };
