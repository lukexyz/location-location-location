const LABELS: Record<string, string> = {
  amenities: "Local signal",
  environment: "Ground condition",
  essentials: "Core fit",
  betting_shops: "Betting shops",
  cafes: "Cafés",
  door_to_door_commute: "Door-to-door commute",
  green_space: "Green-space access",
  housing_affordability: "Housing affordability",
  premium_grocers: "Premium grocers",
  street_care: "Street care",
  yoga_studios: "Yoga studios",
};

export function label(value: string): string {
  return LABELS[value] ?? value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

const BASIS_LABELS: Record<string, string> = {
  measured: "Measured",
  transformed: "Transformed",
  agent_inferred: "Agent-inferred",
  user_observed: "User-observed",
  synthetic: "Synthetic",
};

export function basisLabel(value: string): string {
  return BASIS_LABELS[value] ?? value;
}

/** Minutes of walking a `count_<n>_min_walk` unit describes, or undefined for other units. */
export function catchmentMinutes(unit: string): number | undefined {
  const match = /^count_(\d+)_min_walk$/.exec(unit);
  return match ? Number(match[1]) : undefined;
}

/** Short catchment wording for a count unit, e.g. "15 min"; falls back to the unit itself. */
export function catchmentShort(unit: string): string {
  const minutes = catchmentMinutes(unit);
  return minutes === undefined ? unit.replaceAll("_", " ") : `${minutes} min`;
}

/** Prose catchment wording for a count unit, e.g. "a 15-minute walk". */
export function catchmentPhrase(unit: string): string {
  const minutes = catchmentMinutes(unit);
  return minutes === undefined ? `the researched catchment (${unit.replaceAll("_", " ")})` : `a ${minutes}-minute walk`;
}

export function rawValue(value: number, unit: string): string {
  if (unit === "minutes" || unit === "walk_minutes") return `${value} min`;
  if (unit === "budget_ratio") return `${Math.round(value * 100)}% of budget`;
  if (unit === "desirability_score") return `${value}/100`;
  if (catchmentMinutes(unit) !== undefined) return `${value} in ${catchmentShort(unit)}`;
  return `${value} ${unit}`;
}

/** Decimal degrees with a hemisphere letter, e.g. `51.803N / 0.208W`; never a signed value. */
export function coordinates(latitude: number, longitude: number, digits = 3): string {
  const lat = `${Math.abs(latitude).toFixed(digits)}${latitude < 0 ? "S" : "N"}`;
  const lon = `${Math.abs(longitude).toFixed(digits)}${longitude < 0 ? "W" : "E"}`;
  return `${lat} / ${lon}`;
}

export function compactDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}
