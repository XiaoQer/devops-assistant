<template>
  <div class="page-content page-stack">
    <DetailBreadcrumb :items="[
      { label: 'DevCenter', to: '/devcenter/projects' },
      { label: 'Application Pipeline', to: pipelineBackTo },
      { label: name, current: true },
    ]" />
    <PageHeader eyebrow="Pipeline run" :title="name" description="按执行链路、任务状态与日志上下文组织问题定位体验。">
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="warning" :loading="retrying" :disabled="!canRetry" @click="retryRun">重试执行</el-button>
    </PageHeader>

    <el-skeleton :loading="loading && !details" animated :rows="9">
      <template v-if="details">
        <section class="summary-grid">
          <article class="surface summary-card">
            <span>Pipeline status</span>
            <StatusBadge :status="details.status" />
            <p>{{ details.message || details.reason || '正在执行中' }}</p>
          </article>
          <article class="surface summary-card">
            <span>Started</span>
            <strong>{{ format(details.started_at) }}</strong>
            <p>开始执行时间</p>
          </article>
          <article class="surface summary-card">
            <span>Finished</span>
            <strong>{{ format(details.finished_at) }}</strong>
            <p>结束执行时间</p>
          </article>
          <article class="surface summary-card">
            <span>Duration</span>
            <strong>{{ duration }}</strong>
            <p>总耗时</p>
          </article>
        </section>

        <div class="release-flow">
        <section class="surface flow release-stage-overview">
          <div class="surface-header">
            <div>
              <h3>发布执行流程</h3>
              <p>先构建镜像，再将同一构建产物部署到所选环境。</p>
            </div>
            <span>已完成 {{ completedStageCount }}/{{ totalStageCount }} 个阶段 · 进行中 {{ runningStageCount }} · 待执行 {{ remainingStageCount }} · 预计剩余 {{ remainingEstimate }}</span>
          </div>
          <div class="stage-columns">
            <div class="stage-column ci-stage">
              <div class="stage-column-header"><span>CI</span><strong>构建镜像</strong><small>源码 → 构建产物</small></div>
              <PipelineStatusTimeline :tasks="orderedTasks" :selected="selectedTask?.name" @select="selectedTask = $event; cdTask = undefined; cdTarget = undefined" />
            </div>
            <div class="stage-column cd-stage">
              <div class="stage-column-header"><span>CD</span><strong>部署环境</strong><small>构建产物 → Kubernetes</small></div>
              <div v-if="flow?.batch?.targets?.length" class="cd-stage-list">
                <button v-for="target in flow.batch.targets" :key="target.id" :class="{ active: cdTarget?.id === target.id, failed: target.status === 'Failed' }" @click="selectDeploymentTarget(target)">
                  <i />
                  <div><b>{{ target.display_name || target.environment }}</b><small>{{ target.namespace }}</small></div>
                  <StatusBadge :status="target.status" />
                </button>
              </div>
              <div v-else class="cd-stage-empty">暂无部署环境</div>
            </div>
          </div>
        </section>

        <div class="content-grid">
          <aside class="surface tasks">
            <div class="surface-header">
              <div>
                <h3>Task runs</h3>
                <p>选择一个任务继续深入</p>
              </div>
            </div>
            <button
              v-for="task in orderedTasks"
              :key="task.name"
              :class="{ active: selectedTask?.name === task.name, failed: task.status === 'Failed' }"
              @click="selectedTask = task; cdTask = undefined; cdTarget = undefined"
            >
              <i />
              <div>
                <b>{{ task.task_name || task.name }}</b>
                <small>{{ task.pod || 'Pod pending' }}</small>
              </div>
              <StatusBadge :status="task.status" />
            </button>
            <div v-if="flow?.batch?.targets?.length" class="task-list-divider"><span>CD · 部署环境</span></div>
            <button
              v-for="target in flow?.batch?.targets || []"
              :key="`cd-${target.id}`"
              class="cd-task-item"
              :class="{ active: cdTarget?.id === target.id, failed: target.status === 'Failed' }"
              @click="selectDeploymentTarget(target)"
            >
              <i />
              <div>
                <b>Deploy · {{ target.display_name || target.environment }}</b>
                <small>{{ target.namespace }}</small>
              </div>
              <StatusBadge :status="target.status" />
            </button>
          </aside>
          <TaskRunLogViewer :task="cdTask || selectedTask" @retry="refresh" />
        </div>
        </div>
      </template>
      <EmptyState v-else title="PipelineRun 不可用" description="无法读取该流水线，可能已被清理或后端连接异常。" />
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { pipelineApi } from '../api/pipeline'
import { projectApi } from '../api/project'
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import PipelineStatusTimeline from '../components/pipeline/PipelineStatusTimeline.vue'
import TaskRunLogViewer from '../components/pipeline/TaskRunLogViewer.vue'
import DetailBreadcrumb from '../components/common/DetailBreadcrumb.vue'

