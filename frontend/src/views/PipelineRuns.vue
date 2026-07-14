<template>
  <div class="page-content page-stack">
    <PageHeader
      title="CI/CD 工作台"
      description="跨 Application 快速构建、发布和跟踪交付状态。"
    >
      <el-button :loading="loadingWorkbench" @click="loadWorkbench">刷新</el-button>
      <el-button type="primary" @click="openApplicationPicker">＋ 快速构建</el-button>
    </PageHeader>

    <section class="surface application-section">
      <div class="toolbar">
        <el-input
          v-model="query"
          placeholder="搜索 Application 或仓库…"
          clearable
        />
        <el-select v-model="status" placeholder="全部状态" style="width: 150px">
          <el-option label="全部状态" value="" />
          <el-option v-for="item in statuses" :key="item" :label="item" :value="item" />
        </el-select>
        <span>{{ workbenchItems.length }} Applications</span>
        <span v-if="counts.running">{{ counts.running }} 个进行中</span>
        <span v-if="counts.failed" class="failed-count">{{ counts.failed }} 个失败</span>
      </div>
      <el-skeleton :loading="loadingWorkbench" animated :rows="8">
        <div v-if="workbenchItems.length" class="application-grid">
          <article v-for="item in workbenchItems" :key="item.application.id" class="application-card">
            <div class="card-head">
              <div>
                <h4>{{ item.application.name }}</h4>
                <p>{{ shortRepo(item.application.repo_url) }}</p>
              </div>
              <StatusBadge :status="item.activity_status" />
            </div>

            <div class="build-meta">
              <span>{{ item.latest_build?.git_branch || item.application.branch }}</span>
              <span>{{ shortSha(item.latest_build?.git_commit) }}</span>
              <span>{{ formatRelative(item.last_activity_at) }}</span>
            </div>

            <div class="delivery-flow">
              <span :class="stageClass(item.latest_build?.status)">Build {{ statusMark(item.latest_build?.status) }}</span>
              <template v-if="item.latest_batch?.targets.length">
                <span class="flow-arrow">→</span>
                <span
                  v-for="target in item.latest_batch.targets"
                  :key="target.id"
                  :class="stageClass(target.status)"
                >
                  {{ target.display_name || target.environment }} {{ statusMark(target.status) }}
                </span>
              </template>
              <span v-else class="stage muted-stage">尚未关联环境</span>
            </div>

            <p v-if="item.latest_build?.commit_message" class="commit-message">
              {{ item.latest_build.commit_message }}
            </p>

            <div class="card-actions">
              <el-button
                v-if="isRunning(item)"
                type="primary"
                @click="openPipeline(item)"
              >
                查看进度
              </el-button>
              <template v-else>
                <el-tooltip content="构建" placement="top">
                  <el-button
                    class="compact-action"
                    type="primary"
                    circle
                    aria-label="构建"
                    :icon="Tools"
                    @click="openBuild(item)"
                  />
                </el-tooltip>
              </template>
              <el-button
                v-if="canPromote(item)"
                @click="openPromote(item)"
              >
                发布此版本
              </el-button>
              <el-button
                v-if="isFailed(item) && pipelineName(item)"
                @click="retry(item)"
              >
                重试
              </el-button>
              <el-tooltip content="查看构建历史" placement="top">
                <el-button
                  class="compact-action"
                  circle
                  aria-label="查看构建历史"
                  :icon="View"
                  @click="openBuildHistory(item)"
                />
              </el-tooltip>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="没有匹配的 Application"
          description="调整搜索或状态筛选，或者先在当前 Project 中创建 Application。"
        />
      </el-skeleton>
    </section>

    <el-dialog v-model="applicationPicker" title="选择要构建的 Application" width="460px">
      <el-select
        v-model="pickedApplicationId"
        filterable
        class="full-width"
        placeholder="搜索 Application"
      >
        <el-option
          v-for="item in workbenchItems"
          :key="item.application.id"
          :label="item.application.name"
          :value="item.application.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="applicationPicker = false">取消</el-button>
        <el-button type="primary" :disabled="!pickedApplicationId" @click="confirmApplicationPicker">
          下一步
        </el-button>
      </template>
    </el-dialog>

    <QuickBuildDrawer
      v-model="buildDrawer"
      :project-id="projectId"
      :application="selectedItem?.application"
      :environments="selectedItem?.available_environments || []"
      @submitted="handleSubmitted"
    />

    <PromoteBuildDrawer
      v-if="promoteItem?.latest_build && promoteItem.latest_batch"
      v-model="promoteDrawer"
      :project-id="projectId"
      :application="promoteItem.application"
      :build="promoteItem.latest_build"
      :batch="promoteItem.latest_batch"
      :environments="promoteItem.available_environments"
      @submitted="handleSubmitted"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Tools, View } from '@element-plus/icons-vue'
