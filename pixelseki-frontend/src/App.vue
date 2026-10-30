<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
/* Prevent text selections when dragging canvas components */
.select-none {
  user-select: none;
}
</style>

