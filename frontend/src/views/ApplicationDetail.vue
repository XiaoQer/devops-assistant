<template>
  <div class="page-content page-stack">
    <el-skeleton v-if="loadingApp" animated :rows="9" />
    <template v-else-if="app">
      <PageHeader eyebrow="Application workspace" :title="app.name" :description="`${shortRepo(app.repo_url)} · ${app.branch}`">
        <el-select v-model="environment" style="width: 132px">
          <el-option v-for="env in environmentOptions" :key="env" :label="env.toUpperCase()" :value="env" />
        </el-select>
        <el-button :loading="loadingRuntime" @click="loadRuntime">刷新状态</el-button>
        <el-button type="primary" :loading="deploying" @click="openDeployPlan">发布应用</el-button>
      </PageHeader>

      <section class="surface hero-card glass-card">
        <div class="hero-main">
          <div class="app-avatar">{{ app.name[0].toUpperCase() }}</div>
          <div>
            <div class="hero-pills">
              <StatusBadge :status="runtime?.status || 'Unknown'" />
              <span class="soft-pill">{{ environment.toUpperCase() }}</span>
              <span class="soft-pill">{{ app.language }}</span>
              <span class="soft-pill">{{ app.framework }}</span>
            </div>
            <h2>{{ app.name }} 正在作为一个可交付的软件工作区运行</h2>
            <p>优先展示现在最需要关心的环境、健康度、镜像与发布动作，而不是一上来就让你面对大量配置项。</p>
          </div>
        </div>
        <div class="hero-side">
          <div>
            <label>Current image</label>
            <b>{{ runtime?.deployment.images?.[0] || `${app.image_name}:${app.image_tag}` }}</b>
          </div>
          <div>
            <label>Replicas</label>
            <b>{{ runtime?.deployment.ready_replicas ?? '—' }} / {{ runtime?.deployment.replicas ?? '—' }}</b>
          </div>
          <div>
            <label>Latest execution</label>
            <b>{{ executions[0]?.pipeline_run_name || 'No runs yet' }}</b>
          </div>
        </div>
      </section>

      <section class="surface ai-panel">
        <span>✦</span>
        <div>
          <h3>Ask Aegis about this service</h3>
          <p>下一步可接入真正的应用级 AI：分析失败原因、建议环境配置、生成回滚方案、解释运行异常。</p>
        </div>
        <el-button disabled>Analyze this application</el-button>
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
        <el-tab-pane label="Overview" name="overview"><ApplicationOverview :application="app" /></el-tab-pane>
        <el-tab-pane label="Environments" name="environments"><EnvironmentCenter :application-id="app.id" :project-id="app.project_id || 0" /></el-tab-pane>
        <el-tab-pane label="Pipeline" name="pipeline"><section class="surface tab-card"><div class="surface-header"><div><h3>Pipeline executions</h3><p>最近 Tekton PipelineRun</p></div></div><el-table :data="executions"><el-table-column prop="pipeline_run_name" label="PipelineRun" min-width="280" /><el-table-column label="状态" width="130"><template #default="{row}"><StatusBadge :status="row.status" /></template></el-table-column><el-table-column label="创建时间" width="180"><template #default="{row}">{{ format(row.created_at) }}</template></el-table-column><el-table-column label="操作" width="100"><template #default="{row}"><el-button link @click="$router.push(`/pipelines/${row.pipeline_run_name}`)">详情</el-button></template></el-table-column></el-table><EmptyState v-if="!executions.length" title="暂无 Pipeline 执行" description="点击发布应用以启动第一条流水线。" /></section></el-tab-pane>
        <el-tab-pane label="Release History" name="releases"><ReleaseHistoryTable :releases="releases" :rollback-id="rollbackId" @logs="openLogs" @rollback="rollback" /></el-tab-pane>
        <el-tab-pane label="Runtime Status" name="runtime"><el-skeleton :loading="loadingRuntime" animated :rows="8"><RuntimeStatusPanel :status="runtime" :application-id="app.id" :environment="environment" /></el-skeleton></el-tab-pane>
        <el-tab-pane label="Config" name="config"><ConfigurationCenter :application-id="app.id" /></el-tab-pane>
        <el-tab-pane label="Logs" name="logs"><EmptyState title="选择 Pipeline 查看日志" description="在 Pipeline 标签页中选择一次执行，查看 Task 与 Step 日志。" icon="≡" /></el-tab-pane>
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

const shortRepo = (url: string) => url.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\.git$/, '')
const format = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false })

async function load() {
  loadingApp.value = true
  try {
    const id = Number(route.params.id)
    const [application, executionItems, envItems] = await Promise.all([
      applicationApi.get(id),
      applicationApi.executions(id),
      applicationApi.environments(id),
    ])
    app.value = application
    executions.value = executionItems
    environmentRecords.value = envItems
    if (!environmentOptions.value.includes(environment.value)) {
      environment.value = environmentOptions.value[0] || 'dev'
    }
    releases.value = await applicationApi.releases(id, environment.value)
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
    runtime.value = await applicationApi.status(Number(route.params.id), environment.value)
  } catch {
    runtime.value = undefined
  } finally {
    loadingRuntime.value = false
  }
}

async function loadEnvironment() {
  if (!app.value) return
  ;[releases.value] = await Promise.all([
    applicationApi.releases(Number(route.params.id), environment.value),
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
    deployPlan.value = await applicationApi.deployPlan(Number(route.params.id), {
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
    const run = await applicationApi.deploy(Number(route.params.id), { environment: deployEnvironment.value })
    deployDialog.value = false
    environment.value = deployEnvironment.value
    if (run.approval_required) {
      ElMessage.success('Production 发布审批已提交')
      router.push('/approvals')
    } else if (run.pipeline_run_name) {
      ElMessage.success('PipelineRun 已启动')
      router.push(`/pipelines/${run.pipeline_run_name}`)
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
    await applicationApi.rollback(Number(route.params.id), release.id, environment.value)
    ElMessage.success('回滚已提交')
    await loadEnvironment()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error((error as Error).message)
  } finally {
    rollbackId.value = 0
  }
}

function openLogs(release: Release) {
  if (release.pipeline_run_name) router.push(`/pipelines/${release.pipeline_run_name}`)
}

watch(environment, () => {
  if (app.value) loadEnvironment()
})
onMounted(load)
</script>

<style scoped>
.hero-card,
.ai-panel,
.tab-card {
  box-shadow: none;
}

.hero-card {
  padding: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
  gap: 24px;
}

.hero-main {
  display: flex;
  gap: 18px;
}

.app-avatar {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 22px;
  font-weight: 800;
  flex-shrink: 0;
}

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.hero-card h2 {
  margin: 0 0 10px;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -0.05em;
}

.hero-card p {
  margin: 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.8;
}

.hero-side {
  display: grid;
  gap: 14px;
}

.hero-side > div {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--theme-panel);
}

.hero-side label,
.hero-side b {
  display: block;
}

.hero-side label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.hero-side b {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.ai-panel {
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.ai-panel > span {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: var(--primary);
  color: white;
}

.ai-panel h3 {
  margin: 0 0 6px;
  font-size: 18px;
}

.ai-panel p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
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
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .hero-main {
    flex-direction: column;
  }

  .deploy-target-grid {
    grid-template-columns: 1fr;
  }
}
</style>
