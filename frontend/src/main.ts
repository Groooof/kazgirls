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
