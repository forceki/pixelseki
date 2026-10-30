import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/creation',
      name: 'creation',
      component: () => import('../views/CreationView.vue'),
    },
    {
      path: '/creation/:id',
      name: 'creation-detail',
      component: () => import('../views/CreationDetailView.vue'),
    },
    {
      path: '/gallery',
      name: 'gallery',
      component: () => import('../views/GalleryView.vue'),
    },
    {
      path: '/objects',
      name: 'objects',
      component: () => import('../views/ObjectsView.vue'),
    },
    {
      path: '/objects/:id',
      name: 'object-detail',
      component: () => import('../views/AssetDetailView.vue'),
    },
  ],
})

export default router