const route = useRoute()
const projectId = Number(route.params.projectId)
const name = String(route.params.name)
const details = ref<Awaited<ReturnType<typeof pipelineApi.logs>>>()
const projectName = ref('')
const selectedTask = ref<any>()
const flow = ref<Awaited<ReturnType<typeof pipelineApi.flow>>>()
const cdTarget = ref<any>()
const cdDetails = ref<Awaited<ReturnType<typeof pipelineApi.logs>>>()
const cdTask = ref<any>()
const pipelineBackTo = computed(() => flow.value?.build?.application_id
  ? `/devcenter/projects/${projectId}/applications/${flow.value.build.application_id}?tab=pipeline`
  : `/devcenter/projects/${projectId}/applications`)
const loading = ref(false)
const retrying = ref(false)
let timer: number | undefined
let cdRequestId = 0
const canRetry = computed(() => ['Failed', 'Cancelled'].includes(details.value?.status || ''))
const orderedTasks = computed(() => [...(details.value?.tasks || [])].sort((a, b) => {
  const aTime = a.started_at || ''
  const bTime = b.started_at || ''
  if (!aTime && !bTime) return (a.name || '').localeCompare(b.name || '')
  if (!aTime) return 1
  if (!bTime) return -1
  return aTime.localeCompare(bTime)
}))
const totalStageCount = computed(() => {
  if (flow.value?.batch && !flow.value.build?.pipeline_run_name) return 1
  const buildType = flow.value?.build?.build_type || ''
  return buildType.includes('dockerfile') || buildType.includes('docker') ? 2 : 3
})
const completedStageCount = computed(() => orderedTasks.value.filter(task => ['Succeeded', 'Failed', 'Cancelled'].includes(task.status)).length)
const runningStageCount = computed(() => orderedTasks.value.filter(task => ['Running', 'InProgress'].includes(task.status)).length)
const remainingStageCount = computed(() => Math.max(totalStageCount.value - completedStageCount.value - runningStageCount.value, 0))
const remainingEstimate = computed(() => {
  if (['Succeeded', 'Failed', 'Cancelled'].includes(details.value?.status || '')) return '已结束'
  const completed = orderedTasks.value.filter(task => task.started_at && task.finished_at)
  const averageSeconds = completed.length
    ? completed.reduce((sum, task) => sum + (new Date(task.finished_at!).getTime() - new Date(task.started_at!).getTime()) / 1000, 0) / completed.length
    : 60
  const minutes = Math.max(1, Math.ceil((averageSeconds * Math.max(remainingStageCount.value, 1)) / 60))
  return `${minutes}–${minutes + 2} 分钟`
})

const format = (value?: string) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
const duration = computed(() => details.value?.started_at && details.value?.finished_at
  ? `${Math.round((new Date(details.value.finished_at).getTime() - new Date(details.value.started_at).getTime()) / 1000)}s`
  : 'Running')

