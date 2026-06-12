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
.claim-list { list-style: none; padding: 0.5rem 0; }

.claim {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  cursor: pointer;
  padding: 0.75rem 1rem;
  border-left: 3px solid transparent;
  transition: background 0.12s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.claim:hover { background: oklch(97% 0.005 80); }
.claim.active { background: oklch(96% 0.01 80); }

.claim.label-grounded { border-left-color: oklch(55% 0.12 175); }
.claim.label-partial   { border-left-color: oklch(68% 0.14 80); }
.claim.label-unsupported { border-left-color: oklch(50% 0.16 25); }

.claim-text { font-size: 0.8125rem; line-height: 1.5; color: oklch(15% 0.01 80); flex: 1; }

.label-badge {
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 0.125rem;
}
.label-badge.grounded   { background: oklch(93% 0.04 175); color: oklch(35% 0.12 175); }
.label-badge.partial    { background: oklch(94% 0.05 80);  color: oklch(45% 0.14 80); }
.label-badge.unsupported { background: oklch(93% 0.04 25); color: oklch(38% 0.16 25); }

.claim + .claim { border-top: 1px solid oklch(95% 0.005 80); }
</style>
