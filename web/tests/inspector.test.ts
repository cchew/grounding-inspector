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

// Fixture is already imported at the top of this file — reuse it directly.
const fixtureWithOmissions: Fixture = {
  ...fixture,
  omissions: [{
    method: "embedkde",
    global_score: 0.8,
    flagged_sections: [
      { section_id: "s4_2", score: 0.8, top_tokens: ["hepatectomy", "infection"] },
    ],
    hyperparameters: { pca_components: 16, kde_bandwidth: 1.0, threshold_std: 1.5 },
    validated: false,
    caveat: "Omission signals are unvalidated: no ground-truth omission labels exist for these fixtures.",
  }],
};

describe("OmissionPanel via Inspector", () => {
  it("does not render an omission panel when the fixture has no omissions field", () => {
    const w = mount(Inspector, { props: { fixture } });
    expect(w.find('[data-testid^="omission-panel-"]').exists()).toBe(false);
  });

  it("renders flagged sections and the caveat when omissions data is present", () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithOmissions } });
    expect(w.find('[data-testid="omission-panel-embedkde"]').exists()).toBe(true);
    expect(w.get('[data-omission="s4_2"]').text()).toContain("hepatectomy");
    expect(w.get('[data-testid="omission-caveat-embedkde"]').text()).toContain("unvalidated");
  });

  it("clicking a flagged section highlights it in the source doc, independent of claim selection", async () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithOmissions } });
    await w.get('[data-omission="s4_2"]').trigger("click");
    expect(w.get('[data-span="s4_2"]').classes()).toContain("span-active-omission");
  });
});

const fixtureWithBothOmissionMethods: Fixture = {
  ...fixture,
  omissions: [
    fixtureWithOmissions.omissions![0],
    {
      method: "comprehensiveness_qa",
      global_score: 0.5,
      flagged_sections: [
        {
          section_id: "s4_2", score: 0.5,
          omitted_facts: [
            { fact: "policy excludes pre-existing conditions", question: "Does it exclude pre-existing conditions?", evidence: null },
          ],
        },
      ],
      hyperparameters: { model: "claude-sonnet-4-5-20250929", flag_threshold: 0 },
      validated: false,
      caveat: "Comprehensiveness signals are unvalidated.",
    },
  ],
};

describe("OmissionPanel via Inspector — multi-method", () => {
  it("renders one panel per omissions entry", () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithBothOmissionMethods } });
    expect(w.find('[data-testid="omission-panel-embedkde"]').exists()).toBe(true);
    expect(w.find('[data-testid="omission-panel-comprehensiveness_qa"]').exists()).toBe(true);
  });

  it("shows omitted facts (not tokens) in the comprehensiveness_qa panel", () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithBothOmissionMethods } });
    const panel = w.get('[data-testid="omission-panel-comprehensiveness_qa"]');
    expect(panel.text()).toContain("policy excludes pre-existing conditions");
  });

  it("active-row highlight is scoped to the clicked panel's method", async () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithBothOmissionMethods } });
    const embedRow = w.get('[data-testid="omission-panel-embedkde"] [data-omission="s4_2"]');
    const qaRow = w.get('[data-testid="omission-panel-comprehensiveness_qa"] [data-omission="s4_2"]');
    await embedRow.trigger("click");
    expect(embedRow.classes()).toContain("active");
    expect(qaRow.classes()).not.toContain("active");
    await qaRow.trigger("click");
    expect(qaRow.classes()).toContain("active");
    expect(embedRow.classes()).not.toContain("active");
  });

  it("clicking either panel's row highlights the same source span", async () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithBothOmissionMethods } });
    const qaRow = w.get('[data-testid="omission-panel-comprehensiveness_qa"] [data-omission="s4_2"]');
    await qaRow.trigger("click");
    expect(w.get('[data-span="s4_2"]').classes()).toContain("span-active-omission");
  });

  it("a fixture with only one omissions entry still renders exactly one panel", () => {
    const w = mount(Inspector, { props: { fixture: fixtureWithOmissions } });
    expect(w.findAll('[data-testid^="omission-panel-"]').length).toBe(1);
  });
});
