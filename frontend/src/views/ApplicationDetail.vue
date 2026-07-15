<template>
  <div class="page-content page-stack">
    <el-skeleton v-if="loadingApp" animated :rows="9" />
    <template v-else-if="app">
      <DetailBreadcrumb :items="[
        { label: 'DevCenter', to: '/devcenter/projects' },
        { label: app.project_name || `Project ${projectId}`, to: `/devcenter/projects/${projectId}` },
        { label: 'Applications', to: `/devcenter/projects/${projectId}/applications` },
        { label: app.name, current: true },
      ]" />
      <PageHeader eyebrow="Application / Release" :title="app.name" :description="`${shortRepo(app.repo_url)} · ${app.branch}`">
        <el-select v-model="environment" style="width: 132px">
          <el-option v-for="env in environmentOptions" :key="env" :label="env.toUpperCase()" :value="env" />
        </el-select>
        <el-button :loading="loadingRuntime" @click="loadRuntime">刷新状态</el-button>
        <el-button type="primary" :loading="deploying" @click="openDeployPlan">发布应用</el-button>
      </PageHeader>

      <section class="surface application-summary">
        <div class="summary-heading">
          <div class="summary-context">
            <strong>运行环境概览</strong>
            <span>查看当前应用在各 Kubernetes 环境中的运行状态</span>
          </div>
          <span class="environment-count">{{ environmentRecords.length }} 个环境</span>
        </div>
        <div v-if="environmentRecords.length" class="environment-summary-grid">
          <article
            v-for="env in environmentRecords"
            :key="env.id"
            class="environment-summary-card"
            :class="{ selected: env.environment_name === environment }"
            @click="selectEnvironment(env.environment_name)"
          >
            <header>
              <strong>{{ env.display_name || env.environment_name }}</strong>
            </header>
            <div class="environment-summary-status">
              <span>状态</span>
              <StatusBadge :status="environmentRuntimes[env.environment_name]?.status || env.status || 'Unknown'" />
            </div>
            <div class="environment-summary-field">
              <span>分支</span>
              <b>{{ latestEnvironmentRelease(env.environment_name)?.git_branch || app.branch }}</b>
            </div>
            <div class="environment-summary-field">
              <span>当前版本</span>
              <b class="mono">{{ latestEnvironmentRelease(env.environment_name)?.image_tag || '未发布' }}</b>
            </div>
            <div class="environment-summary-field">
              <span>发布时间</span>
              <b>{{ latestEnvironmentRelease(env.environment_name) ? format(latestEnvironmentRelease(env.environment_name)!.created_at) : '—' }}</b>
            </div>
          </article>
        </div>
        <div v-else class="environment-summary-empty">尚未配置环境，请在“环境”Tab 中新建目标环境。</div>
      </section>

      <el-dialog v-model="deployDialog" title="发布应用" width="720px" class="release-dialog">
        <section class="release-flow">
          <div class="release-step">
            <label>1. 选择分支</label>
            <el-select v-model="releaseBranch" filterable style="width:100%" :loading="releaseLoading" @change="loadReleaseCommits">
              <el-option v-for="item in releaseBranches" :key="item.name" :label="item.name" :value="item.name" />
            </el-select>
          </div>
          <div class="release-step">
            <label>2. 选择提交</label>
            <el-select v-model="releaseCommit" style="width:100%" :loading="releaseLoading" placeholder="选择最近 20 条提交">
              <el-option v-for="item in releaseCommits" :key="item.sha" :label="`${item.sha.slice(0, 8)} · ${item.message}`" :value="item.sha">
                <div class="commit-option"><b>{{ item.message }}</b><small>{{ item.sha.slice(0, 12) }} · {{ item.author }}</small></div>
              </el-option>
            </el-select>
          </div>
          <div class="release-step">
            <label>3. 发布环境</label>
            <el-checkbox-group v-model="releaseEnvironmentIds" class="release-environments">
              <el-checkbox v-for="env in environmentRecords" :key="env.id" :label="env.id" border>
                {{ env.display_name || env.environment_name }} · {{ env.namespace }}{{ env.approval_required ? ' · 需审批' : '' }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
          <p class="release-hint">一次构建，按所选环境分别部署同一个镜像版本。</p>
        </section>
        <template #footer>
          <el-button @click="deployDialog = false">取消</el-button>
          <el-button type="primary" :disabled="!releaseBranch || !releaseCommit || !releaseEnvironmentIds.length" :loading="deploying" @click="confirmReleaseBatch">确认发布</el-button>
        </template>
      </el-dialog>

      <el-drawer
        v-model="environmentConfigDrawer"
        :title="`${configEnvironmentLabel} · 环境配置`"
        size="860px"
        destroy-on-close
        class="environment-config-drawer"
      >
        <ConfigurationCenter
          :application-id="app.id"
          :project-id="projectId"
          :initial-environment-id="configEnvironmentId"
        />
      </el-drawer>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="服务概览" name="overview"><ApplicationOverview :application="app" /></el-tab-pane>
        <el-tab-pane :label="`环境 (${environmentRecords.length})`" name="environments"><EnvironmentCenter :application-id="app.id" :project-id="app.project_id || 0" @configure="openEnvironmentConfig" /></el-tab-pane>
        <el-tab-pane :label="`Pipeline (${pipelineBuildCount})`" name="pipeline">
          <ApplicationBuildWorkspace
            :project-id="projectId"
            :application-id="app.id"
            :selected-build-id="pipelineSelectedBuildId"
            @build-count="pipelineBuildCount = $event"
            @select-build="pipelineSelectedBuildId = $event"
          />
        </el-tab-pane>
        <el-tab-pane :label="`发布记录 (${releases.length})`" name="releases"><ReleaseHistoryTable :releases="releases" :rollback-id="rollbackId" @logs="openLogs" @rollback="rollback" /></el-tab-pane>
        <el-tab-pane label="Kubernetes 资源" name="runtime"><el-skeleton :loading="loadingRuntime" animated :rows="8"><RuntimeStatusPanel :status="runtime" :application-id="app.id" :project-id="projectId" :environment="environment" /></el-skeleton></el-tab-pane>
        <el-tab-pane label="配置与密钥" name="config"><ConfigurationCenter :application-id="app.id" :project-id="projectId" /></el-tab-pane>
        <el-tab-pane label="操作日志" name="logs"><section class="surface tab-card"><div class="surface-header"><div><h3>交付操作日志</h3><p>从 Pipeline 和发布记录进入具体的构建、部署与回滚日志。</p></div></div><div class="log-guide"><div><span>01</span><strong>查看 Pipeline Step</strong><p>定位 clone、build、deploy 等任务的执行输出。</p></div><div><span>02</span><strong>检查 Kubernetes 事件</strong><p>在 Kubernetes 资源页查看 Pod、Service、Ingress 和事件。</p></div><div><span>03</span><strong>执行回滚</strong><p>从发布记录选择成功版本，恢复到稳定镜像。</p></div></div></section></el-tab-pane>
      </el-tabs>
    </template>
    <EmptyState v-else title="应用加载失败" description="请检查后端服务连接后重试。"><el-button @click="load">重新加载</el-button></EmptyState>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { applicationApi } from '../api/application'
import type {
  Application,
  ApplicationEnvironment,
  Execution,
  Release,
  RuntimeStatus,
  GitBranch,
  GitCommit,
  ReleaseBatch,
} from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ApplicationOverview from '../components/application/ApplicationOverview.vue'
import ReleaseHistoryTable from '../components/application/ReleaseHistoryTable.vue'
import RuntimeStatusPanel from '../components/application/RuntimeStatusPanel.vue'
import EnvironmentCenter from '../components/application/EnvironmentCenter.vue'
import ConfigurationCenter from '../components/application/ConfigurationCenter.vue'
import DetailBreadcrumb from '../components/common/DetailBreadcrumb.vue'
import ApplicationBuildWorkspace from '../components/pipeline/ApplicationBuildWorkspace.vue'

const route = useRoute()
const router = useRouter()
const app = ref<Application>()
const executions = ref<Execution[]>([])
const pipelineBuildCount = ref(0)
const pipelineSelectedBuildId = ref<number>()
const releases = ref<Release[]>([])
const runtime = ref<RuntimeStatus>()
const environmentRuntimes = ref<Record<string, RuntimeStatus | undefined>>({})
const environmentReleases = ref<Record<string, Release[]>>({})
const environmentRecords = ref<ApplicationEnvironment[]>([])
const activeTab = ref('overview')
const environment = ref('dev')
const loadingApp = ref(true)
const loadingRuntime = ref(false)
const deploying = ref(false)
const deployDialog = ref(false)
const releaseLoading = ref(false)
const releaseBranches = ref<GitBranch[]>([])
const releaseCommits = ref<GitCommit[]>([])
const releaseBranch = ref('')
const releaseCommit = ref('')
const releaseEnvironmentIds = ref<number[]>([])
const releaseBatch = ref<ReleaseBatch>()
const configEnvironmentId = ref<number>()
const environmentConfigDrawer = ref(false)
const rollbackId = ref(0)
const environmentOptions = computed(() => environmentRecords.value.map(item => item.environment_name))
const projectId = computed(() => Number(route.params.projectId))
const currentEnvironment = computed(() => environmentRecords.value.find(item => item.environment_name === environment.value))
const configEnvironmentLabel = computed(() => {
  const env = environmentRecords.value.find(item => item.id === configEnvironmentId.value)
  return env?.display_name || env?.environment_name || '当前环境'
})

const shortRepo = (url: string) => url.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\.git$/, '')
const format = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false })

