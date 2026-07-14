<template>
  <div class="page-content page-stack">
    <DetailBreadcrumb :items="[
      { label: 'DevCenter', to: '/devcenter' },
      { label: 'Applications', to: applicationsPath },
      { label: '创建应用', current: true },
    ]" />
    <PageHeader
      eyebrow="Application setup"
      title="创建应用"
      description="连接代码仓库，平台会识别技术栈并初始化应用交付工作区。"
    >
      <el-button @click="goBack">返回 Applications</el-button>
    </PageHeader>

    <div class="create-grid">
      <section class="surface form-card create-form-card">
        <div class="surface-header">
          <div>
            <h3>应用与仓库</h3>
            <p>填写应用标识和代码仓库，创建后可继续完善环境与发布配置。</p>
          </div>
        </div>
        <div class="form-body">
          <el-form label-position="top" :model="form">
            <div class="form-section-title">应用信息</div>
            <el-form-item label="所属 Project">
              <el-select v-model="form.project_id" placeholder="选择项目">
                <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="应用名称">
              <el-input v-model="form.name" placeholder="order-api" />
            </el-form-item>

            <div class="form-section-title repository-title">代码仓库</div>
            <el-form-item label="GitHub 仓库地址">
              <el-input v-model="form.repo_url" placeholder="https://github.com/org/repo.git" />
            </el-form-item>
            <div class="inline-grid">
              <el-form-item label="分支">
                <el-input v-model="form.branch" />
              </el-form-item>
              <el-form-item label="Namespace">
                <el-input v-model="form.namespace" />
              </el-form-item>
            </div>
            <div class="callout">
              <strong>创建后自动执行</strong>
              <p>平台会克隆仓库、识别语言与框架，并生成应用的基础交付配置。</p>
            </div>
            <el-button class="submit" type="primary" :loading="loading" @click="submit">分析仓库并创建应用</el-button>
          </el-form>
        </div>
      </section>

      <aside class="create-aside">
        <section class="surface context-card">
          <div class="aside-label">PROJECT CONTEXT</div>
          <h3>{{ selectedProject?.name || '选择一个 Project' }}</h3>
          <p v-if="selectedProject?.description">{{ selectedProject.description }}</p>
          <p v-else>应用会继承当前 Project 的交付边界和默认配置。</p>
          <dl>
            <div><dt>目标环境</dt><dd>{{ selectedProject?.environments?.length || 0 }}</dd></div>
            <div><dt>Kubernetes 集群</dt><dd>{{ selectedProject?.clusters?.length || 0 }}</dd></div>
            <div><dt>镜像仓库</dt><dd>{{ selectedProject?.registries?.length || 0 }}</dd></div>
          </dl>
        </section>

        <section class="surface checklist-card">
          <div class="aside-label">创建后将完成</div>
          <ul>
            <li><span>01</span><div><strong>分析代码仓库</strong><small>识别语言、框架与构建方式</small></div></li>
            <li><span>02</span><div><strong>初始化应用规格</strong><small>生成基础端口和镜像配置</small></div></li>
            <li><span>03</span><div><strong>进入发布工作区</strong><small>继续配置环境并执行交付</small></div></li>
          </ul>
        </section>
      </aside>
    </div>

    <section v-if="result" class="surface result-card">
      <div class="surface-header">
        <div>
          <h3>应用初始化结果</h3>
          <p>创建成功后，这里会展示平台识别出的运行时与基础交付规格。</p>
        </div>
        <el-button v-if="result" type="primary" @click="router.push(`/devcenter/projects/${form.project_id}/applications/${result.id}`)">进入应用工作区</el-button>
      </div>
      <div class="result-content">
        <div class="result-overview">
          <span class="soft-pill">{{ result.language }}</span>
          <span class="soft-pill">{{ result.framework }}</span>
          <span class="soft-pill">{{ result.build_type }}</span>
          <span class="soft-pill">Port {{ result.port }}</span>
        </div>
        <pre class="code-block">{{ yaml }}</pre>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import yamlLib from 'js-yaml'
import { applicationApi } from '../api/application'
import { projectApi } from '../api/project'
import type { Application, Project } from '../types'
import PageHeader from '../components/common/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const form = reactive({ project_id: 0, name: '', repo_url: '', branch: 'main', namespace: 'default' })
const loading = ref(false)
const result = ref<Application>()
const projects = ref<Project[]>([])
const selectedProject = computed(() => projects.value.find(project => project.id === form.project_id))
const applicationsPath = computed(() => form.project_id ? `/devcenter/projects/${form.project_id}/applications` : '/devcenter')

const yaml = computed(() => result.value ? yamlLib.dump(result.value.application_spec) : '')

async function submit() {
  if (!form.project_id) return ElMessage.warning('请先选择所属项目')
  if (!form.name || !form.repo_url) return ElMessage.warning('请填写应用名称和仓库地址')
  loading.value = true
  try {
    result.value = await applicationApi.create(form.project_id, {
      name: form.name,
      repo_url: form.repo_url,
      branch: form.branch,
      namespace: form.namespace,
    })
    ElMessage.success('仓库分析完成')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (form.project_id) {
    router.push(`/devcenter/projects/${form.project_id}/applications`)
  } else {
    router.push('/devcenter')
  }
}

onMounted(async () => {
  projects.value = await projectApi.list()
  const selected = Number(route.query.projectId || 0)
  if (selected && projects.value.some(item => item.id === selected)) {
    form.project_id = selected
  } else if (projects.value.length === 1) {
    form.project_id = projects.value[0].id
  }
})
</script>

<style scoped>
.create-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 286px;
  align-items: start;
  gap: 16px;
  max-width: 1120px;
}

.form-card,
.result-card {
  box-shadow: none;
}

.create-form-card {
  min-width: 0;
}

.create-aside {
  display: grid;
  gap: 16px;
}

.context-card,
.checklist-card {
  padding: 20px;
}

.aside-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
}

.context-card h3 {
  margin: 12px 0 8px;
  font-size: 20px;
}

.context-card p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

.context-card dl {
  display: grid;
  gap: 12px;
  margin: 20px 0 0;
  padding-top: 16px;
  border-top: 1px solid var(--border-soft);
}

.context-card dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.context-card dt,
.context-card dd {
  margin: 0;
  font-size: 13px;
}

.context-card dt { color: var(--muted); }
.context-card dd { color: var(--text); font-weight: 700; }

.checklist-card ul {
  display: grid;
  gap: 18px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}

.checklist-card li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.checklist-card li > span {
  display: grid;
  flex: 0 0 26px;
  height: 26px;
  place-items: center;
  border-radius: 8px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 11px;
  font-weight: 700;
}

.checklist-card strong,
.checklist-card small {
  display: block;
}

.checklist-card strong { font-size: 13px; }
.checklist-card small { margin-top: 3px; color: var(--muted); font-size: 12px; line-height: 1.45; }

.form-body {
  padding: 8px 24px 24px;
}

.form-section-title {
  margin: 8px 0 16px;
  color: var(--text);
  font-size: 14px;
  font-weight: 700;
}

.repository-title {
  margin-top: 24px;
}

.inline-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.callout {
  margin-top: 8px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.callout strong,
.callout p {
  display: block;
}

.callout p {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.submit {
  width: 100%;
  margin-top: 18px;
}

.result-content {
  padding: 14px 24px 24px;
}

.result-overview {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .create-grid {
    grid-template-columns: 1fr;
  }

  .create-aside {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .inline-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .create-aside {
    grid-template-columns: 1fr;
  }
}
</style>
