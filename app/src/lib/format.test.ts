import { catchmentPhrase, catchmentShort, coordinates, rawValue } from "./format";
import { pinSizeForZoom } from "./pins";

describe("formatting helpers", () => {
  it("renders coordinates with hemisphere letters and never a signed value", () => {
    expect(coordinates(51.8032, -0.2077)).toBe("51.803N / 0.208W");
    expect(coordinates(-33.8688, 151.2093)).toBe("33.869S / 151.209E");
    expect(coordinates(0, 0)).toBe("0.000N / 0.000E");
    expect(coordinates(51.5, -0.1)).not.toMatch(/-/);
  });

  it("reads the walking catchment out of a count unit", () => {
    expect(catchmentShort("count_15_min_walk")).toBe("15 min");
    expect(catchmentPhrase("count_15_min_walk")).toBe("a 15-minute walk");
    expect(catchmentShort("count_10_min_walk")).toBe("10 min");
    expect(rawValue(3, "count_10_min_walk")).toBe("3 in 10 min");
    expect(catchmentPhrase("count_per_km2")).toContain("count per km2");
  });
});

describe("map pins", () => {
  it("scale with zoom so a wide field stays legible", () => {
    expect(pinSizeForZoom(7)).toBe(34);
    expect(pinSizeForZoom(8.9)).toBe(34);
    expect(pinSizeForZoom(9)).toBe(46);
    expect(pinSizeForZoom(10)).toBe(46);
    expect(pinSizeForZoom(11)).toBe(58);
  });
});
