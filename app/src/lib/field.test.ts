import { MIN_PIN, pinSizeForField, planLabels, samePlan } from "./field";
import { pinSizeForZoom } from "./pins";

const pin = (id: string, x: number, y: number, rank: number, name = id) => ({ id, x, y, rank, name });

describe("pin size for a field", () => {
  it("keeps the zoom's size when pins are far apart", () => {
    const pins = [pin("a", 0, 0, 1), pin("b", 400, 0, 2), pin("c", 0, 400, 3)];
    expect(pinSizeForField(12, pins)).toBe(pinSizeForZoom(12));
  });

  it("shrinks pins that crowd each other, but never below the floor", () => {
    const crowd = Array.from({ length: 8 }, (_, i) => pin(`p${i}`, i * 40, 0, i + 1));
    expect(pinSizeForField(12, crowd)).toBe(38);
    const pile = Array.from({ length: 8 }, (_, i) => pin(`p${i}`, i * 3, 0, i + 1));
    expect(pinSizeForField(12, pile)).toBe(MIN_PIN);
    expect(MIN_PIN).toBe(pinSizeForZoom(8));
  });

  it("gives a single pin the zoom's size", () => {
    expect(pinSizeForField(9, [pin("a", 0, 0, 1)])).toBe(pinSizeForZoom(9));
    expect(pinSizeForField(9, [])).toBe(pinSizeForZoom(9));
  });
});

describe("label plan", () => {
  it("labels every pin on the right when nothing collides", () => {
    const pins = [pin("a", 0, 0, 1), pin("b", 400, 0, 2), pin("c", 0, 400, 3)];
    expect(planLabels(pins, 46, "a")).toEqual(new Map([["a", "right"], ["b", "right"], ["c", "right"]]));
  });

  it("moves a label to the left when the right would cover another pin", () => {
    // b sits just right of a, where a's label goes; a's name moves to its left. b's right side is clear.
    const pins = [pin("a", 0, 0, 1, "Fleetville"), pin("b", 60, 0, 2, "St Julians")];
    expect(planLabels(pins, 46, "a")).toEqual(new Map([["a", "left"], ["b", "right"]]));
  });

  it("drops a label that fits on neither side", () => {
    // c sits left of a and b right of it, so a's name has nowhere to go; the others are clear on their outer sides.
    const pins = [pin("a", 0, 0, 1, "Fleetville"), pin("b", 60, 0, 2, "St Julians"), pin("c", -60, 0, 3, "Sopwell")];
    expect(planLabels(pins, 46, "b")).toEqual(new Map([["b", "right"], ["c", "left"]]));
  });

  it("drops a label that would overlap a label already placed on either side", () => {
    const pins = [pin("a", 0, 0, 1, "Fleetville"), pin("b", 0, 12, 2, "Sopwell"), pin("c", 300, 0, 3, "Far")];
    const plan = planLabels(pins, 30, "a");
    expect(plan.get("a")).toBe("right");
    expect(plan.get("b")).toBe("left");
    expect(plan.get("c")).toBe("right");
  });

  it("always names the selected place, on the right if nowhere is clear", () => {
    const pins = [pin("a", 0, 0, 1, "Fleetville"), pin("b", 60, 0, 2, "St Julians"), pin("c", -60, 0, 3, "Sopwell")];
    expect(planLabels(pins, 46, "a").get("a")).toBe("right");
  });
});

describe("same plan", () => {
  it("compares size and the labelled set", () => {
    const right = new Map<string, "right" | "left">([["a", "right"]]);
    expect(samePlan({ size: 46, labelled: right }, { size: 46, labelled: new Map(right) })).toBe(true);
    expect(samePlan({ size: 46, labelled: right }, { size: 40, labelled: new Map(right) })).toBe(false);
    expect(samePlan({ size: 46, labelled: right }, { size: 46, labelled: new Map([["b", "right"]]) })).toBe(false);
    expect(samePlan({ size: 46, labelled: right }, { size: 46, labelled: new Map([["a", "left"]]) })).toBe(false);
    const anchored = { size: 46, labelled: right, anchor: { x: 10.2, y: 20.4 }, field: { width: 900, height: 600 } };
    expect(samePlan(anchored, { ...anchored, anchor: { x: 10.4, y: 19.6 } })).toBe(true);
    expect(samePlan(anchored, { ...anchored, anchor: { x: 12, y: 20 } })).toBe(false);
    expect(samePlan(anchored, { ...anchored, field: { width: 901, height: 600 } })).toBe(false);
    expect(samePlan(anchored, { size: 46, labelled: right })).toBe(false);
  });
});
