<script setup lang="ts">
import type { FlaggedSection } from "../types";
defineProps<{
  method: string;
  flaggedSections: FlaggedSection[];
  caveat: string;
  activeSectionId: string | null;
}>();
defineEmits<{ select: [section: FlaggedSection] }>();
</script>

<template>
  <div class="omission-panel" :data-testid="`omission-panel-${method}`">
    <p :data-testid="`omission-caveat-${method}`" class="omission-caveat">{{ caveat }}</p>
    <ul class="omission-list" v-if="flaggedSections.length > 0">
      <li v-for="f in flaggedSections" :key="f.section_id" :data-omission="f.section_id"
          :class="['omission', { active: f.section_id === activeSectionId }]"
          @click="$emit('select', f)">
        <span class="omission-tokens" v-if="f.top_tokens">{{ f.top_tokens.join(', ') }}</span>
        <span class="omission-facts" v-else-if="f.omitted_facts">
          <span v-for="of in f.omitted_facts" :key="of.fact" class="omitted-fact">{{ of.fact }}</span>
        </span>
        <span class="omission-score mono">{{ f.score.toFixed(2) }}</span>
      </li>
    </ul>
    <p v-else class="no-omissions">No sections flagged.</p>
  </div>
</template>

<style scoped>
.omission-list { list-style: none; padding: var(--s-2) 0; }

.omission {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  cursor: pointer;
  padding: var(--s-3) var(--s-4);
  border-left: 3px solid transparent;
  transition: background 0.12s var(--ease-spring);
}

.omission:hover { background: var(--color-surface-hover); }

.omission.active {
  background: var(--chip-omission-bg);
  border-left-color: var(--chip-omission-border);
}

.omission-tokens { font-size: 0.8125rem; color: var(--color-ink); flex: 1; }
.omission-facts { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.omitted-fact { font-size: 0.8125rem; color: var(--color-ink); }
.omission-score { font-size: 0.75rem; color: var(--chip-omission-text); flex-shrink: 0; }
.omission + .omission { border-top: 1px solid var(--color-border-light); }

.no-omissions {
  padding: var(--s-3) var(--s-4);
  font-size: 0.8125rem;
  color: var(--color-ink-3);
}

.omission-caveat {
  margin: var(--s-3) var(--s-4) var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--color-surface-hover);
  border-left: 3px solid var(--color-ink-3);
  font-size: 0.6875rem;
  line-height: 1.5;
  color: var(--color-ink-2);
}
</style>
