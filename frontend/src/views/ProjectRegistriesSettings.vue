<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Project resources"
      :title="project ? `${project.name} · Registries` : 'Registries'"
      description="配置当前 Project 的镜像仓库凭据，并验证 OCI Registry 连接。"
    >
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="primary" @click="openDialog()">＋ 添加 Registry</el-button>
    </PageHeader>

    <section class="surface panel-card">
      <div class="surface-header">
        <div>
          <h3>Container registries</h3>
          <p>应用继承当前 Project 的默认 Registry；Token 加密保存且不会回显。</p>
        </div>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <div v-if="registries.length" class="registry-grid">
          <article v-for="registry in registries" :key="registry.id" class="registry-card">
            <div class="registry-head">
              <div>
                <div class="title-line">
                  <h4>{{ registry.name }}</h4>
                  <span v-if="registry.is_default" class="soft-pill">Default</span>
                </div>
                <p>{{ registry.server }}</p>
              </div>
              <span class="connection-pill" :class="`status-${registry.connection_status}`">
                {{ connectionLabel(registry.connection_status) }}
              </span>
            </div>

            <div class="registry-meta">
              <span class="soft-pill">{{ providerLabel(registry.provider) }}</span>
              <span v-if="registry.namespace" class="soft-pill">{{ registry.namespace }}</span>
              <span class="soft-pill">{{ registry.is_active ? 'Active' : 'Disabled' }}</span>
              <span class="soft-pill">Credentials configured</span>
            </div>

            <pre class="code-block">{{ registry.image_prefix }}</pre>

            <div class="connection-detail">
              <p>{{ registry.last_connection_message || '尚未执行连接测试。' }}</p>
              <small v-if="registry.last_checked_at">最近测试：{{ formatTime(registry.last_checked_at) }}</small>
              <small v-else>最近测试：—</small>
            </div>

            <div v-if="registry.skip_tls_verify" class="tls-warning">
              TLS 证书校验已关闭。连接可能被中间人攻击，请仅用于受控的自签名 Registry。
            </div>

            <div class="registry-actions">
              <el-button
                :loading="testingRegistryId === registry.id"
                @click="testSavedRegistry(registry)"
              >测试连接</el-button>
              <el-button v-if="!registry.is_default" @click="makeDefault(registry.id)">设为默认</el-button>
              <el-button @click="openDialog(registry)">编辑</el-button>
              <el-button :disabled="registry.is_default" @click="removeRegistry(registry)">删除</el-button>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="还没有项目级 Registry"
          description="添加 ACR、Harbor、Docker Hub、GHCR 或其他 OCI Registry。"
        />
      </el-skeleton>
    </section>

    <el-dialog
      v-model="dialog"
      :title="editing ? '编辑 Registry' : '添加 Registry'"
      width="700px"
      class="governance-form-dialog"
      custom-class="governance-form-dialog"
      modal-class="governance-form-overlay"
    >
      <el-form label-position="top">
        <section class="form-section">
          <div class="section-title">
            <h4>镜像仓库</h4>
            <p>用户名和 Token 为必填凭据。保存失败的连接配置后仍可继续排查。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="名称"><el-input v-model="form.name" placeholder="Company Registry" /></el-form-item>
            <el-form-item label="类型">
              <el-select v-model="form.provider">
                <el-option v-for="provider in providers" :key="provider.value" :label="provider.label" :value="provider.value" />
              </el-select>
            </el-form-item>
            <el-form-item class="wide" label="Registry Server">
              <el-input v-model="form.server" placeholder="ghcr.io" />
              <small>只填写域名或域名:端口，不包含协议和仓库路径。</small>
            </el-form-item>
            <el-form-item label="Namespace / Project"><el-input v-model="form.namespace" placeholder="platform" /></el-form-item>
            <el-form-item label="Pull Secret"><el-input v-model="form.pull_secret_name" placeholder="aegis-registry-credentials" /></el-form-item>
            <el-form-item label="用户名 / Client ID"><el-input v-model="form.username" autocomplete="off" /></el-form-item>
            <el-form-item :label="editing ? 'Token（留空表示沿用已保存 Token）' : 'Token'">
              <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item label="Email（可选）"><el-input v-model="form.email" /></el-form-item>
            <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
            <el-form-item class="wide" label="TLS 证书校验">
              <el-switch
                v-model="form.skip_tls_verify"
                inline-prompt
                active-text="跳过"
                inactive-text="验证"
              />
              <div v-if="form.skip_tls_verify" class="tls-warning form-warning">
                高风险：将跳过 Registry 和认证服务的 TLS 证书校验，但仍只允许 HTTPS。
              </div>
            </el-form-item>
          </div>

          <div v-if="formResult" class="test-result" :class="formResult.connected ? 'result-success' : 'result-failed'">
            <b>{{ formResult.connected ? '连接成功' : '连接失败' }}</b>
            <span>{{ formResult.message }}</span>
            <small v-if="!formResult.tls_verified">TLS 证书未验证</small>
            <small v-else-if="formResult.auth_method">认证方式：{{ formResult.auth_method }}</small>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button :loading="testingForm" @click="testFormConnection">测试连接</el-button>
        <el-button type="primary" :loading="saving" @click="saveRegistry">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { projectApi } from '../api/project'
