import { defineStore } from 'pinia'
import { ref } from 'vue'
import { indexApi } from '@/fastApi/apiClient'
import type { LinkReadSchema, SuccessResponseListLinkReadSchema } from '@/fastApi'

export const useAppStore = defineStore('app', () => {
  const fontsLoaded = ref(false)
  const socialLinks = ref<LinkReadSchema[]>([])

  async function ensureFontsLoaded() {
    if (!fontsLoaded.value) {
      try {
        await document.fonts.ready
        await new Promise((resolve) => setTimeout(resolve, 300))
      } catch (e) {
        console.warn(e)
      }
      fontsLoaded.value = true
    }
  }

  async function fetchLinks() {
    try {
      const { data } = (await indexApi.getSocialMedia()) as SuccessResponseListLinkReadSchema
      socialLinks.value = data ?? []
    } catch (e) {
      console.error(e)
    }
  }

  function getLinkByIndex(label: string): string {
    const filtered = socialLinks.value.filter((link) => link.label === label)
    return filtered[0]?.link_url || ''
  }

  return {
    fontsLoaded,
    socialLinks,
    ensureFontsLoaded,
    fetchLinks,
    getLinkByIndex,
  }
})
