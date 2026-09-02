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
});
