<template>
  <div class="page-content page-stack">
    <el-skeleton v-if="loading && !project" animated :rows="10" />
    <template v-else-if="project">
      <PageHeader
        eyebrow="Project workspace"
        :title="project.name"
        :description="project.description || '项目级设置、成员、应用和部署资源统一组织在这里。'"
      >
        <el-button @click="refresh" :loading="loading">刷新</el-button>
        <el-button type="primary" @click="createApplication">＋ 新建应用</el-button>
      </PageHeader>

      <div class="metrics">
        <MetricCard title="Applications" :value="applications.length" icon="◇" helper="项目内服务" />
        <MetricCard title="Members" :value="members.length" icon="👥" tone="green" helper="RBAC 基础对象" />
        <MetricCard title="Clusters" :value="clusters.length" icon="☸" tone="blue" helper="项目可用部署目标" />
        <MetricCard title="Registries" :value="registries.length" icon="▣" tone="purple" helper="项目默认构建推送仓库" />
      </div>

      <section class="surface project-summary glass-card">
        <div>
          <span class="soft-pill">{{ project.key }}</span>
          <h3>Project-scoped delivery settings</h3>
          <p>把镜像仓库、Kubernetes 集群、成员、未来 Terraform 与共享资源都挂到 Project 下，Application 再去引用这些能力。</p>
        </div>
        <div class="summary-meta">
          <div>
            <label>Default cluster</label>
            <b>{{ defaultCluster?.name || '未配置' }}</b>
          </div>
          <div>
            <label>Default registry</label>
            <b>{{ defaultRegistry?.name || '未配置' }}</b>
          </div>
          <div>
            <label>Project owner</label>
            <b>{{ owner?.name || '未设置' }}</b>
          </div>
        </div>
      </section>

      <el-tabs v-model="tab">
        <el-tab-pane label="Applications" name="applications">
          <section class="surface panel-card">
            <div class="surface-header">
              <div>
                <h3>Applications</h3>
                <p>项目内所有服务工作区都归属到同一个交付边界下。</p>
              </div>
            </div>
            <div class="app-grid">
              <article v-for="app in applications" :key="app.id" class="project-app-card">
                <div>
                  <h4>{{ app.name }}</h4>
                  <p>{{ app.language }} / {{ app.framework }} · {{ app.namespace }}</p>
                </div>
                <div class="app-actions">
                  <el-button @click="router.push(`/applications/${app.id}`)">打开</el-button>
                </div>
              </article>
            </div>
            <EmptyState v-if="!applications.length" title="项目里还没有应用" description="建议先创建 Application，再为它绑定环境、集群、镜像仓库与资源。">
              <el-button type="primary" @click="createApplication">创建应用</el-button>
            </EmptyState>
          </section>
        </el-tab-pane>

        <el-tab-pane label="Members" name="members">
          <section class="surface panel-card">
            <div class="surface-header">
              <div>
                <h3>Project members</h3>
                <p>后续 RBAC、审批人、变更归属都会基于项目成员模型展开。</p>
              </div>
              <el-button type="primary" @click="openMemberDialog()">＋ 添加成员</el-button>
            </div>
            <el-table :data="members">
              <el-table-column prop="name" label="姓名" min-width="160" />
              <el-table-column prop="email" label="邮箱" min-width="220" />
              <el-table-column prop="role" label="角色" width="120" />
              <el-table-column prop="title" label="Title" min-width="160" />
              <el-table-column label="操作" width="160">
                <template #default="{ row }">
                  <el-button link @click="openMemberDialog(row)">编辑</el-button>
                  <el-button link @click="removeMember(row)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="Kubernetes" name="clusters">
          <section class="surface panel-card">
            <div class="surface-header">
              <div>
                <h3>Kubernetes clusters</h3>
                <p>项目可用的 Kubernetes 目标集群，Environment 将从这里选择部署目标。</p>
              </div>
              <el-button type="primary" @click="openClusterDialog()">＋ 添加集群</el-button>
            </div>
            <div class="cluster-grid">
              <article v-for="cluster in clusters" :key="cluster.id" class="cluster-card">
                <div class="cluster-head">
                  <div>
                    <h4>{{ cluster.name }}</h4>
                    <p>{{ cluster.kube_context }}</p>
                  </div>
                  <span v-if="cluster.is_default" class="soft-pill">Default</span>
                </div>
                <div class="cluster-meta">
                  <span class="soft-pill">{{ cluster.namespace_prefix || 'no namespace prefix' }}</span>
                  <span class="soft-pill">{{ cluster.is_active ? 'Active' : 'Disabled' }}</span>
                </div>
                <div class="cluster-actions">
                  <el-button v-if="!cluster.is_default" @click="setDefaultCluster(cluster.id)">设为默认</el-button>
                  <el-button @click="openClusterDialog(cluster)">编辑</el-button>
                  <el-button @click="removeCluster(cluster)">删除</el-button>
                </div>
              </article>
            </div>
            <EmptyState v-if="!clusters.length" title="还没有 Kubernetes 集群" description="先把 cluster / kube context 配好，后面环境才能显式绑定部署目标。" />
          </section>
        </el-tab-pane>

        <el-tab-pane label="Registries" name="registries">
          <section class="surface panel-card">
            <div class="surface-header">
              <div>
                <h3>Container registries</h3>
                <p>项目默认镜像仓库、构建推送凭据与 Kubernetes 拉取凭据统一放在这里管理。</p>
              </div>
              <el-button type="primary" @click="openRegistryDialog()">＋ 添加 Registry</el-button>
            </div>
            <div class="registry-grid">
              <article v-for="registry in registries" :key="registry.id" class="registry-card">
                <div class="cluster-head">
                  <div>
                    <h4>{{ registry.name }}</h4>
                    <p>{{ registry.server }}</p>
                  </div>
                  <span v-if="registry.is_default" class="soft-pill">Default</span>
                </div>
                <div class="cluster-meta">
                  <span class="soft-pill">{{ registry.provider }}</span>
                  <span class="soft-pill">{{ registry.image_prefix }}</span>
                </div>
                <div class="cluster-actions">
                  <el-button v-if="!registry.is_default" @click="makeDefaultRegistry(registry.id)">设为默认</el-button>
                  <el-button @click="openRegistryDialog(registry)">编辑</el-button>
                  <el-button @click="removeRegistry(registry)">删除</el-button>
                </div>
              </article>
            </div>
            <EmptyState v-if="!registries.length" title="还没有项目级 Registry" description="后续应用会优先继承当前项目的默认镜像仓库。" />
          </section>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>

  <el-dialog v-model="memberDialog" :title="editingMember ? '编辑成员' : '添加成员'" width="560px">
    <el-form label-position="top">
      <el-form-item label="姓名"><el-input v-model="memberForm.name" /></el-form-item>
      <el-form-item label="邮箱"><el-input v-model="memberForm.email" /></el-form-item>
      <el-form-item label="角色">
        <el-select v-model="memberForm.role">
          <el-option v-for="role in roles" :key="role" :label="role" :value="role" />
        </el-select>
      </el-form-item>
      <el-form-item label="Title"><el-input v-model="memberForm.title" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="memberDialog = false">取消</el-button>
      <el-button type="primary" :loading="memberSaving" @click="saveMember">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="clusterDialog" :title="editingCluster ? '编辑集群' : '添加集群'" width="620px">
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item label="名称"><el-input v-model="clusterForm.name" /></el-form-item>
        <el-form-item label="Kube Context"><el-input v-model="clusterForm.kube_context" /></el-form-item>
        <el-form-item label="Namespace Prefix"><el-input v-model="clusterForm.namespace_prefix" /></el-form-item>
        <el-form-item label="API Server"><el-input v-model="clusterForm.api_server" /></el-form-item>
        <el-form-item class="wide" label="描述"><el-input v-model="clusterForm.description" type="textarea" :rows="3" /></el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="clusterDialog = false">取消</el-button>
      <el-button type="primary" :loading="clusterSaving" @click="saveCluster">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="registryDialog" :title="editingRegistry ? '编辑 Registry' : '添加 Registry'" width="660px">
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item label="名称"><el-input v-model="registryForm.name" /></el-form-item>
        <el-form-item label="类型"><el-input v-model="registryForm.provider" /></el-form-item>
        <el-form-item class="wide" label="Registry Server"><el-input v-model="registryForm.server" /></el-form-item>
        <el-form-item label="Namespace"><el-input v-model="registryForm.namespace" /></el-form-item>
        <el-form-item label="Pull Secret"><el-input v-model="registryForm.pull_secret_name" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="registryForm.username" /></el-form-item>
        <el-form-item label="密码 / Token"><el-input v-model="registryForm.password" type="password" show-password /></el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="registryDialog = false">取消</el-button>
      <el-button type="primary" :loading="registrySaving" @click="saveRegistry">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { projectApi } from '../api/project'
