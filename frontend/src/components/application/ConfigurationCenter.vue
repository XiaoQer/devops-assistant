<template>
  <div class="page-stack">
    <div class="section-head">
      <div>
        <h3>Configuration center</h3>
        <p>用版本化配置工作区来管理环境变量、Secret 和运行参数。</p>
      </div>
      <div class="section-actions">
        <el-select v-model="environmentId" style="width: 180px">
          <el-option v-for="env in environments" :key="env.id" :label="env.display_name || env.environment_name" :value="env.id" />
        </el-select>
        <el-button type="primary" :disabled="!environmentId" @click="openCreate">＋ 添加配置</el-button>
      </div>
    </div>

    <el-tabs v-model="type" class="config-tabs">
      <el-tab-pane v-for="tab in tabs" :key="tab.value" :label="tab.label" :name="tab.value" />
    </el-tabs>

    <section class="surface list-card">
      <div class="surface-header">
        <div>
          <h3>{{ activeLabel }}</h3>
          <p>{{ descriptions[type] }}</p>
        </div>
        <span>{{ configs.length }} items</span>
      </div>

      <el-skeleton :loading="loading" animated :rows="5">
        <div v-if="configs.length" class="config-list">
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
        <EmptyState v-else title="该环境暂无配置" description="添加第一条配置后，所有变更都会自动保留版本历史。" />
      </el-skeleton>
    </section>

    <section class="surface redeploy-card">
      <div>
        <span>↻</span>
        <div>
          <b>配置变更尚未应用？</b>
          <p>保存配置后可直接重新部署，让最新配置进入 Kubernetes 工作负载。</p>
        </div>
      </div>
      <el-button :loading="redeploying" @click="redeploy">重新部署</el-button>
    </section>

    <el-dialog v-model="dialog" :title="editing ? '编辑配置' : '添加配置'" width="640px">
      <el-form label-position="top">
        <el-form-item label="配置类型">
          <el-select v-model="form.config_type" :disabled="!!editing">
            <el-option v-for="tab in tabs" :key="tab.value" :label="tab.label" :value="tab.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="Key">
          <el-input v-model="form.config_key" :disabled="!!editing" placeholder="DATABASE_URL" />
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
import EmptyState from '../common/EmptyState.vue'

const props = defineProps<{ applicationId: number; projectId: number }>()
const environments = ref<ApplicationEnvironment[]>([])
const environmentId = ref(0)
const configs = ref<ApplicationConfig[]>([])
const loading = ref(false)
const saving = ref(false)
const redeploying = ref(false)
const dialog = ref(false)
const editing = ref<ApplicationConfig>()
const type = ref('env')
const tabs = [
  { label: 'Environment Variables', value: 'env' },
  { label: 'ConfigMap', value: 'configmap' },
  { label: 'Secret', value: 'secret' },
  { label: 'Resources', value: 'resource' },
  { label: 'Ingress', value: 'ingress' },
]

const descriptions: Record<string, string> = {
  env: '应用容器环境变量',
  configmap: '非敏感 Kubernetes 配置',
  secret: '加密存储的敏感信息',
  resource: 'CPU、Memory、Replica 与 Storage',
  ingress: '域名与流量入口配置',
}

const form = reactive({ config_type: 'env', config_key: '', value: '', change_message: '' })
const activeLabel = computed(() => tabs.find(tab => tab.value === type.value)?.label)

async function init() {
  environments.value = await applicationApi.environments(props.projectId, props.applicationId)
  environmentId.value = environments.value[0]?.id || 0
  load()
}

async function load() {
  if (!environmentId.value) return
  loading.value = true
  try {
    configs.value = await applicationApi.configs(props.projectId, props.applicationId, environmentId.value, type.value)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = undefined
  Object.assign(form, { config_type: type.value, config_key: '', value: '', change_message: '' })
  dialog.value = true
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
    if (editing.value) await applicationApi.updateConfig(props.projectId, editing.value.id, { value: form.value, change_message: form.change_message })
    else await applicationApi.saveConfig(props.projectId, props.applicationId, { ...form, environment_id: environmentId.value })
    ElMessage.success('配置新版本已保存')
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(item: ApplicationConfig) {
  await ElMessageBox.confirm(`确认删除 ${item.config_key}？历史版本仍会保留。`, '删除配置', { type: 'warning' })
  await applicationApi.deleteConfig(props.projectId, item.id)
  ElMessage.success('配置已删除')
  load()
}

async function redeploy() {
  redeploying.value = true
  try {
    const env = environments.value.find(item => item.id === environmentId.value)
    const result = await applicationApi.deploy(props.projectId, props.applicationId, { environment: env?.environment_name })
    ElMessage.success(result.approval_required ? '生产发布审批已提交' : '重新部署已启动')
  } finally {
    redeploying.value = false
  }
}

function format(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

watch([environmentId, type], load)
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

.list-card,
.redeploy-card {
  box-shadow: none;
}

.config-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.redeploy-card {
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.redeploy-card > div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.redeploy-card > div > span {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--primary-soft);
  color: var(--primary);
}

.redeploy-card b,
.redeploy-card p {
  display: block;
}

.redeploy-card p {
  margin: 6px 0 0;
  color: var(--muted);
}

@media (max-width: 1000px) {
  .section-head,
  .section-actions,
  .redeploy-card {
    flex-direction: column;
    align-items: stretch;
  }

  .config-card {
    grid-template-columns: 1fr;
  }

  .config-head {
    flex-direction: column;
  }
}
</style>
