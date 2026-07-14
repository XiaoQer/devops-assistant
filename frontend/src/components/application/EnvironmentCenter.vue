<template>
  <div class="page-stack">
    <div class="section-head">
      <div>
        <h3>Environment center</h3>
        <p>把环境配置展示成交付能力卡片，而不是一组分散的基础字段。</p>
      </div>
      <div class="section-actions">
        <el-button @click="openCompare" :disabled="environments.length < 2">环境对比</el-button>
        <el-button type="primary" @click="openCreate">＋ 新建环境</el-button>
      </div>
    </div>

    <el-skeleton :loading="loading" animated :rows="6">
      <div class="env-grid">
        <article v-for="env in environments" :key="env.id" class="surface env-card">
          <header>
            <div class="env-identify">
              <span class="env-icon" :class="env.environment_name">{{ env.environment_name.slice(0, 2).toUpperCase() }}</span>
              <div>
                <h4>{{ env.display_name || env.environment_name }}</h4>
                <small>{{ env.cluster_name }} / {{ env.namespace }}</small>
              </div>
            </div>
            <StatusBadge :status="env.status" />
          </header>

          <div class="env-pills">
            <span class="soft-pill">{{ env.deploy_strategy }}</span>
            <span class="soft-pill">{{ env.replicas }} replicas</span>
            <span class="soft-pill">{{ env.approval_required ? 'Needs approval' : 'Direct delivery' }}</span>
          </div>

          <dl>
            <div>
              <dt>CPU</dt>
              <dd>{{ env.cpu_request }} / {{ env.cpu_limit }}</dd>
            </div>
            <div>
              <dt>Memory</dt>
              <dd>{{ env.memory_request }} / {{ env.memory_limit }}</dd>
            </div>
            <div>
              <dt>Ingress</dt>
              <dd>{{ env.ingress_domain || 'Not configured' }}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{{ formatTime(env.updated_at) }}</dd>
            </div>
          </dl>

          <footer>
            <el-button @click="edit(env)">编辑</el-button>
            <el-button @click="clone(env)">克隆</el-button>
            <el-dropdown trigger="click">
              <el-button>更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="exportConfig(env)">导出配置</el-dropdown-item>
                  <el-dropdown-item divided :disabled="env.environment_name === 'prod'" @click="remove(env)">删除环境</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </footer>
        </article>
      </div>

      <EmptyState v-if="!environments.length && !loading" title="还没有环境" description="先创建 dev、staging 或 prod 环境，让交付策略与运行配置开始具备结构化表达。" />
    </el-skeleton>

    <el-dialog v-model="dialog" :title="editing?.id ? '编辑环境' : '新建环境'" width="720px">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="环境标识"><el-input v-model="form.environment_name" :disabled="!!editing?.id" placeholder="qa" /></el-form-item>
          <el-form-item label="显示名称"><el-input v-model="form.display_name" placeholder="QA" /></el-form-item>
            <el-form-item label="Kubernetes 集群">
              <el-select v-model="form.kubernetes_cluster_id" clearable placeholder="选择部署集群">
                <el-option v-for="cluster in clusters" :key="cluster.id" :label="cluster.name" :value="cluster.id" />
              </el-select>
            </el-form-item>
          <el-form-item label="Kubernetes Namespace"><el-input v-model="form.namespace" /></el-form-item>
          <el-form-item label="副本数"><el-input-number v-model="form.replicas" :min="1" :max="100" /></el-form-item>
          <el-form-item label="CPU Request / Limit"><div class="inline"><el-input v-model="form.cpu_request" /><el-input v-model="form.cpu_limit" /></div></el-form-item>
          <el-form-item label="Memory Request / Limit"><div class="inline"><el-input v-model="form.memory_request" /><el-input v-model="form.memory_limit" /></div></el-form-item>
          <el-form-item class="wide" label="Ingress Domain"><el-input v-model="form.ingress_domain" /></el-form-item>
          <el-form-item label="发布策略"><el-select v-model="form.deploy_strategy"><el-option v-for="strategy in strategies" :key="strategy" :label="strategy" :value="strategy" /></el-select></el-form-item>
          <el-form-item label="生产审批"><el-switch v-model="form.approval_required" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="compareDialog" title="环境配置对比" width="860px">
      <div class="compare-picker">
        <el-select v-model="compareLeft"><el-option v-for="env in environments" :key="env.id" :label="env.display_name || env.environment_name" :value="env.id" /></el-select>
        <span>vs</span>
        <el-select v-model="compareRight"><el-option v-for="env in environments" :key="env.id" :label="env.display_name || env.environment_name" :value="env.id" /></el-select>
        <el-button @click="compare">对比</el-button>
      </div>
      <div class="diff-list">
        <article v-for="row in differences" :key="row.field" class="diff-item" :class="{ changed: row.changed }">
          <div>
            <strong>{{ row.field }}</strong>
            <small>{{ row.changed ? 'Changed' : 'Same' }}</small>
          </div>
          <code>{{ display(row.left) }}</code>
          <code>{{ display(row.right) }}</code>
        </article>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { applicationApi } from '../../api/application'
import { projectApi } from '../../api/project'
import type { ApplicationEnvironment, KubernetesCluster } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'

