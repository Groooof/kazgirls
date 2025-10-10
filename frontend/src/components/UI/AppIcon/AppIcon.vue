<script setup lang="ts">
import { computed } from 'vue'

interface AppIconProps {
  icon: string
  width?: string
  height?: string
}

const props = withDefaults(defineProps<AppIconProps>(), {
  width: '16px',
  height: '16px',
})

const dimensions = computed(() => ({
  width: props.width,
  height: props.height,
}))

const symbolId = computed(() => `#icon-${props.icon}`)
</script>

<template>
  <svg
    class="app-icon"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    fill="currentColor"
    :style="dimensions"
    :width="width"
    :height="height"
  >
    <use :href="symbolId" fill="currentColor" />
  </svg>
</template>

<style lang="scss" scoped>
.app-icon {
  user-select: none;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  vertical-align: middle;
}
</style>
