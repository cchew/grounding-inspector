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
      {{ c.text }}
    </li>
  </ul>
</template>

<style scoped>
.claim { cursor: pointer; padding: .4rem; }
.label-grounded { border-left: 4px solid #2e7d32; }
.label-partial { border-left: 4px solid #f9a825; }
.label-unsupported { border-left: 4px solid #c62828; }
</style>
