<script setup lang="ts">
import { onMounted } from 'vue'
</script>

<template>
  <main>
    <router-view />
  </main>
</template>

<style scoped lang="scss">
main {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
}
</style>
