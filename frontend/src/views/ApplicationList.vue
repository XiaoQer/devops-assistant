<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Software catalog"
      title="Applications"
      description="用软件工作区而不是配置表，查看每个服务当前状态、最近交付与下一步操作。"
    >
      <el-button @click="store.load()" :loading="store.loading">刷新</el-button>
      <el-button type="primary" @click="router.push('/applications/new')">＋ 创建应用</el-button>
    </PageHeader>

    <div class="metrics">
      <MetricCard title="All services" :value="store.items.length" icon="◇" helper="当前已接入" />
      <MetricCard title="Healthy" :value="succeeded" icon="✓" tone="green" helper="最近执行成功" />
      <MetricCard title="In progress" :value="running" icon="↻" tone="blue" helper="仍在交付中" />
      <MetricCard title="At risk" :value="failed" icon="!" tone="red" helper="需要人工介入" />
    </div>

    <section class="surface filter-bar">
      <div class="search-box">
        <span>⌘</span>
        <el-input v-model="query" placeholder="搜索应用、仓库或技术栈…" clearable />
      </div>
      <div class="filter-actions">
        <el-select v-model="projectId" style="width: 220px">
          <el-option label="全部项目" :value="0" />
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-select v-model="status" style="width: 150px">
          <el-option label="全部状态" value="" />
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <span class="result-count">{{ filtered.length }} services</span>
      </div>
    </section>

    <div class="content-grid">
      <section class="applications-grid">
        <article v-for="app in paged" :key="app.id" class="surface app-card">
          <div class="app-card-head">
            <div class="app-identify">
              <span class="app-avatar">{{ app.name[0]?.toUpperCase() }}</span>
              <div>
                <h3>{{ app.name }}</h3>
                <p>{{ shortRepo(app.repo_url) }}</p>
                <small class="project-badge">{{ app.project_name || 'Default Project' }}</small>
              </div>
            </div>
            <StatusBadge :status="getStatus(app)" />
          </div>

          <div class="app-meta">
            <span class="soft-pill">{{ app.language || 'Unknown runtime' }}</span>
            <span class="soft-pill">{{ app.framework || 'Framework n/a' }}</span>
            <span class="soft-pill">{{ app.namespace }}</span>
          </div>

          <div class="app-summary">
            <div>
              <label>Current image</label>
              <b>{{ app.image_name }}:{{ app.image_tag }}</b>
            </div>
            <div>
              <label>Latest pipeline</label>
              <b>{{ app.latest_execution?.pipeline_run_name || 'No runs yet' }}</b>
            </div>
            <div>
              <label>Branch</label>
              <b>{{ app.branch }}</b>
            </div>
          </div>

          <div class="app-actions">
            <el-button @click="router.push(`/applications/${app.id}`)">打开工作区</el-button>
            <el-button type="primary" @click="router.push(`/applications/${app.id}`)">进入发布</el-button>
          </div>
        </article>

        <EmptyState
          v-if="!paged.length && !store.loading"
          title="没有找到匹配的服务"
          description="换一个搜索条件，或者直接创建一个新的应用工作区。"
        >
          <el-button type="primary" @click="router.push('/applications/new')">创建应用</el-button>
        </EmptyState>
      </section>

      <aside class="surface ai-rail">
        <div class="surface-header">
          <div>
            <h3>AI suggestions</h3>
            <p>帮助你更快定位应该优先处理的服务。</p>
          </div>
        </div>
        <div class="rail-list">
          <article>
            <span class="soft-pill">Priority</span>
            <h4>{{ failed ? `${failed} 个服务最近交付失败` : '当前没有失败服务' }}</h4>
            <p>{{ failed ? '建议先打开失败服务工作区，查看执行日志并发起修复。' : '可以开始新一轮部署或清理待优化配置。' }}</p>
            <el-button @click="router.push(failed ? '/pipelines' : '/applications/new')">{{ failed ? '查看失败执行' : '新建应用' }}</el-button>
          </article>
          <article>
            <span class="soft-pill">Focus</span>
            <h4>{{ running ? `${running} 个服务正在交付中` : '当前没有进行中的交付' }}</h4>
            <p>把注意力放在真正影响交付的工作流上，而不是浏览大而全的表格。</p>
            <el-button @click="router.push('/releases')">进入发布中心</el-button>
          </article>
        </div>
      </aside>
    </div>

    <footer v-if="filtered.length > pageSize" class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" layout="prev, pager, next" :total="filtered.length" />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useApplicationStore } from '../stores/application'
import { projectApi } from '../api/project'
import { useProjectStore } from '../stores/project'
import type { Application, Project } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const store = useApplicationStore()
const projectStore = useProjectStore()
const query = ref('')
const status = ref('')
const projectId = ref(0)
const page = ref(1)
const pageSize = 9
const statuses = ['Succeeded', 'Running', 'Pending', 'Failed', 'analyzed']
const projects = ref<Project[]>([])

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

watch([query, status, projectId], () => {
  page.value = 1
})

watch(projectId, async value => {
  await store.load(value || undefined)
  if (value) projectStore.setActiveProject(value)
})

onMounted(async () => {
  projectStore.init()
  projects.value = await projectApi.list()
  projectId.value = projectStore.activeProjectId
  await store.load(projectId.value || undefined)
})
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.filter-bar {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  box-shadow: none;
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

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.applications-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-content: start;
}

.app-card {
  padding: 22px;
  box-shadow: none;
}

.app-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.app-identify {
  display: flex;
  align-items: center;
  gap: 14px;
}

.app-avatar {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 800;
}

.app-identify h3 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.app-identify p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.project-badge {
  display: inline-block;
  margin-top: 8px;
  color: var(--primary);
  font-size: 12px;
}

.app-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 18px 0;
}

.app-summary {
  display: grid;
  gap: 14px;
  padding: 18px 0;
  border-top: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.app-summary label,
.app-summary b {
  display: block;
}

.app-summary label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.app-summary b {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.app-actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.ai-rail {
  box-shadow: none;
}

.rail-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rail-list article {
  padding: 18px;
  border-radius: 14px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.rail-list h4 {
  margin: 14px 0 8px;
  font-size: 17px;
  letter-spacing: -0.03em;
}

.rail-list p {
  margin: 0 0 16px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.pager {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .content-grid,
  .applications-grid,
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
}
</style>
