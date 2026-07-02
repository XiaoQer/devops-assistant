<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Delivery scope"
      title="Projects"
      description="先定义项目边界，再在项目里统一管理应用、成员、集群、镜像仓库和共享资源。"
    >
      <el-button :loading="store.loading" @click="refresh">刷新</el-button>
      <el-button type="primary" @click="openCreate">＋ 创建项目</el-button>
    </PageHeader>

    <div class="metrics">
      <MetricCard title="Projects" :value="store.items.length" icon="◫" helper="当前已创建" />
      <MetricCard title="Applications" :value="applicationsCount" icon="◇" helper="项目内服务总数" />
      <MetricCard title="Clusters" :value="clustersCount" icon="☸" tone="blue" helper="项目级 Kubernetes" />
      <MetricCard title="Members" :value="membersCount" icon="👥" tone="green" helper="为 RBAC 做准备" />
    </div>

    <section class="projects-grid">
      <article v-for="project in store.items" :key="project.id" class="surface project-card">
        <div class="project-head">
          <div>
            <span class="soft-pill">{{ project.key }}</span>
            <h3>{{ project.name }}</h3>
            <p>{{ project.description || '这个项目还没有补充描述。' }}</p>
          </div>
        </div>

        <div class="project-stats">
          <div>
            <label>Applications</label>
            <b>{{ project.applications_count || 0 }}</b>
          </div>
          <div>
            <label>Members</label>
            <b>{{ project.members_count || 0 }}</b>
          </div>
          <div>
            <label>Clusters</label>
            <b>{{ project.clusters_count || 0 }}</b>
          </div>
          <div>
            <label>Registries</label>
            <b>{{ project.registries_count || 0 }}</b>
          </div>
        </div>

        <div class="project-actions">
          <el-button @click="setActive(project.id)">设为当前项目</el-button>
          <el-button type="primary" @click="router.push(`/projects/${project.id}`)">进入项目</el-button>
        </div>
      </article>
    </section>

    <EmptyState
      v-if="!store.items.length && !store.loading"
      title="还没有项目"
      description="建议先创建 Project，再在项目里配置 Registry、Kubernetes 集群、成员和应用。"
    >
      <el-button type="primary" @click="openCreate">创建第一个项目</el-button>
    </EmptyState>

    <el-dialog v-model="dialog" title="Create project" width="620px">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="项目标识 Key">
            <el-input v-model="form.key" placeholder="payments-platform" />
          </el-form-item>
          <el-form-item label="项目名称">
            <el-input v-model="form.name" placeholder="Payments Platform" />
          </el-form-item>
          <el-form-item class="wide" label="项目描述">
            <el-input v-model="form.description" type="textarea" :rows="3" placeholder="例如：支付域服务交付平台" />
          </el-form-item>
          <el-form-item label="Owner 名称">
            <el-input v-model="form.owner_name" placeholder="Alice" />
          </el-form-item>
          <el-form-item label="Owner 邮箱">
            <el-input v-model="form.owner_email" placeholder="alice@example.com" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">创建项目</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import EmptyState from '../components/common/EmptyState.vue'
import { projectApi } from '../api/project'
import { useProjectStore } from '../stores/project'

const router = useRouter()
const store = useProjectStore()
const dialog = ref(false)
const saving = ref(false)
const form = reactive({
  key: '',
  name: '',
  description: '',
  owner_name: '',
  owner_email: '',
})

const applicationsCount = computed(() => store.items.reduce((sum, item) => sum + (item.applications_count || 0), 0))
const membersCount = computed(() => store.items.reduce((sum, item) => sum + (item.members_count || 0), 0))
const clustersCount = computed(() => store.items.reduce((sum, item) => sum + (item.clusters_count || 0), 0))

function openCreate() {
  Object.assign(form, { key: '', name: '', description: '', owner_name: '', owner_email: '' })
  dialog.value = true
}

async function refresh() {
  await store.load()
}

function setActive(projectId: number) {
  store.setActiveProject(projectId)
  ElMessage.success('当前项目已切换')
}

async function save() {
  if (!form.key.trim() || !form.name.trim()) return ElMessage.warning('请填写项目标识和名称')
  saving.value = true
  try {
    const project = await projectApi.create(form)
    await store.load()
    store.setActiveProject(project.id)
    dialog.value = false
    ElMessage.success('项目已创建')
    router.push(`/projects/${project.id}`)
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  store.init()
  await store.load()
})
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.project-card {
  padding: 22px;
  box-shadow: none;
}

.project-head h3 {
  margin: 14px 0 10px;
  font-size: 24px;
  letter-spacing: -0.04em;
}

.project-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.project-stats {
  margin: 20px 0;
  padding: 18px 0;
  border-top: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.project-stats label,
.project-stats b {
  display: block;
}

.project-stats label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.project-actions {
  display: flex;
  gap: 10px;
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
  .projects-grid,
  .project-stats,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-grid .wide {
    grid-column: auto;
  }
}
</style>

