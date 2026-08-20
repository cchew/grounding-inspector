import { test, expect } from "@playwright/test";
import { readFile } from "fs/promises";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const here = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Fixture data mirrored here so tests are self-documenting and assertions are
// driven by the source of truth, not magic numbers.
// ---------------------------------------------------------------------------
const FIXTURES = {
  "travel-pds-01": {
    btn: "Synthetic 01",
    claimCount: 3,
    score: 50,
    groundedness: { grounded: 1, partial: 1, unsupported: 1 },
    claims: [
      { id: "c1", label: "unsupported", spans: [] },
      { id: "c2", label: "grounded",    spans: ["s4_2"] },
      { id: "c3", label: "partial",     spans: ["s7_1"] },
    ],
  },
  "travel-pds-02": {
    btn: "Synthetic 02",
    claimCount: 4,
    score: 63,
    groundedness: { grounded: 2, partial: 1, unsupported: 1 },
    claims: [
      { id: "c1", label: "partial",     spans: ["s5_1"] },
      { id: "c2", label: "grounded",    spans: ["s5_2"] },
      { id: "c3", label: "unsupported", spans: [] },
      { id: "c4", label: "grounded",    spans: ["s5_1"] },
    ],
  },
  "travel-pds-03": {
    btn: "Synthetic 03",
    claimCount: 5,
    score: 40,
    groundedness: { grounded: 1, partial: 2, unsupported: 2 },
    claims: [
      { id: "c1", label: "partial",     spans: ["s3_1"] },
      { id: "c2", label: "partial",     spans: ["s3_2"] },
      { id: "c3", label: "grounded",    spans: ["s6_1"] },
      { id: "c4", label: "unsupported", spans: [] },
      { id: "c5", label: "unsupported", spans: [] },
    ],
  },
  "covermore-pds-01": {
    btn: "Cover-More",
    claimCount: 5,
    score: 40,
    groundedness: { grounded: 1, partial: 2, unsupported: 2 },
    claims: [
      { id: "c1", label: "unsupported", spans: [] },
      { id: "c2", label: "partial",     spans: ["cov_5_table"] },
      { id: "c3", label: "grounded",    spans: ["cov_5_table"] },
      { id: "c4", label: "partial",     spans: ["cov_5_table"] },
      { id: "c5", label: "unsupported", spans: [] },
    ],
  },
  "budgetdirect-pds-01": {
    btn: "Budget Direct",
    claimCount: 4,
    score: 63,
    groundedness: { grounded: 2, partial: 1, unsupported: 1 },
    claims: [
      { id: "c1", label: "grounded",    spans: ["bd_3_limit"] },
      { id: "c2", label: "partial",     spans: ["bd_3_excl_redundancy"] },
      { id: "c3", label: "unsupported", spans: [] },
      { id: "c4", label: "grounded",    spans: ["bd_3_limit"] },
    ],
  },
} as const;

type FixtureId = keyof typeof FIXTURES;

