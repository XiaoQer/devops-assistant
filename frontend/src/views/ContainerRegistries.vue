<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Project settings"
      title="Container registries"
      :description="projectStore.activeProject ? `管理 ${projectStore.activeProject.name} 的镜像仓库和凭证。` : '请先选择一个项目。'"
    >
      <el-button type="primary" @click="openCreate">＋ 添加镜像仓库</el-button>
    </PageHeader>

    <section class="surface info-banner glass-card">
      <span>▣</span>
      <div>
        <b>平台级镜像仓库</b>
        <p>应用默认继承当前项目的 Registry，镜像路径自动生成为 Registry / Namespace / Application / Tag。</p>
      </div>
    </section>

    <section class="registry-layout">
      <section class="surface registry-list-card">
        <div class="surface-header">
          <div>
            <h3>Registry connections</h3>
            <p>凭证加密保存，并自动同步为 Kaniko Push Secret 与 Deployment Pull Secret。</p>
          </div>
          <el-button :loading="loading" @click="load">刷新</el-button>
        </div>
        <el-skeleton :loading="loading" animated :rows="6">
          <div v-if="items.length" class="registry-list">
            <article v-for="row in items" :key="row.id" class="registry-card">
              <div class="registry-head">
                <div class="registry-name">
                  <span>{{ icon(row.provider) }}</span>
                  <div>
                    <h4>{{ row.name }}</h4>
                    <small>{{ providerLabel(row.provider) }}</small>
                  </div>
                </div>
                <div class="registry-statuses">
                  <StatusBadge :status="row.has_credentials ? 'Healthy' : 'Unknown'" :label="row.has_credentials ? 'Configured' : 'Anonymous'" />
                  <StatusBadge :status="row.is_active ? 'Healthy' : 'Unknown'" :label="row.is_active ? 'Active' : 'Disabled'" />
                </div>
              </div>

              <div class="registry-meta">
                <span class="soft-pill">{{ row.server }}</span>
                <span class="soft-pill">{{ row.namespace }}</span>
                <span v-if="row.is_default" class="soft-pill default-pill">Default</span>
              </div>

              <pre class="code-block prefix-block">{{ row.image_prefix }}</pre>

              <div class="registry-actions">
                <el-button v-if="!row.is_default" @click="makeDefault(row)">设为默认</el-button>
                <el-button @click="edit(row)">编辑</el-button>
                <el-button :disabled="row.is_default" @click="remove(row)">删除</el-button>
              </div>
            </article>
          </div>
          <EmptyState v-else title="尚未配置镜像仓库" description="添加 ACR、Harbor 或 Docker Hub 后，所有应用将自动继承默认仓库。" />
        </el-skeleton>
      </section>

      <aside class="surface help-rail">
        <div class="surface-header">
          <div>
            <h3>Registry guidance</h3>
            <p>平台设置页应尽量减少低价值配置噪音。</p>
          </div>
        </div>
        <div class="rail-content">
          <article>
            <span class="soft-pill">Secure by default</span>
            <h4>凭证集中托管</h4>
            <p>所有凭证都作为平台能力统一管理，而不是分散到每个应用里重复输入。</p>
          </article>
          <article>
            <span class="soft-pill">Platform policy</span>
            <h4>默认 Registry 自动继承</h4>
            <p>减少每个服务重复选择仓库的步骤，把更多精力留给交付决策本身。</p>
          </article>
        </div>
      </aside>
    </section>

    <el-dialog v-model="dialog" :title="editing ? '编辑镜像仓库' : '添加镜像仓库'" width="680px">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="显示名称"><el-input v-model="form.name" placeholder="Company ACR" /></el-form-item>
          <el-form-item label="Registry 类型"><el-select v-model="form.provider"><el-option v-for="p in providers" :key="p.value" :label="p.label" :value="p.value" /></el-select></el-form-item>
          <el-form-item class="wide" label="Registry Server"><el-input v-model="form.server" placeholder="company.azurecr.io" /><small>只填写域名，不要包含 https:// 或仓库路径</small></el-form-item>
          <el-form-item label="默认 Namespace / Project"><el-input v-model="form.namespace" placeholder="platform" /></el-form-item>
          <el-form-item label="Pull Secret 名称"><el-input v-model="form.pull_secret_name" placeholder="aegis-registry-credentials" /></el-form-item>
          <el-form-item label="用户名 / Client ID"><el-input v-model="form.username" autocomplete="off" /></el-form-item>
          <el-form-item :label="editing ? '密码 / Token（留空表示不修改）' : '密码 / Token'"><el-input v-model="form.password" type="password" show-password autocomplete="new-password" /></el-form-item>
          <el-form-item label="Email（可选）"><el-input v-model="form.email" /></el-form-item>
          <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { registryApi } from '../api/registry'
