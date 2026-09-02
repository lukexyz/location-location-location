export interface LocationPoint {
  latitude: number;
  longitude: number;
}

export type BoundaryGeometry =
  | { type: "Polygon"; coordinates: number[][][] }
  | { type: "MultiPolygon"; coordinates: number[][][][] };

export interface RouteBoundary {
  type: "isochrone" | "fixture_polygon";
  description?: string;
  duration_minutes?: number;
  travel_profile?: string;
  provider: string;
  departure_time: string | null;
  traffic_treatment: string;
  retrieved_at: string;
  geometry_file?: string;
  geometry: BoundaryGeometry;
}

export type ConstraintStatus = "pass" | "fail" | "unknown";

export interface ConstraintResult {
  metric: string;
  destination_label?: string;
  operator: "<=" | ">=";
  value: number;
  actual: number | null;
  status: ConstraintStatus;
  warning?: string;
}

export interface HardConstraints {
  status: ConstraintStatus;
  results: ConstraintResult[];
}

export interface UnmeasuredCategory {
  category: string;
  weight: number;
}

export type EvidenceBasis = "measured" | "transformed" | "agent_inferred" | "user_observed" | "synthetic";

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
  basis: EvidenceBasis;
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
  basis: EvidenceBasis;
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
  basis: EvidenceBasis;
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

export interface StreetCareSource {
  label: string;
  url: string;
  retrieved_at: string;
  source_date: string;
  licence: string;
}

export interface StreetCarePlace {
  id: string;
  candidate_id: string;
  local_authority: string;
  fly_tipping: {
    current_incidents_per_1000: number;
    previous_incidents_per_1000: number;
    current_period: string;
    previous_period: string;
    reporting_basis: string;
    source: StreetCareSource;
  };
  local_reports: null | {
    scope_kind: "lsoa" | "local_authority" | "other_small_area";
    geographic_scope: string;
    reports_per_1000: number | null;
    unresolved_percent: number | null;
    median_resolution_days: number | null;
    period_start: string;
    period_end: string;
    source: StreetCareSource;
  };
  visit_audit: null | {
    audited_at: string;
    geographic_scope: string;
    ratings: Record<string, number>;
    notes: string;
  };
  basis: EvidenceBasis;
}

export interface StreetCareComponent {
  key: string;
  raw_value: number | null;
  unit: string;
  normalized_score: number | null;
  weight: number;
  included: boolean;
}

export interface StreetCareSummary {
  assessment_date: string;
  score: number;
  basis: "proxy" | "recent_visit_audit";
  confidence: number;
  audit_age_days: number | null;
  components: StreetCareComponent[];
  place: StreetCarePlace;
}

export interface CandidateResult {
  id: string;
  name: string;
  place_kind?: "city" | "town" | "suburb" | "village" | "neighbourhood";
  location: LocationPoint;
  rank: number;
  overall_score: number;
  confidence: number;
  hard_constraints: HardConstraints;
  categories: CategoryResult[];
  unmeasured_categories: UnmeasuredCategory[];
  score_coverage_percent: number;
  informational_metrics: MetricResult[];
  rail_summary?: RailSummary;
  housing_summary?: HousingSummary;
  street_care_summary?: StreetCareSummary;
  missing_metrics: string[];
  warnings: string[];
}

export interface ResearchResult {
  schema_version: "2";
  scoring_version: string;
  run_id: string;
  generated_at: string;
  unknown_data_policy: "warn";
  route_boundary?: RouteBoundary;
  candidates: CandidateResult[];
}

export type LoadState =
  | { kind: "demo"; message: string }
  | { kind: "loaded"; message: string }
  | { kind: "error"; message: string };
