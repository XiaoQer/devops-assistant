<template>
  <div class="page-content page-stack">
    <el-skeleton v-if="loading && !project" animated :rows="8" />
    <template v-else-if="project">
      <PageHeader
        eyebrow="Project governance"
        :title="project.name"
        description="按类别查看和维护 Project 本体治理信息。Kubernetes 与 Registry 通过独立菜单管理。"
      >
        <el-button @click="refresh" :loading="loading">刷新</el-button>
        <el-button @click="router.push(`/project-center/projects/${projectId}/clusters`)">Kubernetes 配置</el-button>
        <el-button @click="router.push(`/project-center/projects/${projectId}/registries`)">Registries 配置</el-button>
      </PageHeader>

      <section class="surface overview-panel">
        <div class="overview-main">
          <span class="overview-label">Project summary</span>
          <h3>{{ project.name }}</h3>
          <p>{{ display(project.description, '这个 Project 还没有补充描述。') }}</p>
        </div>
        <div class="overview-fields">
          <div class="summary-item strong">
            <small>Project Key</small>
            <b>{{ project.key }}</b>
          </div>
          <div class="summary-item">
            <small>Status</small>
            <b><span class="status-dot"></span>{{ project.status || 'active' }}</b>
          </div>
          <div class="summary-item">
            <small>Owner</small>
            <b>{{ display(project.business_owner || project.billing_owner) }}</b>
          </div>
          <div class="summary-item">
            <small>GitHub</small>
            <b>{{ display(project.github_group) }}</b>
          </div>
          <div class="summary-item">
            <small>Aliyun</small>
            <b>{{ display(project.aliyun_region) }} · {{ project.aliyun_binding_status || 'unbound' }}</b>
          </div>
        </div>
      </section>

      <section class="surface settings-panel">
        <article class="setting-row">
          <div class="setting-meta">
            <div class="setting-title">
              <span class="category-icon">Ⅰ</span>
              <div>
                <h3>基础信息</h3>
                <p>描述项目治理范围和生命周期状态。</p>
              </div>
            </div>
          </div>
          <div class="setting-content">
            <div v-if="editingSection === 'basic'" class="edit-body">
              <el-form label-position="top">
                <el-form-item label="Status">
                  <el-select v-model="form.status">
                    <el-option label="Active" value="active" />
                    <el-option label="Inactive" value="inactive" />
                    <el-option label="Archived" value="archived" />
                  </el-select>
                </el-form-item>
                <el-form-item label="Description">
                  <el-input v-model="form.description" type="textarea" :rows="3" />
                </el-form-item>
              </el-form>
            </div>
            <dl v-else class="detail-list">
              <div class="wide-row"><dt>Description</dt><dd>{{ display(project.description) }}</dd></div>
              <div><dt>Status</dt><dd><span class="value-pill">{{ project.status || 'active' }}</span></dd></div>
            </dl>
          </div>
          <div class="category-actions">
            <template v-if="editingSection === 'basic'">
              <el-button :disabled="saving" @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" @click="saveSection('basic')">保存</el-button>
            </template>
            <el-button v-else @click="startEdit('basic')">修改</el-button>
          </div>
        </article>

        <article class="setting-row">
          <div class="setting-meta">
            <div class="setting-title">
              <span class="category-icon">Ⅱ</span>
              <div>
                <h3>Owner 归属</h3>
                <p>记录业务和成本责任人，不替代成员权限管理。</p>
              </div>
            </div>
          </div>
          <div class="setting-content">
            <div v-if="editingSection === 'owners'" class="edit-body">
              <el-form label-position="top">
                <div class="form-grid">
                  <el-form-item label="Business Owner">
                    <el-input v-model="form.business_owner" placeholder="Payments Platform Team" />
                  </el-form-item>
                  <el-form-item label="Billing Owner">
                    <el-input v-model="form.billing_owner" placeholder="FinOps / Cost Center" />
                  </el-form-item>
                </div>
              </el-form>
            </div>
            <dl v-else class="detail-list">
              <div><dt>Business Owner</dt><dd>{{ display(project.business_owner) }}</dd></div>
              <div><dt>Billing Owner</dt><dd>{{ display(project.billing_owner) }}</dd></div>
            </dl>
          </div>
          <div class="category-actions">
            <template v-if="editingSection === 'owners'">
              <el-button :disabled="saving" @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" @click="saveSection('owners')">保存</el-button>
            </template>
            <el-button v-else @click="startEdit('owners')">修改</el-button>
          </div>
        </article>

        <article class="setting-row">
          <div class="setting-meta">
            <div class="setting-title">
              <span class="category-icon">Ⅲ</span>
              <div>
                <h3>GitHub 边界</h3>
                <p>保存后续初始化 GitHub team / repo group 的边界元信息。</p>
              </div>
            </div>
          </div>
          <div class="setting-content">
            <div v-if="editingSection === 'github'" class="edit-body">
              <el-form label-position="top">
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
              </el-form>
            </div>
            <dl v-else class="detail-list">
              <div><dt>GitHub Group</dt><dd>{{ display(project.github_group) }}</dd></div>
              <div><dt>Default Visibility</dt><dd><span class="value-pill">{{ project.github_default_visibility || 'private' }}</span></dd></div>
            </dl>
          </div>
          <div class="category-actions">
            <template v-if="editingSection === 'github'">
              <el-button :disabled="saving" @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" @click="saveSection('github')">保存</el-button>
            </template>
            <el-button v-else @click="startEdit('github')">修改</el-button>
          </div>
        </article>

        <article class="setting-row">
          <div class="setting-meta">
            <div class="setting-title">
              <span class="category-icon">Ⅳ</span>
              <div>
                <h3>Aliyun 资源绑定</h3>
                <p>只保存账号、资源组、区域和 VPC 等可展示元信息；不保存凭据。</p>
              </div>
            </div>
          </div>
          <div class="setting-content">
            <div v-if="editingSection === 'aliyun'" class="edit-body">
              <el-form label-position="top">
                <div class="form-grid aliyun-form-grid">
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
              </el-form>
            </div>
            <dl v-else class="detail-list aliyun-list">
              <div><dt>Account ID</dt><dd>{{ display(project.aliyun_account_id) }}</dd></div>
              <div><dt>Resource Group</dt><dd>{{ display(project.aliyun_resource_group_id) }}</dd></div>
              <div><dt>Region</dt><dd>{{ display(project.aliyun_region) }}</dd></div>
              <div><dt>VPC</dt><dd>{{ display(project.aliyun_vpc_id) }}</dd></div>
              <div><dt>Binding Status</dt><dd><span class="value-pill">{{ project.aliyun_binding_status || 'unbound' }}</span></dd></div>
            </dl>
          </div>
          <div class="category-actions">
            <template v-if="editingSection === 'aliyun'">
              <el-button :disabled="saving" @click="cancelEdit">取消</el-button>
              <el-button type="primary" :loading="saving" @click="saveSection('aliyun')">保存</el-button>
            </template>
            <el-button v-else @click="startEdit('aliyun')">修改</el-button>
          </div>
        </article>
      </section>

      <section class="surface resource-panel">
        <div class="resource-head">
          <div>
            <h3>关联资源管理</h3>
            <p>Kubernetes 集群和 Registry 作为 Project 子资源在独立页面维护。</p>
          </div>
        </div>
        <div class="resource-list">
          <article class="resource-row" @click="router.push(`/project-center/projects/${projectId}/clusters`)">
            <div>
              <h4>Kubernetes environments</h4>
              <p>维护项目可用集群、默认集群和 kube context。</p>
            </div>
            <span class="resource-type">Project subresource</span>
            <b>进入配置 →</b>
          </article>
          <article class="resource-row" @click="router.push(`/project-center/projects/${projectId}/registries`)">
            <div>
              <h4>Container registries</h4>
              <p>维护项目镜像仓库、默认 Registry 和拉取凭据。</p>
            </div>
            <span class="resource-type">Project subresource</span>
            <b>进入配置 →</b>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/common/PageHeader.vue'
