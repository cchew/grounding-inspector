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
    <header class="panels">
      <div data-testid="output-panel" class="panel output">
        <h3>OUTPUT</h3>
        <p>{{ g.n_grounded }} grounded / {{ g.n_partial }} partial / {{ g.n_unsupported }} unsupported</p>
        <p class="secondary">Groundedness {{ g.score }}</p>
      </div>
      <div data-testid="detector-panel" class="panel detector">
        <h3>DETECTOR</h3>
        <p>recall {{ sc.recall }} (CI {{ sc.recall_ci[0] ?? 0 }}&ndash;{{ sc.recall_ci[1] ?? 0 }})</p>
        <p class="secondary">{{ sc.validated_on }} &middot; {{ sc.domain_note }}</p>
      </div>
    </header>
    <main class="two-pane">
      <ClaimList :claims="fixture.claims" :active-id="active?.id ?? null" @select="active = $event" />
      <SourceDoc :sections="fixture.source.sections" :active-span-ids="activeSpanIds" :no-span="noSpan" />
    </main>
  </div>
</template>

<style scoped>
.two-pane { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.panels { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
</style>
