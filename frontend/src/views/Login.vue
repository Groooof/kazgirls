
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios, { AxiosError } from 'axios'
import Cookies from 'js-cookie'
import { config } from '@/config'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

const canSubmit = computed(() => username.value.trim().length > 0 && password.value.trim().length > 0 && !isLoading.value, )

const login = async () => {
  if (!username.value || !password.value) return

  isLoading.value = true
  errorMessage.value = null

  try {
    // логин
    const { data } = await axios.post(`${config.url}${config.apiUrl}/tokens/login`, {
      username: username.value,
      password: password.value,
    })

    // сохраняем токен в куку (ты уже так делаешь)
    Cookies.set('access_token', data.access_token, {
      expires: 7,
      sameSite: 'Lax',
    })

    // забираем информацию о себе
    const { data: me } = await axios.get(`${config.url}${config.apiUrl}/tokens/me`, {
      withCredentials: true,
    })

    const redirect = route.query.redirect as string | undefined

    if (me.is_streamer) {
      // всегда на свою страницу стримера
      await router.push({
        name: 'Streamer',
        params: { id: me.id },
      })
    } else {
      // зритель
      if (redirect && redirect !== '/login') {
        await router.push(redirect)
      } else {
        await router.push({ name: 'StreamersList' })
      }
    }
  } catch (err) {
    const e = err as AxiosError

    if (e.response?.status === 401) {
      errorMessage.value = 'Неверный логин или пароль'
    } else {
      errorMessage.value = 'Ошибка входа. Попробуйте ещё раз'
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">Вход</h1>
      <p class="login-subtitle">
        Введите логин и пароль, чтобы продолжить
      </p>

      <form class="login-form" @submit.prevent="login">
        <div class="field">
          <label class="field-label" for="login-username">Логин</label>
          <input
            id="login-username"
            v-model="username"
            type="text"
            autocomplete="username"
            class="field-input"
            placeholder="Ваш логин"
          >
        </div>

        <div class="field">
          <label class="field-label" for="login-password">Пароль</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            class="field-input"
            placeholder="Ваш пароль"
          >
        </div>

        <p v-if="errorMessage" class="error-text">
          {{ errorMessage }}
        </p>

        <button
          type="submit"
          class="btn-login"
          :disabled="!canSubmit"
        >
          <span v-if="!isLoading">Войти</span>
          <span v-else class="btn-spinner">
            <span class="spinner"></span>
            Входим...
          </span>
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #020617;
  padding: 24px 16px;
  box-sizing: border-box;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #020617;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  padding: 20px 22px 22px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.9);
  box-sizing: border-box;
}

.login-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  color: #e5e7eb;
  text-align: center;
}

.login-subtitle {
  margin: 0 0 18px;
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 12px;
  color: #e5e7eb;
}

.field-input {
  width: 100%;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.7);
  background: rgba(15, 23, 42, 0.9);
  color: #e5e7eb;
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.12s ease, box-shadow 0.12s ease, background 0.12s ease;
}

.field-input::placeholder {
  color: rgba(148, 163, 184, 0.8);
}

.field-input:focus {
  border-color: #38bdf8;
  box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.6);
  background: #020617;
}

.error-text {
  margin: 0;
  font-size: 13px;
  color: #fecaca;
  background: rgba(153, 27, 27, 0.55);
  border-radius: 10px;
  padding: 6px 10px;
}

.btn-login {
  margin-top: 4px;
  width: 100%;
  border: none;
  border-radius: 999px;
  padding: 9px 12px;
  font-size: 14px;
  font-weight: 500;
  background: linear-gradient(135deg, #22c55e, #0ea5e9);
  color: #f9fafb;
  cursor: pointer;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  box-shadow: 0 14px 32px rgba(34, 197, 94, 0.48);
  transition: transform 0.12s ease, box-shadow 0.12s ease, opacity 0.1s ease;
}

.btn-login:disabled {
  opacity: 0.5;
  cursor: default;
  box-shadow: none;
  transform: none;
}

.btn-login:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 40px rgba(34, 197, 94, 0.6);
}

.btn-spinner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid rgba(226, 232, 240, 0.7);
  border-top-color: #38bdf8;
  animation: spinner 0.8s linear infinite;
}

@keyframes spinner {
  to {
    transform: rotate(360deg);
  }
}
</style>