<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Project resources"
      :title="project ? `${project.name} · Kubernetes` : 'Kubernetes'"
      description="维护当前 Project 可用的 Kubernetes 集群、环境标签和连接状态。"
    >
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="primary" @click="openAddDialog">＋ 添加集群</el-button>
    </PageHeader>

    <section class="surface panel-card">
      <div class="surface-header">
        <div>
          <h3>Kubernetes clusters</h3>
          <p>集群凭据加密保存；Application Environment 后续从这里选择部署目标。</p>
        </div>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <div v-if="clusters.length" class="cluster-grid">
          <article v-for="cluster in clusters" :key="cluster.id" class="cluster-card">
            <div class="cluster-head">
              <div>
                <div class="cluster-title-line">
                  <h4>{{ cluster.name }}</h4>
                  <span class="environment-pill">{{ cluster.environment_label || '未标注环境' }}</span>
                </div>
                <p>{{ cluster.kube_context }}</p>
              </div>
              <span v-if="cluster.is_default" class="soft-pill">Default</span>
            </div>
            <div class="cluster-meta">
              <span class="soft-pill" :class="`connection-${cluster.connection_status}`">
                {{ connectionStatusLabel(cluster.connection_status) }}
              </span>
              <span class="soft-pill">{{ cluster.namespace_prefix || 'no namespace prefix' }}</span>
              <span class="soft-pill">{{ cluster.is_active ? 'Active' : 'Disabled' }}</span>
              <span v-if="cluster.kubernetes_version" class="soft-pill">
                {{ cluster.kubernetes_version }}
              </span>
            </div>
            <div class="connection-details">
              <span>{{ cluster.api_server || '尚未通过连接测试发现 API Server' }}</span>
              <span v-if="cluster.last_checked_at">
                最近测试：{{ formatDateTime(cluster.last_checked_at) }}
              </span>
            </div>
            <p v-if="cluster.description" class="cluster-description">{{ cluster.description }}</p>
            <div class="cluster-actions">
              <el-button
                :loading="testingClusterId === cluster.id"
                @click="testSavedConnection(cluster.id)"
              >
                测试连接
              </el-button>
              <el-button v-if="!cluster.is_default" @click="setDefaultCluster(cluster.id)">设为默认</el-button>
              <el-button @click="openEditDialog(cluster)">编辑</el-button>
              <el-button @click="removeCluster(cluster)">删除</el-button>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="还没有 Kubernetes 集群"
          description="添加已有集群并测试连接后，环境才能显式绑定部署目标。"
        />
      </el-skeleton>
    </section>

    <el-dialog
      v-model="dialog"
      :title="dialogTitle"
      width="680px"
      class="governance-form-dialog"
      custom-class="governance-form-dialog"
      modal-class="governance-form-overlay"
      @closed="clearSensitiveForm"
    >
      <div v-if="dialogStep === 'choice'" class="onboarding-choice">
        <button class="choice-card unavailable" type="button" disabled>
          <span class="choice-icon">☁</span>
          <span class="choice-copy">
            <span class="choice-title-line">
              <strong>初始化新 Kubernetes 集群</strong>
              <span class="coming-soon">即将支持</span>
            </span>
            <small>后续将使用当前 Project 的 Aliyun 账号、区域、VPC 和资源组自动初始化 ACK 集群。</small>
          </span>
        </button>
        <button class="choice-card" type="button" @click="chooseExistingCluster">
          <span class="choice-icon">☸</span>
          <span class="choice-copy">
            <strong>添加已有集群</strong>
            <small>粘贴完整 kubeconfig，选择环境标签和 context，并在保存前测试连接。</small>
          </span>
          <span class="choice-arrow">→</span>
        </button>
      </div>

      <el-form v-else label-position="top">
        <section class="form-section">
          <div class="section-title">
            <h4>集群信息</h4>
            <p>kubeconfig 仅用于加密保存和创建该集群的独立 Kubernetes 客户端。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="名称" required>
              <el-input v-model="form.name" placeholder="例如 payments-prod" />
            </el-form-item>
            <el-form-item label="环境标签" required>
              <el-select
                v-model="form.environment_label"
                allow-create
                filterable
                default-first-option
                placeholder="选择或输入环境标签"
              >
                <el-option v-for="label in environmentLabels" :key="label" :label="label" :value="label" />
              </el-select>
            </el-form-item>
            <el-form-item class="wide" :label="editing ? '替换 kubeconfig（留空保留）' : '完整 kubeconfig'" required>
              <el-input
                v-model="form.kubeconfig"
                type="textarea"
                :rows="9"
                spellcheck="false"
                placeholder="粘贴 kubeconfig YAML；不会在编辑时回显"
                @input="parseContexts"
              />
            </el-form-item>
            <el-form-item label="Kube Context" required>
              <el-select v-model="form.kube_context" filterable placeholder="选择 context">
                <el-option v-for="context in contextOptions" :key="context" :label="context" :value="context" />
              </el-select>
            </el-form-item>
            <el-form-item label="Namespace Prefix">
              <el-input v-model="form.namespace_prefix" placeholder="例如 payments" />
            </el-form-item>
            <el-form-item class="wide" label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="默认集群">
              <el-switch v-model="form.is_default" />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </div>
        </section>

        <el-alert
          v-if="transientTestResult"
          :type="transientTestResult.connected ? 'success' : 'warning'"
          :title="transientTestResult.message"
          :closable="false"
          show-icon
        >
          <template #default>
            <span v-if="transientTestResult.api_server">{{ transientTestResult.api_server }}</span>
            <span v-if="transientTestResult.kubernetes_version">
              · {{ transientTestResult.kubernetes_version }}
            </span>
          </template>
        </el-alert>
      </el-form>

      <template #footer>
        <template v-if="dialogStep === 'choice'">
          <el-button @click="dialog = false">取消</el-button>
        </template>
        <template v-else>
          <el-button v-if="!editing" @click="dialogStep = 'choice'">返回</el-button>
          <el-button @click="dialog = false">取消</el-button>
          <el-button :loading="testing" :disabled="!form.kubeconfig?.trim()" @click="testFormConnection">
            测试连接
          </el-button>
          <el-button type="primary" :loading="saving" @click="saveCluster">保存</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { load } from 'js-yaml'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { projectApi } from '../api/project'