async function load() {
  loadingApp.value = true
  try {
    const id = Number(route.params.id)
    const [application, executionItems, envItems] = await Promise.all([
      applicationApi.get(projectId.value, id),
      applicationApi.executions(projectId.value, id),
      applicationApi.environments(projectId.value, id),
    ])
    app.value = application
    const requestedTab = String(route.query.tab || '')
    if (['overview', 'environments', 'pipeline', 'releases', 'runtime', 'config', 'logs'].includes(requestedTab)) {
      activeTab.value = requestedTab
    }
    executions.value = executionItems
    environmentRecords.value = envItems
    if (!environmentOptions.value.includes(environment.value)) {
      environment.value = environmentOptions.value[0] || ''
    }
    releases.value = await applicationApi.releases(projectId.value, id, environment.value)
    await loadEnvironmentStatuses()
    await loadRuntime()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingApp.value = false
  }
}

async function loadRuntime() {
  if (!environment.value) {
    runtime.value = undefined
    return
  }
  loadingRuntime.value = true
  try {
    runtime.value = await applicationApi.status(projectId.value, Number(route.params.id), environment.value)
    environmentRuntimes.value = { ...environmentRuntimes.value, [environment.value]: runtime.value }
  } catch {
    runtime.value = undefined
  } finally {
    loadingRuntime.value = false
  }
}

