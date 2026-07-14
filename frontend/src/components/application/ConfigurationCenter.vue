<template>
  <div class="page-stack">
    <div class="section-head">
      <div>
        <h3>配置中心</h3>
        <p>当前配置仅作用于所选环境，变更会保留版本历史并在发布时注入 Kubernetes 工作负载。</p>
      </div>
      <div class="section-actions">
        <el-select v-model="environmentId" style="width: 180px">
          <el-option v-for="env in environments" :key="env.id" :label="`${env.display_name || env.environment_name} · ${env.namespace}`" :value="env.id" />
        </el-select>
        <el-button v-if="type !== 'env'" type="primary" :disabled="!environmentId" @click="openCreate">＋ 添加配置</el-button>
      </div>
    </div>

    <el-tabs v-model="type" class="config-tabs">
      <el-tab-pane v-for="tab in tabs" :key="tab.value" :label="tab.label" :name="tab.value" :disabled="tab.disabled" />
    </el-tabs>

    <section class="surface list-card">
      <div class="surface-header">
        <div>
          <h3>{{ activeLabel }}</h3>
          <p>{{ selectedEnvironmentLabel }} · {{ descriptions[type] }}</p>
        </div>
        <span>{{ configs.length }} items</span>
      </div>

      <div v-if="type === 'env'" class="env-editor">
        <div class="env-editor-head">
          <span>KEY</span>
          <span>VALUE</span>
          <span>操作</span>
        </div>
        <div class="env-editor-add">
          <el-input v-model="inlineKey" placeholder="例如 DATABASE_URL" />
          <el-input v-model="inlineValue" placeholder="输入环境变量值" />
          <el-button type="primary" :loading="savingInline" :disabled="!environmentId || !inlineKey.trim()" @click="addInline">添加变量</el-button>
        </div>
      </div>

      <el-skeleton :loading="loading" animated :rows="5">
        <div v-if="configs.length && type !== 'env'" class="config-list">
          <article v-for="row in configs" :key="row.id" class="config-card">
            <div class="config-main">
              <div class="config-head">
                <div>
                  <h4>{{ row.config_key }}</h4>
                  <p>
                    <span class="soft-pill">v{{ row.version }}</span>
                    <span class="soft-pill">{{ row.changed_by }}</span>
                    <span v-if="row.is_secret" class="soft-pill warning-pill">Encrypted</span>
                  </p>
                </div>
                <span class="config-date">{{ format(row.created_at) }}</span>
              </div>
              <pre class="code-block config-value" :class="{ masked: row.is_secret }">{{ row.value }}</pre>
            </div>
            <div class="config-actions">
              <el-button @click="edit(row)">编辑</el-button>
              <el-button @click="remove(row)">删除</el-button>
            </div>
          </article>
        </div>
        <div v-else-if="configs.length && type === 'env'" class="env-list">
          <div v-for="row in configs" :key="row.id" class="env-row">
            <el-input :model-value="row.config_key" disabled />
            <el-input v-model="row.value" type="text" placeholder="输入变量值" />
            <div class="env-row-actions">
              <el-button size="small" type="primary" :loading="savingInlineId === row.id" :disabled="!inlineChanged(row)" @click="saveInline(row)">保存</el-button>
              <el-button size="small" @click="remove(row)">删除</el-button>
            </div>
          </div>
        </div>
        <div v-else class="config-empty">
          <span>◇</span>
          <div>
            <strong>该环境暂无配置</strong>
            <p>添加第一条配置后，变更会保留版本历史。</p>
          </div>
        </div>
      </el-skeleton>
    </section>

    <el-dialog v-model="dialog" :title="editing ? '编辑配置' : '添加配置'" width="640px">
      <el-form label-position="top">
        <el-form-item label="配置类型">
          <el-select v-model="form.config_type" :disabled="!!editing">
            <el-option v-for="tab in tabs" :key="tab.value" :label="tab.label" :value="tab.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="Key">
          <el-select v-if="form.config_type === 'resource'" v-model="form.config_key" :disabled="!!editing" placeholder="选择资源参数">
            <el-option v-for="key in resourceKeys" :key="key.value" :label="key.label" :value="key.value" />
          </el-select>
          <el-select v-else-if="form.config_type === 'ingress'" v-model="form.config_key" :disabled="!!editing" placeholder="选择 Ingress 参数">
            <el-option v-for="key in ingressKeys" :key="key.value" :label="key.label" :value="key.value" />
          </el-select>
          <el-input v-else v-model="form.config_key" :disabled="!!editing" placeholder="DATABASE_URL" />
        </el-form-item>
        <el-form-item label="Value">
          <el-input v-model="form.value" type="textarea" :rows="8" :placeholder="form.config_type === 'secret' ? '输入新密文值' : '输入配置值'" />
        </el-form-item>
        <el-form-item label="变更说明">
          <el-input v-model="form.change_message" placeholder="说明本次变更原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存新版本</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { applicationApi } from '../../api/application'
