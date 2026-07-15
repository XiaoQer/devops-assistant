<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Release workspace"
      title="Applications"
      description="集中管理当前 Project 的服务发布状态、目标环境和最近一次交付。"
    >
      <el-button @click="store.load()" :loading="store.loading">刷新</el-button>
      <el-button type="primary" @click="router.push(`/devcenter/projects/${projectId}/applications/new`)">＋ 创建应用</el-button>
    </PageHeader>

    <div class="release-overview">
      <section class="surface project-context">
        <div class="context-heading">
          <span class="context-mark">P{{ projectId }}</span>
          <div>
            <span class="eyebrow-label">CURRENT PROJECT</span>
            <h3>{{ currentProject?.name || 'Project workspace' }}</h3>
          </div>
        </div>
        <div class="context-targets">
          <div><span>Default environment</span><strong>dev</strong></div>
          <div><span>Release policy</span><strong>Project scoped</strong></div>
          <div><span>Service count</span><strong>{{ store.items.length }}</strong></div>
        </div>
      </section>
      <div class="metrics">
        <MetricCard title="Total services" :value="store.items.length" icon="◇" helper="当前 Project" />
        <MetricCard title="Ready to release" :value="succeeded" icon="✓" tone="green" helper="最近执行成功" />
        <MetricCard title="In delivery" :value="running" icon="↻" tone="blue" helper="构建或部署中" />
        <MetricCard title="Needs attention" :value="failed" icon="!" tone="red" helper="最近执行失败" />
      </div>
    </div>

    <section class="surface filter-bar">
      <div class="search-box">
        <span>⌕</span>
        <el-input v-model="query" placeholder="搜索服务、仓库或镜像…" clearable />
      </div>
      <div class="filter-actions">
        <el-select v-model="status" style="width: 150px">
          <el-option label="All statuses" value="" />
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <span class="result-count">{{ filtered.length }} services</span>
      </div>
    </section>

    <section class="surface release-table-card">
      <div class="table-header">
        <div>
          <span class="eyebrow-label">RELEASE INVENTORY</span>
          <h3>服务发布清单</h3>
          <p>选择服务进入发布工作区，查看环境、流水线和回滚记录。</p>
        </div>
        <div class="table-actions">
          <el-button @click="router.push(`/devcenter/projects/${projectId}/pipelines`)">查看 Pipeline</el-button>
        </div>
      </div>

      <el-table v-if="paged.length" :data="paged" class="release-table" @row-click="openApplication">
        <el-table-column label="服务" min-width="250">
          <template #default="{ row }">
            <div class="service-cell">
              <span class="app-avatar">{{ row.name[0]?.toUpperCase() }}</span>
              <div><strong>{{ row.name }}</strong><small>{{ shortRepo(row.repo_url) }}</small></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150"><template #default="{ row }"><StatusBadge :status="getStatus(row)" /></template></el-table-column>
        <el-table-column label="运行环境" width="150"><template #default="{ row }"><span class="env-value">{{ row.namespace || 'default' }}</span></template></el-table-column>
        <el-table-column label="镜像版本" min-width="220"><template #default="{ row }"><code>{{ row.image_name ? `${row.image_name}:${row.image_tag}` : 'Registry not configured' }}</code></template></el-table-column>
        <el-table-column label="最近执行" min-width="220"><template #default="{ row }"><div class="execution-cell"><strong>{{ row.latest_execution?.pipeline_run_name || '尚未发布' }}</strong><small>{{ formatExecution(row.latest_execution?.created_at) }}</small></div></template></el-table-column>
        <el-table-column label="操作" width="120" fixed="right"><template #default="{ row }"><el-button link type="primary" @click.stop="openApplication(row)">进入发布</el-button></template></el-table-column>
      </el-table>

      <EmptyState v-else-if="!store.loading" title="没有找到匹配的服务" description="换一个筛选条件，或者在当前 Project 创建一个新的应用。">
        <el-button type="primary" @click="router.push(`/devcenter/projects/${projectId}/applications/new`)">创建应用</el-button>
      </EmptyState>
    </section>

    <footer v-if="filtered.length > pageSize" class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" layout="prev, pager, next" :total="filtered.length" />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApplicationStore } from '../stores/application'