import { registryApi } from '../api/registry'
import { useProjectStore } from '../stores/project'
import type { Application, ContainerRegistry, KubernetesCluster, Project, ProjectMember } from '../types'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const project = ref<Project>()
const applications = ref<Application[]>([])
const members = ref<ProjectMember[]>([])
const clusters = ref<KubernetesCluster[]>([])
const registries = ref<ContainerRegistry[]>([])
const loading = ref(false)
const tab = ref('applications')

const memberDialog = ref(false)
const memberSaving = ref(false)
const editingMember = ref<ProjectMember>()
const memberForm = reactive<{ name: string; email: string; role: ProjectMember['role']; title: string }>({
  name: '',
  email: '',
  role: 'developer',
  title: '',
})
const roles: Array<ProjectMember['role']> = ['owner', 'admin', 'developer', 'viewer']

const clusterDialog = ref(false)
const clusterSaving = ref(false)
const editingCluster = ref<KubernetesCluster>()
const clusterForm = reactive({ name: '', kube_context: '', namespace_prefix: '', api_server: '', description: '' })

const registryDialog = ref(false)
const registrySaving = ref(false)
const editingRegistry = ref<ContainerRegistry>()
const registryForm = reactive({
  name: '', provider: 'acr', server: '', namespace: '', username: '', password: '', email: '',
  pull_secret_name: 'aegis-registry-credentials', is_active: true,
})

