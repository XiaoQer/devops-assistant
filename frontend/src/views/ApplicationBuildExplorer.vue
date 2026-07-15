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

    <section v-if="contentState === 'error'" class="surface explorer-empty">
      <EmptyState title="构建历史加载失败" :description="contextError">
        <el-button type="primary" @click="refresh">重新加载</el-button>
      </EmptyState>
    </section>

    <section v-else-if="contentState === 'invalid'" class="surface explorer-empty">
      <EmptyState
        title="找不到这个构建版本"
        description="该构建不存在，或不属于当前 Project 和 Application。"
      >
        <el-button type="primary" @click="openLatestBuild">查看最新构建</el-button>
      </EmptyState>
    </section>

    <div v-else-if="contentState === 'history'" class="explorer-layout">
      <ApplicationBuildHistory
        :builds="builds"
        :selected-id="selectedBuild?.id"
        :loading="loadingContext"
        @select="selectBuild"
      />
      <ApplicationBuildDetail
        ref="detailPanel"
        :build="selectedBuild"
        :steps="visibleSteps"
        :selected-step-id="visibleStepId"
        :loading="loadingDetail"
        :execution-loading="executionLoading"
        :logs-error="visibleLogsError"
        :batch="selectedBatch"
        :selected-execution-key="selectedExecutionKey"
        @select-step="selectVisibleStep"
        @retry-logs="reloadLogs"
        @select-execution="selectExecution"
      />
    </div>

    <section v-else-if="contentState === 'empty'" class="surface explorer-empty">
      <EmptyState
        title="暂无构建版本"
        description="发起第一次构建后，历史与步骤日志会显示在这里。"
      >
        <el-button type="primary" @click="buildDrawer = true">发起构建</el-button>
      </EmptyState>
    </section>

    <QuickBuildDrawer
      v-model="buildDrawer"
      :project-id="projectId"
      :application="application"
      :environments="environments"
      @submitted="handleBuildSubmitted"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { applicationApi } from '../api/application'
import { pipelineApi } from '../api/pipeline'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ApplicationBuildHistory from '../components/pipeline/ApplicationBuildHistory.vue'
import ApplicationBuildDetail from '../components/pipeline/ApplicationBuildDetail.vue'
import QuickBuildDrawer from '../components/pipeline/QuickBuildDrawer.vue'
import {
  buildExplorerPath,
  canApplyBuildRefresh,
  canRefreshHistory,
  createRequestGate,
  defaultExecutionStepId,
  explorerContentState,
  batchForBuild,
  hasActiveDelivery,
  normalizeExecutionSteps,
  preserveExecutionKey,
  selectRequestedBuild,
  targetIdFromExecutionKey,
  type DeliveryExecutionKey,
  type ExecutionStepDetail,
} from '../features/build-explorer/state'
import type { Application, BuildVersion, CicdEnvironmentOption, ReleaseBatch } from '../types'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.projectId)
const applicationId = Number(route.params.applicationId)
const application = ref<Application>()
const builds = ref<BuildVersion[]>([])
const environments = ref<CicdEnvironmentOption[]>([])
const releaseBatches = ref<ReleaseBatch[]>([])
const selectedBuild = ref<BuildVersion>()
const selectedBatch = ref<ReleaseBatch>()
const steps = ref<ExecutionStepDetail[]>([])
const selectedStepId = ref<string>()
const selectedExecutionKey = ref<DeliveryExecutionKey>('build')
const deploySteps = ref<ExecutionStepDetail[]>([])
const selectedDeployStepId = ref<string>()
const invalidRequestedId = ref(false)
const contextError = ref('')
const logsError = ref('')
const deployError = ref('')
const loadingContext = ref(true)
const loadingDetail = ref(false)
const deployLoading = ref(false)
const buildDrawer = ref(false)
const detailPanel = ref<{ scrollIntoView: () => void }>()
const contextGate = createRequestGate()
const targetGate = createRequestGate()
const contentState = computed(() => explorerContentState(
  builds.value,
  invalidRequestedId.value,
  loadingContext.value,
  Boolean(contextError.value),
))
const visibleSteps = computed(() => selectedExecutionKey.value === 'build' ? steps.value : deploySteps.value)
const visibleStepId = computed(() => selectedExecutionKey.value === 'build'
  ? selectedStepId.value
  : selectedDeployStepId.value)
