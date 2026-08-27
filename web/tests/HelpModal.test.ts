import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import HelpModal from "../src/components/HelpModal.vue";
import type { Fixture } from "../src/types";

const baseFixture = (): Fixture => ({
  fixture_id: "travel-pds-01",
  source: { title: "T", sections: [] },
  ai_output: "x",
  claims: [
    { id: "c1", text: "Backed claim.", label: "grounded", evidence_span_ids: [], quote: null, page: null, rationale: "" },
  ],
  groundedness: { score: 100, n_grounded: 1, n_partial: 0, n_unsupported: 0 },
});

const liveFixture = (): Fixture => ({
  ...baseFixture(),
  fixture_id: "live-check",
  live_disclosure:
    "This check used the same Claude verifier (claude-haiku-4-5-20251001) as Grounding Inspector's other checks.",
});

describe("HelpModal", () => {
  it("renders nothing while closed", () => {
    const wrapper = mount(HelpModal, { props: { fixture: baseFixture(), open: false } });
    expect(wrapper.find('[data-testid="help-modal"]').exists()).toBe(false);
  });

  it("shows the MiniCheck verifier table and domain note for a browsed fixture", () => {
    const wrapper = mount(HelpModal, { props: { fixture: baseFixture(), open: true } });
    expect(wrapper.find('[data-testid="verifier-table"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="verifier-table"]').text()).toContain("0.69");
    expect(wrapper.find('[data-testid="domain-note"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="live-disclosure"]').exists()).toBe(false);
  });

  it("shows the live disclosure and hides the fixture-only accuracy claims for a live result", () => {
    // Regression: the MiniCheck/Haiku recall+kappa table used to render
    // unconditionally, directly contradicting the live_disclosure text a few
    // lines below it — which says no independent accuracy validation exists
    // for the live verifier. The plan's global constraint is that a live
    // check carries no scorecard.
    const wrapper = mount(HelpModal, { props: { fixture: liveFixture(), open: true } });
    const html = wrapper.html();

    expect(wrapper.find('[data-testid="live-disclosure"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="live-disclosure"]').text()).toContain("This check.");
    expect(wrapper.find('[data-testid="live-disclosure"]').text()).toContain("claude-haiku-4-5-20251001");

    expect(wrapper.find('[data-testid="verifier-table"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="domain-note"]').exists()).toBe(false);
    expect(html).not.toContain("0.69");
    expect(html).not.toContain("RAGTruth");
    expect(html).not.toContain("Landis");
  });

  it("renders a generic explanation with no fixture at all", () => {
    // The Help button is present on the default upload landing view, before
    // any check has run — the modal must open and say something useful
    // rather than silently no-op or throw on a missing fixture.
    const wrapper = mount(HelpModal, { props: { open: true } });
    expect(wrapper.find('[data-testid="help-modal"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="scope-declaration"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("What this measures");
    // No fixture means no validated numbers to show and no example claims.
    expect(wrapper.find('[data-testid="verifier-table"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="domain-note"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="live-disclosure"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Example from this fixture");
    expect(wrapper.text()).toContain("no independent accuracy validation yet");
  });
});
