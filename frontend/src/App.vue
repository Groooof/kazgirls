<script setup lang="ts">
import AppNotification from '@/components/UI/AppNotification/AppNotification.vue'
import AppHeader from '@/components/Header/AppHeader.vue'
import AppFooter from '@/components/Footer/AppFooter.vue'
import AppPageLoaderOverlay from '@/components/UI/AppPageLoaderOverlay/AppPageLoaderOverlay.vue'
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

onMounted(async () => {
  await appStore.ensureFontsLoaded()
  await appStore.fetchLinks()
})
</script>

<template>
  <AppPageLoaderOverlay v-if="!appStore.fontsLoaded" />
  <template v-else>
    <AppHeader />
    <main>
      <router-view />
    </main>
    <AppFooter />
    <AppNotification />
  </template>
</template>

<style scoped lang="scss">
main {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
}
</style>
