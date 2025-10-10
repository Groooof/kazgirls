import './assets/style/main.scss'
import { createApp } from 'vue'
import App from './App.vue'
import { createPinia } from 'pinia'
import '@/plugins/svg-icons'
import { config } from '@/config.ts'
import * as Sentry from '@sentry/vue'
import { setupErrorHandler } from '@/utils/initErrorHandler.ts'
import router from '@/router'

const setupSentry = (app: ReturnType<typeof createApp>) => {
  if (!config.sentryDsn) return

  Sentry.init({
    app,
    dsn: config.sentryDsn,
    sendDefaultPii: true,
    integrations: [Sentry.replayIntegration()],
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    tracesSampleRate: 1.0,
  })
}

const initApp = () => {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)
  setupSentry(app)
  setupErrorHandler(app)
  app.use(router)
  app.mount('#app')
}

initApp()
