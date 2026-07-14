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
        <div class="summary-identity">
          <div class="app-avatar">{{ app.name[0].toUpperCase() }}</div>
          <div>
            <div class="summary-pills"><StatusBadge :status="runtime?.status || 'Unknown'" /><span class="soft-pill">{{ environment.toUpperCase() }}</span></div>
            <strong>{{ app.name }}</strong>
            <span>{{ app.language }} · {{ app.framework }} · {{ app.build_type }}</span>
          </div>
        </div>
        <div class="summary-stat"><span>Target namespace</span><strong>{{ runtime?.namespace || currentEnvironment?.namespace || app.namespace }}</strong></div>
        <div class="summary-stat"><span>Replicas</span><strong>{{ runtime ? `${runtime.deployment.ready_replicas} / ${runtime.deployment.replicas}` : '—' }}</strong></div>
        <div class="summary-stat"><span>Current image</span><strong class="mono">{{ runtime?.deployment.images?.[0] || `${app.image_name || 'not-configured'}:${app.image_tag}` }}</strong></div>
        <div class="summary-stat"><span>Cluster</span><strong>{{ currentEnvironment?.cluster_name || 'Not bound' }}</strong></div>
      </section>

      <el-dialog v-model="deployDialog" title="Deployment plan" width="780px">
        <el-skeleton :loading="loadingPlan" animated :rows="8">
          <template v-if="deployDialog">
            <section class="deploy-plan-stack">
              <div class="deploy-selector surface-soft-card">
                <label>Deploy target environment</label>
                <el-select v-model="deployEnvironment" placeholder="请选择要部署的环境" style="width: 100%" @change="loadDeployPlan">
                  <el-option v-for="env in environmentOptions" :key="env" :label="env.toUpperCase()" :value="env" />
                </el-select>
                <p>查看页面状态使用的环境，不会自动作为发布目标。发布前必须在这里显式确认一次。</p>
              </div>

              <EmptyState
                v-if="!deployEnvironment && !loadingPlan"
                title="先选择发布环境"
                description="例如 dev / test / staging / prod。选择后平台会生成对应的发布计划与风险检查结果。"
                icon="⇢"
              />

              <template v-else-if="deployPlan">
              <div class="deploy-summary" :class="`risk-${deployPlan.risk_level}`">
                <div>
                  <strong>{{ riskLabel(deployPlan.risk_level) }}</strong>
                  <p>{{ deployPlan.summary }}</p>
                </div>
                <span class="soft-pill">{{ environment.toUpperCase() }}</span>
              </div>

              <div class="deploy-target-grid">
                <article>
                  <label>Target namespace</label>
                  <b>{{ deployPlan.target.namespace }}</b>
                </article>
                <article>
                  <label>Image</label>
                  <b>{{ deployPlan.target.image_name }}:{{ deployPlan.target.image_tag }}</b>
                </article>
                <article>
                  <label>Pipeline</label>
                  <b>{{ deployPlan.target.pipeline_name || 'Unavailable' }}</b>
                </article>
                <article>
                  <label>Delivery mode</label>
                  <b>{{ deployPlan.target.approval_required ? 'Approval required' : 'Direct delivery' }}</b>
                </article>
              </div>

              <div class="plan-check-list">
                <article
                  v-for="check in deployPlan.checks"
                  :key="check.name"
                  class="plan-check-item"
                  :class="`status-${check.status}`"
                >
                  <div class="plan-check-head">
                    <strong>{{ check.summary }}</strong>
                    <span>{{ check.status.toUpperCase() }}</span>
                  </div>
                  <p>{{ check.detail }}</p>
                </article>
              </div>
              </template>
            </section>
          </template>
        </el-skeleton>
        <template #footer>
          <el-button @click="deployDialog = false">取消</el-button>
          <el-button
            type="primary"
            :disabled="!deployEnvironment || !deployPlan?.can_deploy || loadingPlan"
            :loading="deploying"
            @click="confirmDeploy"
          >
            {{ deployPlan?.target.approval_required ? '提交审批' : '确认发布' }}
          </el-button>
        </template>
      </el-dialog>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="服务概览" name="overview"><ApplicationOverview :application="app" /></el-tab-pane>
        <el-tab-pane :label="`环境 (${environmentRecords.length})`" name="environments"><EnvironmentCenter :application-id="app.id" :project-id="app.project_id || 0" /></el-tab-pane>
        <el-tab-pane :label="`Pipeline (${executions.length})`" name="pipeline">
          <section class="surface tab-card pipeline-panel">
            <div class="surface-header">
              <div>
                <h3>构建与部署执行</h3>
                <p>中央 Tekton PipelineRun 及其交付状态</p>
              </div>
              <el-button type="primary" @click="openDeployPlan">新建发布</el-button>
            </div>
            <div v-if="executions.length" class="pipeline-list">
              <article v-for="(run, index) in executions" :key="run.pipeline_run_name" class="pipeline-item">
                <div class="pipeline-index">{{ String(index + 1).padStart(2, '0') }}</div>
                <div class="pipeline-main">
                  <div class="pipeline-name-row">
                    <strong>{{ run.pipeline_run_name }}</strong>
                    <StatusBadge :status="run.status" />
                  </div>
                  <div class="pipeline-meta">
                    <span>创建于 {{ format(run.created_at) }}</span>
                    <span v-if="run.error_message">{{ run.error_message }}</span>
                  </div>
                </div>
                <el-button class="pipeline-action" text @click="$router.push(`/devcenter/projects/${projectId}/pipelines/${run.pipeline_run_name}`)">查看详情 <span>→</span></el-button>
              </article>
            </div>
            <EmptyState v-else title="暂无 Pipeline 执行" description="点击新建发布启动第一条流水线。" />
          </section>
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
  DeploymentPlan,
  Execution,
  Release,
  RuntimeStatus,
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