// ---------------------------------------------------------------------------
// Suppress the first-visit guided tour (driver.js, see src/tour.ts) for every
// test in this file. Each Playwright test gets a fresh browser context, so
// localStorage is empty and the tour would otherwise auto-fire on every
// page.goto("/") and open a full-viewport overlay that intercepts pointer
// events outside whatever element it's currently highlighting -- unrelated
// to whatever the test is actually checking. Same workaround as
// tests/App.test.ts's beforeEach, applied at the page level via
// addInitScript since these tests drive a real browser, not a Vue mount.
// ---------------------------------------------------------------------------
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gi-tour-seen", "1"));
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
async function navigateTo(page: import("@playwright/test").Page, id: FixtureId) {
  const fx = FIXTURES[id];
  await page.getByRole("button", { name: fx.btn }).click();
  // Wait for first claim to confirm the fixture loaded
  await page.waitForSelector(`[data-claim="c1"]`, { timeout: 10000 });
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------
test.describe("API", () => {
  test("fixture index lists all 5 IDs", async ({ request }) => {
    const res = await request.get("/fixtures/index.json");
    expect(res.ok()).toBe(true);
    const ids = await res.json();
    expect(ids).toHaveLength(5);
    for (const id of Object.keys(FIXTURES)) {
      expect(ids).toContain(id);
    }
  });

  for (const [id, fx] of Object.entries(FIXTURES) as [FixtureId, typeof FIXTURES[FixtureId]][]) {
    test(`fixtures/${id}.json has correct claim count and labels`, async ({ request }) => {
      const res = await request.get(`/fixtures/${id}.json`);
      expect(res.ok()).toBe(true);
      const body = await res.json();
      expect(body.fixture_id).toBe(id);
      expect(body.claims).toHaveLength(fx.claimCount);
      for (const expected of fx.claims) {
        const actual = body.claims.find((c: { id: string }) => c.id === expected.id);
        expect(actual, `claim ${expected.id}`).toBeDefined();
        expect(actual.label).toBe(expected.label);
        expect(actual.evidence_span_ids).toEqual(expected.spans);
      }
    });
  }

  test("unknown fixture returns 404", async ({ request }) => {
    const res = await request.get("/fixtures/nonexistent.json");
    expect(res.status()).toBe(404);
  });

  test("scorecard recall is 0.69 on all fixtures", async ({ request }) => {
    for (const id of Object.keys(FIXTURES)) {
      const res = await request.get(`/fixtures/${id}.json`);
      const body = await res.json();
      expect(body.scorecard.recall, id).toBeCloseTo(0.69, 2);
    }
  });
});

// ---------------------------------------------------------------------------
// Page shell
// ---------------------------------------------------------------------------
test.describe("Page shell", () => {
  test("title is Grounding Inspector", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Grounding Inspector");
  });

  test("subtitle describes claim grounding purpose", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".subtitle")).toContainText("claims are backed by document evidence");
  });

  test("all 5 fixture nav buttons are present", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    const buttons = page.locator(".fixture-btn");
    await expect(buttons).toHaveCount(5);
    for (const fx of Object.values(FIXTURES)) {
      await expect(page.getByRole("button", { name: fx.btn })).toBeVisible();
    }
  });

  test("first fixture loads automatically on mount", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="output-panel"]', { timeout: 8000 });
    await expect(page.locator('[data-testid="output-panel"]')).toContainText("OUTPUT");
    await expect(page.locator('[data-testid="help-button"]')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Help modal
// ---------------------------------------------------------------------------
test.describe("Help modal", () => {
  test("opens on help button click and closes on close button click", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="help-button"]', { timeout: 8000 });
    await expect(page.locator('[data-testid="help-modal"]')).not.toBeVisible();
    await page.click('[data-testid="help-button"]');
    await expect(page.locator('[data-testid="help-modal"]')).toBeVisible();
    await page.click('[data-testid="help-close"]');
    await expect(page.locator('[data-testid="help-modal"]')).not.toBeVisible();
  });

  test("verdict legend shows an example from the active fixture", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "covermore-pds-01");
    await page.click('[data-testid="help-button"]');
    await expect(page.locator('[data-testid="help-modal"]')).toContainText("Cameras are covered for up to $4,000");
  });

  test("scope declaration is present", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="help-button"]', { timeout: 8000 });
    await page.click('[data-testid="help-button"]');
    await expect(page.locator('[data-testid="scope-declaration"]')).toContainText("have not been verified as false");
  });
});

// ---------------------------------------------------------------------------
// Fixture switching — scorecard counts and score
// ---------------------------------------------------------------------------
test.describe("Fixture switching", () => {
  for (const [id, fx] of Object.entries(FIXTURES) as [FixtureId, typeof FIXTURES[FixtureId]][]) {
    test(`${id}: OUTPUT panel shows correct groundedness counts`, async ({ page }) => {
      await page.goto("/");
      await page.waitForSelector(".fixture-btn", { timeout: 5000 });
      await navigateTo(page, id);
      const outputPanel = page.locator('[data-testid="output-panel"]');
      await expect(outputPanel).toContainText(`${fx.groundedness.grounded} grounded`);
      await expect(outputPanel).toContainText(`${fx.groundedness.partial} partial`);
      await expect(outputPanel).toContainText(`${fx.groundedness.unsupported} unsupported`);
    });

    test(`${id}: OUTPUT panel shows groundedness score ${fx.score}/100`, async ({ page }) => {
      await page.goto("/");
      await page.waitForSelector(".fixture-btn", { timeout: 5000 });
      await navigateTo(page, id);
      await expect(page.locator('[data-testid="output-panel"]')).toContainText(`${fx.score}/100`);
    });

    test(`${id}: help modal shows recall 0.69 when opened`, async ({ page }) => {
      await page.goto("/");
      await page.waitForSelector(".fixture-btn", { timeout: 5000 });
      await navigateTo(page, id);
      await page.click('[data-testid="help-button"]');
      await expect(page.locator('[data-testid="verifier-table"]')).toContainText("0.69");
      await page.click('[data-testid="help-close"]');
    });
  }
});

