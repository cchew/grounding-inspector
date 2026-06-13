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
    const res = await fetch("/api/fixtures");
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
    const res = await fetch(`/api/fixtures/${id}`);
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
        <p class="subtitle">Layer-3 groundedness evaluation — LLM Security</p>
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
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}
.app-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid oklch(88% 0.01 80);
  flex-wrap: wrap;
}
.app-header h1 {
  font-size: 1.125rem;
  color: oklch(15% 0.01 80);
  letter-spacing: -0.02em;
}
.subtitle {
  font-size: 0.75rem;
  color: oklch(55% 0.01 80);
  margin-top: 0.2rem;
}
.fixture-nav {
  display: flex;
  gap: 0.375rem;
  flex-wrap: wrap;
  align-items: center;
}
.fixture-btn {
  font-family: Inter, system-ui, sans-serif;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.3125rem 0.75rem;
  border-radius: 6px;
  border: 1px solid oklch(85% 0.01 80);
  background: oklch(100% 0 0);
  color: oklch(35% 0.01 80);
  cursor: pointer;
  transition: all 0.12s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.fixture-btn:hover {
  background: oklch(97% 0.005 80);
  border-color: oklch(75% 0.01 80);
}
.fixture-btn.active {
  background: oklch(15% 0.01 80);
  border-color: oklch(15% 0.01 80);
  color: oklch(98% 0.005 80);
}
.load-error { color: oklch(50% 0.16 25); font-size: 0.875rem; }
.loading { color: oklch(55% 0.01 80); font-size: 0.875rem; }
</style>
