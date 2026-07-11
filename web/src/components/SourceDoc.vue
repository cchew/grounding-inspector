<script setup lang="ts">
import { watch, ref } from "vue";
import type { Section, Label } from "../types";
const props = defineProps<{
  sections: Section[];
  activeSpanIds: string[];
  noSpan: boolean;
  activeLabel: Label | null;
  activeRationale: string;
}>();
const root = ref<HTMLElement | null>(null);
watch(() => props.activeSpanIds, (ids) => {
  if (!ids.length || !root.value) return;
  const el = root.value.querySelector(`[data-span="${ids[0]}"]`);
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
}, { flush: "post" });
</script>

<template>
  <div class="source-doc" ref="root">
    <div v-show="noSpan" data-testid="no-span" class="no-span">
      No matching span found in source.
    </div>
    <p v-if="activeRationale" data-testid="evidence-note" class="evidence-note">
      <span class="evidence-note-label">Evidence note</span> {{ activeRationale }}
    </p>
    <p v-for="s in sections" :key="s.id" :data-span="s.id"
       :class="['section', {
         'span-active': activeSpanIds.includes(s.id),
         'span-active-grounded': activeSpanIds.includes(s.id) && activeLabel === 'grounded',
         'span-active-partial': activeSpanIds.includes(s.id) && activeLabel === 'partial',
       }]">
      <span class="page mono">p.{{ s.page }}</span>
      <span class="section-text">{{ s.text }}</span>
    </p>
  </div>
</template>

<style scoped>
.source-doc {
  padding: var(--s-2) 0;
  max-height: 480px;
  overflow-y: auto;
}

.evidence-note {
  margin: 0 var(--s-4) var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--color-surface-hover);
  border-left: 3px solid var(--color-ink-3);
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--color-ink-2);
}

.evidence-note-label {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.625rem;
  letter-spacing: 0.06em;
  color: var(--color-ink-3);
  margin-right: var(--s-2);
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

.section.span-active-grounded {
  background: var(--chip-grounded-bg);
  border-left-color: var(--chip-grounded-border);
}

.section.span-active-partial {
  background: var(--chip-partial-bg);
  border-left-color: var(--chip-partial-border);
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
