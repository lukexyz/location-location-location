/** Pin diameter in CSS pixels for a map zoom level; pins shrink as the field widens so a dense run stays readable. */
export function pinSizeForZoom(zoom: number): number {
  if (zoom < 9) return 34;
  if (zoom <= 10) return 46;
  return 58;
}

/** The dullest and the most vivid green a pin can be: the worst and the best fit in the run. */
export const FIT_LOW = "#7a9b85";
export const FIT_HIGH = "#4ade80";

/**
 * Where a score sits between the lowest and the highest score in the run, 0 to 1.
 * A run of one place, or of equal scores, is all best: there is nothing to be worse than.
 */
export function fitScale(scores: readonly number[]): (score: number) => number {
  const low = Math.min(...scores);
  const high = Math.max(...scores);
  if (!Number.isFinite(low) || !Number.isFinite(high) || high - low < 1e-9) return () => 1;
  return (score) => Math.min(1, Math.max(0, (score - low) / (high - low)));
}

/** The pin green for a fit fraction: a straight mix from FIT_LOW to FIT_HIGH. */
export function fitColour(fraction: number): string {
  const t = Math.min(1, Math.max(0, fraction));
  const mix = (a: number, b: number) => Math.round(a + (b - a) * t);
  const [lr, lg, lb] = channels(FIT_LOW);
  const [hr, hg, hb] = channels(FIT_HIGH);
  return `#${[mix(lr, hr), mix(lg, hg), mix(lb, hb)].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

function channels(hex: string): [number, number, number] {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
}