async function loadEnvironmentStatuses() {
  const entries = await Promise.all(environmentRecords.value.map(async env => {
    try {
      const [status, releasesForEnvironment] = await Promise.all([
        applicationApi.status(projectId.value, Number(route.params.id), env.environment_name),
        applicationApi.releases(projectId.value, Number(route.params.id), env.environment_name),
      ])
      return { name: env.environment_name, status, releases: releasesForEnvironment }
    } catch {
      return { name: env.environment_name, status: undefined, releases: [] as Release[] }
    }
  }))
  environmentRuntimes.value = Object.fromEntries(entries.map(item => [item.name, item.status]))
  environmentReleases.value = Object.fromEntries(entries.map(item => [item.name, item.releases]))
}

function latestEnvironmentRelease(environmentName: string) {
  return environmentReleases.value[environmentName]?.[0]
}

function selectEnvironment(value: string) {
  environment.value = value
}

function openEnvironmentConfig(environmentId: number) {
  configEnvironmentId.value = environmentId
  environmentConfigDrawer.value = true
}

async function loadEnvironment() {
  if (!app.value) return
  ;[releases.value] = await Promise.all([
    applicationApi.releases(projectId.value, Number(route.params.id), environment.value),
    loadRuntime(),
  ])
  environmentReleases.value = { ...environmentReleases.value, [environment.value]: releases.value }
}

