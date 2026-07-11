<script setup lang="ts">
import { ref, computed } from "vue";
import type { Fixture, Claim } from "../types";
import ClaimList from "./ClaimList.vue";
import SourceDoc from "./SourceDoc.vue";

const props = defineProps<{ fixture: Fixture }>();
const active = ref<Claim | null>(null);
const detectorOpen = ref(false);
const activeSpanIds = computed(() => active.value?.evidence_span_ids ?? []);
const noSpan = computed(() => !!active.value && active.value.evidence_span_ids.length === 0);
const activeLabel = computed(() => active.value?.label ?? null);
const activeRationale = computed(() => active.value?.rationale ?? "");
const g = computed(() => props.fixture.groundedness);
const sc = computed(() => props.fixture.scorecard);
const claimCount = computed(() => props.fixture.claims.length);
</script>

<template>
  <div class="inspector">

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

      <!-- Left: claims + detector accordion -->
      <div class="left-stack">
        <section class="pane pane-claims">
          <h2 class="pane-heading">AI Output</h2>
          <div class="label-legend">
            <span class="legend-chip grounded">✓ grounded</span>
            <span class="legend-chip partial">~ partial</span>
            <span class="legend-chip unsupported">✗ unsupported</span>
          </div>
          <ClaimList :claims="fixture.claims" :active-id="active?.id ?? null" @select="active = $event" />
        </section>

        <div class="detector-accordion">
          <button data-testid="detector-panel" class="detector-toggle" @click="detectorOpen = !detectorOpen">
            <span class="detector-toggle-label">DETECTOR</span>
            <span class="detector-hint">benchmark performance</span>
            <span class="toggle-icon">{{ detectorOpen ? '▴' : '▾' }}</span>
          </button>
          <div v-show="detectorOpen" data-testid="detector-body" class="detector-body">
            <dl class="detector-stats">
              <div class="stat-row">
                <dt>recall</dt>
                <dd class="mono">{{ sc.recall.toFixed(2) }} <span class="ci">(CI {{ sc.recall_ci[0].toFixed(2) }}–{{ sc.recall_ci[1].toFixed(2) }})</span></dd>
              </div>
              <div class="stat-row" v-if="sc.cohen_kappa !== null">
                <dt>agreement (κ)</dt>
                <dd class="mono">{{ sc.cohen_kappa.toFixed(3) }} <span class="ci">— slight agreement</span></dd>
              </div>
              <div class="stat-row" v-if="sc.balanced_accuracy !== null">
                <dt>balanced accuracy</dt>
                <dd class="mono">{{ sc.balanced_accuracy.toFixed(3) }}</dd>
              </div>
              <div class="stat-row">
                <dt>validated on</dt>
                <dd>{{ sc.validated_on }}</dd>
              </div>
            </dl>
            <p class="detector-caveat">⚠ {{ sc.domain_note }}</p>
          </div>
        </div>
      </div>

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
        />
      </section>

    </div>
  </div>
</template>

<style scoped>
.inspector { display: flex; flex-direction: column; gap: var(--s-4); }

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

.left-stack {
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
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

/* ── Detector accordion ── */
.detector-accordion {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.detector-toggle {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  width: 100%;
  padding: var(--s-3) var(--s-4);
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--color-ink-2);
  font-family: var(--font-ui);
  transition: background 0.12s var(--ease-spring);
}
.detector-toggle:hover { background: var(--color-surface-hover); }

.detector-toggle-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-ink-3);
}

.detector-hint {
  font-size: 0.75rem;
  color: var(--color-ink-3);
  flex: 1;
}

.toggle-icon {
  font-size: 0.625rem;
  color: var(--color-ink-3);
}

.detector-body {
  padding: var(--s-3) var(--s-4) var(--s-4);
  border-top: 1px solid var(--color-border-light);
}

.detector-stats { display: flex; flex-direction: column; gap: var(--s-2); }

.stat-row {
  display: flex;
  gap: var(--s-4);
  font-size: 0.8125rem;
}
.stat-row dt {
  color: var(--color-ink-2);
  width: 9rem;
  flex-shrink: 0;
  font-size: 0.75rem;
}
.stat-row dd { color: var(--color-ink); }
.ci { color: var(--color-ink-3); font-size: 0.75rem; }

.detector-caveat {
  margin-top: var(--s-3);
  font-size: 0.75rem;
  color: var(--chip-partial-text);
  background: var(--chip-partial-bg);
  border: 1px solid var(--chip-partial-border);
  border-radius: var(--radius-sm);
  padding: var(--s-2) var(--s-3);
}
</style>
