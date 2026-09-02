import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

/**
 * Documentation screenshots of the public demo. Skipped in normal test runs;
 * set CAPTURE_SCREENSHOTS=1 to refresh docs/screenshots. Map tiles are allowed
 * here so the captures show the attributed OpenStreetMap basemap.
 */
const capture = process.env.CAPTURE_SCREENSHOTS === "1";
// Playwright runs from app/, so the repository's docs directory is one level up.
const outputDirectory = resolve(process.cwd(), "../docs/screenshots");

test.describe("documentation screenshots", () => {
  test.skip(!capture, "set CAPTURE_SCREENSHOTS=1 to refresh docs/screenshots");

  test("captures the instrument", async ({ page }, testInfo) => {
    mkdirSync(outputDirectory, { recursive: true });
    await page.goto("./");
    await expect(page.getByRole("heading", { name: "Candidate register" })).toBeVisible();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.screenshot({ path: resolve(outputDirectory, `${testInfo.project.name}-overview.png`) });

    if (testInfo.project.name === "chromium") {
      await page.getByText("Tune importance").click();
      await page.getByLabel(/Cafés/).fill("5");
      await page.getByLabel(/Door-to-door commute/).fill("1");
      await expect(page.getByText("WHAT-IF ACTIVE")).toBeVisible();
      // Filling the last slider scrolls the tune panel; show it from its first category.
      await page.locator(".tune-panel").evaluate((panel) => { panel.scrollTop = 0; });
      await page.waitForTimeout(500);
      await page.screenshot({ path: resolve(outputDirectory, "chromium-whatif.png") });
      await page.getByRole("button", { name: "RESTORE RESEARCHED IMPORTANCE" }).click();

      const dossier = page.locator(".dossier");
      await dossier.locator(".metric-row summary").first().click();
      await page.waitForTimeout(300);
      await dossier.screenshot({ path: resolve(outputDirectory, "chromium-dossier.png") });
    }
  });
});
