<template>
  <div class="page-content">
    <PageHeader
      eyebrow="Platform settings"
      title="Container Registries"
      description="统一管理构建推送与 Kubernetes 拉取镜像所需的仓库和凭证"
    >
      <el-button type="primary" @click="openCreate">＋ 添加镜像仓库</el-button>
    </PageHeader>

    <section class="surface info-banner">
      <span>▣</span>
      <div>
        <b>平台级镜像仓库</b>
        <p>应用默认继承平台 Registry，镜像路径自动生成为 Registry / Namespace / Application / Tag。</p>
      </div>
    </section>

    <section class="surface registry-table">
      <div class="surface-header">
        <div><h3>Registry connections</h3><p>凭证加密保存，并自动同步为 Kaniko Push Secret 与 Deployment Pull Secret</p></div>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <el-table v-if="items.length" :data="items">
          <el-table-column label="名称" min-width="190">
            <template #default="{ row }">
              <div class="registry-name"><span>{{ icon(row.provider) }}</span><div><b>{{ row.name }}</b><small>{{ providerLabel(row.provider) }}</small></div></div>
            </template>
          </el-table-column>
          <el-table-column label="镜像前缀" min-width="280">
            <template #default="{ row }"><code>{{ row.image_prefix }}</code></template>
          </el-table-column>
          <el-table-column label="凭证" width="120">
            <template #default="{ row }"><StatusBadge :status="row.has_credentials ? 'Healthy' : 'Unknown'" :label="row.has_credentials ? 'Configured' : 'Anonymous'" /></template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }"><StatusBadge :status="row.is_active ? 'Healthy' : 'Unknown'" :label="row.is_active ? 'Active' : 'Disabled'" /></template>
          </el-table-column>
          <el-table-column label="默认" width="100">
            <template #default="{ row }"><span v-if="row.is_default" class="default-tag">DEFAULT</span><el-button v-else link @click="makeDefault(row)">设为默认</el-button></template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }"><el-button link @click="edit(row)">编辑</el-button><el-button link type="danger" :disabled="row.is_default" @click="remove(row)">删除</el-button></template>
          </el-table-column>
        </el-table>
        <EmptyState v-else title="尚未配置镜像仓库" description="添加 ACR、Harbor 或 Docker Hub 后，所有应用将自动继承默认仓库。" />
      </el-skeleton>
    </section>

    <el-dialog v-model="dialog" :title="editing ? '编辑镜像仓库' : '添加镜像仓库'" width="640px">
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
      <template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存配置</el-button></template>
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
import type { ContainerRegistry } from '../types'

const items = ref<ContainerRegistry[]>([])
const loading = ref(false), saving = ref(false), dialog = ref(false)
const editing = ref<ContainerRegistry>()
const providers = [
  { value: 'acr', label: 'Azure Container Registry' },
  { value: 'harbor', label: 'Harbor' },
  { value: 'dockerhub', label: 'Docker Hub' },
  { value: 'ecr', label: 'Amazon ECR' },
  { value: 'gcr', label: 'Google Artifact Registry' },
  { value: 'generic', label: 'Generic OCI Registry' },
]
const defaults = { name: '', provider: 'acr', server: '', namespace: '', username: '', password: '', email: '', pull_secret_name: 'aegis-registry-credentials', is_active: true }
const form = reactive({ ...defaults })
const providerLabel = (value: string) => providers.find(p => p.value === value)?.label || value
const icon = (value: string) => value === 'acr' ? 'AZ' : value === 'harbor' ? 'H' : value === 'dockerhub' ? 'D' : 'OCI'

async function load() { loading.value = true; try { items.value = await registryApi.list() } finally { loading.value = false } }
function openCreate() { editing.value = undefined; Object.assign(form, defaults); dialog.value = true }
function edit(item: ContainerRegistry) { editing.value = item; Object.assign(form, { ...defaults, ...item, password: '' }); dialog.value = true }
async function save() {
  if (!form.name.trim() || !form.server.trim()) return ElMessage.warning('请填写名称和 Registry Server')
  saving.value = true
  try {
    if (editing.value) await registryApi.update(editing.value.id, form)
    else await registryApi.create(form)
    ElMessage.success('镜像仓库配置已保存'); dialog.value = false; await load()
  } finally { saving.value = false }
}
async function makeDefault(item: ContainerRegistry) { await registryApi.setDefault(item.id); ElMessage.success('默认镜像仓库已更新'); load() }
async function remove(item: ContainerRegistry) {
  await ElMessageBox.confirm(`确认删除镜像仓库 ${item.name}？`, '危险操作', { type: 'warning' })
  await registryApi.remove(item.id); ElMessage.success('镜像仓库已删除'); load()
}
onMounted(load)
</script>

<style scoped>
.info-banner{padding:16px 18px;margin-bottom:14px;display:flex;gap:13px;align-items:center;box-shadow:none}.info-banner>span{width:36px;height:36px;border-radius:9px;display:grid;place-items:center;background:var(--primary-soft);color:#aea4ff}.info-banner b{font-size:13px}.info-banner p{font-size:12px;color:var(--muted);margin:4px 0 0}.registry-table{overflow:hidden}.registry-name{display:flex;align-items:center;gap:10px}.registry-name>span{width:32px;height:32px;border-radius:8px;display:grid;place-items:center;background:var(--surface-raised);color:#a9b6c8;font-size:11px;font-weight:700}.registry-name b,.registry-name small{display:block}.registry-name small{color:var(--muted);font-size:11px;margin-top:3px}code{font-size:12px;color:var(--text-2)}.default-tag{font-size:10px;letter-spacing:.7px;color:#b6adff;background:var(--primary-soft);padding:5px 7px;border-radius:5px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}.form-grid .wide{grid-column:1/-1}.form-grid small{display:block;color:var(--muted);font-size:11px;margin-top:5px}@media(max-width:900px){.form-grid{grid-template-columns:1fr}.form-grid .wide{grid-column:auto}}
</style>