const visibleLogsError = computed(() => selectedExecutionKey.value === 'build'
  ? logsError.value
  : deployError.value)
const executionLoading = computed(() => selectedExecutionKey.value === 'build'
  ? loadingDetail.value
  : deployLoading.value)
let requestGeneration = 0
let refreshTimer: number | undefined

function requestedBuildId() {
  const value = route.params.buildId
  if (value === undefined || value === '') return undefined
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : Number.NaN
}

async function loadContext() {
  stopPolling()
  const contextGeneration = contextGate.next()
  loadingContext.value = true
  contextError.value = ''
  try {
    const [applicationData, buildItems, environmentItems, batchItems] = await Promise.all([
      applicationApi.get(projectId, applicationId),
      applicationApi.buildVersions(projectId, applicationId),
      applicationApi.environments(projectId, applicationId),
      applicationApi.releaseBatches(projectId, applicationId),
    ])
    if (!contextGate.isCurrent(contextGeneration)) return
    application.value = applicationData
    builds.value = buildItems
    environments.value = environmentItems.map(item => ({
      id: item.id,
      environment_name: item.environment_name,
      display_name: item.display_name,
      approval_required: item.approval_required,
    }))
    releaseBatches.value = batchItems
    await resolveRouteSelection(selectedBuild.value?.id === requestedBuildId())
  } catch (error) {
    if (contextGate.isCurrent(contextGeneration)) {
      contextError.value = (error as Error).message
      ElMessage.error(contextError.value)
    }
  } finally {
    if (contextGate.isCurrent(contextGeneration)) loadingContext.value = false
  }
}

async function resolveRouteSelection(preserveSelection = false) {
  const requestedId = requestedBuildId()
  const result = selectRequestedBuild(builds.value, requestedId)
  invalidRequestedId.value = result.invalidRequestedId
  if (!result.build) {
    selectedBuild.value = undefined
    selectedBatch.value = undefined
    steps.value = []
    selectedStepId.value = undefined
    resetDeployState()
    selectedExecutionKey.value = 'build'
    stopPolling()
    return
  }
  if (requestedId === undefined) {
    await router.replace(buildExplorerPath(projectId, applicationId, result.build.id))
    await loadSelectedBuild(result.build.id, preserveSelection)
    return
  }
  await loadSelectedBuild(result.build.id, preserveSelection)
}

async function loadSelectedBuild(buildId: number, preserveSelection = false) {
  const generation = ++requestGeneration
  const previousExecutionKey = selectedExecutionKey.value
  loadingDetail.value = true
  logsError.value = ''
  steps.value = []
  selectedStepId.value = undefined
  selectedBatch.value = undefined
  resetDeployState()
  if (!preserveSelection) selectedExecutionKey.value = 'build'
  try {
    const build = await applicationApi.buildVersion(projectId, applicationId, buildId)
    if (generation !== requestGeneration) return
    selectedBuild.value = build
    const index = builds.value.findIndex(item => item.id === build.id)
    if (index >= 0) builds.value.splice(index, 1, build)
    selectedBatch.value = batchForBuild(releaseBatches.value, build.id)
    selectedExecutionKey.value = preserveSelection
      ? preserveExecutionKey(previousExecutionKey, selectedBatch.value)
      : 'build'
    const targetId = targetIdFromExecutionKey(selectedExecutionKey.value)
    const requests: Promise<void>[] = []
    if (build.pipeline_run_name) requests.push(loadLogs(build, generation))
    if (targetId !== undefined) requests.push(loadTargetLogs(targetId))
    await Promise.all(requests)
  } catch (error) {
    if (generation !== requestGeneration) return
    invalidRequestedId.value = true
    selectedBuild.value = undefined
    selectedBatch.value = undefined
    ElMessage.error((error as Error).message)
  } finally {
    if (generation === requestGeneration) {
      loadingDetail.value = false
      syncPolling()
    }
  }
}

function resetDeployState() {
  targetGate.next()
  deploySteps.value = []
  selectedDeployStepId.value = undefined
  deployError.value = ''
  deployLoading.value = false
}

