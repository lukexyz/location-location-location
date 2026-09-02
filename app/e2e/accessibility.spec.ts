import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/tile.openstreetmap.org/**", (route) => route.abort());
  await page.goto("./");
});

test("has no automatically detectable WCAG A or AA violations", async ({ page }) => {
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
});

test("supports skip navigation, keyboard import, and candidate arrow keys", async ({ page }) => {
  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "Skip to candidate results" });
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main", { name: "Candidate results and evidence" })).toBeFocused();

  const firstCandidate = page.getByRole("button", { name: /Alder Green/ });
  const secondCandidate = page.getByRole("button", { name: /Northbridge/ });
  await firstCandidate.focus();
  await page.keyboard.press("ArrowDown");
  await expect(secondCandidate).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Northbridge" })).toBeVisible();
  await expect(page.getByText(/Selected candidate: Northbridge/)).toBeAttached();

  const importButton = page.getByRole("button", { name: /IMPORT RESULT.JSON/ });
  await importButton.focus();
  await expect(importButton).toBeFocused();
});