import { useProjectStore } from '../stores/project'
import type { ContainerRegistry } from '../types'

const projectStore = useProjectStore()
const items = ref<ContainerRegistry[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<ContainerRegistry>()
const providers = [
  { value: 'acr', label: 'Azure Container Registry' },
  { value: 'harbor', label: 'Harbor' },
  { value: 'dockerhub', label: 'Docker Hub' },
  { value: 'ecr', label: 'Amazon ECR' },
  { value: 'gcr', label: 'Google Artifact Registry' },
  { value: 'generic', label: 'Generic OCI Registry' },
]

const defaults = {
  name: '',
  provider: 'acr',
  server: '',
  namespace: '',
  username: '',
  password: '',
  email: '',
  pull_secret_name: 'aegis-registry-credentials',
  is_active: true,
}

const form = reactive({ ...defaults })
const providerLabel = (value: string) => providers.find(provider => provider.value === value)?.label || value
const icon = (value: string) => value === 'acr' ? 'AZ' : value === 'harbor' ? 'H' : value === 'dockerhub' ? 'D' : 'OCI'

async function load() {
  loading.value = true
  try {
    items.value = await registryApi.list(projectStore.activeProjectId || undefined)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = undefined
  Object.assign(form, defaults)
  dialog.value = true
}

function edit(item: ContainerRegistry) {
  editing.value = item
  Object.assign(form, { ...defaults, ...item, password: '' })
  dialog.value = true
}

async function save() {
  if (!form.name.trim() || !form.server.trim()) return ElMessage.warning('请填写名称和 Registry Server')
  saving.value = true
  try {
    if (editing.value) await registryApi.update(editing.value.id, form)
    else await registryApi.create({ ...form, project_id: projectStore.activeProjectId || undefined })
    ElMessage.success('镜像仓库配置已保存')
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function makeDefault(item: ContainerRegistry) {
  await registryApi.setDefault(item.id)
  ElMessage.success('默认镜像仓库已更新')
  load()
}

async function remove(item: ContainerRegistry) {
  await ElMessageBox.confirm(`确认删除镜像仓库 ${item.name}？`, '危险操作', { type: 'warning' })
  await registryApi.remove(item.id)
  ElMessage.success('镜像仓库已删除')
  load()
}

onMounted(async () => {
  projectStore.init()
  await projectStore.load()
  await load()
})
</script>

<style scoped>
.info-banner {
  padding: 18px 20px;
  display: flex;
  gap: 14px;
  align-items: center;
  box-shadow: none;
}

.info-banner > span {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: var(--primary-soft);
  color: var(--primary);
}

.info-banner b {
  font-size: 15px;
}

.info-banner p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.registry-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.registry-list-card,
.help-rail {
  box-shadow: none;
}

.registry-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.registry-card {
  padding: 18px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.registry-head,
.registry-name,
.registry-meta,
.registry-actions,
.registry-statuses {
  display: flex;
  align-items: center;
}

.registry-head {
  justify-content: space-between;
  gap: 14px;
}

.registry-name {
  gap: 12px;
}

.registry-name > span {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: var(--theme-panel);
  color: var(--text);
  font-size: 12px;
  font-weight: 700;
}

.registry-name h4 {
  margin: 0 0 4px;
  font-size: 18px;
}

.registry-name small {
  color: var(--muted);
}

.registry-statuses,
.registry-meta,
.registry-actions {
  gap: 10px;
  flex-wrap: wrap;
}

.registry-meta {
  margin: 16px 0 12px;
}

.prefix-block {
  margin: 0 0 14px;
}

.default-pill {
  color: var(--primary);
}

.rail-content {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rail-content article {
  padding: 18px;
  border-radius: 14px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.rail-content h4 {
  margin: 14px 0 8px;
  font-size: 17px;
}

.rail-content p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.form-grid .wide {
  grid-column: 1 / -1;
}

.form-grid small {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-top: 6px;
}

@media (max-width: 1000px) {
  .registry-layout,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-grid .wide {
    grid-column: auto;
  }

  .registry-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