import type { ApplicationConfig, ApplicationEnvironment } from '../../types'

const props = defineProps<{ applicationId: number; projectId: number; initialEnvironmentId?: number }>()
const environments = ref<ApplicationEnvironment[]>([])
const environmentId = ref(0)
const configs = ref<ApplicationConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<ApplicationConfig>()
const savingInline = ref(false)
const savingInlineId = ref(0)
const inlineKey = ref('')
const inlineValue = ref('')
const inlineOriginalValues = ref<Record<number, string>>({})
const type = ref('env')
const tabs = [
  { label: '环境变量', value: 'env', disabled: false },
  { label: 'ConfigMap', value: 'configmap', disabled: true },
  { label: 'Secret', value: 'secret', disabled: true },
  { label: '资源参数', value: 'resource', disabled: true },
  { label: 'Ingress', value: 'ingress', disabled: true },
]

const descriptions: Record<string, string> = {
  env: '应用容器环境变量',
  configmap: '非敏感 Kubernetes 配置',
  secret: '加密存储的敏感信息',
  resource: 'CPU、Memory、Replica 与 Storage',
  ingress: '域名与流量入口配置',
}

const resourceKeys = [
  { label: '副本数', value: 'replicas' },
  { label: 'CPU Request', value: 'cpu_request' },
  { label: 'CPU Limit', value: 'cpu_limit' },
  { label: 'Memory Request', value: 'memory_request' },
  { label: 'Memory Limit', value: 'memory_limit' },
  { label: 'Storage Size', value: 'storage_size' },
  { label: '发布策略', value: 'deploy_strategy' },
  { label: 'Max Unavailable', value: 'max_unavailable' },
  { label: 'Max Surge', value: 'max_surge' },
]

const ingressKeys = [
  { label: '域名 Host', value: 'host' },
  { label: '路径 Path', value: 'path' },
  { label: 'Service Port', value: 'service_port' },
]

const form = reactive({ config_type: 'env', config_key: '', value: '', change_message: '' })
const activeLabel = computed(() => tabs.find(tab => tab.value === type.value)?.label)
const selectedEnvironmentLabel = computed(() => {
  const env = environments.value.find(item => item.id === environmentId.value)
  return env ? `当前环境：${env.display_name || env.environment_name}` : '尚未选择环境'
})

async function init() {
  environments.value = await applicationApi.environments(props.projectId, props.applicationId)
  environmentId.value = props.initialEnvironmentId && environments.value.some(item => item.id === props.initialEnvironmentId)
    ? props.initialEnvironmentId
    : environments.value[0]?.id || 0
  load()
}

async function load() {
  if (!environmentId.value) return
  loading.value = true
  try {
    configs.value = await applicationApi.configs(props.projectId, props.applicationId, environmentId.value, type.value)
    if (type.value === 'env') {
      inlineOriginalValues.value = Object.fromEntries(configs.value.map(item => [item.id, item.value]))
    }
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = undefined
  Object.assign(form, { config_type: type.value, config_key: '', value: '', change_message: '' })
  dialog.value = true
}

async function addInline() {
  const key = inlineKey.value.trim()
  if (!key) return ElMessage.warning('请输入变量名')
  if (!environmentId.value) return ElMessage.warning('请先选择环境')
  if (configs.value.some(item => item.config_key === key)) return ElMessage.warning(`变量 ${key} 已存在，请直接修改原变量`)
  savingInline.value = true
  try {
    await applicationApi.saveConfig(props.projectId, props.applicationId, {
      config_type: 'env',
      config_key: key,
      value: inlineValue.value,
      environment_id: environmentId.value,
      change_message: '新增环境变量',
    })
    inlineKey.value = ''
    inlineValue.value = ''
    ElMessage.success('环境变量已添加')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '环境变量添加失败')
  } finally {
    savingInline.value = false
  }
}