async function refresh() {
  loading.value = true
  try {
    const [pipelineDetails, flowDetails] = await Promise.all([
      pipelineApi.logs(projectId, name),
      pipelineApi.flow(projectId, name),
      projectApi.get(projectId).then(project => {
        projectName.value = project.name
      }).catch(() => undefined),
    ])
    details.value = pipelineDetails
    flow.value = flowDetails
    if (flowDetails.batch) {
      const activeTargetId = cdTarget.value?.id
      const latestTarget = activeTargetId
        ? flowDetails.batch.targets.find(target => target.id === activeTargetId)
        : undefined
      if (latestTarget) {
        cdTarget.value = latestTarget
        if (!latestTarget.pipeline_run_name) {
          cdDetails.value = undefined
          cdTask.value = undefined
        } else if (latestTarget.pipeline_run_name !== cdDetails.value?.pipeline_run) {
          await selectDeploymentTarget(latestTarget)
        }
      } else if (!activeTargetId) {
        const firstDeploy = flowDetails.batch.targets.find(target => target.pipeline_run_name)
        if (firstDeploy) await selectDeploymentTarget(firstDeploy)
      }
    }
    if (!cdTarget.value) {
      selectedTask.value = orderedTasks.value.find(task => task.name === selectedTask.value?.name)
        || orderedTasks.value.find(task => task.status === 'Failed')
        || orderedTasks.value[0]
    }
    if (details.value && ['Succeeded', 'Failed'].includes(details.value.status)) clearInterval(timer)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

async function selectDeploymentTarget(target: any) {
  const requestId = ++cdRequestId
  selectedTask.value = undefined
  cdTarget.value = target
  cdDetails.value = undefined
  cdTask.value = undefined
  if (!target.pipeline_run_name) {
    return
  }
  try {
    const result = await pipelineApi.logs(projectId, target.pipeline_run_name)
    if (requestId !== cdRequestId || cdTarget.value?.id !== target.id) return
    cdDetails.value = result
    cdTask.value = result.tasks.find(task => task.status === 'Failed') || result.tasks[0]
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

async function retryRun() {
  if (!canRetry.value || retrying.value) return
  retrying.value = true
  try {
    const result = await pipelineApi.retry(projectId, name)
    ElMessage.success(`已提交重试执行 ${result.name}`)
    window.location.href = `/devcenter/projects/${projectId}/pipelines/${result.name}`
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    retrying.value = false
  }
}

onMounted(async () => {
  await refresh()
  timer = window.setInterval(refresh, 5000)
})

onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.summary-card,
.flow,
.tasks {
  box-shadow: none;
}

.summary-card {
  padding: 14px 16px;
}

.summary-card span,
.summary-card strong,
.summary-card p {
  display: block;
}

.summary-card span {
  color: var(--muted);
  font-size: 13px;
}

.summary-card strong {
  margin-top: 8px;
  font-size: 20px;
  letter-spacing: -0.04em;
}

.summary-card p {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.page-content :deep(.page-header) {
  margin-bottom: 12px;
}

.page-content :deep(.page-header h1) {
  font-size: 26px;
}

.flow {
  overflow: hidden;
}

.surface-header > span {
  font-size: 12px;
  color: var(--muted);
  max-width: 70%;
  text-align: right;
}

.content-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.tasks {
  overflow: hidden;
}

.tasks > button {
  width: 100%;
  min-height: 74px;
  padding: 0 16px;
  border: 0;
  border-bottom: 1px solid var(--border-soft);
  background: none;
  color: var(--text-2);
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
}

.tasks > button:hover,
.tasks > button.active {
  background: var(--surface-soft);
}

.tasks > button.active {
  box-shadow: inset 3px 0 0 var(--primary);
}

.tasks > button > i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
}

.tasks > button.failed > i {
  background: var(--danger);
}

.tasks > button > div {
  flex: 1;
  min-width: 0;
}

.tasks > button b,
.tasks > button small {
  display: block;
}

.release-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.release-stage-overview {
  overflow: hidden;
}

.stage-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(300px, 1fr);
  border-top: 1px solid var(--border-soft);
}

.stage-column {
  min-width: 0;
  padding: 14px 18px 16px;
}

.ci-stage {
  border-right: 1px solid var(--border-soft);
}

.stage-column-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}

.stage-column-header span {
  color: var(--primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .12em;
}

.stage-column-header strong {
  font-size: 15px;
}

.stage-column-header small {
  margin-left: auto;
  color: var(--muted);
  font-size: 12px;
}

.stage-column :deep(.timeline) {
  padding: 14px 0 4px;
}

.cd-stage-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 8px;
  padding-top: 10px;
}

.cd-stage-list button {
  width: 100%;
  min-height: 52px;
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: var(--surface-soft);
  color: var(--text-2);
  text-align: left;
  cursor: pointer;
}

.cd-stage-list button:hover,
.cd-stage-list button.active {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.cd-stage-list button.failed i {
  background: var(--danger);
}

.cd-stage-list button i,
.cd-task-item > i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
}

.cd-stage-list button b,
.cd-stage-list button small {
  display: block;
}

.cd-stage-list button b {
  font-size: 13px;
}

.cd-stage-list button small {
  margin-top: 4px;
  color: var(--muted);
  font-size: 11px;
}

.cd-stage-empty {
  margin-top: 14px;
  padding: 24px 12px;
  border: 1px dashed var(--border);
  border-radius: 12px;
  color: var(--muted);
  font-size: 12px;
  text-align: center;
}

.release-section-label {
  display: flex;
  align-items: baseline;
  gap: 9px;
  margin-top: 8px;
  padding: 0 4px;
}

.release-section-label span {
  color: var(--primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .12em;
}

.release-section-label strong {
  color: var(--text-2);
  font-size: 16px;
}

.release-section-label small {
  color: var(--muted);
  font-size: 12px;
}

.release-section-label.cd-label {
  margin-top: 18px;
}

.deployment-flow {
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border-soft);
  background: var(--surface);
  box-shadow: none;
}

.deployment-flow > .surface-header {
  padding: 20px 22px;
  background: var(--surface);
}

.deployment-flow > .surface-header h3 {
  font-size: 18px;
}

.deployment-header-meta {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.deployment-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px 20px;
  background: var(--surface-soft);
  border-top: 1px solid var(--border-soft);
}

.deployment-layout :deep(.viewer) {
  width: 100%;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--surface);
}

.environment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.deployment-target {
  min-width: 0;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  padding: 16px;
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  text-align: left;
  transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}

.deployment-target:hover,
.deployment-target.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-soft);
  transform: translateY(-1px);
}