import { projectApi, type ProjectPayload } from '../api/project'
import { useProjectStore } from '../stores/project'
import type { Project } from '../types'

type Section = 'basic' | 'owners' | 'github' | 'aliyun'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const project = ref<Project>()
const loading = ref(false)
const saving = ref(false)
const editingSection = ref<Section>()
const projectId = computed(() => Number(route.params.id))

const form = reactive<Required<Pick<ProjectPayload,
  'description' |
  'status' |
  'business_owner' |
  'billing_owner' |
  'github_group' |
  'github_default_visibility' |
  'aliyun_account_id' |
  'aliyun_resource_group_id' |
  'aliyun_region' |
  'aliyun_vpc_id' |
  'aliyun_binding_status'
>>>({
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
})

async function refresh() {
  loading.value = true
  try {
    const item = await projectApi.get(projectId.value)
    project.value = item
    syncForm(item)
    projectStore.setActiveProject(projectId.value)
    await projectStore.load()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}

function syncForm(item: Project) {
  Object.assign(form, {
    description: item.description || '',
    status: item.status || 'active',
    business_owner: item.business_owner || '',
    billing_owner: item.billing_owner || '',
    github_group: item.github_group || '',
    github_default_visibility: item.github_default_visibility || 'private',
    aliyun_account_id: item.aliyun_account_id || '',
    aliyun_resource_group_id: item.aliyun_resource_group_id || '',
    aliyun_region: item.aliyun_region || 'cn-hangzhou',
    aliyun_vpc_id: item.aliyun_vpc_id || '',
    aliyun_binding_status: item.aliyun_binding_status || 'unbound',
  })
}

function display(value?: string | null, fallback = '未配置') {
  return value || fallback
}

function startEdit(section: Section) {
  if (project.value) syncForm(project.value)
  editingSection.value = section
}

function cancelEdit() {
  if (project.value) syncForm(project.value)
  editingSection.value = undefined
}

function sectionPayload(section: Section): ProjectPayload {
  if (section === 'basic') {
    return {
      description: form.description.trim(),
      status: form.status,
    }
  }
  if (section === 'owners') {
    return {
      business_owner: form.business_owner.trim(),
      billing_owner: form.billing_owner.trim(),
    }
  }
  if (section === 'github') {
    return {
      github_group: form.github_group.trim(),
      github_default_visibility: form.github_default_visibility,
    }
  }
  return {
    aliyun_account_id: form.aliyun_account_id.trim(),
    aliyun_resource_group_id: form.aliyun_resource_group_id.trim(),
    aliyun_region: form.aliyun_region.trim(),
    aliyun_vpc_id: form.aliyun_vpc_id.trim(),
    aliyun_binding_status: form.aliyun_binding_status,
  }
}

async function saveSection(section: Section) {
  saving.value = true
  try {
    const updated = await projectApi.update(projectId.value, sectionPayload(section))
    project.value = updated
    syncForm(updated)
    editingSection.value = undefined
    await projectStore.load()
    ElMessage.success('Project 治理信息已保存')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  projectStore.init()
  await refresh()
})
</script>

<style scoped>
.overview-panel,
.settings-panel,
.resource-panel {
  box-shadow: none;
}

.overview-panel {
  display: grid;
  grid-template-columns: minmax(260px, 0.65fr) minmax(0, 1.35fr);
  align-items: center;
  gap: 20px;
  padding: 18px 22px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
}

.overview-main {
  min-width: 0;
}

.overview-label {
  display: block;
  margin-bottom: 7px;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.overview-main h3 {
  margin: 0 0 6px;
  color: #111827;
  font-size: 20px;
  line-height: 1.2;
}

.overview-main p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.overview-fields {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  min-width: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  overflow: hidden;
  background: #f8fafc;
}

.summary-item {
  min-width: 0;
  padding: 12px 14px;
  background: #fff;
}

.summary-item + .summary-item {
  border-left: 1px solid rgba(15, 23, 42, 0.08);
}

.summary-item.strong {
  background: #f8fafc;
}

.summary-item small,
.summary-item b,
.detail-list dt,
.detail-list dd {
  display: block;
}

.summary-item small,
.detail-list dt {
  margin-bottom: 5px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.summary-item b,
.detail-list dd {
  min-width: 0;
  overflow-wrap: anywhere;
}

.summary-item b {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 800;
}

.status-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #22c55e;
}

.detail-list dd {
  color: #111827;
  font-size: 13px;
  line-height: 1.35;
}

.settings-panel {
  overflow: hidden;
  padding: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.92);
}

.setting-row {
  display: grid;
  grid-template-columns: minmax(220px, 0.72fr) minmax(0, 1.65fr) auto;
  gap: 18px;
  align-items: start;
  min-height: 92px;
  padding: 18px 22px;
}

.setting-row + .setting-row {
  border-top: 1px solid rgba(15, 23, 42, 0.07);
}

.setting-row:hover {
  background: #fbfdff;
}

.setting-meta {
  min-width: 0;
}

.setting-title {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.setting-content {
  min-width: 0;
}

.setting-title h3 {
  margin: 0 0 5px;
  color: #111827;
  font-size: 15px;
  line-height: 1.25;
}

.setting-title p {
  max-width: 560px;
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.35;
}

.category-icon {
  display: inline-grid;
  place-items: center;
  min-width: 26px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.12);
  color: #0f766e;
  font-size: 11px;
  font-weight: 800;
}

.category-actions {
  display: flex;
  gap: 6px;
  flex: 0 0 auto;
}

.category-actions :deep(.el-button) {
  min-height: 30px;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 700;
}

.detail-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 18px;
  margin: 0;
  padding: 0;
}

