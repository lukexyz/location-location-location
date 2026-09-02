import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/tile.openstreetmap.org/**", (route) => route.abort());
  await page.goto("./");
});

test("map, ranked list, and dossier stay synchronized", async ({ page }) => {
  await expect(page.getByLabel("Location cubed")).toBeVisible();
  await expect(page.locator(".score-marker")).toHaveCount(3);
  await page.getByRole("button", { name: /Hemel Hempstead/ }).click();
  await expect(page.getByRole("heading", { name: "Hemel Hempstead" })).toBeVisible();
  await expect(page.locator(".score-marker.selected b")).toHaveText("73");
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(1);
});

test("route assumptions and contribution points are inspectable", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Route boundary" })).toBeVisible();
  await expect(page.getByText(/not modelled; fictional boundary/i)).toBeVisible();
  await expect(page.getByText(/overall/i).first()).toBeVisible();
  await page.locator(".metric-row").first().click();
  await expect(page.getByText("Category points").first()).toBeVisible();
});

test("a local result can be imported and rejected without navigation", async ({ page }) => {
  await page.getByTestId("result-import").setInputFiles({
    name: "invalid-results.json",
    mimeType: "application/json",
    buffer: Buffer.from('{"schema_version":"7"}'),
  });
  await expect(page.getByRole("status")).toContainText("Incompatible schema 7");
  await expect(page).toHaveURL(/127\.0\.0\.1:43117/);
});

test("an imported result can be reset on desktop and mobile", async ({ page }) => {
  await page.getByTestId("result-import").setInputFiles({
    name: "local-results.json",
    mimeType: "application/json",
    buffer: readFileSync("src/data/demo-results.json"),
  });
  await expect(page.getByRole("button", { name: "RESET DEMO" })).toBeVisible();
  await page.getByRole("button", { name: "RESET DEMO" }).click();
  await expect(page.getByRole("button", { name: "RESET DEMO" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Welwyn Garden City" })).toBeVisible();
});

test("the instrument reflows without horizontal overflow", async ({ page }) => {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport + 1);
});

test("housing evidence is explicit about its market-only scope", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Housing affordability" })).toBeVisible();
  await expect(page.getByText(/live inventory was not checked/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /Search current listings/ })).toBeVisible();
});

test("street-care evidence exposes its basis and raw prior", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Street care" })).toBeVisible();
  await expect(page.getByText(/PAVEMENT PRIDE \/ Recent visit audit/i)).toBeVisible();
  await expect(page.getByText("12/1k")).toBeVisible();
});

test("playful readouts restate cited evidence", async ({ page }) => {
  const readouts = page.locator(".readout-grid");
  await expect(readouts).toBeVisible();
  await expect(readouts.getByText("SOURDOUGH-TO-SLOTS")).toBeVisible();
  await expect(readouts.getByText("LAST TRAIN HOME")).toBeVisible();
  await expect(page.getByText("Readouts restate cited evidence; they add nothing to the score.")).toBeVisible();
  await expect(page.getByText("no evidence")).toHaveCount(0);
});

test("sorting and what-if sliders never refit the map or discard a pan", async ({ page }) => {
  await expect(page.locator(".score-marker")).toHaveCount(3);
  const map = page.locator(".map-canvas");
  const box = (await map.boundingBox())!;
  const centre = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await page.mouse.move(centre.x, centre.y);
  await page.mouse.down();
  await page.mouse.move(centre.x + 60, centre.y + 40, { steps: 6 });
  await page.mouse.up();
  await page.waitForTimeout(400);
  const pane = page.locator(".leaflet-map-pane");
  const afterPan = await pane.evaluate((element) => element.style.transform);
  await page.getByRole("group", { name: "Sort candidates" }).getByRole("button", { name: "Name" }).click();
  await page.waitForTimeout(300);
  expect(await pane.evaluate((element) => element.style.transform)).toBe(afterPan);
  await page.getByText("Tune importance").click();
  await page.getByLabel(/Cafés/).fill("5");
  await expect(page.getByText("WHAT-IF ACTIVE")).toBeVisible();
  await page.waitForTimeout(300);
  expect(await pane.evaluate((element) => element.style.transform)).toBe(afterPan);
});

test("importance sliders preview a what-if order while researched ranks stay put", async ({ page }) => {
  await page.getByText("Tune importance").click();
  await page.getByLabel(/Door-to-door commute/).fill("0");
  await page.getByLabel(/Cafés/).fill("5");
  await expect(page.getByText("WHAT-IF ACTIVE")).toBeVisible();
  await expect(page.getByText("WHAT-IF ORDER")).toBeVisible();
  const numbers = await page.locator(".rank-number").allTextContents();
  expect([...numbers].sort()).toEqual(["01", "02", "03"]);
  await expect(page.locator(".rank-score.whatif")).toHaveCount(3);
  await page.getByRole("button", { name: "RESTORE RESEARCHED IMPORTANCE" }).click();
  await expect(page.getByText("RESEARCHED WEIGHTS")).toBeVisible();
  await expect(page.locator(".rank-score.whatif")).toHaveCount(0);
});
