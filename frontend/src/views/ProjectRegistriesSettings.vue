<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Project resources"
      :title="project ? `${project.name} · Registries` : 'Registries'"
      description="维护当前 Project 的镜像仓库、默认 Registry 和 Kubernetes 拉取凭据。"
    >
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="primary" @click="openDialog()">＋ 添加 Registry</el-button>
    </PageHeader>

    <section class="surface panel-card">
      <div class="surface-header">
        <div>
          <h3>Container registries</h3>
          <p>应用默认继承当前 Project 的 Registry；Project 本体不保存 Registry 凭据。</p>
        </div>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <div v-if="registries.length" class="registry-grid">
          <article v-for="registry in registries" :key="registry.id" class="registry-card">
            <div class="registry-head">
              <div>
                <h4>{{ registry.name }}</h4>
                <p>{{ registry.server }}</p>
              </div>
              <span v-if="registry.is_default" class="soft-pill">Default</span>
            </div>
            <div class="registry-meta">
              <span class="soft-pill">{{ registry.provider }}</span>
              <span class="soft-pill">{{ registry.namespace }}</span>
              <span class="soft-pill">{{ registry.is_active ? 'Active' : 'Disabled' }}</span>
            </div>
            <pre class="code-block">{{ registry.image_prefix }}</pre>
            <div class="registry-actions">
              <el-button v-if="!registry.is_default" @click="makeDefault(registry.id)">设为默认</el-button>
              <el-button @click="openDialog(registry)">编辑</el-button>
              <el-button :disabled="registry.is_default" @click="removeRegistry(registry)">删除</el-button>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="还没有项目级 Registry"
          description="添加 ACR、Harbor 或 Docker Hub 后，应用可以继承默认镜像仓库。"
        />
      </el-skeleton>
    </section>

    <el-dialog
      v-model="dialog"
      :title="editing ? '编辑 Registry' : '添加 Registry'"
      width="660px"
      class="governance-form-dialog"
      custom-class="governance-form-dialog"
      modal-class="governance-form-overlay"
    >
      <el-form label-position="top">
        <section class="form-section">
          <div class="section-title">
            <h4>镜像仓库</h4>
            <p>保存 Project 默认构建推送仓库和 Kubernetes Pull Secret 名称。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="类型"><el-input v-model="form.provider" /></el-form-item>
            <el-form-item class="wide" label="Registry Server"><el-input v-model="form.server" /></el-form-item>
            <el-form-item label="Namespace"><el-input v-model="form.namespace" /></el-form-item>
            <el-form-item label="Pull Secret"><el-input v-model="form.pull_secret_name" /></el-form-item>
            <el-form-item label="用户名"><el-input v-model="form.username" autocomplete="off" /></el-form-item>
            <el-form-item :label="editing ? '密码 / Token（留空表示不修改）' : '密码 / Token'">
              <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
            </el-form-item>
            <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRegistry">保存</el-button>
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
import { registryApi } from '../api/registry'
import { useProjectStore } from '../stores/project'
import type { ContainerRegistry, Project } from '../types'

const route = useRoute()
const projectStore = useProjectStore()
const project = ref<Project>()
const registries = ref<ContainerRegistry[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<ContainerRegistry>()
const projectId = computed(() => Number(route.params.id))

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
  Object.assign(form, item ? { ...defaults, ...item, password: '' } : defaults)
  dialog.value = true
}

async function saveRegistry() {
  if (!form.name.trim() || !form.server.trim()) {
    ElMessage.warning('请填写名称和 Registry Server')
    return
  }
  saving.value = true
  try {
    const payload = { ...form, project_id: projectId.value }
    if (editing.value) await registryApi.update(editing.value.id, payload)
    else await registryApi.create(payload)
    dialog.value = false
    await refresh()
    ElMessage.success('Registry 已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
}

async function makeDefault(registryId: number) {
  await registryApi.setDefault(registryId)
  ElMessage.success('默认 Registry 已更新')
  await refresh()
}

async function removeRegistry(item: ContainerRegistry) {
  await ElMessageBox.confirm(`确认删除 Registry ${item.name}？`, '提示', { type: 'warning' })
  await registryApi.remove(item.id)
  ElMessage.success('Registry 已删除')
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

.registry-grid {
  display: grid;
  gap: 12px;
  padding: 16px 24px 24px;
}

.registry-card {
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--surface-soft);
}

.registry-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.registry-head h4 {
  margin: 0 0 8px;
  font-size: 18px;
}

.registry-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.registry-meta,
.registry-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.registry-meta {
  margin: 14px 0;
}

.registry-actions {
  margin-top: 14px;
}

</style>
