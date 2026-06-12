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