.deployment-target.failed {
  border-color: color-mix(in srgb, var(--danger) 35%, var(--border-soft));
}

.deployment-target-top,
.deployment-target-bottom {
  display: flex;
  align-items: center;
  gap: 10px;
}

.deployment-target-top {
  min-height: 38px;
}

.environment-mark {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
}

.deployment-target-info {
  flex: 1;
  min-width: 0;
}

.deployment-target-info strong,
.deployment-target-info small {
  display: block;
}

.deployment-target-info strong {
  font-size: 14px;
}

.deployment-target-info small {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.deployment-detail {
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
}

.deployment-target-bottom {
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
  font-size: 12px;
}

.target-arrow {
  color: var(--primary);
  font-size: 18px;
  line-height: 1;
}

.deployment-log-empty {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border: 1px dashed var(--border);
  border-radius: 14px;
  color: var(--muted);
  text-align: center;
}

.deployment-log-empty strong {
  color: var(--text-2);
  font-size: 14px;
}

.error-text {
  grid-column: 2 / -1;
  margin: 0;
  color: var(--danger);
  font-size: 12px;
}

.tasks > button b {
  font-size: 14px;
}

.tasks > button small {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-list-divider {
  padding: 14px 16px 8px;
  border-top: 1px solid var(--border-soft);
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
}

.tasks > button.cd-task-item {
  min-height: 68px;
}

@media (max-width: 1100px) {
  .summary-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .stage-columns {
    grid-template-columns: 1fr;
  }

  .ci-stage {
    border-right: 0;
    border-bottom: 1px solid var(--border-soft);
  }

  .stage-column-header small {
    display: none;
  }

  .deployment-flow > .surface-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .deployment-layout {
    padding: 12px;
  }
}
</style>
