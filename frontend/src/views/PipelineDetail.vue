<template>
  <div class="page-content page-stack">
    <PageHeader eyebrow="Pipeline run" :title="name" description="按执行链路、任务状态与日志上下文组织问题定位体验。">
      <el-button :loading="loading" @click="refresh">刷新</el-button>
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

        <section class="surface ai-callout">
          <span>✦</span>
          <div>
            <h3>AI-assisted investigation</h3>
            <p>当执行失败时，优先分析失败任务、日志片段与错误原因，而不是先去翻大量 Kubernetes 细节。</p>
          </div>
        </section>

        <section class="surface flow">
          <div class="surface-header">
            <div>
              <h3>Task execution flow</h3>
              <p>点击任务即可在右侧查看对应 Step 日志。</p>
            </div>
            <span>{{ details.tasks.length }} tasks</span>
          </div>
          <PipelineStatusTimeline :tasks="details.tasks" :selected="selectedTask?.name" @select="selectedTask = $event" />
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
              v-for="task in details.tasks"
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
          <TaskRunLogViewer :task="selectedTask" @analyze="analyze" />
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
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import PipelineStatusTimeline from '../components/pipeline/PipelineStatusTimeline.vue'
import TaskRunLogViewer from '../components/pipeline/TaskRunLogViewer.vue'

const name = String(useRoute().params.name)
const details = ref<Awaited<ReturnType<typeof pipelineApi.logs>>>()
const selectedTask = ref<any>()
const loading = ref(false)
let timer: number | undefined

const format = (value?: string) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
const duration = computed(() => details.value?.started_at && details.value?.finished_at
  ? `${Math.round((new Date(details.value.finished_at).getTime() - new Date(details.value.started_at).getTime()) / 1000)}s`
  : 'Running')

async function refresh() {
  loading.value = true
  try {
    details.value = await pipelineApi.logs(name)
    selectedTask.value = details.value.tasks.find(task => task.name === selectedTask.value?.name)
      || details.value.tasks.find(task => task.status === 'Failed')
      || details.value.tasks[0]
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
  gap: 16px;
}

.summary-card,
.ai-callout,
.flow,
.tasks {
  box-shadow: none;
}

.summary-card {
  padding: 20px;
}

.summary-card span,
.summary-card strong,
summary-card p {
  display: block;
}

.summary-card span {
  color: var(--muted);
  font-size: 13px;
}

.summary-card strong {
  margin-top: 12px;
  font-size: 24px;
  letter-spacing: -0.04em;
}

.summary-card p {
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.ai-callout {
  padding: 22px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(135deg, var(--primary-soft), transparent 65%), var(--theme-panel);
}

.ai-callout > span {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: var(--primary);
  color: white;
}

.ai-callout h3 {
  margin: 0 0 6px;
  font-size: 18px;
}

.ai-callout p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
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
