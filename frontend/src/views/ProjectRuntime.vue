<template>
  <div class="page-content page-stack runtime-page">
    <PageHeader
      eyebrow="Kubernetes runtime"
      title="Runtime"
      description="按环境查看当前 Project 的 Deployment 与 Pod，并在明确确认后执行受治理的运维操作。"
    >
      <el-switch v-model="autoRefresh" active-text="自动刷新" />
      <el-button :loading="loading" @click="refresh">刷新</el-button>
    </PageHeader>

    <el-alert v-if="refreshError" :title="refreshError" type="warning" :closable="false" show-icon />

    <div class="runtime-metrics">
      <MetricCard title="Environments" :value="summary.environments" icon="◫" helper="当前 Project" />
      <MetricCard title="Deployments" :value="summary.deployments" icon="▦" tone="blue" helper="已发现工作负载" />
      <MetricCard title="Healthy Pods" :value="summary.healthy_pods" icon="✓" tone="green" helper="Ready" />
      <MetricCard title="Unhealthy Pods" :value="summary.unhealthy_pods" icon="!" tone="red" helper="需要关注" />
      <MetricCard title="Restarts" :value="summary.restart_count" icon="↻" helper="Pod 累计重启" />
    </div>

    <section class="surface runtime-toolbar">
      <el-input v-model="query" placeholder="搜索 Application、Deployment、Pod、镜像…" clearable />
      <el-select v-model="environment" placeholder="全部环境" clearable>
        <el-option v-for="item in overview?.environments || []" :key="item.name" :label="item.display_name" :value="item.name" />
      </el-select>
      <el-select v-model="status" placeholder="全部状态" clearable>
        <el-option v-for="item in ['Healthy', 'Progressing', 'Degraded', 'Failed', 'Unknown']" :key="item" :label="item" :value="item" />
      </el-select>
      <span>{{ filteredEnvironments.length }} environments</span>
    </section>

    <el-skeleton :loading="loading && !overview" animated :rows="10">
      <div v-if="filteredEnvironments.length" class="environment-list">
        <RuntimeEnvironmentGroup
          v-for="group in filteredEnvironments"
          :key="group.name"
          :group="group"
          @deployment-yaml="openDeploymentYaml(group.name, $event)"
          @restart="restart(group.name, $event)"
          @pod-logs="(application, pod) => openPodLogs(group.name, application, pod)"
          @pod-yaml="(application, pod) => openPodYaml(group.name, application, pod)"
          @terminal="(application, pod) => prepareTerminal(group.name, application, pod)"
          @delete-pod="(application, pod) => removePod(group.name, application, pod)"
        />
      </div>
      <EmptyState v-else title="没有可展示的运行资源" description="当前筛选条件下没有 Deployment 或 Pod；也可能尚未创建 Application Environment。" />
    </el-skeleton>

    <RuntimeResourceDrawer v-model="resourceDrawer" :title="resourceTitle" :content="resourceContent" :loading="resourceLoading" />

    <el-dialog v-model="terminalSetup" title="进入 Pod 终端" width="520px">
      <el-form label-position="top">
        <el-form-item label="Pod"><el-input :model-value="terminalTarget?.pod.name" disabled /></el-form-item>
        <el-form-item label="Container">
          <el-select v-model="terminalContainer" style="width: 100%">
            <el-option v-for="item in terminalTarget?.pod.containers || []" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作原因" required>
          <el-input v-model="terminalReason" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="说明本次进入终端的目的" />
        </el-form-item>
        <el-alert v-if="terminalTarget && isProduction(terminalTarget.environment)" title="这是生产环境终端，会话元数据将进入审计。" type="error" :closable="false" />
      </el-form>
      <template #footer>
        <el-button @click="terminalSetup = false">取消</el-button>
        <el-button type="danger" :loading="terminalCreating" @click="createTerminal">确认并连接</el-button>
      </template>
    </el-dialog>

    <RuntimeTerminalDrawer v-model="terminalDrawer" :title="terminalTitle" :session="terminalSession" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runtimeApi } from '../api/runtime'
import { useProjectRuntime } from '../composables/useProjectRuntime'
import type { RuntimeApplication, RuntimeExecSession, RuntimePod } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import EmptyState from '../components/common/EmptyState.vue'
import RuntimeEnvironmentGroup from '../components/runtime/RuntimeEnvironmentGroup.vue'
import RuntimeResourceDrawer from '../components/runtime/RuntimeResourceDrawer.vue'
import RuntimeTerminalDrawer from '../components/runtime/RuntimeTerminalDrawer.vue'
import { confirmationCopy, isProduction } from '../components/runtime/runtime-view-model'

