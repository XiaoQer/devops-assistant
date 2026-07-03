<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Portal"
      title="Portal"
      description="Portal 作为独立入口项目，只负责把用户分流到 ProjectManager 和 DevCenter 两个一级模块。"
    >
      <el-button @click="refresh" :loading="store.loading">刷新</el-button>
      <el-button type="primary" @click="router.push(PROJECT_MANAGER_PATH)">进入 ProjectManager</el-button>
    </PageHeader>

    <div class="metrics">
      <MetricCard title="Projects" :value="store.items.length" icon="◫" helper="当前可见项目" />
      <MetricCard title="Applications" :value="applicationsCount" icon="◇" helper="项目内服务总数" />
      <MetricCard title="Clusters" :value="clustersCount" icon="☸" tone="blue" helper="项目级部署目标" />
      <MetricCard title="Viewer scope" :value="viewerStore.email || 'Demo mode'" icon="⌘" tone="green" :helper="store.viewerScoped ? '按成员权限过滤' : '未配置身份时展示全部项目'" />
    </div>

    <section class="module-grid">
      <article class="surface glass-card module-card">
        <div>
          <span class="soft-pill">Project governance</span>
          <h3>ProjectManager</h3>
          <p>在这里管理项目、成员权限、云资源、Kubernetes 集群、镜像仓库和未来的基础设施配置。</p>
        </div>
        <ul>
          <li>项目列表</li>
          <li>成员 / 权限</li>
          <li>资源与基础设施配置</li>
        </ul>
        <div class="module-actions">
          <el-button @click="router.push(PROJECT_MANAGER_PATH)">浏览项目</el-button>
          <el-button type="primary" @click="openProject(store.activeProjectId)">进入当前项目</el-button>
        </div>
      </article>

      <article class="surface glass-card module-card">
        <div>
          <span class="soft-pill">Application delivery</span>
          <h3>DevCenter</h3>
          <p>先看到自己有权限进入的 Project，再进入项目级 DevCenter，只处理应用、流水线、发布和审批这些服务交付事务。</p>
        </div>
        <ul>
          <li>按权限展示可进入的 Project</li>
          <li>项目级应用与流水线入口</li>
          <li>发布 / 审批 / 运行态</li>
        </ul>
        <div class="module-actions">
          <el-button @click="router.push(DEV_CENTER_PATH)">浏览 DevCenter</el-button>
          <el-button type="primary" @click="openDevCenter(store.activeProjectId)">进入当前项目 DevCenter</el-button>
        </div>
      </article>
    </section>

    <section class="surface project-preview">
      <div class="surface-header">
        <div>
          <h3>My projects</h3>
          <p>{{ store.viewerScoped ? '当前列表已经按项目成员权限范围过滤。' : '当前未配置登录身份，因此先展示全部项目用于本地演示。' }}</p>
        </div>
      </div>

      <div v-if="store.items.length" class="project-list">
        <article v-for="project in store.items.slice(0, 6)" :key="project.id" class="project-item">
          <div>
            <div class="project-head">
              <span class="soft-pill">{{ project.key }}</span>
              <span v-if="project.my_role" class="soft-pill role-pill">{{ project.my_role }}</span>
              <StatusBadge v-if="project.id === store.activeProjectId" status="Active" label="Current" />
            </div>
            <h4>{{ project.name }}</h4>
            <p>{{ project.description || '这个项目还没有补充描述。' }}</p>
          </div>
          <div class="project-meta">
            <span>{{ project.applications_count || 0 }} applications</span>
            <span>{{ project.members_count || 0 }} members</span>
            <span>{{ project.clusters_count || 0 }} clusters</span>
          </div>
          <div class="module-actions">
            <el-button @click="openProject(project.id)">Project</el-button>
            <el-button type="primary" @click="openDevCenter(project.id)">DevCenter</el-button>
          </div>
        </article>
      </div>

      <EmptyState
        v-else-if="!store.loading"
        title="还没有项目"
        description="建议先在 ProjectManager 创建第一个 Project，然后再进入 DevCenter 组织应用交付流程。"
      >
        <el-button type="primary" @click="router.push(PROJECT_MANAGER_PATH)">创建项目</el-button>
      </EmptyState>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import EmptyState from '../components/common/EmptyState.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import { useProjectStore } from '../stores/project'
import { useViewerStore } from '../stores/viewer'
import { DEV_CENTER_PATH, PROJECT_MANAGER_PATH, devCenterProjectPath, projectManagerProjectPath } from '../utils/navigation'

const router = useRouter()
const store = useProjectStore()
const viewerStore = useViewerStore()

const applicationsCount = computed(() => store.items.reduce((sum, item) => sum + (item.applications_count || 0), 0))
const clustersCount = computed(() => store.items.reduce((sum, item) => sum + (item.clusters_count || 0), 0))

async function refresh() {
  await store.load()
}

function openProject(projectId?: number) {
  if (!projectId) {
    router.push(PROJECT_MANAGER_PATH)
    return
  }
  store.setActiveProject(projectId)
  router.push(projectManagerProjectPath(projectId))
}

function openDevCenter(projectId?: number) {
  if (!projectId) {
    router.push(DEV_CENTER_PATH)
    return
  }
  store.setActiveProject(projectId)
  router.push(devCenterProjectPath(projectId))
}

onMounted(async () => {
  viewerStore.init()
  store.init()
  await store.load()
})
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.module-card,
.project-preview {
  box-shadow: none;
}

.module-card {
  padding: 24px;
}

.module-card h3 {
  margin: 14px 0 10px;
  font-size: 30px;
  letter-spacing: -0.04em;
}

.module-card p,
.project-item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.75;
}

.module-card ul {
  margin: 20px 0 0;
  padding-left: 18px;
  color: var(--muted);
  display: grid;
  gap: 8px;
}

.module-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 20px;
}

.project-list {
  padding: 8px 24px 24px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.project-item {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.project-head,
.project-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.project-item h4 {
  margin: 14px 0 8px;
  font-size: 20px;
  letter-spacing: -0.03em;
}

.project-meta {
  margin-top: 16px;
  color: var(--muted);
  font-size: 13px;
}

.role-pill {
  text-transform: capitalize;
}

@media (max-width: 1100px) {
  .metrics,
  .module-grid,
  .project-list {
    grid-template-columns: 1fr;
  }
}
</style>

