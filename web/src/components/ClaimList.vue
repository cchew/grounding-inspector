<script setup lang="ts">
import type { Claim } from "../types";
defineProps<{ claims: Claim[]; activeId: string | null }>();
defineEmits<{ select: [claim: Claim] }>();
</script>

<template>
  <ul class="claim-list">
    <li v-for="c in claims" :key="c.id" :data-claim="c.id"
        :class="['claim', `label-${c.label}`, { active: c.id === activeId }]"
        @click="$emit('select', c)">
      <span class="claim-text">{{ c.text }}</span>
      <span :class="['label-badge', c.label]">{{ c.label }}</span>
    </li>
  </ul>
</template>

<style scoped>
.claim-list { list-style: none; padding: var(--s-2) 0; }

.claim {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s-3);
  cursor: pointer;
  padding: var(--s-3) var(--s-4);
  border-left: 3px solid transparent;
  transition: background 0.12s var(--ease-spring);
}

.claim:hover { background: var(--color-surface-hover); }
.claim.active { background: var(--color-surface-active); }

.claim.label-grounded    { border-left-color: var(--chip-grounded-text); }
.claim.label-partial     { border-left-color: var(--chip-partial-text); }
.claim.label-unsupported { border-left-color: var(--chip-unsupported-text); }

.claim-text {
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--color-ink);
  flex: 1;
}

.label-badge {
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: var(--s-1) var(--s-2);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 0.125rem;
}

.label-badge.grounded {
  background: var(--chip-grounded-bg);
  color: var(--chip-grounded-text);
  border-color: var(--chip-grounded-border);
}
.label-badge.partial {
  background: var(--chip-partial-bg);
  color: var(--chip-partial-text);
  border-color: var(--chip-partial-border);
}
.label-badge.unsupported {
  background: var(--chip-unsupported-bg);
  color: var(--chip-unsupported-text);
  border-color: var(--chip-unsupported-border);
}

.claim + .claim { border-top: 1px solid var(--color-border-light); }
</style>
