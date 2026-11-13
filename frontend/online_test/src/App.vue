<script setup>

import { computed } from 'vue';
import { useRoute } from 'vue-router';
import AppHeader from './components/AppHeader.vue';

const route = useRoute();
// Шапка — на всех защищённых (авторизованных) страницах, но не на логине и прохождении
const showHeader = computed(() => !route.meta.public);
</script>

<template>
  <AppHeader v-if="showHeader" />
  <RouterView />
</template>