.detail-list > div {
  min-height: 0;
  padding: 0;
  border-bottom: none;
}

.detail-list .wide-row {
  grid-column: 1 / -1;
}

.aliyun-list {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.value-pill {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.12);
  color: #0f766e;
  font-size: 11px;
  font-weight: 800;
}

.edit-body {
  margin: 0;
  padding: 14px 14px 0;
  border: 1px solid rgba(20, 184, 166, 0.18);
  border-radius: 12px;
  background: rgba(240, 253, 250, 0.46);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.aliyun-form-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.resource-panel {
  overflow: hidden;
  padding: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
}

.resource-head {
  padding: 14px 18px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
}

.resource-head h3 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 15px;
}

.resource-head p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.resource-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px 110px;
  align-items: center;
  gap: 14px;
  min-height: 62px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background 0.2s;
}

.resource-row + .resource-row {
  border-top: 1px solid rgba(15, 23, 42, 0.07);
}

.resource-row:hover {
  background: #fbfdff;
}

.resource-row h4 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 14px;
}

.resource-row p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.resource-type {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.resource-row b {
  justify-self: end;
  color: #2563eb;
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .overview-panel,
  .overview-fields,
  .setting-row,
  .detail-list,
  .aliyun-list,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .summary-item + .summary-item {
    border-top: 1px solid rgba(15, 23, 42, 0.08);
    border-left: 0;
  }

  .resource-row {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }
}
</style>