async function openDeployPlan() {
  deployDialog.value = true
  releaseLoading.value = true
  releaseBatch.value = undefined
  releaseEnvironmentIds.value = []
  try {
    releaseBranches.value = await applicationApi.gitBranches(projectId.value, Number(route.params.id))
    releaseBranch.value = releaseBranches.value.some(item => item.name === app.value?.branch)
      ? app.value?.branch || releaseBranches.value[0]?.name || ''
      : releaseBranches.value[0]?.name || ''
    await loadReleaseCommits()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    releaseLoading.value = false
  }
}

async function loadReleaseCommits() {
  if (!releaseBranch.value) return
  releaseLoading.value = true
  try {
    releaseCommits.value = await applicationApi.gitCommits(projectId.value, Number(route.params.id), releaseBranch.value, 20)
    releaseCommit.value = releaseCommits.value[0]?.sha || ''
  } catch (error) {
    releaseCommits.value = []
    releaseCommit.value = ''
    ElMessage.error((error as Error).message)
  } finally {
    releaseLoading.value = false
  }
}

async function confirmReleaseBatch() {
  if (!releaseBranch.value || !releaseCommit.value || !releaseEnvironmentIds.value.length) return
  deploying.value = true
  try {
    releaseBatch.value = await applicationApi.createReleaseBatch(projectId.value, Number(route.params.id), {
      branch: releaseBranch.value,
      git_commit: releaseCommit.value,
      environment_ids: releaseEnvironmentIds.value,
    })
    deployDialog.value = false
    ElMessage.success(`发布批次已创建：${releaseBranch.value} · ${releaseCommit.value.slice(0, 8)}`)
    await load()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    deploying.value = false
  }
}

async function rollback(release: Release) {
  try {
    await ElMessageBox.confirm(`确认将 ${app.value?.name} 回滚至 ${release.image_tag}？此操作会更新 ${release.deploy_namespace} 中的 Deployment。`, '确认回滚', {
      confirmButtonText: '执行回滚',
      cancelButtonText: '取消',
      type: 'warning',
    })
    rollbackId.value = release.id
    await applicationApi.rollback(projectId.value, Number(route.params.id), release.id, environment.value)
    ElMessage.success('回滚已提交')
    await loadEnvironment()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error((error as Error).message)
  } finally {
    rollbackId.value = 0
  }
}

function openLogs(release: Release) {
  if (release.pipeline_run_name) router.push(`/devcenter/projects/${projectId.value}/pipelines/${release.pipeline_run_name}`)
}

watch(environment, () => {
  if (app.value) loadEnvironment()
})
onMounted(load)
</script>

<style scoped>
.tab-card,
.application-summary {
  box-shadow: none;
}

.page-content :deep(.page-header) {
  gap: 14px;
  margin-bottom: 10px;
}

.page-content :deep(.page-header h1) {
  font-size: 25px;
}

.page-content :deep(.page-header .eyebrow) {
  min-height: 24px;
  padding: 0 10px;
  margin-bottom: 7px;
  font-size: 11px;
}

.page-content :deep(.page-header p) {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.45;
}

.page-content :deep(.page-header .page-actions) {
  gap: 8px;
}

