import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'applications', component: () => import('../views/ApplicationList.vue') },
        { path: 'applications/new', component: () => import('../views/ApplicationCreate.vue') },
        { path: 'applications/:id', component: () => import('../views/ApplicationDetail.vue') },
        { path: 'pipelines/:name', component: () => import('../views/PipelineDetail.vue') },
        { path: 'pipelines', component: () => import('../views/PipelineRuns.vue') },
        { path: 'releases', component: () => import('../views/ReleaseCenter.vue') },
        { path: 'approvals', component: () => import('../views/Approvals.vue') },
        { path: 'settings/registries', component: () => import('../views/ContainerRegistries.vue') },
      ]
    }
  ],
})
