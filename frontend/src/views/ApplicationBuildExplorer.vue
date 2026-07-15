<template>
  <div class="page-content page-stack build-explorer-page">
    <PageHeader
      eyebrow="CI/CD · Application builds"
      :title="application?.name || '构建历史'"
      :description="application ? shortRepo(application.repo_url) : '加载 Application 构建历史和执行日志。'"
    >
      <el-button @click="backToWorkbench">返回工作台</el-button>
      <el-button @click="workspace?.refresh()">刷新</el-button>
    </PageHeader>

    <ApplicationBuildWorkspace
      ref="workspace"
      :project-id="projectId"
      :application-id="applicationId"
      :selected-build-id="requestedBuildId"
      @application-loaded="application = $event"
      @select-build="selectBuild"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ApplicationBuildWorkspace from '../components/pipeline/ApplicationBuildWorkspace.vue'
import { buildExplorerPath } from '../features/build-explorer/state'
import type { Application } from '../types'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.projectId)
const applicationId = Number(route.params.applicationId)
const application = ref<Application>()
const workspace = ref<{ refresh: () => void }>()
const requestedBuildId = computed(() => {
  const value = route.params.buildId
  if (value === undefined || value === '') return undefined
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : Number.NaN
})

function selectBuild(buildId: number) {
  const path = buildExplorerPath(projectId, applicationId, buildId)
  if (requestedBuildId.value === undefined) void router.replace(path)
  else if (requestedBuildId.value !== buildId) void router.push(path)
}

function backToWorkbench() {
  void router.push(`/devcenter/projects/${projectId}/pipelines`)
}

function shortRepo(value: string) {
  return value.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\.git$/, '')
}
</script>

<style scoped>
.build-explorer-page { gap: 12px; }
.build-explorer-page :deep(.page-header) { margin-bottom: 0; }
.build-explorer-page :deep(.page-header h1) { font-size: 27px; }
</style>