import { useProjectStore } from '../stores/project'
import type {
  ClusterConnectionResult,
  ClusterConnectionStatus,
  ClusterPayload,
  KubernetesCluster,
  Project,
} from '../types'

interface KubeconfigSummary {
  contexts?: Array<{ name?: string }>
  'current-context'?: string
}

const route = useRoute()
const projectStore = useProjectStore()
const project = ref<Project>()
const clusters = ref<KubernetesCluster[]>([])
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testingClusterId = ref<number>()
const dialog = ref(false)
const dialogStep = ref<'choice' | 'existing'>('choice')
const editing = ref<KubernetesCluster>()
const contextOptions = ref<string[]>([])
const transientTestResult = ref<ClusterConnectionResult>()
const projectId = computed(() => Number(route.params.id))
const environmentLabels = ['development', 'testing', 'staging', 'production']

const defaults: ClusterPayload = {
  name: '',
  environment_label: 'development',
  kube_context: '',
  kubeconfig: '',
  namespace_prefix: '',
  description: '',
  is_default: false,
  is_active: true,
}
const form = reactive<ClusterPayload>({ ...defaults })
const dialogTitle = computed(() => {
  if (editing.value) return '编辑集群'
  return dialogStep.value === 'choice' ? '添加 Kubernetes 集群' : '添加已有集群'
})

