<script setup lang="ts">
import AppIcon from '@/components/UI/AppIcon/AppIcon.vue'
import { useAppStore } from '@/stores/app.ts'
import { computed } from 'vue'

const { getLinkByIndex } = useAppStore()
const facebookLink = computed(() => getLinkByIndex('facebook'))
const tiktokLink = computed(() => getLinkByIndex('tiktok'))
const instagramLink = computed(() => getLinkByIndex('instagram'))
</script>

<template>
  <ul class="footer-social">
    <li>
      <a :href="facebookLink" target="_blank">
        <AppIcon width="40" height="40" icon="facebook" />
      </a>
    </li>
    <li>
      <a :href="instagramLink" target="_blank">
        <AppIcon width="40" height="40" icon="instagram" />
      </a>
    </li>
    <li>
      <a :href="tiktokLink" target="_blank">
        <AppIcon width="40" height="40" icon="tik-tok" />
      </a>
    </li>
  </ul>
</template>

<style scoped lang="scss">
.footer-social {
  display: flex;
  align-items: center;
  gap: 20px;
}
</style>
