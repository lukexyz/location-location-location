import { focusMask } from "./focusMask";

const square = [[-1, 51], [1, 51], [1, 52], [-1, 52], [-1, 51]];
const island = [[-0.1, 51.4], [0.1, 51.4], [0.1, 51.6], [-0.1, 51.6], [-0.1, 51.4]];

describe("focus mask", () => {
  it("cuts a polygon boundary out of the world", () => {
    const mask = focusMask({ type: "Polygon", coordinates: [square] });
    expect(mask.type).toBe("Polygon");
    expect(mask.coordinates).toHaveLength(2);
    expect(mask.coordinates[0][0]).toEqual([-180, -89]);
    expect(mask.coordinates[1]).toEqual(square);
  });

  it("cuts every outer ring of a multipolygon and keeps islands inside the search", () => {
    const mask = focusMask({
      type: "MultiPolygon",
      coordinates: [[square, island], [[[5, 51], [6, 51], [6, 52], [5, 51]]]],
    });
    expect(mask.coordinates).toHaveLength(3);
    expect(mask.coordinates[1]).toEqual(square);
    expect(mask.coordinates).not.toContainEqual(island);
  });
});
