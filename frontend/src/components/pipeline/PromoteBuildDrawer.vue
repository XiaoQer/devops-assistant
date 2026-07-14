<template>
  <el-drawer
    :model-value="modelValue"
    size="480px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @open="selectedIds = []"
  >
    <template #header>
      <div class="drawer-title">
        <small>发布构建版本</small>
        <h3>{{ application.name }}</h3>
        <p>{{ build.image }}</p>
      </div>
    </template>

    <el-alert
      v-if="build.status !== 'Succeeded'"
      title="只有成功的构建版本才能追加发布环境"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-form label-position="top" @submit.prevent>
      <el-form-item label="追加发布环境" required>
        <el-select
          v-model="selectedIds"
          multiple
          class="full-width"
          placeholder="选择尚未关联的环境"
          :disabled="build.status !== 'Succeeded'"
        >
          <el-option
            v-for="environment in availableEnvironments"
            :key="environment.id"
            :label="environmentLabel(environment)"
            :value="environment.id"
          />
        </el-select>
        <p class="field-help">追加环境会复用当前镜像，不会重新构建。</p>
      </el-form-item>
    </el-form>

    <el-empty
      v-if="!availableEnvironments.length"
      description="所有环境都已关联到这个构建版本"
      :image-size="72"
    />

    <template #footer>
      <div class="drawer-actions">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="build.status !== 'Succeeded' || !selectedIds.length"
          @click="submit"
        >
          确认发布
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
  BuildVersion,
  ReleaseBatch,
} from '../../types'

const props = defineProps<{
  modelValue: boolean
  projectId: number
  application: Application
  build: BuildVersion
  batch: ReleaseBatch
  environments: ApplicationEnvironment[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submitted: [batch: ReleaseBatch]
}>()

const selectedIds = ref<number[]>([])
const submitting = ref(false)
const associatedIds = computed(() => new Set(
  props.batch.targets.map(target => target.environment_id),
))
const availableEnvironments = computed(() => (
  props.environments.filter(item => !associatedIds.value.has(item.id))
))

async function submit() {
  if (!selectedIds.value.length || props.build.status !== 'Succeeded') return
  submitting.value = true
  try {
    const batch = await applicationApi.addReleaseBatchTargets(
      props.projectId,
      props.application.id,
      props.batch.id,
      selectedIds.value,
    )
    emit('submitted', batch)
    emit('update:modelValue', false)
    ElMessage.success('发布环境已追加')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    submitting.value = false
  }
}

function environmentLabel(environment: ApplicationEnvironment) {
  const name = environment.display_name || environment.environment_name
  return environment.approval_required ? `${name}（需审批）` : name
}
</script>

<style scoped>
.drawer-title small {
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
  word-break: break-all;
}

.full-width {
  width: 100%;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