// ---------------------------------------------------------------------------
// Claim label classes
// ---------------------------------------------------------------------------
test.describe("Claim label classes", () => {
  for (const [id, fx] of Object.entries(FIXTURES) as [FixtureId, typeof FIXTURES[FixtureId]][]) {
    test(`${id}: each claim has the correct label CSS class`, async ({ page }) => {
      await page.goto("/");
      await page.waitForSelector(".fixture-btn", { timeout: 5000 });
      await navigateTo(page, id);
      for (const c of fx.claims) {
        await expect(
          page.locator(`[data-claim="${c.id}"]`),
          `${id} ${c.id}`
        ).toHaveClass(new RegExp(`label-${c.label}`));
      }
    });
  }
});

// ---------------------------------------------------------------------------
// Span linking — grounded/partial claims activate spans; unsupported shows no-span
// ---------------------------------------------------------------------------
test.describe("Span linking", () => {
  for (const [id, fx] of Object.entries(FIXTURES) as [FixtureId, typeof FIXTURES[FixtureId]][]) {
    // Claims with spans: clicking should activate the first span and hide no-span
    for (const c of fx.claims.filter(c => c.spans.length > 0)) {
      test(`${id} ${c.id} (${c.label}): activates span ${c.spans[0]}`, async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector(".fixture-btn", { timeout: 5000 });
        await navigateTo(page, id);
        await page.waitForSelector(`[data-span="${c.spans[0]}"]`, { timeout: 5000 });
        await page.click(`[data-claim="${c.id}"]`);
        await expect(page.locator(`[data-span="${c.spans[0]}"]`)).toHaveClass(
          new RegExp(`span-active-${c.label}`)
        );
        await expect(page.locator('[data-testid="no-span"]')).not.toBeVisible();
      });
    }

    // Claims without spans: clicking shows no-span message
    for (const c of fx.claims.filter(c => c.spans.length === 0)) {
      test(`${id} ${c.id} (unsupported, no span): shows no-span message`, async ({ page }) => {
        await page.goto("/");
        await page.waitForSelector(".fixture-btn", { timeout: 5000 });
        await navigateTo(page, id);
        await page.click(`[data-claim="${c.id}"]`);
        await expect(page.locator('[data-testid="no-span"]')).toBeVisible();
      });
    }
  }

  test("covermore-pds-01 c2: shows evidence note for numeric-mismatch claim", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "covermore-pds-01");
    await page.click('[data-claim="c2"]');
    await expect(page.locator('[data-testid="evidence-note"]')).toBeVisible();
    await expect(page.locator('[data-testid="evidence-note"]')).toContainText("$5,000");
  });

  test("covermore-pds-01 c3: evidence note shows the grounded claim's own rationale too", async ({ page }) => {
    // All 21 committed claims across all 5 fixtures have non-empty rationale --
    // 3 are machine-derived from the numeric check (Task 6), the other 18 are
    // pre-existing hand-authored text independently verified accurate during
    // planning. The banner is designed to show for any claim with rationale,
    // not just numeric-mismatch ones -- this was always the intent (surface
    // "why" for every verdict, not just the negative "unsupported" case),
    // so grounded claims showing their rationale too is correct behaviour,
    // not a gap. This test replaces an earlier, incorrect assumption that a
    // grounded claim would have no rationale to show.
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "covermore-pds-01");
    await page.click('[data-claim="c3"]');
    await expect(page.locator('[data-testid="evidence-note"]')).toBeVisible();
    await expect(page.locator('[data-testid="evidence-note"]')).toContainText("$4,000 per item for Camera");
  });
});

