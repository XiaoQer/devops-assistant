import { createRouter, createWebHistory } from 'vue-router'
import type { Pinia } from 'pinia'
import MainLayout from '../layouts/MainLayout.vue'
import PortalLayout from '../layouts/PortalLayout.vue'
import ProjectCenterLayout from '../layouts/ProjectCenterLayout.vue'
import DevCenterLayout from '../layouts/DevCenterLayout.vue'
import Login from '../views/Login.vue'
import { onAuthenticationRequired } from '../api/client'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: Login,
      meta: { public: true },
    },
    {
      path: '/',
      redirect: '/portal',
    },
    {
      path: '/portal',
      component: PortalLayout,
      children: [
        {
          path: '',
          component: () => import('../views/PortalHome.vue'),
        },
      ],
    },
    {
      path: '/project-center',
      component: ProjectCenterLayout,
      children: [
        {
          path: '',
          redirect: '/project-center/projects',
        },
        {
          path: 'projects',
          component: () => import('../views/ProjectCenter.vue'),
          meta: { title: 'Project governance' },
        },
        {
          path: 'projects/:id',
          component: () => import('../views/ProjectDetail.vue'),
          meta: { title: 'Project Overview' },
        },
        {
          path: 'projects/:id/members',
          component: () => import('../views/ProjectResourceOverview.vue'),
          meta: { title: 'Members & Permissions', resource: 'members' },
        },
        {
          path: 'projects/:id/clusters',
          component: () => import('../views/ProjectKubernetesSettings.vue'),
          meta: { title: 'Kubernetes' },
        },
        {
          path: 'projects/:id/registries',
          component: () => import('../views/ProjectRegistriesSettings.vue'),
          meta: { title: 'Registries' },
        },
        {
          path: 'projects/:id/applications',
          component: () => import('../views/DevProjectWorkspace.vue'),
          meta: { title: 'Applications' },
        },
      ],
    },
    {
      path: '/devcenter',
      component: DevCenterLayout,
      children: [
        {
          path: '',
          redirect: '/devcenter/projects',
        },
        {
          path: 'projects',
          component: () => import('../views/DevCenter.vue'),
          meta: { title: 'Application delivery' },
        },
        {
          path: 'projects/:id',
          component: () => import('../views/DevCenterProject.vue'),
          meta: { title: 'Overview' },
        },
        {
          path: 'projects/:projectId/applications',
          component: () => import('../views/ApplicationList.vue'),
          meta: { title: 'Applications' },
        },
        {
          path: 'projects/:projectId/applications/new',
          component: () => import('../views/ApplicationCreate.vue'),
          meta: { title: 'Create application' },
        },
        {
          path: 'projects/:projectId/applications/:id',
          component: () => import('../views/ApplicationDetail.vue'),
          meta: { title: 'Application workspace' },
        },
        {
          path: 'projects/:projectId/pipelines',
          component: () => import('../views/PipelineRuns.vue'),
          meta: { title: 'Pipelines' },
        },
        {
          path: 'projects/:projectId/pipelines/applications/:applicationId/builds/:buildId?',
          component: () => import('../views/ApplicationBuildExplorer.vue'),
          meta: { title: 'Application builds' },
        },
        {
          path: 'projects/:projectId/pipelines/:name',
          component: () => import('../views/PipelineDetail.vue'),
          meta: { title: 'Pipeline detail' },
        },
        {
          path: 'projects/:projectId/releases',
          component: () => import('../views/ReleaseCenter.vue'),
          meta: { title: 'Releases' },
        },
        {
          path: 'projects/:projectId/approvals',
          component: () => import('../views/Approvals.vue'),
          meta: { title: 'Approvals' },
        },
        {
          path: 'projects/:projectId/runtime',
          component: () => import('../views/ProjectRuntime.vue'),
          meta: { title: 'Runtime' },
        },
        {
          path: 'projects/:projectId/runtime/environments/:environment/applications/:applicationId/pods/:podName',
          component: () => import('../views/PodDetail.vue'),
          meta: { title: 'Pod detail' },
        },
        {
          path: 'projects/:projectId/logs',
          component: () => import('../views/PipelineRuns.vue'),
          meta: { title: 'Logs' },
        },
      ],
    },
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: 'dashboard', component: () => import('../views/Dashboard.vue') },
        { path: 'projects', component: () => import('../views/ProjectList.vue') },
        { path: 'projects/:id', component: () => import('../views/ProjectDetail.vue') },
      ],
    },
  ],
})

let authGuardInstalled = false
let authenticationCallbackInstalled = false

export const installAuthGuard = (pinia: Pinia) => {
  if (!authGuardInstalled) {
    authGuardInstalled = true
    router.beforeEach(async to => {
      const auth = useAuthStore(pinia)
      try {
        await auth.initialize()
      } catch {
        if (to.meta.public) {
          if (to.query.session_unavailable !== undefined) return true
          return { path: '/login', query: { ...to.query, session_unavailable: '1' }, replace: true }
        }
        return {
          path: '/login',
          query: { redirect: to.fullPath, error: 'session_unavailable' },
          replace: true,
        }
      }

      if (to.path === '/login' && auth.user) return '/portal'
      if (!to.meta.public && !auth.user) {
        return { path: '/login', query: { redirect: to.fullPath } }
      }
      return true
    })
  }

  if (!authenticationCallbackInstalled) {
    authenticationCallbackInstalled = true
    onAuthenticationRequired(() => {
      const auth = useAuthStore(pinia)
      auth.clear()
      if (router.currentRoute.value.path !== '/login') {
        void router.replace({
          path: '/login',
          query: { redirect: router.currentRoute.value.fullPath },
        })
      }
    })
  }
}

export default router
