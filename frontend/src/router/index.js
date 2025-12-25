import { createRouter, createWebHistory } from 'vue-router'

import LoginPage from '../components/pages/LoginPage.vue'
import MainAppPage from '../components/pages/MainAppPage.vue'

function isAuthed() {
  return !!localStorage.getItem('onyx_token')
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: () => (isAuthed() ? '/app' : '/login') },
    { path: '/login', name: 'login', component: LoginPage },
    { path: '/app', name: 'app', component: MainAppPage, meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthed()) return { name: 'login' }
  if (to.name === 'login' && isAuthed()) return { name: 'app' }
  return true
})

export default router
