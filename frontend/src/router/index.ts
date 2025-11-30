import { createRouter, createWebHistory } from 'vue-router'
import StreamersList from '@/views/StreamersList.vue'
import Streamer from '@/views/Streamer.vue'
import Viewer from '@/views/Viewer.vue'
import Login from '@/views/Login.vue'
import axios from 'axios'
import { config } from '@/config'

type Me = {
  id: number
  username: string
  is_streamer: boolean
  is_superuser: boolean
}

const routes = [
  {
    path: '/',
    name: 'StreamersList',
    component: StreamersList,
  },
  {
    path: '/streamers/:id/stream',
    name: 'Streamer',
    component: Streamer,
  },
  {
    path: '/streamers/:id/view',
    name: 'Viewer',
    component: Viewer,
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'StreamersList' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

let meCache: Me | null = null
let mePromise: Promise<Me | null> | null = null

const getMeSafe = async (): Promise<Me | null> => {
  // простенький кеш, чтобы не долбить /me на каждый чих
  if (meCache) return meCache
  if (mePromise) return mePromise

  mePromise = axios
    .get<Me>(`${config.url}${config.apiUrl}/tokens/me`, {
      withCredentials: true,
    })
    .then((resp) => {
      meCache = resp.data
      return meCache
    })
    .catch((err) => {
      // если 401 — просто считаем, что юзер не залогинен
      if (err.response?.status === 401) {
        meCache = null
        return null
      }

      console.error('[router] /tokens/me error', err)
      meCache = null
      return null
    })
    .finally(() => {
      mePromise = null
    })

  return mePromise
}

router.beforeEach(async (to, from, next) => {
  // 1) Если идём на /login
  if (to.name === 'Login') {
    const me = await getMeSafe()

    // не залогинен → можно показать логин-страницу
    if (!me) {
      return next()
    }

    // уже залогинен
    if (me.is_streamer) {
      return next({
        name: 'Streamer',
        params: { id: me.id },
      })
    }

    const redirect = to.query.redirect as string | undefined
    if (redirect && redirect !== '/login') {
      return next(redirect)
    }

    return next({ name: 'StreamersList' })
  }

  // 2) Для всех остальных страниц — сначала проверяем, кто мы
  const me = await getMeSafe()

  // не залогинен → отправляем на логин с сохранением урла
  if (!me) {
    return next({
      name: 'Login',
      query: { redirect: to.fullPath },
    })
  }

  // 3) Если пользователь — стример
  if (me.is_streamer) {
    const isOnOwnStreamRoute =
      to.name === 'Streamer' && String(to.params.id) === String(me.id)

    if (!isOnOwnStreamRoute) {
      return next({
        name: 'Streamer',
        params: { id: me.id },
      })
    }

    return next()
  }

  // 4) Если НЕ стример — нельзя на стримерскую панель
  if (!me.is_streamer && to.name === 'Streamer') {
    return next({ name: 'StreamersList' })
  }

  // 5) Всё остальное зрителям доступно
  return next()
})

export default router
