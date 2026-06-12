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
      <div data-testid="detector-panel" class="scorecard detector-scorecard">
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
.inspector { display: flex; flex-direction: column; gap: 1.5rem; }

.scorecards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.scorecard {
  padding: 1rem 1.25rem;
  background: oklch(100% 0 0);
  border: 1px solid oklch(88% 0.01 80);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.scorecard-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: oklch(55% 0.01 80);
}

.scorecard-values { display: flex; gap: 0.5rem; flex-wrap: wrap; }

.label-chip {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.125rem 0.625rem;
  border-radius: 99px;
}
.label-chip.grounded {
  background: oklch(93% 0.04 175);
  color: oklch(35% 0.12 175);
}
.label-chip.partial {
  background: oklch(94% 0.05 80);
  color: oklch(45% 0.14 80);
}
.label-chip.unsupported {
  background: oklch(93% 0.04 25);
  color: oklch(38% 0.16 25);
}

.scorecard-primary { font-size: 0.875rem; }
.scorecard-secondary { font-size: 0.75rem; color: oklch(45% 0.01 80); }
.scorecard-tertiary { font-size: 0.6875rem; color: oklch(60% 0.01 80); font-style: italic; }

.two-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

.pane {
  background: oklch(100% 0 0);
  border: 1px solid oklch(88% 0.01 80);
  border-radius: 10px;
  overflow: hidden;
}

.pane-heading {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: oklch(55% 0.01 80);
  padding: 0.75rem 1rem;
  border-bottom: 1px solid oklch(92% 0.01 80);
}

.source-title {
  font-size: 0.75rem;
  color: oklch(45% 0.01 80);
  padding: 0.5rem 1rem 0;
  font-style: italic;
}
</style>
