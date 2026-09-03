import demoData from "../data/demo-results.json";
import { parseResultBundle } from "./validateResult";
import { assetBaseFor, cardFacts, photoUrl } from "./placeCard";

const result = parseResultBundle(demoData);
const first = [...result.candidates].sort((a, b) => a.rank - b.rank)[0];

describe("place card", () => {
  it("resolves a photo against the bundle's folder and has none for a bare file", () => {
    expect(photoUrl("./demo/", first.photo)).toBe(`./demo/${first.photo!.file}`);
    expect(photoUrl(undefined, first.photo)).toBeUndefined();
    expect(photoUrl("./demo/", undefined)).toBeUndefined();
    expect(assetBaseFor("runs/my-search/results.json")).toBe("runs/my-search/");
    expect(assetBaseFor("results.json")).toBe("");
  });

  it("gives three facts from the bundle with the commute first", () => {
    const facts = cardFacts(first);
    expect(facts).toHaveLength(3);
    expect(facts[0].key).toBe("commute");
    expect(facts[0].value).toMatch(/^\d+ min$/);
    expect(facts.map((fact) => fact.key)).not.toContain("housing_affordability");
    for (const fact of facts) {
      expect(fact.label).not.toEqual("");
      expect(fact.value).not.toEqual("");
    }
  });

  it("still has facts for a place with no photo and no housing evidence", () => {
    const bare = { ...first, photo: undefined, housing_summary: undefined };
    const facts = cardFacts(bare);
    expect(facts.length).toBeGreaterThan(0);
    expect(facts.some((fact) => fact.key === "housing")).toBe(false);
  });
});
