/** Pin diameter in CSS pixels for a map zoom level; pins shrink as the field widens so a dense run stays readable. */
export function pinSizeForZoom(zoom: number): number {
  if (zoom < 9) return 34;
  if (zoom <= 10) return 46;
  return 58;
}
