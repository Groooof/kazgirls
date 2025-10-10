import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/views/HomePage.vue'
import NotFound from '@/views/NotFound.vue'
import ConfirmPage from '@/views/ConfirmPage.vue'
import PaymentFailed from '@/views/PaymentFailed.vue'

const routes = [
  {
    path: '/confirm',
    name: 'Confirm',
    component: ConfirmPage,
  },
  {
    path: '/:token',
    name: 'Home',
    component: HomePage,
  },
  {
    path: '/:token',
    name: 'Home',
    component: HomePage,
  },
  {
    path: '/payment',
    name: 'Payment',
    component: PaymentFailed,
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