import { projectApi } from '../api/project'
import { useProjectStore } from '../stores/project'
import type { Application, Project } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const route = useRoute()
const store = useApplicationStore()
const projectStore = useProjectStore()
const query = ref('')
const status = ref('')
const projectId = ref(0)
const page = ref(1)
const pageSize = 9
const statuses = ['Succeeded', 'Running', 'Pending', 'Failed', 'analyzed']
const projects = ref<Project[]>([])
const currentProject = computed(() => projects.value.find(project => project.id === projectId.value))

function getStatus(application: Application) {
  return application.latest_execution?.status || application.status
}

const filtered = computed(() => store.items.filter(application => (
  (!status.value || getStatus(application) === status.value) &&
  (!query.value || `${application.name}${application.repo_url}${application.language}${application.framework}`.toLowerCase().includes(query.value.toLowerCase()))
)))

const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const succeeded = computed(() => store.items.filter(application => getStatus(application) === 'Succeeded').length)
const running = computed(() => store.items.filter(application => ['Running', 'Pending'].includes(getStatus(application))).length)
const failed = computed(() => store.items.filter(application => getStatus(application) === 'Failed').length)

function shortRepo(url: string) {
  return url.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\.git$/, '')
}

function formatExecution(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '等待首次发布'
}

function openApplication(application: Application) {
  router.push(`/devcenter/projects/${projectId.value}/applications/${application.id}`)
}

watch([query, status, projectId], () => {
  page.value = 1
})

watch(projectId, async value => {
  await store.load(value || undefined)
  if (value) projectStore.setActiveProject(value)
})

onMounted(async () => {
  projectStore.init()
  projectId.value = Number(route.params.projectId) || projectStore.activeProjectId
  projects.value = await projectApi.list()
  await store.load(projectId.value || undefined)
})
</script>

<style scoped>
.page-content :deep(.page-header) {
  margin-bottom: 16px;
}

.page-content :deep(.page-header h1) {
  font-size: 28px;
}

.page-content :deep(.page-header p) {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.45;
}

.page-content :deep(.page-header .eyebrow) {
  min-height: 24px;
  margin-bottom: 7px;
  padding: 0 10px;
  font-size: 10px;
}

.page-content :deep(.metric) {
  padding: 14px 16px;
}

.page-content :deep(.metric strong) {
  margin: 12px 0 7px;
  font-size: 26px;
}

.page-content :deep(.metric-top i) {
  width: 28px;
  height: 28px;
  border-radius: 9px;
}

.release-overview {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 12px;
}

.project-context,
.release-table-card {
  box-shadow: none;
}

.project-context {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 116px;
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-soft) 100%);
}

.context-heading,
.service-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.context-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--primary);
  color: white;
  font-weight: 800;
}

.eyebrow-label {
  color: var(--muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .12em;
}

.context-heading h3,
.table-header h3 {
  margin: 4px 0 0;
  letter-spacing: -.03em;
}

.context-targets {
  display: flex;
  gap: 14px;
  margin-top: 12px;
}

.context-targets div {
  display: grid;
  gap: 4px;
}

.context-targets span,
.context-targets strong {
  font-size: 11px;
}

.context-targets span,
.service-cell small,
.execution-cell small {
  color: var(--muted);
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.filter-bar {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  box-shadow: none;
}

.release-table-card {
  overflow: hidden;
}

.table-header {
  padding: 16px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  border-bottom: 1px solid var(--border-soft);
}

.table-header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.release-table :deep(.el-table__header th) {
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .06em;
}

.release-table :deep(.el-table__row) {
  cursor: pointer;
}

.release-table :deep(.el-table__row:hover > td) {
  background: var(--primary-soft);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.search-box > span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
}

.search-box :deep(.el-input) {
  flex: 1;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-count {
  color: var(--muted);
  font-size: 13px;
}

.app-avatar {
  width: 48px;
  height: 48px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 800;
}

.service-cell strong,
.service-cell small,
.execution-cell strong,
.execution-cell small {
  display: block;
}

.service-cell small,
.execution-cell small {
  margin-top: 4px;
  font-size: 12px;
}

.env-value {
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

.release-table code {
  color: var(--text);
  font-size: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .release-overview,
  .metrics {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-actions {
    justify-content: space-between;
  }

  .table-header {
    flex-direction: column;
  }
}
</style>