const route = useRoute()
const router = useRouter()
const app = ref<Application>()
const executions = ref<Execution[]>([])
const releases = ref<Release[]>([])
const runtime = ref<RuntimeStatus>()
const environmentRecords = ref<ApplicationEnvironment[]>([])
const activeTab = ref('overview')
const environment = ref('dev')
const loadingApp = ref(true)
const loadingRuntime = ref(false)
const deploying = ref(false)
const deployDialog = ref(false)
const loadingPlan = ref(false)
const deployEnvironment = ref('')
const deployPlan = ref<DeploymentPlan>()
const rollbackId = ref(0)
const environmentOptions = computed(() => environmentRecords.value.map(item => item.environment_name))
const projectId = computed(() => Number(route.params.projectId))
const currentEnvironment = computed(() => environmentRecords.value.find(item => item.environment_name === environment.value))

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
    executions.value = executionItems
    environmentRecords.value = envItems
    if (!environmentOptions.value.includes(environment.value)) {
      environment.value = environmentOptions.value[0] || 'dev'
    }
    releases.value = await applicationApi.releases(projectId.value, id, environment.value)
    await loadRuntime()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingApp.value = false
  }
}

async function loadRuntime() {
  loadingRuntime.value = true
  try {
    runtime.value = await applicationApi.status(projectId.value, Number(route.params.id), environment.value)
  } catch {
    runtime.value = undefined
  } finally {
    loadingRuntime.value = false
  }
}

async function loadEnvironment() {
  if (!app.value) return
  ;[releases.value] = await Promise.all([
    applicationApi.releases(projectId.value, Number(route.params.id), environment.value),
    loadRuntime(),
  ])
}

async function openDeployPlan() {
  deployDialog.value = true
  deployEnvironment.value = ''
  deployPlan.value = undefined
}

async function loadDeployPlan() {
  if (!deployEnvironment.value) {
    deployPlan.value = undefined
    return
  }
  loadingPlan.value = true
  deployPlan.value = undefined
  try {
    deployPlan.value = await applicationApi.deployPlan(projectId.value, Number(route.params.id), {
      environment: deployEnvironment.value,
    })
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingPlan.value = false
  }
}

async function confirmDeploy() {
  if (!deployEnvironment.value || !deployPlan.value?.can_deploy) return
  deploying.value = true
  try {
    const run = await applicationApi.deploy(projectId.value, Number(route.params.id), { environment: deployEnvironment.value })
    deployDialog.value = false
    environment.value = deployEnvironment.value
    if (run.approval_required) {
      ElMessage.success('Production 发布审批已提交')
      router.push(`/devcenter/projects/${projectId.value}/approvals`)
    } else if (run.pipeline_run_name) {
      ElMessage.success('PipelineRun 已启动')
      router.push(`/devcenter/projects/${projectId.value}/pipelines/${run.pipeline_run_name}`)
    }
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    deploying.value = false
  }
}

function riskLabel(level: DeploymentPlan['risk_level']) {
  return {
    low: 'Low risk',
    medium: 'Needs attention',
    high: 'High risk / gated',
  }[level]
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
  margin-bottom: 14px;
}

.page-content :deep(.page-header h1) {
  font-size: 28px;
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
  display: grid;
  grid-template-columns: minmax(260px, 1.5fr) repeat(4, minmax(120px, 1fr));
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
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

.summary-stat {
  min-width: 0;
  padding-left: 14px;
  border-left: 1px solid var(--border-soft);
}

.summary-stat strong {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: var(--text-2);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.pipeline-panel,
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
  .application-summary {
    grid-template-columns: 1fr;
  }

  .summary-stat {
    padding: 10px 0 0;
    border-left: 0;
    border-top: 1px solid var(--border-soft);
  }

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