const projectId = Number(useRoute().params.projectId)
const {
  overview, loading, refreshError, query, environment, status, autoRefresh,
  filteredEnvironments, refresh,
} = useProjectRuntime(projectId)
const emptySummary = { environments: 0, deployments: 0, healthy_pods: 0, unhealthy_pods: 0, restart_count: 0 }
const summary = computed(() => overview.value?.summary || emptySummary)
const resourceDrawer = ref(false)
const resourceTitle = ref('')
const resourceContent = ref('')
const resourceLoading = ref(false)
const terminalSetup = ref(false)
const terminalDrawer = ref(false)
const terminalCreating = ref(false)
const terminalContainer = ref('')
const terminalReason = ref('')
const terminalSession = ref<RuntimeExecSession>()
const terminalTarget = ref<{ environment: string; application: RuntimeApplication; pod: RuntimePod }>()
const terminalTitle = computed(() => terminalTarget.value
  ? `${terminalTarget.value.pod.name} · ${terminalContainer.value}` : 'Pod Terminal')

async function showResource(title: string, load: () => Promise<unknown>) {
  resourceTitle.value = title
  resourceContent.value = ''
  resourceDrawer.value = true
  resourceLoading.value = true
  try {
    const result = await load()
    resourceContent.value = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '资源读取失败')
    resourceDrawer.value = false
  } finally {
    resourceLoading.value = false
  }
}

function openDeploymentYaml(env: string, app: RuntimeApplication) {
  if (!app.deployment) return
  void showResource(`${app.deployment.name} · Deployment YAML`, () =>
    runtimeApi.deploymentYaml(projectId, app.application_id, env, app.deployment!.name))
}
function openPodLogs(env: string, app: RuntimeApplication, pod: RuntimePod) {
  void showResource(`${pod.name} · Logs`, async () => (
    await runtimeApi.podLogs(projectId, app.application_id, env, pod.name)
  ).logs)
}
function openPodYaml(env: string, app: RuntimeApplication, pod: RuntimePod) {
  void showResource(`${pod.name} · Pod YAML`, () =>
    runtimeApi.podYaml(projectId, app.application_id, env, pod.name))
}

async function restart(env: string, app: RuntimeApplication) {
  if (!app.deployment) return
  await ElMessageBox.confirm(
    confirmationCopy('restart', env, app.deployment.name),
    '确认 Runtime 操作',
    { type: isProduction(env) ? 'error' : 'warning', confirmButtonText: '确认重启' },
  )
  await runtimeApi.restartDeployment(projectId, app.application_id, env, app.deployment.name)
  ElMessage.success('Deployment 重启已提交')
  await refresh()
}

async function removePod(env: string, app: RuntimeApplication, pod: RuntimePod) {
  await ElMessageBox.confirm(
    confirmationCopy('delete-pod', env, pod.name),
    '确认 Runtime 操作',
    { type: 'error', confirmButtonText: '确认删除' },
  )
  await runtimeApi.deletePod(projectId, app.application_id, env, pod.name)
  ElMessage.success('Pod 删除已提交')
  await refresh()
}

function prepareTerminal(env: string, app: RuntimeApplication, pod: RuntimePod) {
  terminalTarget.value = { environment: env, application: app, pod }
  terminalContainer.value = pod.containers?.[0] || ''
  terminalReason.value = ''
  terminalSetup.value = true
}

async function createTerminal() {
  const target = terminalTarget.value
  if (!target || !terminalContainer.value || !terminalReason.value.trim()) {
    ElMessage.warning('请选择 Container 并填写操作原因')
    return
  }
  terminalCreating.value = true
  try {
    terminalSession.value = await runtimeApi.createExecSession(
      projectId,
      target.application.application_id,
      target.environment,
      target.pod.name,
      terminalContainer.value,
      terminalReason.value.trim(),
    )
    terminalSetup.value = false
    terminalDrawer.value = true
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '终端会话创建失败')
  } finally {
    terminalCreating.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.runtime-page :deep(.page-header) { margin-bottom: 4px; }
.runtime-metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.runtime-toolbar { display: grid; grid-template-columns: minmax(260px, 1fr) 170px 170px auto; align-items: center; gap: 12px; padding: 14px 16px; box-shadow: none; }
.runtime-toolbar > span { color: var(--muted); font-size: 12px; white-space: nowrap; }
.environment-list { display: grid; gap: 14px; }
@media (max-width: 1100px) { .runtime-metrics { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 760px) { .runtime-metrics { grid-template-columns: repeat(2, 1fr); } .runtime-toolbar { grid-template-columns: 1fr; } }
</style>
