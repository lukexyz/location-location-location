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

export function rawValue(value: number, unit: string): string {
  if (unit === "minutes" || unit === "walk_minutes") return `${value} min`;
  if (unit === "budget_ratio") return `${Math.round(value * 100)}% of budget`;
  if (unit === "desirability_score") return `${value}/100`;
  if (unit === "count_15_min_walk") return `${value} in 15 min`;
  return `${value} ${unit}`;
}

export function compactDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}
