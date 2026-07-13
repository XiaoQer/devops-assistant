<template>
  <div class="page-content">
    <PageHeader
      eyebrow="Governance system"
      title="Project Center Projects"
      description="选择一个 Project，进入对应的项目治理 Workspace。"
    />

    <section class="surface project-list">
      <div class="surface-header">
        <div>
          <h3>Accessible projects</h3>
          <p>管理项目成员、GitHub 边界、Aliyun 资源组、Kubernetes 集群与镜像仓库边界</p>
        </div>
        <div class="toolbar">
          <el-button :loading="loading" @click="load">刷新</el-button>
          <el-button type="primary" @click="openCreate">＋ Create Project</el-button>
        </div>
      </div>

      <el-skeleton :loading="loading" animated :rows="6">
        <div v-if="items.length" class="cards">
          <article v-for="project in items" :key="project.id" @click="view(project)">
            <div class="project-mark">PR</div>
            <div class="project-copy">
              <div class="project-title">
                <h3>{{ project.name }}</h3>
                <StatusBadge :status="project.status || 'active'" :label="project.status || 'active'" />
              </div>
              <p>{{ project.description || 'Project governance workspace' }}</p>
              <div class="metadata-row">
                <span>{{ project.github_group || 'No GitHub group' }}</span>
                <span>{{ aliyunSummary(project) }}</span>
              </div>
              <small>
                {{ project.members_count || project.member_count || 0 }} Members ·
                {{ project.applications_count || project.application_count || 0 }} Applications ·
                {{ project.clusters_count || 0 }} Clusters
              </small>
            </div>
            <div class="card-actions" @click.stop>
              <el-button link @click="openEdit(project)">Edit</el-button>
              <el-button link type="danger" @click="remove(project)">Delete</el-button>
              <b @click="view(project)">→</b>
            </div>
          </article>
        </div>
        <EmptyState
          v-else
          title="尚未创建 Project"
          description="Project 是成员、GitHub、Aliyun、集群和 Registry 的治理边界。"
        >
          <el-button type="primary" @click="openCreate">Create Project</el-button>
        </EmptyState>
      </el-skeleton>
    </section>

    <el-dialog
      v-model="dialog"
      :title="editing ? 'Edit Project' : 'Create Project'"
      width="780px"
      class="project-dialog"
      :close-on-click-modal="!saving"
      :close-on-press-escape="!saving"
      :before-close="handleDialogClose"
    >
      <el-form
        ref="projectForm"
        label-position="top"
        :model="form"
        :rules="rules"
        status-icon
        @submit.prevent="save"
      >
        <section class="form-section">
          <div class="section-title">
            <h4>基础信息</h4>
            <p>定义项目身份和生命周期状态。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="Project Name" prop="name">
              <el-input v-model="form.name" placeholder="Payments Platform" />
            </el-form-item>
            <el-form-item label="Project Key" prop="key">
              <el-input
                v-model="form.key"
                :disabled="Boolean(editing)"
                placeholder="payments-platform"
              />
            </el-form-item>
            <el-form-item label="Status">
              <el-select v-model="form.status">
                <el-option label="Active" value="active" />
                <el-option label="Inactive" value="inactive" />
                <el-option label="Archived" value="archived" />
              </el-select>
            </el-form-item>
            <el-form-item class="wide" label="Description">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="3"
                placeholder="这个 Project 覆盖的业务域、团队边界和交付范围"
              />
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="section-title">
            <h4>人员归属</h4>
            <p>保存业务和成本责任人；项目成员仍在 Project 详情中独立管理。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="Business Owner">
              <el-input v-model="form.business_owner" placeholder="Payments Platform Team" />
            </el-form-item>
            <el-form-item label="Billing Owner">
              <el-input v-model="form.billing_owner" placeholder="FinOps / Cost Center" />
            </el-form-item>
            <template v-if="!editing">
              <el-form-item label="Initial Owner Name">
                <el-input v-model="form.owner_name" placeholder="Alice" />
              </el-form-item>
              <el-form-item label="Initial Owner Email">
                <el-input v-model="form.owner_email" placeholder="alice@example.com" />
              </el-form-item>
              <el-form-item label="Initial Owner Title">
                <el-input v-model="form.owner_title" placeholder="Project owner" />
              </el-form-item>
            </template>
          </div>
        </section>

        <section class="form-section">
          <div class="section-title">
            <h4>GitHub 边界</h4>
            <p>记录后续初始化 GitHub team、仓库组和成员同步时使用的项目级边界。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="GitHub Group">
              <el-input v-model="form.github_group" placeholder="acme/payments-platform" />
            </el-form-item>
            <el-form-item label="Default Repository Visibility">
              <el-select v-model="form.github_default_visibility">
                <el-option label="Private" value="private" />
                <el-option label="Internal" value="internal" />
                <el-option label="Public" value="public" />
              </el-select>
            </el-form-item>
          </div>
        </section>

        <section class="form-section">
          <div class="section-title">
            <h4>Aliyun 资源绑定</h4>
            <p>保存账号、资源组、区域和 VPC 元信息；敏感凭据不进入 Project。</p>
          </div>
          <div class="form-grid">
            <el-form-item label="Aliyun Account ID">
              <el-input v-model="form.aliyun_account_id" placeholder="1234567890123456" />
            </el-form-item>
            <el-form-item label="Resource Group ID">
              <el-input v-model="form.aliyun_resource_group_id" placeholder="rg-acfm2pz25js****" />
            </el-form-item>
            <el-form-item label="Region">
              <el-input v-model="form.aliyun_region" placeholder="cn-hangzhou" />
            </el-form-item>
            <el-form-item label="VPC ID">
              <el-input v-model="form.aliyun_vpc_id" placeholder="vpc-bp1example" />
            </el-form-item>
            <el-form-item label="Binding Status">
              <el-select v-model="form.aliyun_binding_status">
                <el-option label="Unbound" value="unbound" />
                <el-option label="Pending" value="pending" />
                <el-option label="Linked" value="linked" />
                <el-option label="Failed" value="failed" />
              </el-select>
            </el-form-item>
          </div>
        </section>
      </el-form>

      <div class="submit-panel" :class="{ error: submitError }">
        <p v-if="saving">{{ submitMessage }}</p>
        <p v-else-if="submitError">{{ submitError }}</p>
        <p v-else>保存后 Project 列表会刷新，成员、集群和 Registry 仍在项目详情中管理。</p>
      </div>

      <template #footer>
        <el-button :disabled="saving" @click="dialog = false">取消</el-button>
        <el-button type="primary" native-type="submit" :loading="saving" @click="save">
          {{ saving ? '保存中' : '保存 Project' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { projectApi, type ProjectPayload } from '../api/project'
import type { Project } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const items = ref<Project[]>([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const editing = ref<Project>()
const projectForm = ref<FormInstance>()
const submitError = ref('')
const submitMessage = ref('')

const defaults: ProjectPayload = {
  key: '',
  name: '',
  description: '',
  status: 'active',
  business_owner: '',
  billing_owner: '',
  github_group: '',
  github_default_visibility: 'private',
  aliyun_account_id: '',
  aliyun_resource_group_id: '',
  aliyun_region: 'cn-hangzhou',
  aliyun_vpc_id: '',
  aliyun_binding_status: 'unbound',
  owner_name: '',
  owner_email: '',
  owner_title: '',
}

const form = reactive<ProjectPayload>({ ...defaults })

const rules: FormRules<ProjectPayload> = {
  name: [{ required: true, message: '请输入 Project Name', trigger: 'blur' }],
  key: [{ required: true, message: '请输入 Project Key', trigger: 'blur' }],
}

function aliyunSummary(project: Project) {
  const parts = [
    project.aliyun_account_id,
    project.aliyun_resource_group_id,
    project.aliyun_region,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : 'No Aliyun binding'
}

async function load() {
  loading.value = true
  try {
    items.value = await projectApi.list()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = undefined
  Object.assign(form, defaults)
  resetSubmitState()
  dialog.value = true
  nextTick(() => projectForm.value?.clearValidate())
}

function openEdit(project: Project) {
  editing.value = project
  Object.assign(form, defaults, {
    key: project.key,
    name: project.name,
    description: project.description || '',
    status: project.status || 'active',
    business_owner: project.business_owner || '',
    billing_owner: project.billing_owner || '',
    github_group: project.github_group || '',
    github_default_visibility: project.github_default_visibility || 'private',
    aliyun_account_id: project.aliyun_account_id || '',
    aliyun_resource_group_id: project.aliyun_resource_group_id || '',
    aliyun_region: project.aliyun_region || 'cn-hangzhou',
    aliyun_vpc_id: project.aliyun_vpc_id || '',
    aliyun_binding_status: project.aliyun_binding_status || 'unbound',
    owner_name: '',
    owner_email: '',
    owner_title: '',
  })
  resetSubmitState()
  dialog.value = true
  nextTick(() => projectForm.value?.clearValidate())
}

function view(project: Project) {
  router.push(`/project-center/projects/${project.id}`)
}

function compactPayload(): ProjectPayload {
  const payload: ProjectPayload = {}
  for (const [key, value] of Object.entries(form)) {
    if (editing.value && key.startsWith('owner_')) continue
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (trimmed) payload[key as keyof ProjectPayload] = trimmed
      continue
    }
    if (value !== undefined && value !== null) {
      payload[key as keyof ProjectPayload] = value
    }
  }
  return payload
}

async function save() {
  if (saving.value) return
  submitError.value = ''
  try {
    await projectForm.value?.validate()
  } catch {
    submitError.value = '请先修正表单中的必填项。'
    return
  }
  const payload = compactPayload()
  saving.value = true
  submitMessage.value = editing.value
    ? '正在更新 Project 治理元信息...'
    : '正在创建 Project 治理边界...'
  try {
    if (editing.value) {
      await projectApi.update(editing.value.id, payload)
      ElMessage.success('Project 已更新')
    } else {
      await projectApi.create(payload as ProjectPayload & { key: string; name: string })
      ElMessage.success('Project 已创建')
    }
    dialog.value = false
    await load()
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : 'Project 保存失败'
    ElMessage.error(submitError.value)
  } finally {
    saving.value = false
    submitMessage.value = ''
  }
}

function resetSubmitState() {
  submitError.value = ''
  submitMessage.value = ''
}

function handleDialogClose(done: () => void) {
  if (saving.value) return
  done()
}

async function remove(project: Project) {
  await ElMessageBox.confirm(
    `确认删除 ${project.name}？仅空 Project 可以删除。`,
    'Delete Project',
    { type: 'warning' },
  )
  await projectApi.remove(project.id)
  ElMessage.success('Project 已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.project-list {
  overflow: hidden;
}

.toolbar,
.project-title,
.card-actions,
.metadata-row {
  display: flex;
  align-items: center;
}

.toolbar {
  gap: 8px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 16px;
}

.cards article {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  cursor: pointer;
  background: var(--surface-soft);
  transition: border-color 0.2s, transform 0.2s;
}

.cards article:hover {
  border-color: #66718a;
  transform: translateY(-1px);
}

.project-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  background: rgba(20, 184, 166, 0.12);
  color: #55d6c8;
  font-size: 12px;
  font-weight: 800;
}

.project-copy {
  min-width: 0;
  flex: 1;
}

.project-title {
  gap: 8px;
  min-width: 0;
}

.project-title h3,
.cards p {
  margin: 0;
}

.project-title h3 {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.cards p,
.cards small,
.metadata-row {
  color: var(--muted);
  font-size: 11px;
}

.cards p {
  margin: 6px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cards small {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metadata-row {
  gap: 8px;
  min-width: 0;
}

.metadata-row span {
  min-width: 0;
  max-width: 50%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  gap: 3px;
  flex: 0 0 auto;
}

.card-actions b {
  padding: 6px;
  color: #14b8a6;
  cursor: pointer;
}

:deep(.project-dialog) {
  --el-dialog-bg-color: #f7f9fc;
  --el-dialog-border-radius: 10px;
  width: min(780px, calc(100vw - 40px));
  overflow: hidden;
  border: 1px solid #d8dee8 !important;
  background: #f7f9fc !important;
  box-shadow: 0 24px 70px rgba(6, 12, 24, 0.38);
}

:deep(.project-dialog .el-dialog__header) {
  margin: 0;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e2e7ef;
  background: #fff;
}

:deep(.project-dialog .el-dialog__title) {
  color: #172033;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0;
}

:deep(.project-dialog .el-dialog__headerbtn) {
  top: 14px;
  right: 16px;
}

:deep(.project-dialog .el-dialog__body) {
  max-height: min(72vh, 760px);
  padding: 18px 24px 0;
  overflow: auto;
  background: #f7f9fc;
}

:deep(.project-dialog .el-dialog__footer) {
  padding: 14px 24px 18px;
  border-top: 1px solid #e2e7ef;
  background: #fff;
}

:deep(.project-dialog .el-form-item) {
  margin-bottom: 14px;
}

:deep(.project-dialog .el-form-item__label) {
  padding-bottom: 5px;
  color: #536074;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

:deep(.project-dialog .el-input__wrapper),
:deep(.project-dialog .el-textarea__inner),
:deep(.project-dialog .el-select__wrapper) {
  min-height: 38px;
  border-radius: 7px;
  box-shadow: 0 0 0 1px #d8dee8 inset;
  background: #fff;
}

:deep(.project-dialog .el-input__wrapper:hover),
:deep(.project-dialog .el-textarea__inner:hover),
:deep(.project-dialog .el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px #b9c4d5 inset;
}

:deep(.project-dialog .el-input__wrapper.is-focus),
:deep(.project-dialog .el-textarea__inner:focus),
:deep(.project-dialog .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.12);
}

:deep(.project-dialog .el-input__inner),
:deep(.project-dialog .el-textarea__inner) {
  color: #172033;
  font-size: 13px;
}

:deep(.project-dialog .el-input__inner::placeholder),
:deep(.project-dialog .el-textarea__inner::placeholder) {
  color: #9aa4b2;
}

:deep(.project-dialog .el-button) {
  min-height: 36px;
  border-radius: 7px;
  font-weight: 700;
}

.form-section {
  margin-bottom: 14px;
  padding: 16px 16px 2px;
  border: 1px solid #e2e7ef;
  border-radius: 9px;
  background: #fff;
}

.form-section:first-child {
  padding-top: 16px;
  border-top: 1px solid #e2e7ef;
}

.section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}

.section-title h4 {
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
}

.section-title p {
  margin: 0;
  color: #7c8798;
  font-size: 12px;
  line-height: 1.5;
  text-align: right;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.submit-panel {
  min-height: 36px;
  margin: 2px 0 16px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  color: #475569;
  background: #eff6ff;
  font-size: 12px;
}

.submit-panel p {
  margin: 0;
}

.submit-panel.error {
  color: #b91c1c;
  border-color: rgba(220, 38, 38, 0.2);
  background: rgba(220, 38, 38, 0.08);
}

.wide {
  grid-column: 1 / -1;
}

@media (max-width: 900px) {
  :deep(.project-dialog .el-dialog__body) {
    max-height: 76vh;
    padding: 16px 16px 0;
  }

  :deep(.project-dialog .el-dialog__header),
  :deep(.project-dialog .el-dialog__footer) {
    padding-left: 16px;
    padding-right: 16px;
  }

  .cards,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .section-title {
    display: block;
  }

  .section-title p {
    margin-top: 4px;
    text-align: left;
  }

  .wide {
    grid-column: auto;
  }

  .card-actions .el-button {
    display: none;
  }
}
</style>
