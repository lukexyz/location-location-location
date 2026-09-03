import type { BoundaryGeometry } from "../types";

/** A ring of [longitude, latitude] pairs, as GeoJSON orders them. */
type Ring = number[][];

// Slightly inside the poles so the Mercator projection never sees an infinite edge.
const WORLD: Ring = [[-180, -89], [180, -89], [180, 89], [-180, 89], [-180, -89]];

/**
 * The world with the search boundary cut out of it. Drawn with an even-odd
 * fill, it dims everything outside the boundary and leaves the inside as the
 * map draws it, so the focus of the search reads at a glance. Only each
 * polygon's outer ring becomes a hole: an island inside the boundary is still
 * inside the search.
 */
export function focusMask(geometry: BoundaryGeometry): GeoJSON.Polygon {
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  const holes = polygons.map((polygon) => polygon[0]).filter((ring) => ring !== undefined && ring.length >= 4);
  return { type: "Polygon", coordinates: [WORLD, ...holes] };
}
