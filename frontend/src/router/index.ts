import { createRouter, createWebHistory } from 'vue-router'
import ApplicationList from '../views/ApplicationList.vue'
import ApplicationCreate from '../views/ApplicationCreate.vue'
import ApplicationDetail from '../views/ApplicationDetail.vue'
import PipelineDetail from '../views/PipelineDetail.vue'
import Dashboard from '../views/Dashboard.vue'
import ReleaseCenter from '../views/ReleaseCenter.vue'
import PipelineRuns from '../views/PipelineRuns.vue'
import Approvals from '../views/Approvals.vue'
import ContainerRegistries from '../views/ContainerRegistries.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: Dashboard },
    { path: '/applications', component: ApplicationList },
    { path: '/applications/new', component: ApplicationCreate },
    { path: '/applications/:id', component: ApplicationDetail },
    { path: '/pipelines/:name', component: PipelineDetail },
    { path: '/pipelines', component: PipelineRuns },
    { path: '/releases', component: ReleaseCenter },
    { path: '/approvals', component: Approvals },
    { path: '/settings/registries', component: ContainerRegistries },
  ],
})
