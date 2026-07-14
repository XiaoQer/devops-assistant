<template>
  <div class="page-content page-stack build-explorer-page">
    <PageHeader
      eyebrow="CI/CD · Application builds"
      :title="application?.name || '构建历史'"
      :description="application ? shortRepo(application.repo_url) : '加载 Application 构建历史和执行日志。'"
    >
      <el-button @click="backToWorkbench">返回工作台</el-button>
      <el-button :loading="loadingContext || loadingDetail" @click="refresh">刷新</el-button>
    </PageHeader>

    <div v-if="builds.length" class="explorer-layout">
      <ApplicationBuildHistory
        :builds="builds"
        :selected-id="selectedBuild?.id"
        :loading="loadingContext"
        @select="selectBuild"
      />
      <ApplicationBuildDetail
        ref="detailPanel"
        :build="selectedBuild"
        :steps="steps"
        :selected-step-id="selectedStepId"
        :loading="loadingDetail"
        :logs-error="logsError"
        @select-step="selectedStepId = $event"
        @retry-logs="reloadLogs"
      />
    </div>

    <section v-else-if="invalidRequestedId && !loadingContext" class="surface explorer-empty">
      <EmptyState
        title="找不到这个构建版本"
        description="该构建不存在，或不属于当前 Project 和 Application。"
      >
        <el-button type="primary" @click="openLatestBuild">查看最新构建</el-button>
      </EmptyState>
    </section>

    <section v-else-if="!loadingContext" class="surface explorer-empty">
      <EmptyState
        title="暂无构建版本"
        description="从 CI/CD 工作台发起第一次构建后，历史与步骤日志会显示在这里。"
      >
        <el-button type="primary" @click="backToWorkbench">返回工作台构建</el-button>
      </EmptyState>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { applicationApi } from '../api/application'
import { pipelineApi } from '../api/pipeline'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ApplicationBuildHistory from '../components/pipeline/ApplicationBuildHistory.vue'
import ApplicationBuildDetail from '../components/pipeline/ApplicationBuildDetail.vue'
import {
  buildExplorerPath,
  defaultStepId,
  normalizeBuildSteps,
  selectRequestedBuild,
  shouldPollBuild,
  type BuildStepDetail,
} from '../features/build-explorer/state'
import type { Application, BuildVersion } from '../types'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.projectId)
const applicationId = Number(route.params.applicationId)
const application = ref<Application>()
const builds = ref<BuildVersion[]>([])
const selectedBuild = ref<BuildVersion>()
const steps = ref<BuildStepDetail[]>([])
const selectedStepId = ref<string>()
const invalidRequestedId = ref(false)
const logsError = ref('')
const loadingContext = ref(true)
const loadingDetail = ref(false)
const detailPanel = ref<{ scrollIntoView: () => void }>()
let requestGeneration = 0
let refreshTimer: number | undefined

function requestedBuildId() {
  const value = route.params.buildId
  if (value === undefined || value === '') return undefined
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : Number.NaN
}

async function loadContext() {
  loadingContext.value = true
  try {
    const [applicationData, buildItems] = await Promise.all([
      applicationApi.get(projectId, applicationId),
      applicationApi.buildVersions(projectId, applicationId),
    ])
    application.value = applicationData
    builds.value = buildItems
    await resolveRouteSelection()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingContext.value = false
  }
}

async function resolveRouteSelection() {
  const requestedId = requestedBuildId()
  const result = selectRequestedBuild(builds.value, requestedId)
  invalidRequestedId.value = result.invalidRequestedId
  if (!result.build) {
    selectedBuild.value = undefined
    steps.value = []
    selectedStepId.value = undefined
    stopPolling()
    return
  }
  if (requestedId === undefined) {
    await router.replace(buildExplorerPath(projectId, applicationId, result.build.id))
    return
  }
  await loadSelectedBuild(result.build.id)
}

async function loadSelectedBuild(buildId: number) {
  const generation = ++requestGeneration
  loadingDetail.value = true
  logsError.value = ''
  steps.value = []
  selectedStepId.value = undefined
  try {
    const build = await applicationApi.buildVersion(projectId, applicationId, buildId)
    if (generation !== requestGeneration) return
    selectedBuild.value = build
    const index = builds.value.findIndex(item => item.id === build.id)
    if (index >= 0) builds.value.splice(index, 1, build)
    if (build.pipeline_run_name) await loadLogs(build, generation)
  } catch (error) {
    if (generation !== requestGeneration) return
    invalidRequestedId.value = true
    selectedBuild.value = undefined
    ElMessage.error((error as Error).message)
  } finally {
    if (generation === requestGeneration) {
      loadingDetail.value = false
      syncPolling()
    }
  }
}

async function loadLogs(build: BuildVersion, generation: number) {
  if (!build.pipeline_run_name) return
  try {
    const details = await pipelineApi.logs(projectId, build.pipeline_run_name)
    if (generation !== requestGeneration) return
    steps.value = normalizeBuildSteps(details)
    selectedStepId.value = defaultStepId(steps.value)
  } catch (error) {
    if (generation !== requestGeneration) return
    logsError.value = (error as Error).message
  }
}

function selectBuild(buildId: number) {
  if (selectedBuild.value?.id === buildId) return
  void router.push(buildExplorerPath(projectId, applicationId, buildId)).then(async () => {
    if (window.matchMedia('(max-width: 760px)').matches) {
      await nextTick()
      detailPanel.value?.scrollIntoView()
    }
  })
}

async function refreshSelected() {
  const buildId = selectedBuild.value?.id
  if (!buildId) return
  try {
    builds.value = await applicationApi.buildVersions(projectId, applicationId)
    if (builds.value.some(item => item.id === buildId)) await loadSelectedBuild(buildId)
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

function reloadLogs() {
  if (selectedBuild.value) void loadSelectedBuild(selectedBuild.value.id)
}

function refresh() {
  void loadContext()
}

function openLatestBuild() {
  const latest = builds.value[0]
  if (latest) void router.replace(buildExplorerPath(projectId, applicationId, latest.id))
  else void router.replace(buildExplorerPath(projectId, applicationId, 0).replace('/0', ''))
}

function backToWorkbench() {
  void router.push(`/devcenter/projects/${projectId}/pipelines`)
}

function syncPolling() {
  stopPolling()
  if (selectedBuild.value && shouldPollBuild(selectedBuild.value.status)) {
    refreshTimer = window.setInterval(() => void refreshSelected(), 15000)
  }
}

function stopPolling() {
  if (refreshTimer !== undefined) window.clearInterval(refreshTimer)
  refreshTimer = undefined
}

function shortRepo(value: string) {
  return value.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\.git$/, '')
}

watch(() => route.params.buildId, () => {
  if (!loadingContext.value && builds.value.length) void resolveRouteSelection()
})

onMounted(() => void loadContext())
onBeforeUnmount(() => {
  requestGeneration += 1
  stopPolling()
})
</script>

<style scoped>
.build-explorer-page {
  gap: 12px;
}

.build-explorer-page :deep(.page-header) {
  margin-bottom: 0;
}

.build-explorer-page :deep(.page-header h1) {
  font-size: 27px;
}

.explorer-layout {
  display: grid;
  grid-template-columns: minmax(250px, 300px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.explorer-empty {
  box-shadow: none;
}

@media (max-width: 760px) {
  .explorer-layout {
    grid-template-columns: 1fr;
  }
}
</style>
