import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/tile.openstreetmap.org/**", (route) => route.abort());
  await page.goto("./");
});

test("preserves the instrument layout and colour contract", async ({ page }) => {
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Playwright viewport is unavailable");
  const header = await page.locator(".instrument-header").boundingBox();
  const map = await page.locator(".map-field").boundingBox();
  const rank = await page.locator(".rank-panel").boundingBox();
  const dossier = await page.locator(".dossier").boundingBox();
  if (!header || !map || !rank || !dossier) throw new Error("Instrument geometry is unavailable");

  const tokens = await page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    return {
      acid: styles.getPropertyValue("--acid").trim(),
      danger: styles.getPropertyValue("--danger").trim(),
      panel: styles.getPropertyValue("--panel").trim(),
    };
  });
  expect(tokens).toEqual({
    acid: "#bdff78",
    danger: "#ff776d",
    panel: "rgba(12, 18, 17, 0.93)",
  });
  expect(map.width).toBeCloseTo(viewport.width, 0);

  if (viewport.width > 760) {
    expect(rank.x).toBeCloseTo(14, 0);
    expect(dossier.x + dossier.width).toBeCloseTo(viewport.width - 14, 0);
    expect(header.y + header.height).toBeLessThan(rank.y);
    expect(rank.x + rank.width).toBeLessThan(dossier.x);
  } else {
    expect(rank.y).toBeGreaterThanOrEqual(map.y + map.height);
    expect(dossier.y).toBeGreaterThan(rank.y);
    expect(rank.width).toBeLessThanOrEqual(viewport.width - 16);
    expect(dossier.width).toBeLessThanOrEqual(viewport.width - 16);
  }
});

test("honours reduced-motion preferences", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const durationMs = await page.locator(".scan-line").evaluate(
    (element) => {
      const duration = getComputedStyle(element).animationDuration;
      const value = Number.parseFloat(duration);
      return duration.endsWith("ms") ? value : value * 1000;
    },
  );
  expect(durationMs).toBeLessThanOrEqual(0.01);
});
