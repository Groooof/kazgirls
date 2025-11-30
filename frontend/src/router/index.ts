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
  // const token = Cookies.get('access_token')

  // // 1) Нет токена → только /login
  // if (!token) {
  //   meCache = null

  //   if (to.name === 'Login') {
  //     return next()
  //   }

  //   return next({
  //     name: 'Login',
  //     query: { redirect: to.fullPath },
  //   })
  // }

  const { data: me } = await axios.get(`${config.url}${config.apiUrl}/tokens/me`, { withCredentials: true })

  if (!me) {
    if (to.name === 'Login') return next()
    return next({
      name: 'Login',
      query: { redirect: to.fullPath },
    })
  }

  if (to.name === 'Login') {
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

  if (me.is_streamer) {
    const isOnOwnStreamRoute =
      to.name === 'Streamer' && String(to.params.id) === String(me.id)

    if (!isOnOwnStreamRoute) {
      return next({
        name: 'Streamer',
        params: { id: me.id },
      })
    }

    // уже на своей /streamers/:id/stream → всё ок
    return next()
  }

  // 5) Если НЕ стример:
  //    можно доп. защиту — запретить заходить на /streamers/:id/stream
  if (!me.is_streamer && to.name === 'Streamer') {
    return next({ name: 'StreamersList' })
  }

  // Остальные страницы (Models/Viewer и т.п.) доступны
  return next()
})

export default router
