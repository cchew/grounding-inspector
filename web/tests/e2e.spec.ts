import { test, expect } from "@playwright/test";

test.describe("Grounding Inspector E2E", () => {
  test("fixture list API returns known fixtures", async ({ request }) => {
    const res = await request.get("/api/fixtures");
    expect(res.ok()).toBe(true);
    const ids = await res.json();
    expect(ids).toContain("travel-pds-01");
    expect(ids).toContain("covermore-pds-01");
    expect(ids).toContain("budgetdirect-pds-01");
  });

  test("fixture API serves travel-pds-01 with correct structure", async ({ request }) => {
    const res = await request.get("/api/fixtures/travel-pds-01");
    expect(res.ok()).toBe(true);
    const fx = await res.json();
    expect(fx.fixture_id).toBe("travel-pds-01");
    expect(Array.isArray(fx.claims)).toBe(true);
    expect(fx.claims.length).toBe(3);
    const unsupported = fx.claims.filter((c: { label: string }) => c.label === "unsupported");
    expect(unsupported.length).toBeGreaterThanOrEqual(1);
  });

  test("fixture API serves covermore-pds-01 (real PDS)", async ({ request }) => {
    const res = await request.get("/api/fixtures/covermore-pds-01");
    expect(res.ok()).toBe(true);
    const fx = await res.json();
    expect(fx.fixture_id).toBe("covermore-pds-01");
    expect(fx.claims.length).toBe(5);
  });

  test("unknown fixture returns 404", async ({ request }) => {
    const res = await request.get("/api/fixtures/nonexistent");
    expect(res.status()).toBe(404);
  });

  test("app page loads with correct title", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Grounding Inspector");
  });

  test("fixture selector shows multiple fixtures", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    const buttons = page.locator(".fixture-btn");
    await expect(buttons).toHaveCount(5);
  });

  test("OUTPUT and DETECTOR panels render after fixture loads", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="output-panel"]', { timeout: 8000 });
    await expect(page.locator('[data-testid="output-panel"]')).toContainText("OUTPUT");
    await expect(page.locator('[data-testid="detector-panel"]')).toContainText("DETECTOR");
  });

  test("clicking a grounded claim highlights the corresponding span in the right pane", async ({ page }) => {
    await page.goto("/");
    // Navigate to travel-pds-01 (which has c2 grounded → s4_2)
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await page.getByRole("button", { name: "Synthetic 01" }).click();
    await page.waitForSelector('[data-claim="c2"]', { timeout: 8000 });
    await page.waitForSelector('[data-span="s4_2"]', { timeout: 5000 });
    await page.click('[data-claim="c2"]');
    await expect(page.locator('[data-span="s4_2"]')).toHaveClass(/span-active/);
  });

  test("clicking the value-for-money unsupported claim shows no-span message", async ({ page }) => {
    await page.goto("/");
    // Navigate to travel-pds-01 (which has c1 unsupported with empty evidence_span_ids)
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await page.getByRole("button", { name: "Synthetic 01" }).click();
    await page.waitForSelector('[data-claim="c1"]', { timeout: 8000 });
    await page.click('[data-claim="c1"]');
    await expect(page.locator('[data-testid="no-span"]')).toBeVisible();
  });
});
