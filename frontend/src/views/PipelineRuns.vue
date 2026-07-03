<template>
  <div class="page-content page-stack">
    <PageHeader eyebrow="Delivery execution" title="Pipeline runs" description="统一查看最近的构建与部署执行，把排障和继续推进交付放在第一位。">
      <el-button :loading="loading" @click="load">刷新</el-button>
    </PageHeader>

    <div class="metrics">
      <MetricCard title="Runs" :value="total" icon="↯" helper="当前结果窗口" />
      <MetricCard title="Succeeded" :value="counts.succeeded" icon="✓" tone="green" helper="已稳定完成" />
      <MetricCard title="Running" :value="counts.running" icon="↻" tone="blue" helper="进行中的执行" />
      <MetricCard title="Failed" :value="counts.failed" icon="!" tone="red" helper="建议优先处理" />
    </div>

    <section class="surface toolbar-card">
      <div class="toolbar">
        <el-input v-model="query" placeholder="搜索 PipelineRun 或应用…" clearable />
        <el-select v-model="status" style="width: 150px">
          <el-option label="全部状态" value="" />
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <span>{{ total }} pipeline runs</span>
      </div>
    </section>

    <div class="pipeline-layout">
      <section class="surface list-card">
        <div class="surface-header">
          <div>
            <h3>Execution activity</h3>
            <p>按执行结果组织页面，让你最快定位失败链路与正在运行的任务。</p>
          </div>
        </div>
        <el-skeleton :loading="loading" animated :rows="7">
          <div v-if="items.length" class="run-list">
            <article v-for="row in items" :key="row.name" class="run-item" @click="open(row)">
              <div class="run-icon">↯</div>
              <div class="run-main">
                <div class="run-head">
                  <div>
                    <h4>{{ row.name }}</h4>
                    <p>{{ row.application || 'Unknown application' }} · {{ row.pipeline || 'Pipeline' }}</p>
                  </div>
                  <StatusBadge :status="row.status" />
                </div>
                <div class="run-meta">
                  <span class="soft-pill">{{ row.branch || 'No branch' }}</span>
                  <span class="soft-pill">{{ duration(row) }}</span>
                  <span class="soft-pill">{{ format(row.started_at || row.created_at) }}</span>
                </div>
                <code>{{ row.image || 'No image metadata' }}</code>
              </div>
            </article>
          </div>
          <EmptyState v-else title="没有 PipelineRun" description="调整筛选条件，或从应用工作区发起一次新的部署。" />
        </el-skeleton>
      </section>

      <aside class="surface rail-card">
        <div class="surface-header">
          <div>
            <h3>Operator hints</h3>
            <p>帮助你快速决定下一步动作。</p>
          </div>
        </div>
        <div class="rail-content">
          <article>
            <span class="soft-pill">Focus</span>
            <h4>{{ counts.failed ? `${counts.failed} 个失败执行等待排障` : '当前没有失败执行' }}</h4>
            <p>把注意力集中在失败链路，而不是浏览无关的节点、Pod 或资源图表。</p>
          </article>
          <article>
            <span class="soft-pill">Live</span>
            <h4>{{ counts.running ? `${counts.running} 个执行仍在运行` : '当前没有进行中的执行' }}</h4>
            <p>运行中的发布应尽快确认状态，以减少等待与不确定性。</p>
          </article>
        </div>
      </aside>
    </div>

    <footer class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" layout="prev,pager,next" :total="total" />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { pipelineApi } from '../api/pipeline'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

type Run = Awaited<ReturnType<typeof pipelineApi.list>>['items'][number]

const router = useRouter()
const items = ref<Run[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('')
const query = ref('')
const loading = ref(false)
const statuses = ['Succeeded', 'Running', 'Pending', 'Failed']
const counts = reactive({ succeeded: 0, running: 0, failed: 0 })

async function load() {
  loading.value = true
  try {
    const data = await pipelineApi.list({ page: page.value, pageSize, status: status.value || undefined, query: query.value || undefined })
    items.value = data.items
    total.value = data.total
    counts.succeeded = items.value.filter(item => item.status === 'Succeeded').length
    counts.running = items.value.filter(item => ['Running', 'Pending'].includes(item.status)).length
    counts.failed = items.value.filter(item => item.status === 'Failed').length
  } finally {
    loading.value = false
  }
}

function format(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function duration(run: Run) {
  if (run.started_at && run.finished_at) {
    return `${Math.max(0, Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000))}s`
  }
  return run.status === 'Running' ? 'Running' : '—'
}

function open(run: Run) {
  router.push(`/pipelines/${run.name}`)
}

let searchTimer: number
watch([page, status], load)
watch(query, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})

onMounted(load)
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

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
  width: 260px;
}

.toolbar span {
  color: var(--muted);
  font-size: 13px;
}

.pipeline-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.list-card,
.rail-card {
  box-shadow: none;
}

.run-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.run-item {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 14px;
  cursor: pointer;
}

.run-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
}

.run-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.run-head h4 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.run-head p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.run-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
}

.run-main code {
  display: block;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
  word-break: break-all;
}

.rail-content {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rail-content article {
  padding: 18px;
  border-radius: 14px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.rail-content h4 {
  margin: 14px 0 8px;
  font-size: 17px;
}

.rail-content p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.pager {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1100px) {
  .metrics,
  .pipeline-layout {
    grid-template-columns: 1fr;
  }
}
</style>
