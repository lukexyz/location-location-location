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
  const door = await page.locator(".start-banner").boundingBox();
  if (!header || !map || !rank || !dossier || !door) throw new Error("Instrument geometry is unavailable");

  const tokens = await page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    return {
      acid: styles.getPropertyValue("--acid").trim(),
      danger: styles.getPropertyValue("--danger").trim(),
      panel: styles.getPropertyValue("--panel").trim(),
    };
  });
  expect(tokens).toEqual({
    acid: "#f6c343",
    danger: "#ff7a6b",
    panel: "rgba(43, 46, 45, 0.94)",
  });
  expect(map.width).toBeCloseTo(viewport.width, 0);

  if (viewport.width > 760) {
    expect(rank.x).toBeCloseTo(14, 0);
    expect(dossier.x + dossier.width).toBeCloseTo(viewport.width - 14, 0);
    expect(header.y + header.height).toBeLessThan(rank.y);
    expect(rank.x + rank.width).toBeLessThan(dossier.x);
    // The front door sits over the map between the bezels and never covers either.
    expect(door.x).toBeGreaterThanOrEqual(rank.x + rank.width);
    expect(door.x + door.width).toBeLessThanOrEqual(dossier.x);
    expect(door.y).toBeGreaterThanOrEqual(header.y + header.height);
  } else {
    expect(door.y).toBeGreaterThanOrEqual(map.y + map.height);
    expect(rank.y).toBeGreaterThanOrEqual(door.y + door.height);
    expect(rank.y).toBeGreaterThanOrEqual(map.y + map.height);
    expect(dossier.y).toBeGreaterThan(rank.y);
    expect(rank.width).toBeLessThanOrEqual(viewport.width - 16);
    expect(dossier.width).toBeLessThanOrEqual(viewport.width - 16);
  }
});

test("nothing animates while the viewer is idle", async ({ page }) => {
  const animated = await page.evaluate(() =>
    Array.from(document.querySelectorAll("*")).filter((element) => getComputedStyle(element).animationName !== "none").length,
  );
  expect(animated).toBe(0);
});

test("the place card stays inside the map and off the side cards", async ({ page }) => {
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Playwright viewport is unavailable");
  await page.getByRole("button", { name: /Welwyn Garden City/ }).click();
  const card = await page.getByTestId("place-card").boundingBox();
  const map = await page.locator(".map-field").boundingBox();
  if (!card || !map) throw new Error("Card geometry is unavailable");
  expect(card.x).toBeGreaterThanOrEqual(map.x);
  expect(card.x + card.width).toBeLessThanOrEqual(map.x + map.width + 1);
  expect(card.y).toBeGreaterThanOrEqual(map.y);
  expect(card.y + card.height).toBeLessThanOrEqual(map.y + map.height + 1);
  if (viewport.width > 760) {
    const rank = await page.locator(".rank-panel").boundingBox();
    const dossier = await page.locator(".dossier").boundingBox();
    if (!rank || !dossier) throw new Error("Panel geometry is unavailable");
    expect(card.x).toBeGreaterThanOrEqual(rank.x + rank.width);
    expect(card.x + card.width).toBeLessThanOrEqual(dossier.x);
  }
});
