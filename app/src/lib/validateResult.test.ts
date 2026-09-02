import demoData from "../data/demo-results.json";
import { parseResultBundle, ResultValidationError } from "./validateResult";

describe("parseResultBundle", () => {
  it("accepts the generated demonstration bundle", () => {
    const result = parseResultBundle(demoData);
    expect(result.candidates).toHaveLength(3);
    expect(result.candidates[0].name).toBe("Welwyn Garden City");
  });

  it("rejects incompatible schema versions with a useful message", () => {
    expect(() => parseResultBundle({ ...demoData, schema_version: "99" })).toThrow(
      new ResultValidationError("Incompatible schema 99. This viewer requires schema 2; rerun the research command to regenerate the bundle."),
    );
  });

  it("rejects agent-inferred evidence that claims high confidence", () => {
    const inferred = structuredClone(demoData);
    const metric = inferred.candidates[0].categories[0].metrics[0];
    metric.basis = "agent_inferred";
    metric.confidence = 0.9;
    expect(() => parseResultBundle(inferred)).toThrow(/agent-inferred but claims confidence above 0.5/);
    metric.confidence = 0.5;
    expect(() => parseResultBundle(inferred)).not.toThrow();
  });

  it("rejects duplicate candidate identities", () => {
    const duplicate = structuredClone(demoData);
    duplicate.candidates[1].id = duplicate.candidates[0].id;
    expect(() => parseResultBundle(duplicate)).toThrow(/Duplicate candidate id/);
  });

  it("rejects unsupported candidate place kinds", () => {
    const invalid = structuredClone(demoData) as unknown as Record<string, unknown>;
    const candidate = (invalid.candidates as Array<Record<string, unknown>>)[0];
    candidate.place_kind = "planet";
    expect(() => parseResultBundle(invalid)).toThrow(/place_kind must be one of/);
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

  it("rejects street-care components that smuggle report volume into the score", () => {
    const invalid = structuredClone(demoData);
    const density = invalid.candidates[0].street_care_summary.components.find(
      (component) => component.key === "report_density",
    );
    expect(density).toBeUndefined();

    const proxy = invalid.candidates.find((candidate) => candidate.id === "hemel-hempstead")!;
    const proxyDensity = proxy.street_care_summary.components.find(
      (component) => component.key === "report_density",
    )!;
    proxyDensity.included = true;
    proxyDensity.weight = 0.1;
    expect(() => parseResultBundle(invalid)).toThrow(/included components need score and weight/);
  });
});