.app-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 18px;
  font-weight: 800;
  flex-shrink: 0;
}

.application-summary {
  padding: 16px;
}

.release-flow {
  display: grid;
  gap: 16px;
}

.release-step {
  padding: 0 0 16px;
  border-bottom: 1px solid var(--border-soft);
}

.release-step label {
  display: block;
  margin-bottom: 7px;
  color: var(--text-2);
  font-size: 13px;
  font-weight: 700;
}

.release-step :deep(.el-select) {
  --el-border-color: #d8e0eb;
  --el-border-color-hover: #93b4f8;
  --el-text-color-regular: #172033;
}

.release-environments {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.release-environments :deep(.el-checkbox) {
  display: flex;
  width: 100%;
  min-width: 0;
  margin-right: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--surface);
}

.commit-option {
  display: grid;
  gap: 3px;
  line-height: 1.35;
}

.commit-option b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.commit-option small {
  color: var(--muted);
  font-size: 11px;
}

.release-batch-list {
  display: grid;
  gap: 8px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border-soft);
}

.release-batch-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: var(--surface-soft);
}

.release-batch-item b,
.release-batch-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.release-batch-item small,
.release-target-count {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.release-target-list {
  grid-column: 1 / -1;
  display: grid;
  gap: 6px;
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--border-soft);
}

.release-target-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--surface);
}

.release-target-name {
  min-width: 0;
  font-size: 12px;
  font-weight: 700;
}

.release-target-name small,
.release-target-note {
  margin-left: 6px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 400;
}

.release-hint {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.summary-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.summary-context strong,
.summary-context span {
  display: block;
}

.summary-context strong {
  color: var(--text-1);
  font-size: 15px;
}

.summary-context span {
  margin-top: 3px;
  color: var(--muted);
  font-size: 12px;
}

.environment-count {
  color: var(--muted);
  font-size: 12px;
}

.environment-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.environment-summary-card {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(110px, 1fr) minmax(130px, 1.1fr) minmax(120px, 1fr) minmax(150px, 1.2fr) minmax(130px, 1fr);
  align-items: center;
  gap: 18px;
  padding: 12px 16px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--surface-soft);
  cursor: pointer;
  transition: border-color .15s ease, box-shadow .15s ease;
}

.environment-summary-card > * {
  min-width: 0;
}

.environment-summary-card:hover,
.environment-summary-card.selected {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-soft);
}

