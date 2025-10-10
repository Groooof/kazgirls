import type { App, ComponentPublicInstance } from 'vue'
import * as Sentry from '@sentry/vue'
import axios from 'axios'
import { useNotificationStore } from '@/stores/notification'

export function shouldNotifyUser(error: unknown): boolean {
  if (axios.isCancel(error)) return false

  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    if (status === 401 || status === 403) return false
    if (status && status >= 400 && status < 500) return true
    return true
  }

  const message = (error instanceof Error ? error.message : String(error)).toLowerCase()
  const silentSubstrings = [
    'cancel',
    'abort',
    'timeout',
    'resizeobserver',
    'chunkloaderror',
    'script error',
  ]

  return !silentSubstrings.some((substr) => message.includes(substr))
}

export function setupErrorHandler(app: App) {
  app.config.errorHandler = (
    err: unknown,
    instance: ComponentPublicInstance | null,
    info: string,
  ) => {
    const error = err instanceof Error ? err : new Error(String(err))
    const store = useNotificationStore()

    if (import.meta.env.DEV) {
      console.error('Vue error:', error)
      console.error('Info:', info)
      if (instance) console.error('Instance:', instance)
    }

    if (shouldNotifyUser(error)) {
      store.notify('An error has occurred')
    }

    if (import.meta.env.PROD) {
      Sentry.captureException(error)
    }
  }

  axios.interceptors.response.use(
    (response) => response,
    (error) => {
      if (shouldNotifyUser(error)) {
        const store = useNotificationStore()
        store.notify('Server request error')
      }

      if (import.meta.env.PROD) {
        Sentry.captureException(error)
      }
      return Promise.reject(error)
    },
  )
}
