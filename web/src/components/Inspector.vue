<script setup lang="ts">
import { ref, computed } from "vue";
import type { Fixture, Claim, FlaggedSection } from "../types";
import ClaimList from "./ClaimList.vue";
import SourceDoc from "./SourceDoc.vue";
import OmissionPanel from "./OmissionPanel.vue";
import { track } from "../analytics";

const props = defineProps<{ fixture: Fixture }>();
const active = ref<Claim | null>(null);
const activeSpanIds = computed(() => active.value?.evidence_span_ids ?? []);
const noSpan = computed(() => !!active.value && active.value.evidence_span_ids.length === 0);
const activeLabel = computed(() => active.value?.label ?? null);
const activeRationale = computed(() => active.value?.rationale ?? "");
const g = computed(() => props.fixture.groundedness);
const claimCount = computed(() => props.fixture.claims.length);
// Keyed by (method, section_id), not section_id alone: two panels can flag the
// same source section, and a row highlighted in one panel must not imply the
// other method flagged it too. The source-doc highlight stays shared -- both
// methods point at the same span, and only one row is ever active.
const activeOmission = ref<{ method: string; section: FlaggedSection } | null>(null);
const activeOmissionSectionId = computed(() => activeOmission.value?.section.section_id ?? null);
const activeOmissionMethod = computed(() => activeOmission.value?.method ?? null);

function onSelectClaim(claim: Claim) {
  active.value = claim;
  track("claim_clicked", { label: claim.label, hasEvidence: claim.evidence_span_ids.length > 0 });
}

function onSelectOmission(method: string, section: FlaggedSection) {
  activeOmission.value = { method, section };
  track("omission_clicked", { method, sectionId: section.section_id, score: section.score });
}
</script>

<template>
  <div class="inspector">

    <p
      v-if="fixture.live_disclosure"
      data-testid="live-result-banner"
      class="live-result-banner"
    >{{ fixture.live_disclosure }}</p>

    <!-- Full-width output scorecard -->
    <div data-testid="output-panel" class="output-scorecard">
      <div class="output-left">
        <span class="scorecard-label">OUTPUT</span>
        <div class="scorecard-chips">
          <span class="label-chip grounded" title="Supported by source text">✓ {{ g.n_grounded }} grounded</span>
          <span class="label-chip partial" title="Related to source but contains errors, omissions, or misrepresented detail">~ {{ g.n_partial }} partial</span>
          <span class="label-chip unsupported" title="No supporting evidence found in source document">✗ {{ g.n_unsupported }} unsupported</span>
        </div>
        <p class="score-formula">grounded = 1pt · partial = 0.5pt · unsupported = 0pt</p>
        <p v-if="claimCount < 5" class="low-n-note">n={{ claimCount }} — score is indicative at this sample size</p>
      </div>
      <div class="output-right">
        <span class="score-number mono">{{ g.score }}</span>
        <span class="score-denom">/100</span>
      </div>
    </div>

    <!-- Two-pane -->
    <div class="two-pane">

      <!-- Left: claims -->
      <section class="pane pane-claims">
        <h2 class="pane-heading">AI Output</h2>
        <div class="label-legend">
          <span class="legend-label">Legend:</span>
          <span class="legend-chip grounded">✓ grounded</span>
          <span class="legend-chip partial">~ partial</span>
          <span class="legend-chip unsupported">✗ unsupported</span>
        </div>
        <ClaimList :claims="fixture.claims" :active-id="active?.id ?? null" @select="onSelectClaim" />
      </section>

      <!-- Right: source document -->
      <section class="pane pane-source">
        <h2 class="pane-heading">Source Document</h2>
        <p class="source-title">{{ fixture.source.title }}</p>
        <SourceDoc
          :sections="fixture.source.sections"
          :active-span-ids="activeSpanIds"
          :no-span="noSpan"
          :active-label="activeLabel"
          :active-rationale="activeRationale"
          :active-omission-section-id="activeOmissionSectionId"
        />
      </section>

    </div>

    <!-- Possible omissions: full-width, secondary/unvalidated signal -->
    <div v-if="fixture.omissions?.length" class="omissions-panel">
      <div class="omissions-panel-heading">
        <h2>Possible Omissions</h2>
        <p>Experimental, unvalidated signals — treat a flagged row as a prompt to review the source, not a finding.</p>
      </div>
      <div class="omissions-columns">
        <section v-for="entry in fixture.omissions" :key="entry.method" class="omissions-column">
          <h3 class="pane-heading omission-heading">
            {{ entry.method === 'embedkde' ? 'EmbedKDECheck' : 'Comprehensiveness (QA)' }}
          </h3>
          <OmissionPanel
            :method="entry.method"
            :flagged-sections="entry.flagged_sections"
            :caveat="entry.caveat"
            :active-section-id="entry.method === activeOmissionMethod ? activeOmissionSectionId : null"
            @select="(section) => onSelectOmission(entry.method, section)"
          />
        </section>
      </div>
    </div>

    <p
      v-if="fixture.live_disclosure && !fixture.omissions?.length"
      data-testid="omission-parity-note"
      class="omission-parity-note"
    >Omission analysis runs on the sample fixtures only.</p>
  </div>