import { pipelineApi } from '../api/pipeline'
import { buildExplorerPath } from '../features/build-explorer/state'
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import QuickBuildDrawer from '../components/pipeline/QuickBuildDrawer.vue'
import PromoteBuildDrawer from '../components/pipeline/PromoteBuildDrawer.vue'
import type { CicdWorkbenchItem } from '../types'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.projectId)
const workbenchItems = ref<CicdWorkbenchItem[]>([])
const status = ref('')
const query = ref('')
const loadingWorkbench = ref(false)
const buildDrawer = ref(false)
const promoteDrawer = ref(false)
const applicationPicker = ref(false)
const pickedApplicationId = ref<number>()
const selectedItem = ref<CicdWorkbenchItem>()
const promoteItem = ref<CicdWorkbenchItem>()
const statuses = ['Succeeded', 'Running', 'Pending', 'WaitingApproval', 'Failed', 'BuildFailed']
const counts = computed(() => ({
  running: workbenchItems.value.filter(item => ['Running', 'Pending', 'Building', 'Deploying', 'WaitingApproval'].includes(item.activity_status)).length,
  failed: workbenchItems.value.filter(item => ['Failed', 'BuildFailed', 'PartialFailed'].includes(item.activity_status)).length,
}))

async function loadWorkbench() {
  loadingWorkbench.value = true
  try {
    const data = await pipelineApi.workbench(projectId, {
      query: query.value || undefined,
      status: status.value || undefined,
    })
    workbenchItems.value = data.items
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingWorkbench.value = false
  }
}

function openBuild(item: CicdWorkbenchItem) {
  selectedItem.value = item
  buildDrawer.value = true
}

function openPromote(item: CicdWorkbenchItem) {
  promoteItem.value = item
  promoteDrawer.value = true
}

function openApplicationPicker() {
  pickedApplicationId.value = undefined
  applicationPicker.value = true
}

function confirmApplicationPicker() {
  const item = workbenchItems.value.find(entry => entry.application.id === pickedApplicationId.value)
  if (!item) return
  applicationPicker.value = false
  openBuild(item)
}

function handleSubmitted() {
  void loadWorkbench()
}

function openBuildHistory(item: CicdWorkbenchItem) {
  router.push(buildExplorerPath(projectId, item.application.id, item.latest_build?.id))
}

function openPipeline(item: CicdWorkbenchItem) {
  const name = pipelineName(item)
  if (name) openRun(name)
}

function openRun(name: string) {
  router.push(`/devcenter/projects/${projectId}/pipelines/${name}`)
}