const props = defineProps<{ applicationId: number; projectId: number }>()
const environments = ref<ApplicationEnvironment[]>([])
const clusters = ref<KubernetesCluster[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<ApplicationEnvironment>()
const compareDialog = ref(false)
const compareLeft = ref(0)
const compareRight = ref(0)
const differences = ref<Array<{ field: string; left: unknown; right: unknown; changed: boolean }>>([])
const strategies = ['RollingUpdate', 'Recreate']

const defaults = {
  environment_name: '',
  display_name: '',
  kubernetes_cluster_id: undefined,
  namespace: '',
  replicas: 1,
  cpu_request: '100m',
  cpu_limit: '500m',
  memory_request: '128Mi',
  memory_limit: '512Mi',
  ingress_domain: '',
  deploy_strategy: 'RollingUpdate',
  approval_required: false,
}

const form = reactive({ ...defaults })

function formatTime(value: string) {
  return new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    const [environmentItems, clusterItems] = await Promise.all([
      applicationApi.environments(props.projectId, props.applicationId),
      props.projectId ? projectApi.clusters(props.projectId) : Promise.resolve([]),
    ])
    environments.value = environmentItems
    clusters.value = clusterItems
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = undefined
  Object.assign(form, defaults)
  dialog.value = true
}

function edit(env: ApplicationEnvironment) {
  editing.value = env
  Object.assign(form, env)
  dialog.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) await applicationApi.updateEnvironment(props.projectId, props.applicationId, editing.value.id, form)
    else await applicationApi.createEnvironment(props.projectId, props.applicationId, form)
    ElMessage.success('环境配置已保存')
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function clone(env: ApplicationEnvironment) {
  const { value } = await ElMessageBox.prompt('输入新环境标识，例如 qa', '克隆环境', {
    inputPattern: /^[a-z][a-z0-9-]*$/,
    inputErrorMessage: '仅支持小写字母、数字和连字符',
  })
  await applicationApi.cloneEnvironment(props.projectId, props.applicationId, env.id, value)
  ElMessage.success('环境已克隆')
  load()
}

async function remove(env: ApplicationEnvironment) {
  await ElMessageBox.confirm(`确认删除 ${env.display_name || env.environment_name}？该操作不会删除 Kubernetes 工作负载。`, '危险操作', { type: 'warning' })
  await applicationApi.deleteEnvironment(props.projectId, props.applicationId, env.id)
  ElMessage.success('环境已删除')
  load()
}

function exportConfig(env: ApplicationEnvironment) {
  const blob = new Blob([JSON.stringify(env, null, 2)], { type: 'application/json' })
  const anchor = document.createElement('a')
  anchor.href = URL.createObjectURL(blob)
  anchor.download = `${env.environment_name}-environment.json`
  anchor.click()
  URL.revokeObjectURL(anchor.href)
}

function openCompare() {
  compareLeft.value = environments.value[0]?.id || 0
  compareRight.value = environments.value[1]?.id || 0
  compareDialog.value = true
  compare()
}

async function compare() {
  if (compareLeft.value && compareRight.value) {
    differences.value = await applicationApi.compareEnvironments(props.projectId, props.applicationId, compareLeft.value, compareRight.value)
  }
}

function display(value: unknown) {
  return typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')
}

onMounted(load)
</script>

<style scoped>
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
}

.section-head h3 {
  margin: 0 0 8px;
  font-size: 22px;
  letter-spacing: -0.03em;
}

.section-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.section-actions {
  display: flex;
  gap: 10px;
}

.env-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.env-card {
  padding: 22px;
  box-shadow: none;
}

.env-card header,
.env-identify,
.env-pills,
.env-card footer {
  display: flex;
  align-items: center;
}

.env-card header {
  justify-content: space-between;
  gap: 12px;
}

.env-identify {
  gap: 12px;
}

.env-icon {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(37, 99, 235, 0.12);
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
}

.env-icon.prod {
  background: rgba(220, 38, 38, 0.12);
  color: var(--danger);
}

.env-icon.staging {
  background: rgba(217, 119, 6, 0.12);
  color: var(--warning);
}

.env-card h4 {
  margin: 0 0 4px;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.env-card small {
  color: var(--muted);
}

.env-pills {
  flex-wrap: wrap;
  gap: 8px;
  margin: 18px 0;
}

.env-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 0;
  padding: 18px 0;
  border-top: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.env-card dt {
  margin-bottom: 6px;
  color: var(--muted);
  font-size: 12px;
}

.env-card dd {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  word-break: break-word;
}

.env-card footer {
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.form-grid .wide {
  grid-column: 1 / -1;
}

.inline {
  display: flex;
  gap: 8px;
}

.compare-picker {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.compare-picker .el-select {
  flex: 1;
}

.diff-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.diff-item {
  display: grid;
  grid-template-columns: 180px 1fr 1fr;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.diff-item.changed {
  border-color: rgba(37, 99, 235, 0.18);
  background: rgba(37, 99, 235, 0.04);
}

.diff-item strong,
.diff-item small {
  display: block;
}

.diff-item small {
  margin-top: 6px;
  color: var(--muted);
}

.diff-item code {
  padding: 12px;
  border-radius: 12px;
  background: var(--theme-panel);
  border: 1px solid var(--border-soft);
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1000px) {
  .env-grid,
  .form-grid,
  .env-card dl,
  .diff-item {
    grid-template-columns: 1fr;
  }

  .section-head,
  .section-actions,
  .compare-picker {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
