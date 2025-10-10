<script setup lang="ts">
import AppIcon from '@/components/UI/AppIcon/AppIcon.vue'
import AppFooterSocial from '@/components/Footer/AppFooterSocial.vue'
import { useAppStore } from '@/stores/app.ts'
import { computed } from 'vue'

const { getLinkByIndex } = useAppStore()
const currentYear = new Date().getFullYear()

const logoLink = computed(() => getLinkByIndex('logo'))
const emailLink = computed(() => getLinkByIndex('email'))
const tcLink = computed(() => getLinkByIndex('tcs'))
const privacyLink = computed(() => getLinkByIndex('policy'))
</script>

<template>
  <footer class="footer">
    <div class="container">
      <div class="footer-wrapper">
        <a :href="logoLink" target="_blank">
          <AppIcon class="footer-icon" icon="logo" width="167" height="40" />
        </a>
        <ul class="footer-menu">
          <li><a :href="'mailto:' + emailLink">Contact</a></li>
          <li><a :href="tcLink" target="_blank">T&C's</a></li>
          <li><a :href="privacyLink" target="_blank">Privacy Policy</a></li>
        </ul>
        <AppFooterSocial />
        <div class="footer-copyright">© Svinka, {{ currentYear }}</div>
      </div>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.footer {
  color: var(--color-white);
  background-color: var(--color-text-header);
  padding: 40px 0;
  text-align: center;

  &-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
    font-size: 20px;
    font-weight: 400;
  }

  &-menu {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
  }

  &-copyright {
    font-size: 12px;
    color: #b8b8b8;
  }

  @media (min-width: $md) {
    text-align: start;
    &-wrapper {
      display: grid;
      grid-template-columns: 170px 1fr 170px;
      gap: 12px;
      align-items: flex-start;
    }

    &-menu {
      justify-content: center;
      flex-direction: row;
    }
  }
}
</style>