import { useProjectStore } from '../stores/project'
import type {
  ContainerRegistry,
  Project,
  RegistryConnectionResult,
  RegistryConnectionStatus,
  RegistryPayload,
} from '../types'

const route = useRoute()
const projectStore = useProjectStore()
const project = ref<Project>()
const registries = ref<ContainerRegistry[]>([])
const loading = ref(false)
const saving = ref(false)
const testingForm = ref(false)
const testingRegistryId = ref<number>()
const dialog = ref(false)
const editing = ref<ContainerRegistry>()
const formResult = ref<RegistryConnectionResult>()
const projectId = computed(() => Number(route.params.id))

const providers: Array<{ value: ContainerRegistry['provider']; label: string }> = [
  { value: 'acr', label: 'Azure Container Registry' },
  { value: 'harbor', label: 'Harbor' },
  { value: 'dockerhub', label: 'Docker Hub' },
  { value: 'ecr', label: 'Amazon ECR' },
  { value: 'gcr', label: 'Google Artifact Registry' },
  { value: 'ghcr', label: 'GitHub Container Registry' },
  { value: 'generic', label: 'Generic OCI Registry' },
]

const defaults: RegistryPayload = {
  name: '',
  provider: 'acr',
  server: '',
  namespace: '',
  username: '',
  password: '',
  email: '',
  pull_secret_name: 'aegis-registry-credentials',
  skip_tls_verify: false,
  is_active: true,
}
const form = reactive<RegistryPayload>({ ...defaults })

const providerLabel = (value: ContainerRegistry['provider']) =>
  providers.find(provider => provider.value === value)?.label || value

