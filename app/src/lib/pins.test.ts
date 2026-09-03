import { FIT_HIGH, FIT_LOW, fitColour, fitScale, pinSizeForZoom } from "./pins";

describe("pin size", () => {
  it("shrinks as the field widens", () => {
    expect(pinSizeForZoom(8)).toBeLessThan(pinSizeForZoom(10));
    expect(pinSizeForZoom(10)).toBeLessThan(pinSizeForZoom(12));
  });
});

describe("fit scale", () => {
  it("places each score between the lowest and highest in the run", () => {
    const fit = fitScale([67.1, 78.8, 73.2]);
    expect(fit(78.8)).toBe(1);
    expect(fit(67.1)).toBe(0);
    expect(fit(73.2)).toBeCloseTo(0.521, 3);
  });

  it("calls a run of one place, or of equal scores, all best", () => {
    expect(fitScale([70])(70)).toBe(1);
    expect(fitScale([70, 70])(70)).toBe(1);
    expect(fitScale([])(70)).toBe(1);
  });

  it("clamps a score outside the run", () => {
    const fit = fitScale([60, 80]);
    expect(fit(90)).toBe(1);
    expect(fit(10)).toBe(0);
  });
});

describe("fit colour", () => {
  it("runs from the dull green to the vivid one", () => {
    expect(fitColour(0)).toBe(FIT_LOW);
    expect(fitColour(1)).toBe(FIT_HIGH);
    expect(fitColour(0.5)).toBe("#62bd83");
    expect(fitColour(2)).toBe(FIT_HIGH);
  });
});
