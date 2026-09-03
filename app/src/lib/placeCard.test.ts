import { cardPosition, pinTarget } from "./placeCard";
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

describe("card position", () => {
  const field = { width: 1440, height: 900 };

  it("sits to the right of the pin, level with it, when there is room", () => {
    expect(cardPosition({ size: 46, anchor: { x: 500, y: 450 }, field })).toEqual({ left: 541, top: 278 });
  });

  it("flips to the left of the pin when the right would run under the evidence card", () => {
    expect(cardPosition({ size: 46, anchor: { x: 900, y: 450 }, field })).toEqual({ left: 499, top: 278 });
  });

  it("never covers the side cards, the header row, or the bottom edge", () => {
    expect(cardPosition({ size: 46, anchor: { x: 350, y: 60 }, field })).toEqual({ left: 391, top: 104 });
    expect(cardPosition({ size: 46, anchor: { x: 1300, y: 880 }, field })).toEqual({ left: 632, top: 512 });
    expect(cardPosition({ size: 46, anchor: { x: 200, y: 450 }, field })).toEqual({ left: 338, top: 278 });
  });

  it("uses the narrower insets on a laptop", () => {
    expect(cardPosition({ size: 46, anchor: { x: 320, y: 450 }, field: { width: 1000, height: 700 } })).toEqual({ left: 298, top: 278 });
  });

  it("leaves a phone, or an unselected field, to the stylesheet", () => {
    expect(cardPosition({ size: 46, anchor: { x: 100, y: 100 }, field: { width: 390, height: 844 } })).toBeUndefined();
    expect(cardPosition({ size: 46, field })).toBeUndefined();
    expect(cardPosition({ size: 46, anchor: { x: 100, y: 100 } })).toBeUndefined();
  });
});

describe("pin target", () => {
  it("lands the pin where its card fits to the right, level with the middle of the hole", () => {
    expect(pinTarget({ width: 1440, height: 900 }, 46)).toEqual({ x: 476, y: 480 });
    const laptop = pinTarget({ width: 1280, height: 720 }, 46)!;
    expect(laptop).toEqual({ x: 396, y: 390 });
    const card = cardPosition({ size: 46, anchor: laptop, field: { width: 1280, height: 720 } })!;
    expect(card.left).toBe(laptop.x + 23 + 18);
    expect(card.left + 360).toBeLessThanOrEqual(1280 - 448);
  });

  it("gives a phone no target", () => {
    expect(pinTarget({ width: 390, height: 844 }, 34)).toBeUndefined();
  });
});
