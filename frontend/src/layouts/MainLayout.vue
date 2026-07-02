<template>
  <div class="app-shell" :class="{ collapsed: uiStore.sidebarCollapsed }">
    <aside class="sidebar surface glass-card">
      <div class="sidebar-head">
        <router-link to="/dashboard" class="brand">
          <div class="brand-mark">
            <span></span><span></span><span></span>
          </div>
          <div v-if="!uiStore.sidebarCollapsed" class="brand-copy">
            <strong>Aegis</strong>
            <small>Software OS</small>
          </div>
        </router-link>

        <button class="icon-button" @click="uiStore.toggleSidebar">
          {{ uiStore.sidebarCollapsed ? '→' : '←' }}
        </button>
      </div>

      <div v-if="!uiStore.sidebarCollapsed" class="workspace-card">
        <span class="soft-pill">AI Native Platform</span>
        <h3>用更少点击完成软件交付</h3>
        <p>把应用、发布、审批与运行状态组织成统一的软件工作流，而不是分散的运维页面。</p>
        <div class="project-switcher">
          <label>Current project</label>
          <el-select v-model="activeProjectId" placeholder="选择项目" @change="handleProjectChange">
            <el-option v-for="project in projectStore.items" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </div>
      </div>

      <div class="nav-group">
        <div v-if="!uiStore.sidebarCollapsed" class="nav-label">Workspace</div>
        <router-link
          v-for="item in nav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="active"
        >
          <component :is="item.icon" />
          <span v-if="!uiStore.sidebarCollapsed">{{ item.name }}</span>
          <span v-if="item.path === '/approvals' && !uiStore.sidebarCollapsed" class="nav-count">3</span>
        </router-link>
      </div>

      <div class="nav-group nav-secondary">
        <div v-if="!uiStore.sidebarCollapsed" class="nav-label">Platform</div>
        <router-link to="/settings/registries" class="nav-item" active-class="active">
          <IconRegistry />
          <span v-if="!uiStore.sidebarCollapsed">Registries</span>
        </router-link>
        <button class="nav-item nav-button" @click="uiStore.toggleTheme">
          <IconTheme />
          <span v-if="!uiStore.sidebarCollapsed">{{ uiStore.theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
        </button>
      </div>

      <footer class="sidebar-footer">
        <div class="avatar">SL</div>
        <div v-if="!uiStore.sidebarCollapsed" class="profile-copy">
          <strong>Shaoqian Li</strong>
          <span>Builder mode</span>
        </div>
      </footer>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <span class="topbar-label">{{ currentSection }}</span>
          <h2>{{ currentTitle }}</h2>
        </div>
        <div class="topbar-actions">
          <router-link to="/applications/new" class="command-button command-button-primary">
            + New application
          </router-link>
          <button class="command-button" @click="commandStore.open()">
            ⌘ Ask Aegis what to do next
          </button>
        </div>
      </header>

      <div class="main-inner">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCommandStore } from '@/stores/command'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import IconDashboard from '../components/icons/IconDashboard.vue'
import IconApplication from '../components/icons/IconApplication.vue'
import IconPipeline from '../components/icons/IconPipeline.vue'
import IconRelease from '../components/icons/IconRelease.vue'
import IconApproval from '../components/icons/IconApproval.vue'
import IconRegistry from '../components/icons/IconRegistry.vue'
import IconTheme from '@/components/icons/IconTheme.vue'

const uiStore = useUiStore()
const commandStore = useCommandStore()
const projectStore = useProjectStore()
const route = useRoute()
const router = useRouter()

const nav = shallowRef([
  { name: 'Overview', path: '/dashboard', icon: IconDashboard },
  { name: 'Projects', path: '/projects', icon: IconApplication },
  { name: 'Applications', path: '/applications', icon: IconApplication },
  { name: 'Pipelines', path: '/pipelines', icon: IconPipeline },
  { name: 'Releases', path: '/releases', icon: IconRelease },
  { name: 'Approvals', path: '/approvals', icon: IconApproval },
])

const currentTitle = computed(() => {
  const match = nav.value.find(item => route.path.startsWith(item.path))
  if (route.path.startsWith('/settings/registries')) return 'Registry settings'
  if (route.path.startsWith('/projects/')) return 'Project workspace'
  if (route.path.startsWith('/applications/new')) return 'Create application'
  if (route.path.startsWith('/applications/')) return 'Application workspace'
  if (route.path.startsWith('/pipelines/')) return 'Pipeline detail'
  return match?.name || 'Workspace'
})

const currentSection = computed(() => {
  if (route.path.startsWith('/settings')) return 'Platform'
  if (route.path.startsWith('/projects')) return 'Project'
  if (route.path.startsWith('/applications')) return 'Software delivery'
  if (route.path.startsWith('/pipelines')) return 'Execution'
  if (route.path.startsWith('/releases')) return 'Release management'
  if (route.path.startsWith('/approvals')) return 'Governance'
  return 'AI Native Software OS'
})

const activeProjectId = computed({
  get: () => projectStore.activeProjectId,
  set: value => projectStore.setActiveProject(value),
})

function handleProjectChange(projectId: number) {
  projectStore.setActiveProject(projectId)
  if (!route.path.startsWith('/projects/')) return
  router.push(`/projects/${projectId}`)
}

onMounted(() => {
  uiStore.initUi()
  projectStore.init()
  projectStore.load()
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 24%),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.09), transparent 22%),
    var(--theme-bg);
}

