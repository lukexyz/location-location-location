import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import demoData from "../data/demo-results.json";
import { parseResultBundle } from "./validateResult";

const schemaDirectory = resolve(process.cwd(), "../schemas");
const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
for (const name of readdirSync(schemaDirectory).filter((item) => item.endsWith(".schema.json"))) {
  ajv.addSchema(JSON.parse(readFileSync(`${schemaDirectory}/${name}`, "utf8")));
}
const validateResultSchema = ajv.getSchema(
  "https://location3.local/schemas/research-result.schema.json",
);
if (!validateResultSchema) throw new Error("research result schema was not registered");

describe("browser and JSON Schema contract parity", () => {
  it("accepts the generated demo through both validators", () => {
    expect(validateResultSchema(demoData), JSON.stringify(validateResultSchema.errors)).toBe(true);
    expect(parseResultBundle(demoData).run_id).toBe(demoData.run_id);
  });

  it.each([
    ["fractional rank", (candidate: Record<string, unknown>) => { candidate.rank = 1.5; }],
    ["unknown candidate field", (candidate: Record<string, unknown>) => { candidate.secret = true; }],
    ["unsupported place kind", (candidate: Record<string, unknown>) => { candidate.place_kind = "planet"; }],
    ["missing contribution", (candidate: Record<string, unknown>) => {
      const categories = candidate.categories as Array<Record<string, unknown>>;
      const metrics = categories[0].metrics as Array<Record<string, unknown>>;
      delete metrics[0].category_contribution;
    }],
    ["invalid constraint operator", (candidate: Record<string, unknown>) => {
      const hard = candidate.hard_constraints as Record<string, unknown>;
      const constraints = hard.results as Array<Record<string, unknown>>;
      constraints[0].operator = "=";
    }],
  ])("rejects %s in both validators", (_name, mutate) => {
    const invalid = structuredClone(demoData) as unknown as Record<string, unknown>;
    const candidates = invalid.candidates as Array<Record<string, unknown>>;
    mutate(candidates[0]);
    expect(validateResultSchema(invalid)).toBe(false);
    expect(() => parseResultBundle(invalid)).toThrow();
  });
});
