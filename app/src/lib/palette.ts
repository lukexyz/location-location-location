import type { ResearchResult } from "../types";

/**
 * One colour per scoring category, so the same category reads the same way in
 * the evidence panel and the tune panel. Colours are assigned by sorted name,
 * so they are stable for a bundle however its candidates order their
 * categories, and they cycle if a run has more categories than colours.
 */
export const SECTION_COLOURS = ["#f26b3a", "#3ec5b8", "#a99cff", "#f6c343", "#ff6fa5", "#5aa9ff"] as const;

export function sectionColours(categories: Iterable<string>): Map<string, string> {
  const names = [...new Set(categories)].sort((left, right) => left.localeCompare(right));
  return new Map(names.map((name, index) => [name, SECTION_COLOURS[index % SECTION_COLOURS.length]]));
}

/** Every category a bundle mentions, measured or not. */
export function categoryNames(result: ResearchResult): string[] {
  return result.candidates.flatMap((candidate) => [
    ...candidate.categories.map((category) => category.category),
    ...candidate.unmeasured_categories.map((category) => category.category),
  ]);
}
