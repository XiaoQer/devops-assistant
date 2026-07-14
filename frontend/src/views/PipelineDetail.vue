<template>
  <div class="page-content page-stack">
    <DetailBreadcrumb :items="[
      { label: 'DevCenter', to: '/devcenter/projects' },
      { label: `${projectName || `Project ${projectId}`} · Pipelines`, to: `/devcenter/projects/${projectId}/pipelines` },
      { label: name, current: true },
    ]" />
    <PageHeader eyebrow="Pipeline run" :title="name" description="按执行链路、任务状态与日志上下文组织问题定位体验。">
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="warning" :loading="retrying" :disabled="!canRetry" @click="retryRun">重试执行</el-button>
      <el-button type="primary" :disabled="details?.status !== 'Failed'" @click="analyze">✦ AI 分析失败</el-button>
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

        <section class="surface flow">
          <div class="surface-header">
            <div>
              <h3>Task execution flow</h3>
              <p>点击任务即可在右侧查看对应 Step 日志。</p>
            </div>
            <span>{{ orderedTasks.length }} tasks · 按执行顺序</span>
          </div>
          <PipelineStatusTimeline :tasks="orderedTasks" :selected="selectedTask?.name" @select="selectedTask = $event" />
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
              @click="selectedTask = task"
            >
              <i />
              <div>
                <b>{{ task.task_name || task.name }}</b>
                <small>{{ task.pod || 'Pod pending' }}</small>
              </div>
              <StatusBadge :status="task.status" />
            </button>
          </aside>
          <TaskRunLogViewer :task="selectedTask" @analyze="analyze" @retry="retryRun" />
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
const loading = ref(false)
const retrying = ref(false)
let timer: number | undefined
const canRetry = computed(() => ['Failed', 'Cancelled'].includes(details.value?.status || ''))
const orderedTasks = computed(() => [...(details.value?.tasks || [])].sort((a, b) => {
  const aTime = a.started_at || ''
  const bTime = b.started_at || ''
  if (!aTime && !bTime) return (a.name || '').localeCompare(b.name || '')
  if (!aTime) return 1
  if (!bTime) return -1
  return aTime.localeCompare(bTime)
}))

const format = (value?: string) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
const duration = computed(() => details.value?.started_at && details.value?.finished_at
  ? `${Math.round((new Date(details.value.finished_at).getTime() - new Date(details.value.started_at).getTime()) / 1000)}s`
  : 'Running')

async function refresh() {
  loading.value = true
  try {
    const [pipelineDetails] = await Promise.all([
      pipelineApi.logs(projectId, name),
      projectApi.get(projectId).then(project => {
        projectName.value = project.name
      }).catch(() => undefined),
    ])
    details.value = pipelineDetails
    selectedTask.value = orderedTasks.value.find(task => task.name === selectedTask.value?.name)
      || orderedTasks.value.find(task => task.status === 'Failed')
      || orderedTasks.value[0]
    if (details.value && ['Succeeded', 'Failed'].includes(details.value.status)) clearInterval(timer)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function analyze() {
  ElMessage.info('AI 失败分析将在下一阶段接入模型服务')
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

@media (max-width: 1100px) {
  .summary-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
