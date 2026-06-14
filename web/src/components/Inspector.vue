<script setup lang="ts">
import { ref, computed } from "vue";
import type { Fixture, Claim } from "../types";
import ClaimList from "./ClaimList.vue";
import SourceDoc from "./SourceDoc.vue";

const props = defineProps<{ fixture: Fixture }>();
const active = ref<Claim | null>(null);
const activeSpanIds = computed(() => active.value?.evidence_span_ids ?? []);
const noSpan = computed(() => !!active.value && active.value.evidence_span_ids.length === 0);
const g = computed(() => props.fixture.groundedness);
const sc = computed(() => props.fixture.scorecard);
</script>

<template>
  <div class="inspector">
    <div class="scorecards">
      <div data-testid="output-panel" class="scorecard">
        <span class="scorecard-label">OUTPUT</span>
        <div class="scorecard-values">
          <span class="label-chip grounded">{{ g.n_grounded }} grounded</span>
          <span class="label-chip partial">{{ g.n_partial }} partial</span>
          <span class="label-chip unsupported">{{ g.n_unsupported }} unsupported</span>
        </div>
        <p class="scorecard-secondary mono">Groundedness score: {{ g.score }}/100</p>
      </div>
      <div data-testid="detector-panel" class="scorecard">
        <span class="scorecard-label">DETECTOR</span>
        <p class="scorecard-primary mono">recall {{ sc.recall.toFixed(2) }} (CI {{ sc.recall_ci[0].toFixed(2) }}&ndash;{{ sc.recall_ci[1].toFixed(2) }})</p>
        <p class="scorecard-secondary">{{ sc.validated_on }}</p>
        <p class="scorecard-tertiary">{{ sc.domain_note }}</p>
      </div>
    </div>
    <div class="two-pane">
      <section class="pane pane-claims">
        <h2 class="pane-heading">AI Output</h2>
        <ClaimList :claims="fixture.claims" :active-id="active?.id ?? null" @select="active = $event" />
      </section>
      <section class="pane pane-source">
        <h2 class="pane-heading">Source Document</h2>
        <p class="source-title">{{ fixture.source.title }}</p>
        <SourceDoc :sections="fixture.source.sections" :active-span-ids="activeSpanIds" :no-span="noSpan" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.inspector { display: flex; flex-direction: column; gap: var(--s-5); }

.scorecards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s-4);
}

.scorecard {
  padding: var(--s-4) var(--s-5);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
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

.scorecard-values { display: flex; gap: var(--s-2); flex-wrap: wrap; }

.label-chip {
  font-size: 0.75rem;
  font-weight: 500;
  padding: var(--s-1) var(--s-3);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}

.label-chip.grounded {
  background: var(--chip-grounded-bg);
  color: var(--chip-grounded-text);
  border-color: var(--chip-grounded-border);
}
.label-chip.partial {
  background: var(--chip-partial-bg);
  color: var(--chip-partial-text);
  border-color: var(--chip-partial-border);
}
.label-chip.unsupported {
  background: var(--chip-unsupported-bg);
  color: var(--chip-unsupported-text);
  border-color: var(--chip-unsupported-border);
}

.scorecard-primary { font-size: 0.875rem; color: var(--color-ink); }
.scorecard-secondary { font-size: 0.75rem; color: var(--color-ink-2); }
.scorecard-tertiary { font-size: 0.6875rem; color: var(--color-ink-3); font-style: italic; }

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

.source-title {
  font-size: 0.75rem;
  color: var(--color-ink-2);
  padding: var(--s-2) var(--s-4) 0;
  font-style: italic;
}
</style>
