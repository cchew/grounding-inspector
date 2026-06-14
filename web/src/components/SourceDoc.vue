<script setup lang="ts">
import { watch, ref } from "vue";
import type { Section } from "../types";
const props = defineProps<{ sections: Section[]; activeSpanIds: string[]; noSpan: boolean }>();
const root = ref<HTMLElement | null>(null);
watch(() => props.activeSpanIds, (ids) => {
  if (!ids.length || !root.value) return;
  const el = root.value.querySelector(`[data-span="${ids[0]}"]`);
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
}, { flush: "post" });
</script>

<template>
  <div class="source-doc" ref="root">
    <p v-for="s in sections" :key="s.id" :data-span="s.id"
       :class="['section', { 'span-active': activeSpanIds.includes(s.id) }]">
      <span class="page mono">p.{{ s.page }}</span>
      <span class="section-text">{{ s.text }}</span>
    </p>
    <div v-show="noSpan" data-testid="no-span" class="no-span">
      No matching span found in source.
    </div>
  </div>
</template>

<style scoped>
.source-doc {
  padding: var(--s-2) 0;
  max-height: 480px;
  overflow-y: auto;
}

.section {
  display: flex;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-4);
  font-size: 0.8125rem;
  line-height: 1.6;
  border-left: 3px solid transparent;
  transition: background 0.15s var(--ease-spring);
}

.section + .section { border-top: 1px solid var(--color-border-light); }

.section.span-active {
  background: var(--color-accent-bg);
  border-left-color: var(--color-accent-border);
}

.page {
  font-size: 0.6875rem;
  color: var(--color-ink-3);
  flex-shrink: 0;
  padding-top: 0.125rem;
}

.section-text { color: var(--color-ink); }

.no-span {
  margin: var(--s-4);
  padding: var(--s-3) var(--s-4);
  background: var(--chip-unsupported-bg);
  border: 1px solid var(--chip-unsupported-border);
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  color: var(--chip-unsupported-text);
}
</style>
