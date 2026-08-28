import { test, expect } from "@playwright/test";

test("live check: upload flow renders claims from a mocked API response", async ({ page }) => {
  await page.route("**/check", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ai_output: "Medical is covered up to $10,000.",
        source: {
          sections: [
            { id: "s1", page: 1, char_start: 0, char_end: 40, text: "Medical expenses covered up to $10,000." },
          ],
        },
        claims: [
          {
            id: "c1",
            text: "Medical is covered up to $10,000.",
            label: "grounded",
            evidence_span_ids: ["s1"],
            quote: "covered up to $10,000",
            page: 1,
            rationale: "",
          },
        ],
        groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
        verifier_model: "claude-haiku-4-5-20251001",
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByTestId("ai-output-input")).toBeVisible();

  await page.getByTestId("ai-output-input").fill("Medical is covered up to $10,000.");
  await page.getByTestId("reference-file-input").setInputFiles({
    name: "policy.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Medical expenses covered up to $10,000."),
  });
  await page.getByTestId("submit-check").click();

  await expect(page.getByText("Medical is covered up to $10,000.")).toBeVisible();
});

test("live check: server error surfaces the returned detail message", async ({ page }) => {
  await page.route("**/check", async (route) => {
    await route.fulfill({
      status: 429,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Today's free checks are used up. Try again tomorrow." }),
    });
  });

  await page.goto("/");
  await page.getByTestId("ai-output-input").fill("x");
  await page.getByTestId("reference-file-input").setInputFiles({
    name: "policy.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("y"),
  });
  await page.getByTestId("submit-check").click();

  await expect(page.getByTestId("upload-error")).toContainText("free checks are used up");
});

test("live check: sample link switches to the fixture browser", async ({ page }) => {
  await page.goto("/");
  await page.getByText("No document handy? Try a sample fixture instead.").click();
  await expect(page.locator(".fixture-nav")).toBeVisible();
});

test("live check: help modal opens on the default landing view, before any result", async ({ page }) => {
  // Regression: HelpModal was mounted only once a fixture or live result
  // existed, so the header's Help button silently did nothing on the
  // upload-first landing view.
  await page.goto("/");
  await expect(page.getByTestId("ai-output-input")).toBeVisible();
  await expect(page.getByTestId("help-modal")).toHaveCount(0);

  await page.getByTestId("help-button").click();
  await expect(page.getByTestId("help-modal")).toBeVisible();
  await expect(page.getByTestId("verifier-table")).toHaveCount(0);
  await expect(page.getByTestId("scope-declaration")).toBeVisible();
});

test("live check: the guided tour is only offered in browse mode", async ({ page }) => {
  // Every tour step targets a fixture-browser selector, none of which exist
  // on the upload view.
  await page.addInitScript(() => localStorage.setItem("gi-tour-seen", "1"));
  await page.goto("/");
  await expect(page.locator(".tour-btn")).toHaveCount(0);

  await page.getByText("No document handy? Try a sample fixture instead.").click();
  await expect(page.locator(".tour-btn")).toBeVisible();
});

test("live check: the sample view has a way back to document upload", async ({ page }) => {
  // Entering browse mode auto-starts the driver.js tour on first fixture load;
  // its full-page SVG overlay intercepts the nav click. Suppress it, matching
  // the "guided tour is only offered in browse mode" spec above.
  await page.addInitScript(() => localStorage.setItem("gi-tour-seen", "1"));
  await page.goto("/");
  await page.getByText("No document handy? Try a sample fixture instead.").click();
  await expect(page.locator(".fixture-nav")).toBeVisible();

  await page.getByTestId("nav-check").click();
  await expect(page.getByTestId("ai-output-input")).toBeVisible();
});

test("live check: 'Check a document' clears a live result and returns a fresh form", async ({ page }) => {
  await page.route("**/check", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ai_output: "Medical is covered up to $10,000.",
        source: { sections: [{ id: "s1", page: 1, char_start: 0, char_end: 40, text: "Medical expenses covered up to $10,000." }] },
        claims: [{ id: "c1", text: "Medical is covered up to $10,000.", label: "grounded", evidence_span_ids: ["s1"], quote: "Medical expenses", page: 1, rationale: "" }],
        groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
        verifier_model: "claude-haiku-4-5-20251001",
      }),
    });
  });

  await page.goto("/");
  await page.getByTestId("ai-output-input").fill("Medical is covered up to $10,000.");
  await page.getByTestId("reference-file-input").setInputFiles({
    name: "policy.txt", mimeType: "text/plain", buffer: Buffer.from("Medical expenses covered up to $10,000."),
  });
  await page.getByTestId("submit-check").click();
  await expect(page.getByTestId("output-panel")).toBeVisible();

  await page.getByTestId("nav-check").click();
  await expect(page.getByTestId("ai-output-input")).toBeVisible();
  await expect(page.getByTestId("output-panel")).toHaveCount(0);
});

test("live check: the reliability caveat is visible on the result without opening Help", async ({ page }) => {
  await page.route("**/check", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ai_output: "Medical is covered up to $10,000.",
        source: { sections: [{ id: "s1", page: 1, char_start: 0, char_end: 40, text: "Medical expenses covered up to $10,000." }] },
        claims: [{ id: "c1", text: "Medical is covered up to $10,000.", label: "grounded", evidence_span_ids: ["s1"], quote: "Medical expenses", page: 1, rationale: "" }],
        groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
        verifier_model: "claude-haiku-4-5-20251001",
      }),
    });
  });

  await page.goto("/");
  await page.getByTestId("ai-output-input").fill("Medical is covered up to $10,000.");
  await page.getByTestId("reference-file-input").setInputFiles({
    name: "policy.txt", mimeType: "text/plain", buffer: Buffer.from("Medical expenses covered up to $10,000."),
  });
  await page.getByTestId("submit-check").click();

  await expect(page.getByTestId("live-result-banner")).toBeVisible();
  await expect(page.getByTestId("live-result-banner")).toContainText("research signal");
});
