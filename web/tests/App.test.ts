import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import App from "../src/App.vue";
import Inspector from "../src/components/Inspector.vue";
import type { Fixture } from "../src/types";

vi.mock("../src/live-check-api", () => ({ checkDocument: vi.fn() }));
import { checkDocument } from "../src/live-check-api";

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

describe("header controls on the default upload view", () => {
  it("opens the help modal with no result loaded", async () => {
    // Regression: HelpModal was mounted only when a fixture or a live
    // result existed, so on the (new) default upload landing view the Help
    // button silently did nothing.
    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.find('[data-testid="help-modal"]').exists()).toBe(false);
    await wrapper.find('[data-testid="help-button"]').trigger("click");
    expect(wrapper.find('[data-testid="help-modal"]').exists()).toBe(true);
  });

  it("hides the tour trigger in upload mode and shows it in browse mode", async () => {
    // Every tour step targets a fixture-browser selector; none of them
    // exist on the upload view, so the tour is only offered where it works.
    global.fetch = vi.fn((url: string) =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(url === "/fixtures/index.json" ? ["fixture-a"] : minimalFixture("fixture-a")),
      } as Response)
    ) as unknown as typeof fetch;

    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.find(".tour-btn").exists()).toBe(false);

    await wrapper.find(".sample-link").trigger("click");
    await flushPromises();
    expect(wrapper.find(".tour-btn").exists()).toBe(true);
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

    // App now defaults to the upload view (Task 7) — switch to browse mode
    // (as a real user would via the "try a sample fixture" link) so the
    // fixture-switch behaviour under test actually engages.
    await wrapper.find(".sample-link").trigger("click");
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

describe("view navigation", () => {
  const fetchWithFixtures = () =>
    vi.fn((url: string) =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            url === "/fixtures/index.json" ? ["fixture-a"] : minimalFixture("fixture-a"),
          ),
      } as Response),
    ) as unknown as typeof fetch;

  it("offers a way back to the upload view from browse mode", async () => {
    global.fetch = fetchWithFixtures();
    const wrapper = mount(App);
    await flushPromises();

    await wrapper.find(".sample-link").trigger("click");
    await flushPromises();
    expect(wrapper.find(".fixture-nav").exists()).toBe(true);

    await wrapper.find('[data-testid="nav-check"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-testid="ai-output-input"]').exists()).toBe(true);
    expect(wrapper.find(".fixture-nav").exists()).toBe(false);
  });

  it("surfaces a live result that resolves after the user switched to browse", async () => {
    global.fetch = fetchWithFixtures();
    let resolveCheck!: (v: Fixture) => void;
    (checkDocument as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise<Fixture>((r) => { resolveCheck = r; }),
    );

    const wrapper = mount(App);
    await flushPromises();

    await wrapper.find('[data-testid="ai-output-input"]').setValue("a live claim");
    const fileInput = wrapper.find('[data-testid="reference-file-input"]');
    Object.defineProperty(fileInput.element, "files", {
      value: [new File(["doc body"], "policy.txt", { type: "text/plain" })],
      writable: false,
    });
    await fileInput.trigger("change");
    await wrapper.find('[data-testid="submit-check"]').trigger("click");

    // User navigates away to browse while the check is still running.
    await wrapper.find('[data-testid="nav-browse"]').trigger("click");
    await flushPromises();
    expect((wrapper.vm as unknown as { mode: string }).mode).toBe("browse");

    // The check now resolves.
    resolveCheck(minimalFixture("live-check"));
    await flushPromises();

    // The arriving result wins: mode is forced back to upload and the live
    // result is displayed rather than silently discarded.
    expect((wrapper.vm as unknown as { mode: string }).mode).toBe("upload");
    const inspector = wrapper.findComponent(Inspector);
    expect(inspector.exists()).toBe(true);
    expect((inspector.props("fixture") as Fixture).fixture_id).toBe("live-check");
  });

  it("keeps a completed live result recoverable behind browse mode", async () => {
    global.fetch = fetchWithFixtures();
    (checkDocument as ReturnType<typeof vi.fn>).mockResolvedValue(minimalFixture("live-check"));

    const wrapper = mount(App);
    await flushPromises();

    await wrapper.find('[data-testid="ai-output-input"]').setValue("a live claim");
    const fileInput = wrapper.find('[data-testid="reference-file-input"]');
    Object.defineProperty(fileInput.element, "files", {
      value: [new File(["doc body"], "policy.txt", { type: "text/plain" })],
      writable: false,
    });
    await fileInput.trigger("change");
    await wrapper.find('[data-testid="submit-check"]').trigger("click");
    await flushPromises();
    expect(wrapper.findComponent(Inspector).props("fixture") as Fixture).toMatchObject({
      fixture_id: "live-check",
    });

    await wrapper.find('[data-testid="nav-browse"]').trigger("click");
    await flushPromises();

    // switchToBrowse must not null the completed result.
    expect(
      ((wrapper.vm as unknown as { liveResult: Fixture | null }).liveResult as Fixture).fixture_id,
    ).toBe("live-check");

    // nav-check is the "start fresh" path: it does null it.
    await wrapper.find('[data-testid="nav-check"]').trigger("click");
    await flushPromises();
    expect((wrapper.vm as unknown as { liveResult: Fixture | null }).liveResult).toBeNull();
  });

  it("keeps the typed AI output across a trip to browse and back", async () => {
    global.fetch = fetchWithFixtures();
    const wrapper = mount(App);
    await flushPromises();

    await wrapper.find('[data-testid="ai-output-input"]').setValue("my draft claim");
    await wrapper.find('[data-testid="nav-browse"]').trigger("click");
    await flushPromises();
    await wrapper.find('[data-testid="nav-check"]').trigger("click");
    await flushPromises();

    expect((wrapper.find('[data-testid="ai-output-input"]').element as HTMLTextAreaElement).value).toBe(
      "my draft claim",
    );
  });
});