async function refresh() {
  loading.value = true
  try {
    const [projectData, clusterItems] = await Promise.all([
      projectApi.get(projectId.value),
      projectApi.clusters(projectId.value),
    ])
    project.value = projectData
    clusters.value = clusterItems
    projectStore.setActiveProject(projectId.value)
    await projectStore.load()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  editing.value = undefined
  Object.assign(form, defaults)
  contextOptions.value = []
  transientTestResult.value = undefined
  dialogStep.value = 'choice'
  dialog.value = true
}

function chooseExistingCluster() {
  dialogStep.value = 'existing'
}

function openEditDialog(item: KubernetesCluster) {
  editing.value = item
  Object.assign(form, {
    name: item.name,
    environment_label: item.environment_label || 'development',
    kube_context: item.kube_context,
    kubeconfig: '',
    namespace_prefix: item.namespace_prefix || '',
    description: item.description || '',
    is_default: item.is_default,
    is_active: item.is_active,
  })
  contextOptions.value = [item.kube_context]
  transientTestResult.value = undefined
  dialogStep.value = 'existing'
  dialog.value = true
}

function parseContexts(value: string) {
  contextOptions.value = []
  transientTestResult.value = undefined
  if (!value.trim()) {
    if (editing.value) {
      contextOptions.value = [editing.value.kube_context]
      form.kube_context = editing.value.kube_context
    }
    return
  }
  try {
    const parsed = load(value) as KubeconfigSummary
    const names = (parsed?.contexts || [])
      .map(item => item.name?.trim())
      .filter((name): name is string => Boolean(name))
    contextOptions.value = [...new Set(names)]
    const current = parsed?.['current-context']
    form.kube_context = current && names.includes(current) ? current : names[0] || ''
  } catch {
    form.kube_context = ''
    ElMessage.warning('无法解析 kubeconfig')
  }
}

async function testFormConnection() {
  if (!form.kubeconfig?.trim() || !form.kube_context) {
    ElMessage.warning('请粘贴 kubeconfig 并选择 context')
    return
  }
  testing.value = true
  try {
    transientTestResult.value = await projectApi.testClusterConnection(projectId.value, {
      kubeconfig: form.kubeconfig,
      kube_context: form.kube_context,
    })
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    testing.value = false
  }
}

async function testSavedConnection(clusterId: number) {
  testingClusterId.value = clusterId
  try {
    const result = await projectApi.testSavedClusterConnection(projectId.value, clusterId)
    result.connected ? ElMessage.success(result.message) : ElMessage.warning(result.message)
    await refresh()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    testingClusterId.value = undefined
  }
}

async function saveCluster() {
  if (!form.name.trim() || !form.environment_label.trim() || !form.kube_context.trim()) {
    ElMessage.warning('请填写名称、环境标签并选择 kube context')
    return
  }
  if (!editing.value && !form.kubeconfig?.trim()) {
    ElMessage.warning('请粘贴完整 kubeconfig')
    return
  }
  saving.value = true
  try {
    const payload: ClusterPayload = { ...form }
    if (editing.value && !payload.kubeconfig?.trim()) delete payload.kubeconfig
    if (editing.value) {
      await projectApi.updateCluster(projectId.value, editing.value.id, payload)
    } else {
      await projectApi.addCluster(projectId.value, payload)
    }
    dialog.value = false
    await refresh()
    ElMessage.success('Kubernetes 集群已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
}

function clearSensitiveForm() {
  form.kubeconfig = ''
  contextOptions.value = []
  transientTestResult.value = undefined
  editing.value = undefined
}

function connectionStatusLabel(status: ClusterConnectionStatus) {
  return {
    untested: '未测试',
    connected: '已连接',
    failed: '连接失败',
  }[status]
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString()
}

async function setDefaultCluster(clusterId: number) {
  await projectApi.setDefaultCluster(projectId.value, clusterId)
  ElMessage.success('默认集群已更新')
  await refresh()
}

async function removeCluster(item: KubernetesCluster) {
  await ElMessageBox.confirm(`确认删除集群 ${item.name}？`, '提示', { type: 'warning' })
  await projectApi.removeCluster(projectId.value, item.id)
  ElMessage.success('集群已删除')
  await refresh()
}

onMounted(async () => {
  projectStore.init()
  await refresh()
})
</script>

<style scoped>
.panel-card {
  box-shadow: none;
}

.cluster-grid {
  display: grid;
  gap: 12px;
  padding: 16px 24px 24px;
}

.cluster-card {
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--surface-soft);
}

.cluster-head,
.cluster-title-line,
.choice-title-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cluster-title-line {
  justify-content: flex-start;
}

.cluster-head h4 {
  margin: 0;
  font-size: 18px;
}

.cluster-head p,
.cluster-description,
.connection-details {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.environment-pill,
.coming-soon {
  padding: 3px 8px;
  border-radius: 999px;
  color: #1d4ed8;
  background: #dbeafe;
  font-size: 12px;
  font-weight: 700;
}

.cluster-meta,
.cluster-actions,
.connection-details {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.cluster-meta {
  margin: 14px 0;
}

.cluster-actions {
  margin-top: 14px;
}

.connection-connected {
  color: #047857;
  background: #d1fae5;
}

.connection-failed {
  color: #b45309;
  background: #fef3c7;
}

.onboarding-choice {
  display: grid;
  gap: 14px;
  padding: 4px 0 10px;
}

.choice-card {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  color: var(--text);
  background: var(--surface-soft);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.choice-card:not(:disabled):hover {
  border-color: #93c5fd;
  transform: translateY(-1px);
}

.choice-card.unavailable {
  cursor: not-allowed;
  opacity: 0.7;
}

.choice-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border-radius: 12px;
  color: #1d4ed8;
  background: #dbeafe;
  font-size: 21px;
}

.choice-copy {
  display: grid;
  flex: 1;
  gap: 7px;
}

.choice-copy strong {
  font-size: 16px;
}

.choice-copy small {
  color: var(--muted);
  line-height: 1.6;
}

.choice-arrow {
  color: #2563eb;
  font-size: 22px;
}

@media (max-width: 720px) {
  .cluster-head,
  .choice-title-line {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
