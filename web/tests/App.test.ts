import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import App from "../src/App.vue";
import Inspector from "../src/components/Inspector.vue";
import type { Fixture } from "../src/types";

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
  );
  // Mark the guided tour (Task 1) as already seen so startTour() (driver.js)
  // never fires during these tests — it mutates the DOM outside Vue's own
  // vdom via document.body, unrelated to the layout-shift fix under test.
  localStorage.setItem("gi-tour-seen", "1");
});

const minimalFixture = (id: string): Fixture => ({
  fixture_id: id,
  source: { title: "T", sections: [] },
  ai_output: "x",
  claims: [],
  groundedness: { score: 0, n_grounded: 0, n_partial: 0, n_unsupported: 0 },
  scorecard: {
    recall: 0, recall_ci: [0, 0], false_negatives: 0, n_positive: 0,
    citation_precision: null, cohen_kappa: null, balanced_accuracy: null,
    validated_on: "x", domain_note: "y",
  },
});

describe("App disclaimer", () => {
  it("renders a persistent not-an-official-service disclaimer", async () => {
    const wrapper = mount(App);
    await new Promise((r) => setTimeout(r, 0));
    expect(wrapper.find('[data-testid="disclaimer"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="disclaimer"]').text().toLowerCase()).toContain("not an official");
  });
});

describe("layout stability on fixture switch", () => {
  it("main survives the collapse when switching from a loaded fixture to a loading one", async () => {
    // Regression: watch(selectedId, ...) sets fixture.value = null while
    // loading, collapsing <main> down to the single-line "Loading..." state
    // before the full Inspector re-renders, causing a visible layout jump on
    // every fixture switch. The fix reserves height via a CSS rule on `main`
    // in App.vue's <style scoped> block (min-height: 480px) so the collapse
    // is no longer visible.
    //
    // Vitest does not process component <style> blocks during tests by
    // default (test.css.include is empty — confirmed via node_modules/vitest
    // /dist/config.d.ts), so the min-height rule is never injected into the
    // test DOM: getComputedStyle() and the CSSOM both come back empty
    // regardless of the fix, under both happy-dom and jsdom. The CSS fix
    // itself is verified by inspecting the production build output (the
    // compiled rule appears as `main[data-v-...]{min-height:480px}`) and by
    // manual check in the browser (playwright-cli sampling of main's
    // bounding-box height during real fixture switches) — not by this unit
    // test. What this test does verify: the actual switch code path runs —
    // watch(selectedId) really fires a second time and really resets
    // fixture.value to null — and <main> (the element the fix's CSS rule
    // targets) survives that reset rather than being torn down, matching the
    // sibling Act Alike project's CorpusStats placeholder-survival pattern
    // (structural DOM presence, not computed CSS).
    let resolveFixtureB: (value: Response) => void = () => {};
    global.fetch = vi.fn((url: string) => {
      if (url === "/fixtures/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(["fixture-a", "fixture-b"]),
        } as Response);
      }
      if (url === "/fixtures/fixture-a.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(minimalFixture("fixture-a")),
        } as Response);
      }
      // fixture-b's fetch is held open so the loading window from the
      // *switch* (not the first load) is observable.
      return new Promise<Response>((resolve) => {
        resolveFixtureB = resolve;
      });
    }) as unknown as typeof fetch;

    const wrapper = mount(App);
    await flushPromises();

    // First fixture has fully loaded — Inspector is actually rendered.
    expect(wrapper.findComponent(Inspector).exists()).toBe(true);

    // Click the fixture-b nav button — real user interaction, triggers
    // watch(selectedId) for real (not a direct vm mutation).
    const fixtureBButton = wrapper
      .findAll(".fixture-btn")
      .find((btn) => btn.text() === "fixture-b");
    expect(fixtureBButton).toBeTruthy();
    await fixtureBButton!.trigger("click");
    await flushPromises();

    // fixture-b's fetch is still pending, so watch(selectedId) has reset
    // fixture.value to null — Inspector must be gone (proves the watcher
    // really ran) while <main> and the loading indicator survive the reset.
    expect(wrapper.findComponent(Inspector).exists()).toBe(false);
    expect(wrapper.find("main").exists()).toBe(true);
    expect(wrapper.find(".loading").exists()).toBe(true);
    expect(wrapper.find(".loading").text()).toContain("Loading");

    // Let the held fetch resolve so it doesn't leak a dangling promise.
    resolveFixtureB({ ok: true, json: () => Promise.resolve(minimalFixture("fixture-b")) } as Response);
    await flushPromises();
  });
});
