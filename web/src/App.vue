<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import type { Fixture } from "./types";
import Inspector from "./components/Inspector.vue";

const fixtureIds = ref<string[]>([]);
const selectedId = ref<string | null>(null);
const fixture = ref<Fixture | null>(null);
const error = ref<string | null>(null);
const loading = ref(false);

onMounted(async () => {
  try {
    const res = await fetch("/fixtures/index.json");
    fixtureIds.value = await res.json();
    if (fixtureIds.value.length > 0) selectedId.value = fixtureIds.value[0] ?? null;
  } catch (e) {
    error.value = "Could not load fixture list";
  }
});

watch(selectedId, async (id) => {
  if (!id) return;
  loading.value = true;
  fixture.value = null;
  error.value = null;
  try {
    const res = await fetch(`/fixtures/${id}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    fixture.value = await res.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load fixture";
  } finally {
    loading.value = false;
  }
});

function label(id: string): string {
  const map: Record<string, string> = {
    "travel-pds-01": "Synthetic 01",
    "travel-pds-02": "Synthetic 02",
    "travel-pds-03": "Synthetic 03",
    "covermore-pds-01": "Cover-More",
    "budgetdirect-pds-01": "Budget Direct",
  };
  return map[id] ?? id;
}
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="app-title">
        <h1>Grounding Inspector</h1>
        <p class="subtitle">Scoring whether AI claims are backed by document evidence</p>
      </div>
      <nav class="fixture-nav" v-if="fixtureIds.length">
        <button
          v-for="id in fixtureIds"
          :key="id"
          :class="['fixture-btn', { active: id === selectedId }]"
          @click="selectedId = id"
        >{{ label(id) }}</button>
      </nav>
    </header>
    <main>
      <Inspector v-if="fixture" :fixture="fixture" />
      <p v-else-if="error" class="load-error">{{ error }}</p>
      <p v-else-if="loading" class="loading">Loading...</p>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  max-width: var(--reading-width);
  margin: 0 auto;
  padding: var(--s-6) var(--s-5);
}

.app-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s-5);
  margin-bottom: var(--s-5);
  padding-bottom: var(--s-4);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.app-header h1 {
  font-size: 1.125rem;
  color: var(--color-ink);
}

.subtitle {
  font-size: 0.75rem;
  color: var(--color-ink-3);
  margin-top: 0.2rem;
}

.fixture-nav {
  display: flex;
  gap: var(--s-1);
  flex-wrap: wrap;
  align-items: center;
}

.fixture-btn {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 500;
  padding: var(--s-1) var(--s-3);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-ink-2);
  cursor: pointer;
  transition: all 0.12s var(--ease-spring);
}

.fixture-btn:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-ink-3);
}

.fixture-btn.active {
  background: var(--color-ink);
  border-color: var(--color-ink);
  color: var(--color-bg);
}

.load-error { color: var(--chip-unsupported-text); font-size: 0.875rem; }
.loading { color: var(--color-ink-3); font-size: 0.875rem; }
</style>
