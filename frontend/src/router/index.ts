import { createRouter, createWebHistory } from 'vue-router'
import StreamersList from '@/views/StreamersList.vue'
import Streamer from '@/views/Streamer.vue'
import Viewer from '@/views/Viewer.vue'
import Login from '@/views/Login.vue'
import Cookies from 'js-cookie'
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

router.beforeEach(async(to, from, next) => {
 // 1) /login всегда доступен, но если уже авторизован — редиректим по роли
  if (to.name === 'Login') {
    const { data: me } = await axios.get(`${config.url}${config.apiUrl}/tokens/me`, { withCredentials: true })

    // не авторизован — показываем логин
    if (!me) {
      meCache = null
      return next()
    }

    // уже авторизован
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

  // 2) Для всех других страниц: сначала проверяем, авторизован ли юзер
  const { data: me } = await axios.get(`${config.url}${config.apiUrl}/tokens/me`, { withCredentials: true })

  // не авторизован → на логин с redirect
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
