import { createRouter, createWebHistory } from 'vue-router'
import DeveloperSearch from '../views/DeveloperSearch.vue'

const routes = [
  {
    path: '/',
    name: 'DeveloperSearch',
    component: DeveloperSearch
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
