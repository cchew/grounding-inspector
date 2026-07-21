<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from "vue";
import type { Fixture } from "./types";
import Inspector from "./components/Inspector.vue";
import HelpModal from "./components/HelpModal.vue";
import { startTour, hasSeenTour } from "./tour";
import { track } from "./analytics";

const fixtureIds = ref<string[]>([]);
const selectedId = ref<string | null>(null);
const fixture = ref<Fixture | null>(null);
const error = ref<string | null>(null);
const loading = ref(false);
const helpOpen = ref(false);
const appVersion = __APP_VERSION__;
let tourFired = false;

onMounted(async () => {
  track("gate_pass");
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
    track("fixture_switched", { id });
    if (!tourFired && !hasSeenTour()) {
      tourFired = true;
      await nextTick();
      startTour();
    }
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
        <div class="title-row">
          <h1>Grounding Inspector</h1>
          <button data-testid="help-button" class="help-btn" @click="helpOpen = true" aria-label="How this works">?</button>
          <button type="button" class="tour-btn" @click="startTour">Take the tour</button>
        </div>
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
    <footer data-testid="disclaimer" class="disclaimer">
      <span class="disclaimer-text">Not an official service. A demonstration tool for checking whether AI-generated claims are backed by a source document.</span>
      <span class="disclaimer-version mono">v{{ appVersion }}</span>
    </footer>
    <HelpModal v-if="fixture" :fixture="fixture" :open="helpOpen" @close="helpOpen = false" />
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

.title-row {
  display: flex;
  align-items: center;
  gap: var(--s-2);
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

.help-btn {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 600;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-ink-2);
  cursor: pointer;
  line-height: 1;
  transition: all 0.12s var(--ease-spring);
}
.help-btn:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-ink-3);
}
.help-btn:focus-visible {
  outline: 2px solid var(--color-accent-border);
  outline-offset: 2px;
}

.tour-btn {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0;
  border: none;
  background: none;
  color: var(--color-ink-2);
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
}
.tour-btn:hover { color: var(--color-ink); }
.tour-btn:focus-visible {
  outline: 2px solid var(--color-accent-border);
  outline-offset: 2px;
}

.load-error { color: var(--chip-unsupported-text); font-size: 0.875rem; }
.loading { color: var(--color-ink-3); font-size: 0.875rem; }

main {
  min-height: 480px;
}

.disclaimer {
  position: sticky;
  bottom: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-4);
  margin-top: var(--s-5);
  margin-left: calc(var(--s-5) * -1);
  margin-right: calc(var(--s-5) * -1);
  padding: var(--s-3) var(--s-5);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
  font-size: 0.75rem;
  color: var(--color-ink-3);
}

.disclaimer-version {
  flex-shrink: 0;
  color: var(--color-ink-3);
}
</style>
