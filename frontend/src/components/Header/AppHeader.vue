<script setup lang="ts">
import AppIcon from '@/components/UI/AppIcon/AppIcon.vue'
import { useAppStore } from '@/stores/app.ts'
import { computed } from 'vue'

const { getLinkByIndex } = useAppStore()
const logoLink = computed(() => getLinkByIndex('logo'))
</script>

<template>
  <header class="header">
    <div class="container">
      <div class="header-wrapper">
        <a :href="logoLink" target="_blank">
          <AppIcon class="header-icon" icon="logo" width="167" height="40" />
          <AppIcon class="header-icon-small" icon="logo" width="146" height="35" />
        </a>
      </div>
    </div>
  </header>
</template>

<style scoped lang="scss">
.header {
  padding: 22.5px 0;
  position: sticky;
  top: 0;
  background-color: rgba(255, 255, 255, 0.9);
  z-index: 10;

  &-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: var(--color-primary);
    gap: 10px;
  }

  &-icon {
    display: none;
  }

  @media (min-width: $md) {
    padding: 33.5px 0;
    background-color: var(--color-white);
    &-icon {
      display: block;

      &-small {
        display: none;
      }
    }
  }
}
</style>
