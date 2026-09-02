import demoData from "../data/demo-results.json";
import { parseResultBundle, ResultValidationError } from "./validateResult";

describe("parseResultBundle", () => {
  it("accepts the generated demonstration bundle", () => {
    const result = parseResultBundle(demoData);
    expect(result.candidates).toHaveLength(3);
    expect(result.candidates[0].name).toBe("Alder Green");
  });

  it("rejects incompatible schema versions with a useful message", () => {
    expect(() => parseResultBundle({ ...demoData, schema_version: "99" })).toThrow(
      new ResultValidationError("Incompatible schema 99. This viewer requires schema 1."),
    );
  });

  it("rejects duplicate candidate identities", () => {
    const duplicate = structuredClone(demoData);
    duplicate.candidates[1].id = duplicate.candidates[0].id;
    expect(() => parseResultBundle(duplicate)).toThrow(/Duplicate candidate id/);
  });

  it("rejects rail totals that hide missing journey components", () => {
    const invalid = structuredClone(demoData);
    invalid.candidates[0].rail_summary.journeys[0].total_minutes += 1;
    expect(() => parseResultBundle(invalid)).toThrow(/component times/);
  });

  it("rejects housing ratios and inventory claims that contradict the evidence", () => {
    const badRatio = structuredClone(demoData);
    badRatio.candidates[0].housing_summary.budget_ratio += 0.1;
    expect(() => parseResultBundle(badRatio)).toThrow(/budget_ratio is inconsistent/);

    const inventoryClaim = structuredClone(demoData) as unknown as Record<string, unknown>;
    const candidate = (inventoryClaim.candidates as Array<Record<string, unknown>>)[0];
    (candidate.housing_summary as Record<string, unknown>).inventory_status = "available";
    expect(() => parseResultBundle(inventoryClaim)).toThrow(/inventory_status must be not_checked/);
  });
});
