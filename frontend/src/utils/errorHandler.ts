import { getCurrentInstance } from 'vue'

export function handleGlobalError(error: unknown) {
  const instance = getCurrentInstance()
  if (instance && instance.appContext.config.errorHandler) {
    instance.appContext.config.errorHandler(error, instance.proxy, 'async function error')
  } else {
    console.error('Global error handler is not available:', error)
  }
}
