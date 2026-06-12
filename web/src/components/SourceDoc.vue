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
  padding: 0.5rem 0;
  max-height: 480px;
  overflow-y: auto;
}

.section {
  display: flex;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  font-size: 0.8125rem;
  line-height: 1.6;
  transition: background 0.15s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.section + .section { border-top: 1px solid oklch(95% 0.005 80); }

.section.span-active {
  background: oklch(94% 0.06 80);
  border-left: 3px solid oklch(68% 0.14 80);
}

.page {
  font-size: 0.6875rem;
  color: oklch(60% 0.01 80);
  flex-shrink: 0;
  padding-top: 0.125rem;
}

.section-text { color: oklch(20% 0.01 80); }

.no-span {
  margin: 1rem;
  padding: 0.75rem 1rem;
  background: oklch(96% 0.03 25);
  border: 1px solid oklch(85% 0.06 25);
  border-radius: 8px;
  font-size: 0.8125rem;
  color: oklch(38% 0.16 25);
}
</style>
