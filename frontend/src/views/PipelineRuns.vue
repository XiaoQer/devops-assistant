<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Project delivery"
      title="CI/CD 工作台"
      description="跨 Application 快速构建、发布和跟踪交付状态。"
    >
      <el-button :loading="loading" @click="loadAll">刷新</el-button>
      <el-button type="primary" @click="openApplicationPicker">＋ 快速构建</el-button>
    </PageHeader>

    <section class="surface toolbar-card">
      <div class="toolbar">
        <el-input
          v-model="query"
          placeholder="搜索 Application 或仓库…"
          clearable
        />
        <el-select v-model="status" style="width: 160px">
          <el-option label="全部状态" value="" />
          <el-option v-for="item in statuses" :key="item" :label="item" :value="item" />
        </el-select>
        <span>{{ workbenchItems.length }} Applications</span>
        <span v-if="counts.running">{{ counts.running }} 个进行中</span>
        <span v-if="counts.failed" class="failed-count">{{ counts.failed }} 个失败</span>
      </div>
    </section>

    <section class="surface application-section">
      <div class="surface-header">
        <div>
          <h3>Application delivery</h3>
          <p>默认按最近活动排序；每张卡片都提供当前最有价值的下一步动作。</p>
        </div>
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
              <el-button
                v-else
                type="primary"
                @click="openBuild(item)"
              >
                构建
              </el-button>
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
              <el-button text @click="openApplication(item)">详情</el-button>
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

    <section class="surface recent-section">
      <div class="surface-header">
        <div>
          <h3>最近执行</h3>
          <p>查看 Project 内最近的 PipelineRun，并进入任务日志排障。</p>
        </div>
      </div>
      <el-skeleton :loading="loadingRuns" animated :rows="6">
        <div v-if="runs.length" class="run-list">
          <article v-for="row in runs" :key="row.name" class="run-item" @click="openRun(row.name)">
            <div class="run-main">
              <div>
                <h4>{{ row.application || 'Unknown application' }}</h4>
                <p>{{ row.name }}</p>
              </div>
              <StatusBadge :status="row.status" />
            </div>
            <div class="run-meta">
              <span>{{ row.branch || 'No branch' }}</span>
              <span>{{ duration(row) }}</span>
              <span>{{ format(row.started_at || row.created_at) }}</span>
            </div>
          </article>
        </div>
        <EmptyState v-else title="没有 PipelineRun" description="从上方 Application 卡片发起第一次构建。" />
      </el-skeleton>
      <footer v-if="runTotal > pageSize" class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          layout="prev,pager,next"
          :total="runTotal"
        />
      </footer>
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
import { pipelineApi } from '../api/pipeline'
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import QuickBuildDrawer from '../components/pipeline/QuickBuildDrawer.vue'
import PromoteBuildDrawer from '../components/pipeline/PromoteBuildDrawer.vue'
import type { CicdWorkbenchItem, PipelineRunSummary } from '../types'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.projectId)
const workbenchItems = ref<CicdWorkbenchItem[]>([])
const runs = ref<PipelineRunSummary[]>([])
const runTotal = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('')
const query = ref('')
const loadingWorkbench = ref(false)
const loadingRuns = ref(false)
const buildDrawer = ref(false)
const promoteDrawer = ref(false)
const applicationPicker = ref(false)
const pickedApplicationId = ref<number>()
const selectedItem = ref<CicdWorkbenchItem>()
const promoteItem = ref<CicdWorkbenchItem>()
const statuses = ['Succeeded', 'Running', 'Pending', 'WaitingApproval', 'Failed', 'BuildFailed']
const loading = computed(() => loadingWorkbench.value || loadingRuns.value)
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

async function loadRuns() {
  loadingRuns.value = true
  try {
    const data = await pipelineApi.list(projectId, {
      page: page.value,
      pageSize,
      status: status.value || undefined,
      query: query.value || undefined,
    })
    runs.value = data.items
    runTotal.value = data.total
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingRuns.value = false
  }
}

function loadAll() {
  return Promise.all([loadWorkbench(), loadRuns()])
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
  void loadAll()
}

function openApplication(item: CicdWorkbenchItem) {
  router.push(`/devcenter/projects/${projectId}/applications/${item.application.id}`)
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
    await loadAll()
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

function format(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function formatRelative(value?: string) {
  if (!value) return '尚无活动'
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return '刚刚'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

function duration(run: PipelineRunSummary) {
  if (run.started_at && run.finished_at) {
    return `${Math.max(0, Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000))}s`
  }
  return run.status === 'Running' ? 'Running' : '—'
}

let searchTimer: number
let refreshTimer: number
watch([page, status], () => void loadAll())
watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    page.value = 1
    void loadAll()
  }, 300)
})

onMounted(() => {
  void loadAll()
  refreshTimer = window.setInterval(() => void loadAll(), 15000)
})
onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  window.clearInterval(refreshTimer)
})
</script>

<style scoped>
.toolbar-card {
  padding: 16px 20px;
  box-shadow: none;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
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

.application-section,
.recent-section {
  box-shadow: none;
}

.application-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  padding: 10px 24px 24px;
}

.application-card {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 16px;
  background: var(--surface-soft);
}

.card-head,
.run-main,
.card-actions,
.build-meta,
.delivery-flow,
.run-meta {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
}

.card-head,
.run-main {
  justify-content: space-between;
  align-items: flex-start;
}

.card-head h4,
.run-main h4 {
  margin: 0;
  font-size: 17px;
}

.card-head p,
.run-main p,
.commit-message {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 12px;
  word-break: break-all;
}

.build-meta {
  margin: 15px 0 10px;
}

.build-meta span,
.run-meta span,
.stage {
  padding: 5px 8px;
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 11px;
}

.delivery-flow {
  min-height: 30px;
  margin-bottom: 10px;
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
  min-height: 34px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-actions {
  margin-top: 16px;
}

.run-list {
  padding: 8px 24px 24px;
  display: grid;
  gap: 10px;
}

.run-item {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-soft);
  cursor: pointer;
}

.run-meta {
  margin-top: 9px;
}

.pager {
  padding: 0 24px 24px;
  display: flex;
  justify-content: flex-end;
}

.full-width {
  width: 100%;
}

@media (max-width: 1100px) {
  .application-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .application-grid {
    grid-template-columns: 1fr;
  }
}
</style>