// ---------------------------------------------------------------------------
// Design system tokens — chip background colours are set (not transparent)
// ---------------------------------------------------------------------------
test.describe("Design system tokens", () => {
  test("grounded chip has non-transparent background", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="output-panel"]', { timeout: 8000 });
    const bg = await page.locator('[data-testid="output-panel"] .label-chip.grounded').evaluate(
      el => getComputedStyle(el).backgroundColor
    );
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bg).not.toBe("transparent");
  });

  test("partial chip has non-transparent background", async ({ page }) => {
    // Navigate to a fixture with a partial claim
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "travel-pds-01");
    const bg = await page.locator('[data-testid="output-panel"] .label-chip.partial').evaluate(
      el => getComputedStyle(el).backgroundColor
    );
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bg).not.toBe("transparent");
  });

  test("grounded and partial chips have different background colours", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "travel-pds-01");
    const panel = page.locator('[data-testid="output-panel"]');
    const greenBg = await panel.locator(".label-chip.grounded").evaluate(
      el => getComputedStyle(el).backgroundColor
    );
    const amberBg = await panel.locator(".label-chip.partial").evaluate(
      el => getComputedStyle(el).backgroundColor
    );
    expect(greenBg).not.toBe(amberBg);
  });

  test("unsupported chip in claim list has non-transparent background", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "travel-pds-01");
    // c1 is unsupported
    const bg = await page.locator('[data-claim="c1"] .label-badge.unsupported').evaluate(
      el => getComputedStyle(el).backgroundColor
    );
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bg).not.toBe("transparent");
  });

  test("active span has non-transparent background (accent highlight)", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "travel-pds-01");
    await page.waitForSelector('[data-span="s4_2"]', { timeout: 5000 });
    await page.click('[data-claim="c2"]');
    const bg = await page.locator('[data-span="s4_2"]').evaluate(
      el => getComputedStyle(el).backgroundColor
    );
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    expect(bg).not.toBe("transparent");
  });
});

// ---------------------------------------------------------------------------
// Fixture switching clears previous state
// ---------------------------------------------------------------------------
test.describe("State reset on fixture switch", () => {
  test("switching fixture deactivates the previously active span", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });

    // Activate a span on travel-pds-01
    await navigateTo(page, "travel-pds-01");
    await page.waitForSelector('[data-span="s4_2"]', { timeout: 5000 });
    await page.click('[data-claim="c2"]');
    await expect(page.locator('[data-span="s4_2"]')).toHaveClass(/span-active/);

    // Switch to another fixture — span element is replaced, no-span should be hidden
    await navigateTo(page, "travel-pds-02");
    await expect(page.locator('[data-testid="no-span"]')).not.toBeVisible();
  });

  test("active fixture button gets the active class", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "covermore-pds-01");
    await expect(page.getByRole("button", { name: "Cover-More" })).toHaveClass(/active/);
    await expect(page.getByRole("button", { name: "Synthetic 01" })).not.toHaveClass(/active/);
  });
});

