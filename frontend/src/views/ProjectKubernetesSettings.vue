<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Project resources"
      :title="project ? `${project.name} · Kubernetes` : 'Kubernetes'"
      description="维护当前 Project 可用的 Kubernetes 集群、默认集群和 kube context。"
    >
      <el-button :loading="loading" @click="refresh">刷新</el-button>
      <el-button type="primary" @click="openDialog()">＋ 添加集群</el-button>
    </PageHeader>

    <section class="surface panel-card">
      <div class="surface-header">
        <div>
          <h3>Kubernetes clusters</h3>
          <p>Environment 后续会从这里选择部署目标；Project 本体不直接保存集群配置。</p>
        </div>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <div v-if="clusters.length" class="cluster-grid">
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
              <span v-if="cluster.api_server" class="soft-pill">{{ cluster.api_server }}</span>
            </div>
            <p v-if="cluster.description" class="cluster-description">{{ cluster.description }}</p>
            <div class="cluster-actions">
              <el-button v-if="!cluster.is_default" @click="setDefaultCluster(cluster.id)">设为默认</el-button>
              <el-button @click="openDialog(cluster)">编辑</el-button>
              <el-button @click="removeCluster(cluster)">删除</el-button>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="还没有 Kubernetes 集群"
          description="先把 cluster / kube context 配好，后面环境才能显式绑定部署目标。"
        />
      </el-skeleton>
    </section>

    <el-dialog
      v-model="dialog"
      :title="editing ? '编辑集群' : '添加集群'"
      width="620px"
      class="governance-form-dialog"
      custom-class="governance-form-dialog"
      modal-class="governance-form-overlay"
    >
      <el-form label-position="top">
        <section class="form-section">
          <div class="section-title">
            <h4>集群连接</h4>
            <p>保存 Project 可用的 Kubernetes 目标集群和 kube context。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="Kube Context"><el-input v-model="form.kube_context" /></el-form-item>
            <el-form-item label="Namespace Prefix"><el-input v-model="form.namespace_prefix" /></el-form-item>
            <el-form-item label="API Server"><el-input v-model="form.api_server" /></el-form-item>
            <el-form-item class="wide" label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" />
            </el-form-item>
          </div>
        </section>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCluster">保存</el-button>
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
import type { KubernetesCluster, Project } from '../types'

const route = useRoute()
const projectStore = useProjectStore()
const project = ref<Project>()
const clusters = ref<KubernetesCluster[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<KubernetesCluster>()
const projectId = computed(() => Number(route.params.id))

const defaults = { name: '', kube_context: '', namespace_prefix: '', api_server: '', description: '' }
const form = reactive({ ...defaults })

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

function openDialog(item?: KubernetesCluster) {
  editing.value = item
  Object.assign(form, item || defaults)
  dialog.value = true
}

async function saveCluster() {
  if (!form.name.trim() || !form.kube_context.trim()) {
    ElMessage.warning('请填写名称和 kube context')
    return
  }
  saving.value = true
  try {
    if (editing.value) await projectApi.updateCluster(projectId.value, editing.value.id, form)
    else await projectApi.addCluster(projectId.value, form)
    dialog.value = false
    await refresh()
    ElMessage.success('Kubernetes 集群已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
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

.cluster-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.cluster-head h4 {
  margin: 0 0 8px;
  font-size: 18px;
}

.cluster-head p,
.cluster-description {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.cluster-meta,
.cluster-actions {
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

</style>
