import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationStore = defineStore('notification', () => {
  const message = ref('')
  const visible = ref(false)
  let timeout: ReturnType<typeof setTimeout> | null = null

  const notify = (msg: string, duration = 3000) => {
    message.value = msg
    visible.value = true

    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      visible.value = false
      message.value = ''
    }, duration)
  }

  return { message, visible, notify }
})
