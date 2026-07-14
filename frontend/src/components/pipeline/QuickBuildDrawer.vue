<template>
  <el-drawer
    :model-value="modelValue"
    size="520px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @open="loadBranches"
  >
    <template #header>
      <div class="drawer-title">
        <small>快速构建</small>
        <h3>{{ application?.name || '选择 Application' }}</h3>
        <p>选择精确 Commit；目标环境可留空，仅生成构建版本。</p>
      </div>
    </template>

    <el-skeleton :loading="loadingBranches" animated :rows="6">
      <el-alert
        v-if="loadError"
        :title="loadError"
        type="error"
        show-icon
        :closable="false"
        class="drawer-alert"
      >
        <el-button size="small" @click="loadBranches">重新加载</el-button>
      </el-alert>

      <el-form v-else label-position="top" @submit.prevent>
        <el-form-item label="Branch" required>
          <el-select
            v-model="branch"
            filterable
            class="full-width"
            :loading="loadingBranches"
            @change="loadCommits"
          >
            <el-option
              v-for="item in branches"
              :key="item.name"
              :label="item.name === application?.branch ? `${item.name}（默认）` : item.name"
              :value="item.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Commit" required>
          <el-select
            v-model="commitSha"
            filterable
            class="full-width"
            :loading="loadingCommits"
            no-data-text="该分支没有可用 Commit"
          >
            <el-option
              v-for="(item, index) in commits"
              :key="item.sha"
              :label="`${shortSha(item.sha)}${index === 0 ? '（最新）' : ''} · ${item.message}`"
              :value="item.sha"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="发布到环境（可选）">
          <el-select
            v-model="environmentIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            class="full-width"
            placeholder="不选择则仅构建"
          >
            <el-option
              v-for="environment in environments"
              :key="environment.id"
              :label="environmentLabel(environment)"
              :value="environment.id"
            />
          </el-select>
          <p class="field-help">构建成功后自动发布；需要审批的环境会先等待审批。</p>
        </el-form-item>

        <section v-if="selectedCommit" class="commit-summary">
          <small>本次构建</small>
          <strong>{{ shortSha(selectedCommit.sha) }} · {{ selectedCommit.message }}</strong>
          <span>{{ selectedCommit.author }} · {{ format(selectedCommit.authored_at) }}</span>
          <code>{{ application?.image_name }}:{{ shortSha(selectedCommit.sha) }}</code>
        </section>
      </el-form>
    </el-skeleton>

    <template #footer>
      <div class="drawer-actions">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!application || !branch || !commitSha || loadingCommits"
          @click="submit"
        >
          确认并开始构建
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { applicationApi } from '../../api/application'
import type {
  Application,
  ApplicationEnvironment,
  GitBranch,
  GitCommit,
  ReleaseBatch,
} from '../../types'

const props = defineProps<{
  modelValue: boolean
  projectId: number
  application?: Application
  environments: ApplicationEnvironment[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submitted: [batch: ReleaseBatch]
}>()

const branches = ref<GitBranch[]>([])
const commits = ref<GitCommit[]>([])
const branch = ref('')
const commitSha = ref('')
const environmentIds = ref<number[]>([])
const loadingBranches = ref(false)
const loadingCommits = ref(false)
const submitting = ref(false)
const loadError = ref('')

const selectedCommit = computed(() => (
  commits.value.find(item => item.sha === commitSha.value)
))

async function loadBranches() {
  if (!props.application) return
  loadingBranches.value = true
  loadError.value = ''
  environmentIds.value = []
  try {
    branches.value = await applicationApi.gitBranches(
      props.projectId,
      props.application.id,
    )
    branch.value = branches.value.some(item => item.name === props.application?.branch)
      ? props.application.branch
      : branches.value[0]?.name || ''
    await loadCommits()
  } catch (error) {
    loadError.value = (error as Error).message
  } finally {
    loadingBranches.value = false
  }
}

async function loadCommits() {
  if (!props.application || !branch.value) return
  loadingCommits.value = true
  loadError.value = ''
  commitSha.value = ''
  try {
    commits.value = await applicationApi.gitCommits(
      props.projectId,
      props.application.id,
      branch.value,
      20,
    )
    commitSha.value = commits.value[0]?.sha || ''
  } catch (error) {
    commits.value = []
    loadError.value = (error as Error).message
  } finally {
    loadingCommits.value = false
  }
}

async function submit() {
  if (!props.application || !branch.value || !commitSha.value) return
  submitting.value = true
  try {
    const batch = await applicationApi.createReleaseBatch(
      props.projectId,
      props.application.id,
      {
        branch: branch.value,
        git_commit: commitSha.value,
        environment_ids: environmentIds.value,
      },
    )
    emit('submitted', batch)
    emit('update:modelValue', false)
    ElMessage.success(
      environmentIds.value.length
        ? '构建已触发，成功后将自动推进所选环境'
        : '构建已触发，本次仅生成构建版本',
    )
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    submitting.value = false
  }
}

function shortSha(value: string) {
  return value.slice(0, 8)
}

function format(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function environmentLabel(environment: ApplicationEnvironment) {
  const name = environment.display_name || environment.environment_name
  return environment.approval_required ? `${name}（需审批）` : name
}
</script>

<style scoped>
.drawer-title small,
.commit-summary small {
  color: var(--primary);
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.drawer-title h3 {
  margin: 5px 0;
  font-size: 22px;
}

.drawer-title p,
.field-help {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.full-width {
  width: 100%;
}

.drawer-alert {
  margin-bottom: 18px;
}

.commit-summary {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--surface-soft);
}

.commit-summary span,
.commit-summary code {
  color: var(--muted);
  font-size: 12px;
}

.commit-summary code {
  word-break: break-all;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
