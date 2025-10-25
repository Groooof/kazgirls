import { createRouter, createWebHistory } from 'vue-router'
import NotFound from '@/views/NotFound.vue'
import Streamer from '@/views/Streamer.vue'
import Viewer from '@/views/Viewer.vue'

const routes = [
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
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
  },
]
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
