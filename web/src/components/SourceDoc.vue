<script setup lang="ts">
import { watch, ref } from "vue";
import type { Section } from "../types";
const props = defineProps<{ sections: Section[]; activeSpanIds: string[]; noSpan: boolean }>();
const root = ref<HTMLElement | null>(null);
watch(() => props.activeSpanIds, (ids) => {
  if (!ids.length || !root.value) return;
  const el = root.value.querySelector(`[data-span="${ids[0]}"]`);
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
});
</script>

<template>
  <div class="source-doc" ref="root">
    <p v-for="s in sections" :key="s.id" :data-span="s.id"
       :class="{ 'span-active': activeSpanIds.includes(s.id) }">
      <span class="page">p.{{ s.page }}</span> {{ s.text }}
    </p>
    <div v-show="noSpan" data-testid="no-span" class="no-span">No matching span found.</div>
  </div>
</template>
