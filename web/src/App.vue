<script setup lang="ts">
import { ref, onMounted } from "vue";
import type { Fixture } from "./types";
import Inspector from "./components/Inspector.vue";
const fixture = ref<Fixture | null>(null);
const error = ref<string | null>(null);
onMounted(async () => {
  try {
    const res = await fetch("/api/fixtures/travel-pds-01");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    fixture.value = await res.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load fixture";
  }
});
</script>
<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>Grounding Inspector</h1>
      <p class="subtitle">Layer-3 groundedness evaluation — LLM Security</p>
    </header>
    <main>
      <Inspector v-if="fixture" :fixture="fixture" />
      <p v-else-if="error" class="load-error">{{ error }}</p>
      <p v-else class="loading">Loading...</p>
    </main>
  </div>
</template>
<style scoped>
.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}
.app-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid oklch(88% 0.01 80);
}
.app-header h1 {
  font-size: 1.25rem;
  color: oklch(15% 0.01 80);
}
.subtitle {
  font-size: 0.8125rem;
  color: oklch(55% 0.01 80);
  margin-top: 0.25rem;
}
.load-error { color: oklch(50% 0.16 25); font-size: 0.875rem; }
.loading { color: oklch(55% 0.01 80); font-size: 0.875rem; }
</style>
