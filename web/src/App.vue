<script setup lang="ts">
import { ref, onMounted } from "vue";
import type { Fixture } from "./types";
import Inspector from "./components/Inspector.vue";
const fixture = ref<Fixture | null>(null);
onMounted(async () => { fixture.value = await (await fetch("/api/fixtures/travel-pds-01")).json(); });
</script>
<template><Inspector v-if="fixture" :fixture="fixture" /></template>