function connectionLabel(status: RegistryConnectionStatus) {
  return status === 'connected' ? '已连接' : status === 'failed' ? '连接失败' : '未测试'
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function refresh() {
  loading.value = true
  try {
    const [projectData, registryItems] = await Promise.all([
      projectApi.get(projectId.value),
      projectApi.registries(projectId.value),
    ])
    project.value = projectData
    registries.value = registryItems
    projectStore.setActiveProject(projectId.value)
    await projectStore.load()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function openDialog(item?: ContainerRegistry) {
  editing.value = item
  formResult.value = undefined
  Object.assign(form, item ? { ...defaults, ...item, password: '' } : defaults)
  dialog.value = true
}

function validateForm(requireToken: boolean) {
  if (!form.name.trim() || !form.server.trim() || !form.username.trim()) {
    ElMessage.warning('请填写名称、Registry Server 和用户名')
    return false
  }
  if (requireToken && !form.password?.trim()) {
    ElMessage.warning('请填写 Registry Token')
    return false
  }
  return true
}

async function testFormConnection() {
  if (!validateForm(!editing.value)) return
  testingForm.value = true
  formResult.value = undefined
  try {
    const input = {
      server: form.server,
      username: form.username,
      password: form.password,
      skip_tls_verify: form.skip_tls_verify,
    }
    formResult.value = editing.value
      ? await projectApi.testSavedRegistryConnection(projectId.value, editing.value.id, input)
      : await projectApi.testRegistryConnection(projectId.value, input)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    testingForm.value = false
  }
}

async function saveRegistry() {
  if (!validateForm(!editing.value)) return
  saving.value = true
  try {
    if (editing.value) {
      await projectApi.updateRegistry(projectId.value, editing.value.id, { ...form })
    } else {
      await projectApi.addRegistry(projectId.value, { ...form })
    }
    dialog.value = false
    await refresh()
    ElMessage.success('Registry 配置已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
}

async function testSavedRegistry(item: ContainerRegistry) {
  testingRegistryId.value = item.id
  try {
    const result = await projectApi.testSavedRegistryConnection(projectId.value, item.id)
    result.connected ? ElMessage.success(result.message) : ElMessage.warning(result.message)
    await refresh()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    testingRegistryId.value = undefined
  }
}

async function makeDefault(registryId: number) {
  try {
    await projectApi.setDefaultRegistry(projectId.value, registryId)
    ElMessage.success('默认 Registry 已更新')
    await refresh()
  } catch (error) {
    ElMessage.error((error as Error).message)
  }
}

async function removeRegistry(item: ContainerRegistry) {
  try {
    await ElMessageBox.confirm(`确认删除 Registry ${item.name}？`, '危险操作', { type: 'warning' })
    await projectApi.removeRegistry(projectId.value, item.id)
    ElMessage.success('Registry 已删除')
    await refresh()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error((error as Error).message)
  }
}

onMounted(async () => {
  projectStore.init()
  await refresh()
})
</script>

<style scoped>
.panel-card { box-shadow: none; }
.registry-grid { display: grid; gap: 12px; padding: 16px 24px 24px; }
.registry-card { padding: 18px; border: 1px solid var(--border-soft); border-radius: 14px; background: var(--surface-soft); }
.registry-head, .title-line, .registry-meta, .registry-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.registry-head { justify-content: space-between; align-items: flex-start; gap: 12px; }
.registry-head h4 { margin: 0; font-size: 18px; }
.registry-head p { margin: 8px 0 0; color: var(--muted); line-height: 1.7; }
.registry-meta { margin: 14px 0; }
.registry-actions { margin-top: 14px; }
.connection-pill { padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.status-connected { color: #147d52; background: #e8f7ef; }
.status-failed { color: #b42318; background: #fff0ee; }
.status-untested { color: var(--muted); background: var(--theme-panel); }
.connection-detail { margin-top: 12px; display: grid; gap: 4px; }
.connection-detail p { margin: 0; color: var(--text); }
.connection-detail small, .form-grid small { color: var(--muted); }
.tls-warning { margin-top: 12px; padding: 10px 12px; border: 1px solid #f3c27b; border-radius: 10px; background: #fff8e8; color: #8a4b08; line-height: 1.6; }
.form-warning { width: 100%; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.form-grid .wide { grid-column: 1 / -1; }
.form-grid small { display: block; margin-top: 6px; }
.test-result { margin-top: 8px; padding: 12px 14px; border-radius: 10px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.result-success { color: #147d52; background: #e8f7ef; }
.result-failed { color: #b42318; background: #fff0ee; }
.test-result small { width: 100%; }
@media (max-width: 760px) {
  .form-grid { grid-template-columns: 1fr; }
  .form-grid .wide { grid-column: auto; }
  .registry-head { flex-direction: column; }
}
</style>