async function saveInline(item: ApplicationConfig) {
  if (!inlineChanged(item)) return
  savingInlineId.value = item.id
  try {
    await applicationApi.updateConfig(props.projectId, props.applicationId, item.id, {
      value: item.value,
      change_message: '更新环境变量',
    })
    ElMessage.success(`${item.config_key} 已保存`)
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '环境变量保存失败')
  } finally {
    savingInlineId.value = 0
  }
}

function inlineChanged(item: ApplicationConfig) {
  return item.value !== inlineOriginalValues.value[item.id]
}

function edit(item: ApplicationConfig) {
  editing.value = item
  Object.assign(form, {
    config_type: item.config_type,
    config_key: item.config_key,
    value: item.is_secret ? '' : item.value,
    change_message: '',
  })
  dialog.value = true
}

async function save() {
  if (!form.config_key) return ElMessage.warning('请输入配置 Key')
  saving.value = true
  try {
    if (editing.value) await applicationApi.updateConfig(props.projectId, props.applicationId, editing.value.id, { value: form.value, change_message: form.change_message })
    else await applicationApi.saveConfig(props.projectId, props.applicationId, { ...form, environment_id: environmentId.value })
    ElMessage.success('配置新版本已保存')
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(item: ApplicationConfig) {
  await ElMessageBox.confirm(`确认删除 ${item.config_key}？历史版本仍会保留。`, '删除配置', {
    type: 'warning',
    customClass: 'light-confirm-box',
  })
  await applicationApi.deleteConfig(props.projectId, props.applicationId, item.id)
  ElMessage.success('配置已删除')
  load()
}

function format(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

watch([environmentId, type], load)
watch(() => props.initialEnvironmentId, value => {
  if (value && environments.value.some(item => item.id === value)) environmentId.value = value
})
onMounted(init)
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

.config-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.config-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: #e4e9f1;
}

.config-tabs :deep(.el-tabs__item) {
  height: 42px;
  padding: 0 18px;
  color: #53627a !important;
  font-size: 13px;
  font-weight: 600;
}

.config-tabs :deep(.el-tabs__item.is-active) {
  color: #2563eb !important;
}

.config-tabs :deep(.el-tabs__item.is-disabled) {
  color: #aeb8c7 !important;
  cursor: not-allowed;
  opacity: .75;
}

.list-card {
  box-shadow: none;
}

.config-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.env-editor {
  padding: 14px 20px 0;
}

.env-editor-head,
.env-editor-add,
.env-row {
  display: grid;
  grid-template-columns: minmax(150px, 0.8fr) minmax(240px, 1.5fr) 150px;
  gap: 10px;
  align-items: center;
}

.env-editor-head {
  padding: 0 12px 8px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.env-editor-add {
  padding: 12px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: var(--surface-soft);
}

.env-list {
  display: grid;
  gap: 8px;
  padding: 12px 20px 20px;
}

.env-row {
  padding: 10px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: var(--surface-soft);
}

.env-row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}

.config-empty {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 12px 20px 20px;
  padding: 18px 20px;
  border: 1px dashed #d8e0eb;
  border-radius: 12px;
  background: #f8fafc;
}

.config-empty > span {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border-radius: 10px;
  background: #eaf0ff;
  color: #2563eb;
  font-size: 17px;
}

.config-empty strong {
  display: block;
  color: #172033;
  font-size: 14px;
}

.config-empty p {
  margin: 4px 0 0;
  color: #7b879b;
  font-size: 12px;
}

.config-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 16px;
  padding: 18px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.el-dialog :deep(.el-form-item) {
  margin-bottom: 14px;
}

.el-dialog :deep(.el-input__wrapper),
.el-dialog :deep(.el-select__wrapper) {
  width: 100%;
}

.config-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.config-head h4 {
  margin: 0 0 10px;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.config-head p {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
}

.config-date {
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.config-value {
  margin-top: 14px;
  min-height: 92px;
}

.config-value.masked {
  letter-spacing: 2px;
}

.warning-pill {
  color: var(--warning);
}

.config-actions {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

@media (max-width: 1000px) {
  .section-head,
  .section-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .config-card {
    grid-template-columns: 1fr;
  }

  .config-head {
    flex-direction: column;
  }

  .env-editor-head {
    display: none;
  }

  .env-editor-add,
  .env-row {
    grid-template-columns: 1fr;
  }

  .env-row-actions {
    justify-content: flex-start;
  }
}
</style>
