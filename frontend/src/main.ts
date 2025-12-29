import './assets/style/reset.scss'
import { createApp } from 'vue'
import App from './App.vue'
import { createPinia } from 'pinia'
// import '@/plugins/svg-icons'
import { config } from '@/config.ts'
import * as Sentry from '@sentry/vue'
import router from '@/router'
import 'plyr/dist/plyr.css'

const initApp = () => {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  app.use(router)
  app.mount('#app')
}

initApp()

(async () => {
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations()
      for (const r of regs) await r.unregister()
    }
    if ('caches' in window) {
      const keys = await caches.keys()
      await Promise.all(keys.map(k => caches.delete(k)))
    }
    console.log('SW/cache cleared')
  } catch (e) {
    console.log('SW/cache clear error', e)
  }
})()