</template>

<style scoped>
.inspector { display: flex; flex-direction: column; gap: var(--s-4); }

.live-result-banner {
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
  padding: var(--s-3) var(--s-4);
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--color-ink-3);
}

.omission-parity-note {
  font-size: 0.75rem;
  font-style: italic;
  color: var(--color-ink-3);
}

/* ── Output scorecard (full width) ── */
.output-scorecard {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-5);
  padding: var(--s-4) var(--s-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.output-left {
  display: flex;
  flex-direction: column;
  gap: var(--s-2);
}

.scorecard-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-ink-3);
}

.scorecard-chips { display: flex; gap: var(--s-2); flex-wrap: wrap; }

.label-chip {
  font-size: 0.75rem;
  font-weight: 500;
  padding: var(--s-1) var(--s-3);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: default;
}
.label-chip.grounded  { background: var(--chip-grounded-bg);    color: var(--chip-grounded-text);    border-color: var(--chip-grounded-border); }
.label-chip.partial   { background: var(--chip-partial-bg);     color: var(--chip-partial-text);     border-color: var(--chip-partial-border); }
.label-chip.unsupported { background: var(--chip-unsupported-bg); color: var(--chip-unsupported-text); border-color: var(--chip-unsupported-border); }

.score-formula {
  font-size: 0.6875rem;
  color: var(--color-ink-3);
  font-style: italic;
}

.low-n-note {
  font-size: 0.6875rem;
  color: var(--chip-partial-text);
}

.output-right {
  display: flex;
  align-items: baseline;
  gap: 0.125rem;
  flex-shrink: 0;
}

.score-number {
  font-size: 3rem;
  font-weight: 600;
  line-height: 1;
  color: var(--color-ink);
  font-variant-numeric: tabular-nums;
}

.score-denom {
  font-size: 1rem;
  color: var(--color-ink-2);
  align-self: flex-end;
  padding-bottom: 0.35rem;
}

/* ── Two-pane ── */
.two-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s-5);
  align-items: start;
}

.pane {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.pane-heading {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-ink-3);
  padding: var(--s-3) var(--s-4);
  border-bottom: 1px solid var(--color-border);
}

/* ── Label legend ── */
.label-legend {
  display: flex;
  gap: var(--s-2);
  flex-wrap: wrap;
  padding: var(--s-2) var(--s-4);
  border-bottom: 1px solid var(--color-border-light);
}

.legend-label {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-ink-3);
  align-self: center;
}

.legend-chip {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 2px var(--s-2);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}
.legend-chip.grounded    { background: var(--chip-grounded-bg);    color: var(--chip-grounded-text);    border-color: var(--chip-grounded-border); }
.legend-chip.partial     { background: var(--chip-partial-bg);     color: var(--chip-partial-text);     border-color: var(--chip-partial-border); }
.legend-chip.unsupported { background: var(--chip-unsupported-bg); color: var(--chip-unsupported-text); border-color: var(--chip-unsupported-border); }

.source-title {
  font-size: 0.75rem;
  color: var(--color-ink-2);
  padding: var(--s-2) var(--s-4) 0;
  font-style: italic;
}

/* ── Possible omissions (full-width, secondary/unvalidated signal) ── */
.omissions-panel {
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
}

.omissions-panel-heading {
  padding: var(--s-4) var(--s-5) var(--s-3);
}

.omissions-panel-heading h2 {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-ink-3);
}

.omissions-panel-heading p {
  font-size: 0.75rem;
  color: var(--color-ink-3);
  font-style: italic;
  margin-top: var(--s-1);
}

.omissions-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s-5);
  padding: 0 var(--s-5) var(--s-5);
}

.omissions-column {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
</style>