.environment-summary-card header,
.environment-summary-status,
.environment-summary-field {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.environment-summary-card header {
  justify-content: flex-start;
}

.environment-summary-card header strong,
.environment-summary-status span,
.environment-summary-field span,
.environment-summary-field b {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.environment-summary-card header strong {
  font-size: 15px;
}

.environment-summary-status span,
.environment-summary-field span {
  display: block;
  color: var(--muted);
  font-size: 11px;
}

.environment-summary-field {
  flex-direction: column;
  align-items: center;
  min-width: 0;
  padding-left: 14px;
  border-left: 1px solid var(--border-soft);
}

.environment-summary-field b {
  max-width: 100%;
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-2);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .release-environments {
    grid-template-columns: 1fr;
  }

  .environment-summary-card {
    grid-template-columns: 1fr 1fr;
  }

  .release-batch-item {
    grid-template-columns: 1fr auto;
  }

  .release-target-count {
    grid-column: 1 / -1;
    margin-top: 0;
  }

  .environment-summary-field {
    padding: 10px 0 0;
    border-top: 1px solid var(--border-soft);
    border-left: 0;
  }
}

.environment-summary-empty {
  padding: 22px;
  border: 1px dashed var(--border);
  border-radius: 12px;
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}

.summary-identity,
.summary-pills {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-identity > div:last-child > strong,
.summary-identity > div:last-child > span {
  display: block;
}

.summary-identity > div:last-child > strong {
  margin-top: 6px;
  font-size: 17px;
}

.summary-identity > div:last-child > span,
.summary-stat span {
  color: var(--muted);
  font-size: 12px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.environment-config-drawer :deep(.el-drawer) {
  background: #f6f8fb;
  color: #172033;
}

:global(.environment-config-drawer.el-drawer) {
  background: #f6f8fb !important;
  color: #172033 !important;
}

:global(.environment-config-drawer.el-drawer .el-drawer__body) {
  background: #f6f8fb !important;
}

.environment-config-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 20px 28px;
  border-bottom: 1px solid #e5eaf2;
  background: #fff;
}

.environment-config-drawer :deep(.el-drawer__title) {
  color: #172033;
  font-size: 18px;
  font-weight: 700;
}

.environment-config-drawer :deep(.el-drawer__close) {
  color: #7b879b;
}

.environment-config-drawer :deep(.el-drawer__body) {
  padding: 0;
  overflow-x: hidden;
}

.environment-config-drawer :deep(.page-stack) {
  gap: 14px;
  padding: 22px 28px 28px;
}

.environment-config-drawer :deep(.section-head) {
  align-items: flex-start;
  padding-bottom: 4px;
}

.environment-config-drawer :deep(.section-head h3) {
  margin-bottom: 6px;
  color: #172033;
  font-size: 20px;
}

.environment-config-drawer :deep(.section-head p) {
  max-width: 520px;
  color: #738097;
  font-size: 13px;
  line-height: 1.55;
}

.environment-config-drawer :deep(.config-tabs) {
  margin: 0 -4px;
}

.environment-config-drawer :deep(.config-tabs .el-tabs__item) {
  color: #718097;
  font-size: 13px;
  font-weight: 600;
}

.environment-config-drawer :deep(.config-tabs .el-tabs__item.is-active) {
  color: #2563eb;
}

:global(.environment-config-drawer .config-tabs .el-tabs__item) {
  color: #53627a !important;
}

:global(.environment-config-drawer .config-tabs .el-tabs__item.is-active) {
  color: #2563eb !important;
}

:global(.environment-config-drawer .config-tabs .el-tabs__item.is-disabled) {
  color: #aeb8c7 !important;
  cursor: not-allowed;
  opacity: .75;
}

.environment-config-drawer :deep(.list-card),
.environment-config-drawer :deep(.redeploy-card) {
  border: 1px solid #e5eaf2;
  border-radius: 14px;
  background: #fff;
}

.environment-config-drawer :deep(.list-card .surface-header) {
  padding: 16px 20px;
}

.environment-config-drawer :deep(.list-card .surface-header h3) {
  color: #172033;
  font-size: 16px;
}

.environment-config-drawer :deep(.list-card .surface-header p) {
  color: #8490a3;
  font-size: 12px;
}

.environment-config-drawer :deep(.config-list) {
  padding: 12px 16px 16px;
}

.environment-config-drawer :deep(.config-card) {
  padding: 14px;
  border-color: #e5eaf2;
  background: #f8fafc;
}

.environment-config-drawer :deep(.config-head h4) {
  color: #172033;
  font-size: 15px;
}

.environment-config-drawer :deep(.empty) {
  min-height: 180px;
  padding: 24px;
  border: 0;
  border-radius: 0 0 14px 14px;
  background: #fff;
}

.environment-config-drawer :deep(.empty > span) {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  font-size: 18px;
}

.environment-config-drawer :deep(.empty h3) {
  margin: 12px 0 6px;
  color: #172033;
  font-size: 16px;
}

.environment-config-drawer :deep(.empty p) {
  color: #8490a3;
  font-size: 12px;
}

.environment-config-drawer :deep(.redeploy-card) {
  padding: 14px 16px;
}

@media (max-width: 900px) {
  .environment-config-drawer :deep(.el-drawer) {
    width: 100% !important;
  }
}

.log-guide {
  overflow: hidden;
}

.pipeline-list {
  padding: 8px 18px 18px;
}

.pipeline-item {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 76px;
  padding: 14px 12px;
  border-bottom: 1px solid var(--border-soft);
  transition: background .16s ease, border-color .16s ease;
}

.pipeline-item:last-child {
  border-bottom: 0;
}

.pipeline-item:hover {
  border-radius: 10px;
  background: var(--surface-soft);
}

.pipeline-index {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 9px;
  background: var(--primary-soft);
  color: var(--primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 700;
}

.pipeline-main {
  min-width: 0;
  flex: 1;
}

.pipeline-name-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.pipeline-name-row strong {
  overflow: hidden;
  color: var(--text-2);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pipeline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 7px;
  color: var(--muted);
  font-size: 12px;
}

.pipeline-meta span + span {
  padding-left: 12px;
  border-left: 1px solid var(--border-soft);
}

.pipeline-action {
  flex: 0 0 auto;
  color: var(--primary) !important;
  font-size: 13px;
  font-weight: 600;
}

.pipeline-action span {
  margin-left: 4px;
  font-size: 16px;
}

.log-guide {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 18px 24px 24px;
}

.log-guide > div {
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: var(--surface-soft);
}

.log-guide span {
  color: var(--primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  font-weight: 800;
}

.log-guide strong {
  display: block;
  margin-top: 12px;
}

.log-guide p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

.deploy-plan-stack {
  display: grid;
  gap: 16px;
}

.deploy-selector {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
}

.deploy-selector label {
  display: block;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--muted);
}

.deploy-selector p {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.deploy-summary {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
}

.deploy-summary strong,
.deploy-summary p {
  display: block;
}

.deploy-summary strong {
  margin-bottom: 6px;
}

.deploy-summary p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.deploy-summary.risk-low {
  background: rgba(34, 197, 94, 0.08);
}

.deploy-summary.risk-medium {
  background: rgba(245, 158, 11, 0.1);
}

.deploy-summary.risk-high {
  background: rgba(239, 68, 68, 0.1);
}

.deploy-target-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.deploy-target-grid article {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.deploy-target-grid label,
.deploy-target-grid b {
  display: block;
}

.deploy-target-grid label {
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 12px;
}

.deploy-target-grid b {
  line-height: 1.6;
  word-break: break-word;
}

.plan-check-list {
  display: grid;
  gap: 12px;
}

.plan-check-item {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.plan-check-item.status-pass {
  border-color: rgba(34, 197, 94, 0.22);
}

.plan-check-item.status-warn {
  border-color: rgba(245, 158, 11, 0.3);
}

.plan-check-item.status-blocked {
  border-color: rgba(239, 68, 68, 0.35);
}

.plan-check-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.plan-check-head span {
  font-size: 12px;
  color: var(--muted);
}

.plan-check-item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.detail-tabs :deep(.el-tabs__header) {
  margin: 18px 0 14px;
  border-bottom: 1px solid var(--border-soft);
}

.detail-tabs :deep(.el-tabs__item) {
  color: #64748b !important;
  font-size: 13px;
  font-weight: 600;
}

.detail-tabs :deep(.el-tabs__item:hover) {
  color: #1d4ed8 !important;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: #1d4ed8 !important;
  font-weight: 700;
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background-color: #2563eb !important;
}

@media (max-width: 1100px) {
  .deploy-target-grid {
    grid-template-columns: 1fr;
  }

  .log-guide {
    grid-template-columns: 1fr;
  }

  .pipeline-item {
    align-items: flex-start;
  }

  .pipeline-action {
    padding-top: 4px;
  }
}

@media (max-width: 640px) {
  .pipeline-item {
    gap: 10px;
    padding: 12px 4px;
  }

  .pipeline-index {
    width: 28px;
    height: 28px;
  }

  .pipeline-name-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .pipeline-action {
    font-size: 0;
  }

  .pipeline-action span {
    margin: 0;
    font-size: 18px;
  }
}
</style>
