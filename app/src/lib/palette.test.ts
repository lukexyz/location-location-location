import demoData from "../data/demo-results.json";
import { parseResultBundle } from "./validateResult";
import { SECTION_COLOURS, categoryNames, sectionColours } from "./palette";

describe("section colours", () => {
  it("assigns one distinct colour per category by sorted name, whatever the input order", () => {
    const forward = sectionColours(["essentials", "amenities", "environment"]);
    const backward = sectionColours(["environment", "essentials", "amenities", "amenities"]);
    expect([...forward.entries()]).toEqual([...backward.entries()]);
    expect(new Set(forward.values()).size).toBe(3);
    expect(forward.get("amenities")).toBe(SECTION_COLOURS[0]);
  });

  it("cycles when a run has more categories than colours", () => {
    const many = sectionColours(Array.from({ length: 8 }, (_, index) => `c${index}`));
    expect(many.size).toBe(8);
    expect(many.get("c6")).toBe(SECTION_COLOURS[0]);
  });

  it("covers every category the demo mentions", () => {
    const result = parseResultBundle(demoData);
    const colours = sectionColours(categoryNames(result));
    for (const candidate of result.candidates) {
      for (const category of candidate.categories) expect(colours.has(category.category)).toBe(true);
    }
  });
});
