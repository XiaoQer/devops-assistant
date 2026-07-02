import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import PortalLayout from '../layouts/PortalLayout.vue'
import ProjectCenterLayout from '../layouts/ProjectCenterLayout.vue'
import DevCenterLayout from '../layouts/DevCenterLayout.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
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
          path: 'projects/:projectId/runtime',
          component: () => import('../views/ApplicationList.vue'),
          meta: { title: 'Runtime' },
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
        { path: 'applications', component: () => import('../views/ApplicationList.vue') },
        { path: 'applications/new', component: () => import('../views/ApplicationCreate.vue') },
        { path: 'applications/:id', component: () => import('../views/ApplicationDetail.vue') },
        { path: 'pipelines/:name', component: () => import('../views/PipelineDetail.vue') },
        { path: 'pipelines', component: () => import('../views/PipelineRuns.vue') },
        { path: 'releases', component: () => import('../views/ReleaseCenter.vue') },
        { path: 'approvals', component: () => import('../views/Approvals.vue') },
        { path: 'settings/registries', component: () => import('../views/ContainerRegistries.vue') },
      ],
    },
  ],
})
