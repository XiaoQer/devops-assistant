<template>
  <div class="page-content page-stack">
    <el-skeleton v-if="loading && !project" animated :rows="10" />
    <template v-else-if="project">
      <DetailBreadcrumb :items="[
        { label: 'DevCenter', to: '/devcenter/projects' },
        { label: project.name, current: true },
      ]" />
      <PageHeader
        eyebrow="Project DevCenter"
        :title="`${project.name} · DevCenter`"
        :description="project.description || '围绕当前项目集中查看应用、流水线执行与发布活动。'"
      >
        <el-button @click="refresh" :loading="loading">刷新</el-button>
        <el-button @click="router.push(`/project-center/projects/${project.id}`)">Project 详情</el-button>
        <el-button type="primary" @click="router.push(`/devcenter/projects/${project.id}/applications/new`)">＋ 新建应用</el-button>
      </PageHeader>

      <div class="metrics">
        <MetricCard title="Applications" :value="applications.length" icon="◇" helper="项目内服务数" />
        <MetricCard title="Pipeline runs" :value="pipelineTotal" icon="↯" tone="blue" helper="当前项目最近执行" />
        <MetricCard title="Running" :value="runningCount" icon="↻" tone="green" helper="进行中的交付" />
        <MetricCard title="Releases" :value="releaseTotal" icon="↗" tone="purple" helper="当前项目发布记录" />
      </div>

      <section class="surface summary-card glass-card">
        <div>
          <span class="soft-pill">{{ project.key }}</span>
          <h3>当前项目的服务发布中心</h3>
          <p>先进入项目，再看应用、流水线和发布活动。这样 DevCenter 与 Project 模块共享同一个交付上下文，不需要再跨页面反复切换筛选条件。</p>
        </div>
        <div class="summary-actions">
          <el-button @click="openPipelines">查看全部 Pipeline</el-button>
          <el-button @click="openReleases">查看全部 Releases</el-button>
          <el-button type="primary" @click="router.push(`/project-center/projects/${project.id}`)">进入 Project 模块</el-button>
        </div>
      </section>

      <div class="delivery-grid">
        <section class="surface panel-card">
          <div class="surface-header">
            <div>
              <h3>Applications</h3>
              <p>从当前项目的服务列表进入应用工作区，再执行发布、查看环境与运行状态。</p>
            </div>
          </div>
          <div v-if="applications.length" class="application-grid">
            <article v-for="app in applications" :key="app.id" class="application-card">
              <div class="application-head">
                <div>
                  <h4>{{ app.name }}</h4>
                  <p>{{ app.language }} / {{ app.framework }} · {{ app.namespace }}</p>
                </div>
                <StatusBadge :status="app.latest_execution?.status || app.status" />
              </div>
              <div class="app-meta">
                <span class="soft-pill">{{ app.branch }}</span>
                <span class="soft-pill">{{ app.build_type }}</span>
                <span class="soft-pill">{{ app.image_tag }}</span>
              </div>
              <div class="summary-actions compact">
                <el-button @click="router.push(`/devcenter/projects/${project.id}/applications/${app.id}`)">进入应用</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-else title="项目里还没有应用" description="请先在当前项目创建应用，DevCenter 才能承接服务发布流程。">
            <el-button type="primary" @click="router.push(`/devcenter/projects/${project.id}/applications/new`)">创建应用</el-button>
          </EmptyState>
        </section>

        <section class="surface panel-card">
          <div class="surface-header">
            <div>
              <h3>Recent pipeline runs</h3>
              <p>优先展示当前项目最近的构建与部署执行，方便快速排障。</p>
            </div>
            <el-button @click="openPipelines">查看全部</el-button>
          </div>
          <div v-if="pipelines.length" class="activity-list">
            <article v-for="run in pipelines" :key="run.name" class="activity-card clickable" @click="router.push(`/devcenter/projects/${project.id}/pipelines/${run.name}`)">
              <div>
                <div class="activity-head">
                  <h4>{{ run.name }}</h4>
                  <StatusBadge :status="run.status" />
                </div>
                <p>{{ run.application || 'Unknown application' }} · {{ run.pipeline || 'Pipeline' }}</p>
                <div class="activity-meta">
                  <span class="soft-pill">{{ run.branch || 'No branch' }}</span>
                  <span class="soft-pill">{{ duration(run.started_at, run.finished_at, run.status) }}</span>
                  <span class="soft-pill">{{ format(run.started_at || run.created_at) }}</span>
                </div>
              </div>
            </article>
          </div>
          <EmptyState v-else title="还没有 Pipeline 记录" description="从应用工作区发起一次部署后，最近执行会自动出现在这里。" />
        </section>
      </div>

      <section class="surface panel-card">
        <div class="surface-header">
          <div>
            <h3>Recent releases</h3>
            <p>按项目查看最近发布活动，并快速跳转到对应的 Pipeline 日志。</p>
          </div>
          <el-button @click="openReleases">查看全部</el-button>
        </div>
        <div v-if="releases.length" class="release-list">
          <article v-for="release in releases" :key="release.id" class="release-card">
            <div>
              <div class="activity-head">
                <h4>{{ release.image_tag }}</h4>
                <StatusBadge :status="release.deploy_status" />
              </div>
              <p>{{ release.application_name || 'Unknown application' }} · {{ release.image }}</p>
              <div class="activity-meta">
                <span class="soft-pill">{{ release.environment.toUpperCase() }}</span>
                <span class="soft-pill">{{ release.release_type }}</span>
                <span class="soft-pill">{{ release.deploy_user }}</span>
                <span class="soft-pill">{{ format(release.created_at) }}</span>
              </div>
            </div>
            <el-button v-if="release.pipeline_run_name" link @click="router.push(`/devcenter/projects/${project.id}/pipelines/${release.pipeline_run_name}`)">查看日志</el-button>
          </article>
        </div>
        <EmptyState v-else title="还没有发布记录" description="当你在当前项目内完成部署后，Release 活动会自动沉淀在这里。" />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Application, PipelineRunSummary, Project, Release } from '../types'