async function retry(item: CicdWorkbenchItem) {
  const name = pipelineName(item)
  if (!name) return
  try {
    await pipelineApi.retry(projectId, name)
    ElMessage.success('PipelineRun 重试已提交')
    await loadWorkbench()
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

function pipelineName(item: CicdWorkbenchItem) {
  return item.current_pipeline_run
}

function isRunning(item: CicdWorkbenchItem) {
  return ['Running', 'Pending', 'Building', 'Deploying', 'WaitingApproval'].includes(item.activity_status)
}

function isFailed(item: CicdWorkbenchItem) {
  return ['Failed', 'BuildFailed', 'PartialFailed'].includes(item.activity_status)
}

function canPromote(item: CicdWorkbenchItem) {
  if (item.latest_build?.status !== 'Succeeded' || !item.latest_batch) return false
  if (item.latest_batch.build_version_id !== item.latest_build.id) return false
  const associated = new Set(item.latest_batch.targets.map(target => target.environment_id))
  return item.available_environments.some(environment => !associated.has(environment.id))
}

function stageClass(value?: string) {
  return ['stage', value ? `stage-${value.toLowerCase()}` : 'muted-stage']
}

function statusMark(value?: string) {
  if (value === 'Succeeded') return '✓'
  if (['Failed', 'BuildFailed', 'PartialFailed'].includes(value || '')) return '✕'
  if (['Running', 'Pending', 'Building', 'Deploying'].includes(value || '')) return '↻'
  if (value === 'WaitingApproval') return '审批'
  return '—'
}

function shortRepo(value: string) {
  return value.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\.git$/, '')
}

function shortSha(value?: string) {
  return value ? value.slice(0, 8) : 'No commit'
}

function formatRelative(value?: string) {
  if (!value) return '尚无活动'
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return '刚刚'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

let searchTimer: number
let refreshTimer: number
watch(status, () => void loadWorkbench())
watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void loadWorkbench()
  }, 300)
})

onMounted(() => {
  void loadWorkbench()
  refreshTimer = window.setInterval(() => void loadWorkbench(), 15000)
})
onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  window.clearInterval(refreshTimer)
})
</script>

<style scoped>
.page-content {
  gap: 12px;
}

.page-content :deep(.page-header) {
  align-items: center;
  margin-bottom: 0;
}

.page-content :deep(.page-header h1) {
  font-size: 27px;
  letter-spacing: -0.035em;
}

.page-content :deep(.page-header p) {
  margin-top: 5px;
  font-size: 13px;
  line-height: 1.45;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-soft);
}

.toolbar :deep(.el-input) {
  width: min(320px, 100%);
}

.toolbar span {
  color: var(--muted);
  font-size: 13px;
}

.toolbar .failed-count {
  color: var(--danger, #c2413b);
}

.application-section {
  overflow: hidden;
  box-shadow: none;
}

.application-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: start;
  gap: 10px;
  padding: 12px 16px 16px;
}

.application-card {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border-soft);
  border-radius: 16px;
  background: var(--surface-soft);
}

.card-head,
.card-actions,
.build-meta,
.delivery-flow {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}

.card-head {
  justify-content: space-between;
  align-items: flex-start;
}

.card-head h4 {
  margin: 0;
  font-size: 17px;
}

.card-head p,
.commit-message {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 12px;
  word-break: break-all;
}

.build-meta {
  margin: 11px 0 8px;
}

.build-meta span,
.stage {
  padding: 5px 8px;
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 11px;
}

.delivery-flow {
  margin-bottom: 8px;
}

.flow-arrow {
  color: var(--muted);
  font-size: 11px;
}

.stage-succeeded {
  color: var(--success, #2d7d52);
  background: color-mix(in srgb, var(--success, #2d7d52) 12%, transparent);
}

.stage-running,
.stage-pending,
.stage-building,
.stage-deploying {
  color: var(--primary);
  background: var(--primary-soft);
}

.stage-failed,
.stage-buildfailed,
.stage-partialfailed {
  color: var(--danger, #c2413b);
  background: color-mix(in srgb, var(--danger, #c2413b) 10%, transparent);
}

.stage-waitingapproval {
  color: var(--warning, #9a6700);
  background: color-mix(in srgb, var(--warning, #9a6700) 12%, transparent);
}

.commit-message {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-actions {
  margin-top: 10px;
}

.compact-action.el-button {
  width: 28px;
  min-width: 28px;
  height: 28px;
  min-height: 28px;
  flex: 0 0 28px;
  padding: 0;
  border-radius: 50%;
}

.full-width {
  width: 100%;
}

@media (min-width: 1500px) {
  .application-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .application-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .page-content :deep(.page-header) {
    align-items: flex-start;
  }

  .application-grid {
    grid-template-columns: 1fr;
  }
}
</style>
