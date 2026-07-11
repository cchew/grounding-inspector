import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import Inspector from "../src/components/Inspector.vue";
import type { Fixture } from "../src/types";

const fixture: Fixture = {
  fixture_id: "t", source: { title: "T", sections: [
    { id: "s4_2", page: 12, char_start: 0, char_end: 10, text: "covered up to $10,000,000" },
  ] },
  ai_output: "x",
  claims: [
    { id: "c1", text: "value for money", label: "unsupported", evidence_span_ids: [], quote: null, page: null, rationale: "r" },
    { id: "c2", text: "medical covered", label: "grounded", evidence_span_ids: ["s4_2"], quote: "covered up to $10,000,000", page: 12, rationale: "r" },
  ],
  groundedness: { score: 50, n_grounded: 1, n_partial: 0, n_unsupported: 1 },
  scorecard: { recall: 0, recall_ci: [0, 0], false_negatives: 0, n_positive: 0, citation_precision: null, cohen_kappa: null, balanced_accuracy: null, validated_on: "x", domain_note: "y" },
};

describe("Inspector", () => {
  it("colours claims by label", () => {
    const w = mount(Inspector, { props: { fixture } });
    expect(w.get('[data-claim="c1"]').classes()).toContain("label-unsupported");
    expect(w.get('[data-claim="c2"]').classes()).toContain("label-grounded");
  });

  it("highlights the evidence span when a grounded claim is clicked", async () => {
    const w = mount(Inspector, { props: { fixture } });
    await w.get('[data-claim="c2"]').trigger("click");
    expect(w.get('[data-span="s4_2"]').classes()).toContain("span-active");
  });

  it("shows 'no matching span' when an unsupported claim is clicked", async () => {
    const w = mount(Inspector, { props: { fixture } });
    await w.get('[data-claim="c1"]').trigger("click");
    expect(w.get('[data-testid="no-span"]').isVisible()).toBe(true);
  });

  it("labels the OUTPUT scorecard", () => {
    const w = mount(Inspector, { props: { fixture } });
    expect(w.get('[data-testid="output-panel"]').text()).toContain("OUTPUT");
  });
});