import { projectApi } from '../api/project'
import { pipelineApi } from '../api/pipeline'
import { releaseApi } from '../api/release'
import { useProjectStore } from '../stores/project'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import EmptyState from '../components/common/EmptyState.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import DetailBreadcrumb from '../components/common/DetailBreadcrumb.vue'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()

const project = ref<Project>()
const applications = ref<Application[]>([])
const pipelines = ref<PipelineRunSummary[]>([])
const releases = ref<Release[]>([])
const loading = ref(false)

const projectId = computed(() => Number(route.params.id))
const pipelineTotal = computed(() => pipelines.value.length)
const releaseTotal = computed(() => releases.value.length)
const runningCount = computed(() => pipelines.value.filter(item => ['Running', 'Pending'].includes(item.status)).length)

async function refresh() {
  loading.value = true
  try {
    const id = projectId.value
    const [projectData, appItems, pipelineData, releaseData] = await Promise.all([
      projectApi.get(id),
      projectApi.applications(id),
      pipelineApi.list(id, { page: 1, pageSize: 6 }),
      releaseApi.list(id, { page: 1, pageSize: 6 }),
    ])
    project.value = projectData
    applications.value = appItems
    pipelines.value = pipelineData.items
    releases.value = releaseData.items
    projectStore.setActiveProject(id)
    if (!projectStore.items.length) {
      await projectStore.load()
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function openPipelines() {
  router.push(`/devcenter/projects/${projectId.value}/pipelines`)
}

function openReleases() {
  router.push(`/devcenter/projects/${projectId.value}/releases`)
}

function format(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function duration(startedAt?: string, finishedAt?: string, status?: string) {
  if (startedAt && finishedAt) {
    return `${Math.max(0, Math.round((new Date(finishedAt).getTime() - new Date(startedAt).getTime()) / 1000))}s`
  }
  return status === 'Running' ? 'Running' : '—'
}

watch(() => route.params.id, () => {
  refresh()
})

onMounted(async () => {
  projectStore.init()
  if (!projectStore.items.length) {
    await projectStore.load()
  }
  await refresh()
})
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-card,
.panel-card {
  box-shadow: none;
}

.summary-card {
  padding: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) auto;
  gap: 20px;
  align-items: end;
}

.summary-card h3 {
  margin: 16px 0 10px;
  font-size: 30px;
  letter-spacing: -0.04em;
}

.summary-card p,
.activity-card p,
.release-card p,
.application-card p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.summary-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-actions.compact {
  margin-top: 16px;
}

.delivery-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.application-grid,
.activity-list,
.release-list {
  padding: 12px 24px 24px;
  display: grid;
  gap: 12px;
}

.application-card,
.activity-card,
.release-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.application-head,
.activity-head,
.release-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.application-card h4,
.activity-card h4,
.release-card h4 {
  margin: 0 0 8px;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.app-meta,
.activity-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.clickable {
  cursor: pointer;
}

@media (max-width: 1100px) {
  .metrics,
  .summary-card,
  .delivery-grid {
    grid-template-columns: 1fr;
  }
}
</style>
