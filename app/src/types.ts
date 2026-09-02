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

export interface RailSource {
  kind: string;
  label: string;
  url: string;
  retrieved_at: string;
  source_date: string;
  licence: string;
}

export interface RailJourney {
  id: string;
  candidate_id: string;
  destination_label: string;
  origin_station: string;
  origin_station_crs: string;
  london_arrival_station: string;
  service_window: string;
  primary: boolean;
  access_minutes: number;
  expected_wait_minutes: number;
  scheduled_rail_minutes: number;
  london_last_mile_minutes: number;
  total_minutes: number;
  changes: number;
  services_per_hour: number;
  last_useful_departure: string | null;
  punctuality_percent: number | null;
  cancellation_percent: number | null;
  confidence: number;
  confidence_notes: string;
  sources: RailSource[];
}

export interface RailSummary {
  primary_journey_id: string;
  fastest_total_minutes: number;
  journeys: RailJourney[];
}

export interface HousingSource {
  kind: string;
  label: string;
  url: string;
  retrieved_at: string;
  source_date: string;
  licence: string;
}

export interface HousingMarket {
  id: string;
  candidate_id: string;
  typical_cost_gbp: number;
  statistic: "median" | "mean";
  geography: {
    kind: "radius" | "local_authority" | "broad_rental_market_area" | "region";
    label: string;
    radius_km: number | null;
  };
  period_start: string;
  period_end: string;
  sample_size: number | null;
  listing_search_url: string | null;
  confidence: number;
  confidence_notes: string;
  sources: HousingSource[];
}

export interface HousingSummary {
  mode: "buy" | "rent";
  budget_gbp: number;
  budget_period: "purchase" | "month";
  property_type: string;
  bedrooms: number | null;
  typical_cost_gbp: number;
  budget_ratio: number;
  inventory_status: "not_checked";
  market: HousingMarket;
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
  rail_summary?: RailSummary;
  housing_summary?: HousingSummary;
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
