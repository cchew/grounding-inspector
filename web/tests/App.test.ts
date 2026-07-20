import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import App from "../src/App.vue";

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
  );
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
  it("main stays mounted through the collapsed loading state", async () => {
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
    // manual check in the browser — not by this unit test.
    //
    // What this test guards structurally, matching the sibling Act Alike
    // project's CorpusStats placeholder-survival pattern: <main> is the one
    // persistent wrapper the fix's CSS rule targets (a bare `main` selector,
    // not a class), and it must still be present — with the collapsed
    // "Loading..." content inside it — during the exact window the bug
    // report describes, i.e. while fixture.value is null and loading.value
    // is true, on the very first fixture load.
    const fixtureJsonPromise = new Promise<Response>(() => {
      /* held open deliberately: this test only inspects the mid-flight
         loading DOM before the fetch resolves */
    });
    global.fetch = vi.fn((url: string) => {
      if (url === "/fixtures/index.json") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(["fixture-a"]),
        } as Response);
      }
      return fixtureJsonPromise;
    }) as unknown as typeof fetch;

    const wrapper = mount(App);
    await flushPromises();

    // The index fetch has resolved (selectedId is now set) but fixture-a's
    // own fetch is still pending, so fixture.value is null and loading.value
    // is true — this is the exact collapsed state from the bug report.
    expect(wrapper.find("main").exists()).toBe(true);
    expect(wrapper.find(".loading").exists()).toBe(true);
    expect(wrapper.find(".loading").text()).toContain("Loading");
  });
});