const projectId = computed(() => Number(route.params.id))
const owner = computed(() => members.value.find(item => item.role === 'owner'))
const defaultCluster = computed(() => clusters.value.find(item => item.is_default))
const defaultRegistry = computed(() => registries.value.find(item => item.is_default))

async function refresh() {
  loading.value = true
  try {
    const id = projectId.value
    const [projectData, appItems, memberItems, clusterItems, registryItems] = await Promise.all([
      projectApi.get(id),
      projectApi.applications(id),
      projectApi.members(id),
      projectApi.clusters(id),
      projectApi.registries(id),
    ])
    project.value = projectData
    applications.value = appItems
    members.value = memberItems
    clusters.value = clusterItems
    registries.value = registryItems
    projectStore.setActiveProject(id)
    await projectStore.load()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function createApplication() {
  router.push({ path: '/applications/new', query: { projectId: String(projectId.value) } })
}

function openMemberDialog(item?: ProjectMember) {
  editingMember.value = item
  Object.assign(memberForm, item || { name: '', email: '', role: 'developer', title: '' })
  memberDialog.value = true
}

async function saveMember() {
  if (!memberForm.name.trim() || !memberForm.email.trim()) return ElMessage.warning('请填写姓名和邮箱')
  memberSaving.value = true
  try {
    if (editingMember.value) await projectApi.updateMember(projectId.value, editingMember.value.id, memberForm)
    else await projectApi.addMember(projectId.value, memberForm)
    memberDialog.value = false
    await refresh()
    ElMessage.success('项目成员已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    memberSaving.value = false
  }
}

async function removeMember(item: ProjectMember) {
  await ElMessageBox.confirm(`确认移除成员 ${item.name}？`, '提示', { type: 'warning' })
  await projectApi.removeMember(projectId.value, item.id)
  ElMessage.success('成员已移除')
  refresh()
}

function openClusterDialog(item?: KubernetesCluster) {
  editingCluster.value = item
  Object.assign(clusterForm, item || { name: '', kube_context: '', namespace_prefix: '', api_server: '', description: '' })
  clusterDialog.value = true
}

async function saveCluster() {
  if (!clusterForm.name.trim() || !clusterForm.kube_context.trim()) return ElMessage.warning('请填写名称和 kube context')
  clusterSaving.value = true
  try {
    if (editingCluster.value) await projectApi.updateCluster(projectId.value, editingCluster.value.id, clusterForm)
    else await projectApi.addCluster(projectId.value, clusterForm)
    clusterDialog.value = false
    await refresh()
    ElMessage.success('Kubernetes 集群已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    clusterSaving.value = false
  }
}

async function setDefaultCluster(clusterId: number) {
  await projectApi.setDefaultCluster(projectId.value, clusterId)
  ElMessage.success('默认集群已更新')
  refresh()
}

async function removeCluster(item: KubernetesCluster) {
  await ElMessageBox.confirm(`确认删除集群 ${item.name}？`, '提示', { type: 'warning' })
  await projectApi.removeCluster(projectId.value, item.id)
  ElMessage.success('集群已删除')
  refresh()
}

function openRegistryDialog(item?: ContainerRegistry) {
  editingRegistry.value = item
  Object.assign(registryForm, item ? { ...registryForm, ...item, password: '' } : {
    name: '', provider: 'acr', server: '', namespace: '', username: '', password: '', email: '',
    pull_secret_name: 'aegis-registry-credentials', is_active: true,
  })
  registryDialog.value = true
}

async function saveRegistry() {
  if (!registryForm.name.trim() || !registryForm.server.trim()) return ElMessage.warning('请填写名称和 Registry Server')
  registrySaving.value = true
  try {
    const payload = { ...registryForm, project_id: projectId.value }
    if (editingRegistry.value) await registryApi.update(editingRegistry.value.id, payload)
    else await registryApi.create(payload)
    registryDialog.value = false
    await refresh()
    ElMessage.success('Registry 已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    registrySaving.value = false
  }
}

async function makeDefaultRegistry(registryId: number) {
  await registryApi.setDefault(registryId)
  ElMessage.success('默认 Registry 已更新')
  refresh()
}

async function removeRegistry(item: ContainerRegistry) {
  await ElMessageBox.confirm(`确认删除 Registry ${item.name}？`, '提示', { type: 'warning' })
  await registryApi.remove(item.id)
  ElMessage.success('Registry 已删除')
  refresh()
}

onMounted(async () => {
  projectStore.init()
  await refresh()
})
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.project-summary,
.panel-card {
  box-shadow: none;
}

.project-summary {
  padding: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 24px;
}

.project-summary h3 {
  margin: 16px 0 10px;
  font-size: 30px;
  letter-spacing: -0.04em;
}

.project-summary p {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
}

.summary-meta {
  display: grid;
  gap: 14px;
}

.summary-meta > div,
.project-app-card,
.cluster-card,
.registry-card {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.summary-meta label,
.summary-meta b {
  display: block;
}

.summary-meta label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.app-grid,
.cluster-grid,
.registry-grid {
  display: grid;
  gap: 12px;
}

.app-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.project-app-card h4,
.cluster-card h4,
.registry-card h4 {
  margin: 0 0 8px;
  font-size: 18px;
}

.project-app-card p,
.cluster-card p,
.registry-card p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.app-actions,
.cluster-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.cluster-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.cluster-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 14px 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.form-grid .wide {
  grid-column: 1 / -1;
}

@media (max-width: 1100px) {
  .metrics,
  .project-summary,
  .app-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-grid .wide {
    grid-column: auto;
  }
}
</style>