.sidebar {
  position: fixed;
  top: 16px;
  left: 16px;
  bottom: 16px;
  width: 280px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  z-index: 10;
}

.collapsed .sidebar {
  width: 88px;
  padding: 18px 12px;
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--theme-text);
  min-width: 0;
}

.brand-copy {
  min-width: 0;
}

.brand-copy strong,
.brand-copy small {
  display: block;
}

.brand-copy strong {
  font-size: 16px;
  letter-spacing: -0.02em;
}

.brand-copy small {
  color: var(--theme-muted);
  font-size: 12px;
  margin-top: 3px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: linear-gradient(145deg, #3b82f6, #1d4ed8);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.24);
  flex-shrink: 0;
}

.brand-mark span {
  width: 4px;
  height: 16px;
  background: white;
  border-radius: 999px;
}

.icon-button,
.command-button,
.nav-button {
  border: 0;
  cursor: pointer;
}

.icon-button {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--surface-soft);
  color: var(--text);
}

.workspace-card {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: linear-gradient(180deg, var(--surface-soft), transparent);
  margin-bottom: 20px;
}

.workspace-card h3 {
  margin: 12px 0 8px;
  font-size: 16px;
  letter-spacing: -0.03em;
}

.workspace-card p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.65;
}

.project-switcher {
  margin-top: 16px;
}

.project-switcher label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--muted);
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-secondary {
  margin-top: auto;
}

.nav-label {
  padding: 0 12px;
  margin: 8px 0 6px;
  color: var(--theme-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.nav-item {
  position: relative;
  min-height: 44px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 12px;
  color: var(--muted);
  font-size: 14px;
  font-weight: 600;
  background: transparent;
}

.nav-item:hover {
  color: var(--text);
  background: var(--surface-soft);
}

.nav-item.active {
  color: var(--primary);
  background: var(--primary-soft);
}

.nav-item :deep(svg) {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.nav-count {
  position: absolute;
  right: 12px;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: var(--primary);
  color: white;
  font-size: 11px;
}

.sidebar-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-soft);
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, var(--surface-soft), var(--surface-raised));
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.profile-copy strong,
.profile-copy span {
  display: block;
}

.profile-copy strong {
  font-size: 13px;
}

.profile-copy span {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.main {
  margin-left: 320px;
  min-height: 100vh;
}

.collapsed .main {
  margin-left: 120px;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 6;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  padding: 28px 32px 0;
  background: linear-gradient(180deg, var(--theme-bg) 75%, transparent);
}

.topbar-label {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.topbar h2 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.04em;
}

.topbar-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.command-button {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.64);
  border: 1px solid var(--border-soft);
  color: var(--text);
  display: inline-flex;
  align-items: center;
  backdrop-filter: blur(10px);
  font-size: 13px;
  font-weight: 600;
}

body[data-theme='dark'] .command-button {
  background: rgba(15, 23, 42, 0.66);
}

.command-button-primary {
  background: var(--primary);
  color: white;
  border-color: transparent;
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.18);
}

.main-inner {
  padding: 0 8px 28px;
}

@media (max-width: 1100px) {
  .sidebar {
    position: sticky;
    top: 0;
    left: 0;
    right: 0;
    width: auto;
    margin: 12px;
  }

  .main,
  .collapsed .main {
    margin-left: 0;
  }

  .topbar {
    padding: 8px 20px 0;
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
