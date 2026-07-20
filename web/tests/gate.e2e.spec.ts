import { test, expect } from "@playwright/test";

test.describe("access gate", () => {
  test("wrong email is rejected with generic copy", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[name="email"]', "someone@example.com");
    await page.click('button[type="submit"]');
    await expect(page.locator("body")).toContainText("Access is limited");
    await expect(page.locator("body")).not.toContainText("test.user");
  });

  test("correct email sets a cookie and loads the app", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[name="email"]', "test.user@gmail.com");
    await page.click('button[type="submit"]');
    await expect(page.locator("h1")).toContainText("Grounding Inspector");
    await expect(page.locator(".fixture-nav")).toBeVisible();
  });

  test("gate cannot be bypassed by requesting a fixture URL directly", async ({ page, context }) => {
    // No cookie set — direct fixture request must not return fixture JSON.
    const response = await page.goto("/fixtures/covermore-pds-01.json");
    const body = await response?.text();
    expect(body).not.toContain("fixture_id");
  });

  test("a valid cookie holder's asset requests still load", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[name="email"]', "test.user@gmail.com");
    await page.click('button[type="submit"]');
    // App has fully loaded, meaning its JS/CSS asset requests (also gated by
    // path = "/*") succeeded — confirms the gate's context.next() pass-through
    // doesn't just work for HTML/fixtures but for hashed build assets too.
    await expect(page.locator(".fixture-nav")).toBeVisible();
    const failedRequests: string[] = [];
    page.on("response", (res) => {
      if (res.url().includes("/assets/") && !res.ok()) failedRequests.push(res.url());
    });
    await page.reload();
    expect(failedRequests).toEqual([]);
  });
});