// ---------------------------------------------------------------------------
// Omission panel — post-regeneration: all 5 fixtures now carry real
// EmbedKDECheck omissions data (Task 8). Assertions are structural, not
// value-exact -- which sections get flagged depends on the real pretrained
// model, not something this test suite can pin down in advance.
// ---------------------------------------------------------------------------
test.describe("Omission panel (post-regeneration)", () => {
  for (const [id, fx] of Object.entries(FIXTURES) as [FixtureId, typeof FIXTURES[FixtureId]][]) {
    test(`${id}: omission caveat discloses unvalidated status`, async ({ page }) => {
      await page.goto("/");
      await page.waitForSelector(".fixture-btn", { timeout: 5000 });
      await navigateTo(page, id);
      const caveats = page.locator('[data-testid^="omission-caveat-"]');
      await expect(caveats.first()).toContainText("unvalidated");
    });

    test(`${id}: clicking a flagged section (if any) highlights it in the source doc`, async ({ page }) => {
      await page.goto("/");
      await page.waitForSelector(".fixture-btn", { timeout: 5000 });
      await navigateTo(page, id);
      const rows = page.locator("[data-omission]");
      const count = await rows.count();
      test.skip(count === 0, `${id}: no sections flagged for this fixture`);
      const firstId = await rows.first().getAttribute("data-omission");
      await rows.first().click();
      await expect(page.locator(`[data-span="${firstId}"]`)).toHaveClass(/span-active-omission/);
    });
  }

  // -------------------------------------------------------------------------
  // travel-pds-01's committed fixture only carries a real embedkde omissions
  // entry (comprehensiveness_qa requires live API spend, so it isn't
  // regenerated for every fixture and must never be hand-faked into the
  // committed file -- see docs/superpowers/plans/
  // 2026-08-19-grounding-inspector-comprehensiveness-recall-qa.md). This test
  // intercepts the fixture request and splices a synthetic
  // comprehensiveness_qa entry into the response in memory, so the on-disk
  // fixture stays real and this test survives a future real regeneration.
  // -------------------------------------------------------------------------
  test("travel-pds-01: renders both an embedkde and a comprehensiveness_qa panel", async ({ page }) => {
    const fixturePath = join(here, "..", "..", "fixtures", "travel-pds-01.json");
    const fixture = JSON.parse(await readFile(fixturePath, "utf-8"));
    fixture.omissions = [
      ...fixture.omissions,
      {
        method: "comprehensiveness_qa",
        global_score: 1.0,
        flagged_sections: [
          {
            section_id: "s9",
            score: 1.0,
            omitted_facts: [
              {
                fact: "SYNTHETIC TEST DATA -- injected at test time via page.route(), not from a real API call or the committed fixture.",
                question: "Does the output mention this fact?",
                evidence: null,
              },
            ],
          },
        ],
        hyperparameters: { model: "claude-sonnet-4-5-20250929", flag_threshold: 0.0 },
        validated: false,
        caveat: "Comprehensiveness signals are unvalidated: no ground-truth omission labels exist for these fixtures, and flag_threshold (any single OMITTED fact flags its section) is an unadjusted default -- a single LLM misjudgment among many subclaims can flag a section. Treat a flagged span as a prompt to review the source directly, not a finding.",
      },
    ];

    await page.route("**/fixtures/travel-pds-01.json", async (route) => {
      await route.fulfill({ json: fixture });
    });

    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "travel-pds-01");
    await expect(page.locator('[data-testid="omission-panel-embedkde"]')).toBeVisible();
    await expect(page.locator('[data-testid="omission-panel-comprehensiveness_qa"]')).toBeVisible();
    await expect(page.locator('[data-testid="omission-panel-comprehensiveness_qa"]')).toContainText("SYNTHETIC TEST DATA");
  });

  // Same synthetic-injection approach as above. No committed fixture currently
  // flags any section under either method, so both entries are faked here --
  // the isolation this asserts only manifests when two panels each render a row
  // for the same section_id.
  test("travel-pds-01: an active row in one panel does not activate the same section in the other", async ({ page }) => {
    const fixturePath = join(here, "..", "..", "fixtures", "travel-pds-01.json");
    const fixture = JSON.parse(await readFile(fixturePath, "utf-8"));
    const synthetic = "SYNTHETIC TEST DATA -- injected at test time via page.route(), not from a real API call or the committed fixture.";
    fixture.omissions = [
      {
        method: "embedkde",
        global_score: 1.0,
        flagged_sections: [{ section_id: "s9", score: 1.0, top_tokens: [synthetic] }],
        hyperparameters: { pca_components: 16, kde_bandwidth: 1.0, threshold_std: 1.5 },
        validated: false,
        caveat: "Omission signals are unvalidated.",
      },
      {
        method: "comprehensiveness_qa",
        global_score: 1.0,
        flagged_sections: [{
          section_id: "s9", score: 1.0,
          omitted_facts: [{ fact: synthetic, question: "Does the output mention this fact?", evidence: null }],
        }],
        hyperparameters: { model: "claude-sonnet-4-5-20250929", flag_threshold: 0.0 },
        validated: false,
        caveat: "Comprehensiveness signals are unvalidated.",
      },
    ];

    await page.route("**/fixtures/travel-pds-01.json", async (route) => {
      await route.fulfill({ json: fixture });
    });

    await page.goto("/");
    await page.waitForSelector(".fixture-btn", { timeout: 5000 });
    await navigateTo(page, "travel-pds-01");

    const embedRow = page.locator('[data-testid="omission-panel-embedkde"] [data-omission="s9"]');
    const qaRow = page.locator('[data-testid="omission-panel-comprehensiveness_qa"] [data-omission="s9"]');

    await embedRow.click();
    await expect(embedRow).toHaveClass(/\bactive\b/);
    await expect(qaRow).not.toHaveClass(/\bactive\b/);
    // The shared source-doc highlight is still driven by either panel.
    await expect(page.locator('[data-span="s9"]')).toHaveClass(/span-active-omission/);

    await qaRow.click();
    await expect(qaRow).toHaveClass(/\bactive\b/);
    await expect(embedRow).not.toHaveClass(/\bactive\b/);
    await expect(page.locator('[data-span="s9"]')).toHaveClass(/span-active-omission/);
  });
});