async function loadTargetLogs(targetId: number) {
  const generation = targetGate.next()
  deploySteps.value = []
  selectedDeployStepId.value = undefined
  deployError.value = ''
  const target = selectedBatch.value?.targets.find(item => item.id === targetId)
  if (!target?.pipeline_run_name) {
    deployLoading.value = false
    return
  }
  deployLoading.value = true
  try {
    const details = await pipelineApi.logs(projectId, target.pipeline_run_name)
    if (!targetGate.isCurrent(generation)) return
    deploySteps.value = normalizeExecutionSteps(details)
    selectedDeployStepId.value = defaultExecutionStepId(deploySteps.value)
  } catch (error) {
    if (targetGate.isCurrent(generation)) deployError.value = (error as Error).message
  } finally {
    if (targetGate.isCurrent(generation)) deployLoading.value = false
  }
}

function selectExecution(key: DeliveryExecutionKey) {
  if (selectedExecutionKey.value === key) return
  selectedExecutionKey.value = key
  const targetId = targetIdFromExecutionKey(key)
  if (targetId === undefined) {
    targetGate.next()
    deployLoading.value = false
    return
  }
  void loadTargetLogs(targetId)
}

function selectVisibleStep(stepId: string) {
  if (selectedExecutionKey.value === 'build') selectedStepId.value = stepId
  else selectedDeployStepId.value = stepId
}

async function loadLogs(build: BuildVersion, generation: number) {
  if (!build.pipeline_run_name) return
  try {
    const details = await pipelineApi.logs(projectId, build.pipeline_run_name)
    if (generation !== requestGeneration) return
    steps.value = normalizeExecutionSteps(details)
    selectedStepId.value = defaultExecutionStepId(steps.value)
  } catch (error) {
    if (generation !== requestGeneration) return
    logsError.value = (error as Error).message
  }
}

function selectBuild(buildId: number) {
  if (selectedBuild.value?.id === buildId) return
  contextGate.next()
  void router.push(buildExplorerPath(projectId, applicationId, buildId)).then(async () => {
    if (window.matchMedia('(max-width: 760px)').matches) {
      await nextTick()
      detailPanel.value?.scrollIntoView()
    }
  })
}

async function refreshSelected() {
  const buildId = selectedBuild.value?.id
  if (!canRefreshHistory(loadingContext.value, buildId)) return
  const contextGeneration = contextGate.next()
  try {
    const [buildItems, batchItems] = await Promise.all([
      applicationApi.buildVersions(projectId, applicationId),
      applicationApi.releaseBatches(projectId, applicationId),
    ])
    if (!contextGate.isCurrent(contextGeneration)
      || !canApplyBuildRefresh(buildId, requestedBuildId(), selectedBuild.value?.id)) return
    builds.value = buildItems
    releaseBatches.value = batchItems
    if (builds.value.some(item => item.id === buildId)) await loadSelectedBuild(buildId, true)
  } catch (error) {
    if (contextGate.isCurrent(contextGeneration)) ElMessage.error((error as Error).message)
  }
}

function reloadLogs() {
  const targetId = targetIdFromExecutionKey(selectedExecutionKey.value)
  if (targetId !== undefined) void loadTargetLogs(targetId)
  else if (selectedBuild.value) void loadSelectedBuild(selectedBuild.value.id, true)
}

function refresh() {
  void loadContext()
}

function openLatestBuild() {
  const latest = builds.value[0]
  if (latest) void router.replace(buildExplorerPath(projectId, applicationId, latest.id))
}

function handleBuildSubmitted() {
  buildDrawer.value = false
  void router.replace(buildExplorerPath(projectId, applicationId)).then(() => loadContext())
}

function backToWorkbench() {
  void router.push(`/devcenter/projects/${projectId}/pipelines`)
}

function syncPolling() {
  stopPolling()
  if (hasActiveDelivery(selectedBuild.value, selectedBatch.value)) {
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
  if (!loadingContext.value && builds.value.length) {
    contextGate.next()
    void resolveRouteSelection()
  }
})

onMounted(() => void loadContext())
onBeforeUnmount(() => {
  contextGate.next()
  targetGate.next()
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

.explorer-layout > .build-history {
  position: sticky;
  top: 80px;
  max-height: calc(100vh - 92px);
}

.explorer-empty {
  box-shadow: none;
}

@media (max-width: 760px) {
  .explorer-layout {
    grid-template-columns: 1fr;
  }

  .explorer-layout > .build-history {
    position: static;
    max-height: none;
  }
}
</style>
