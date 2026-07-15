<template>
  <section class="execution-panel">
    <div class="execution-heading">
      <div><span>DELIVERY EXECUTIONS</span><h3>交付执行</h3></div>
      <small>{{ options.length }} 个执行</small>
    </div>

    <div class="execution-tabs" role="tablist" aria-label="交付执行">
      <button
        v-for="option in options"
        :key="option.key"
        type="button"
        role="tab"
        :aria-selected="option.key === selectedExecutionKey"
        :class="['execution-tab', { active: option.key === selectedExecutionKey }]"
        @click="$emit('select-execution', option.key)"
      >
        <strong>{{ option.label }}</strong>
        <StatusBadge :status="option.status" />
      </button>
    </div>

    <PipelineStepLogPanel
      v-if="selectedOption?.canLoadLogs"
      :eyebrow="selectedExecutionKey === 'build' ? 'BUILD PIPELINE STEPS' : 'DEPLOY PIPELINE STEPS'"
      :title="selectedExecutionKey === 'build' ? '实际构建步骤' : `${selectedOption.label} 部署步骤`"
      :steps="steps"
      :selected-step-id="selectedStepId"
      :loading="loading"
      :error="error"
      :show-header="false"
      empty-description="PipelineRun 可能仍在初始化，请稍后刷新。"
      @select-step="$emit('select-step', $event)"
      @retry="$emit('retry')"
    />

    <div v-else class="execution-waiting">
      <strong>{{ waitingTitle }}</strong>
      <p>{{ waitingDescription }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'
import PipelineStepLogPanel from './PipelineStepLogPanel.vue'
import {
  deliveryExecutionOptions,
  targetExecutionState,
  targetIdFromExecutionKey,
  type DeliveryExecutionKey,
  type ExecutionStepDetail,
} from '../../features/build-explorer/state'
import type { BuildVersion, ReleaseBatch } from '../../types'

const props = withDefaults(defineProps<{
  build: BuildVersion
  batch?: ReleaseBatch
  selectedExecutionKey: DeliveryExecutionKey
  steps: ExecutionStepDetail[]
  selectedStepId?: string
  loading?: boolean
  error?: string
}>(), { loading: false, error: '' })

defineEmits<{
  'select-execution': [key: DeliveryExecutionKey]
  'select-step': [stepId: string]
  retry: []
}>()

const options = computed(() => deliveryExecutionOptions(props.build, props.batch))
const selectedOption = computed(() => options.value.find(option => option.key === props.selectedExecutionKey))
const selectedTarget = computed(() => {
  const targetId = targetIdFromExecutionKey(props.selectedExecutionKey)
  return props.batch?.targets.find(target => target.id === targetId)
})
const waitingTitle = computed(() => {
  if (props.selectedExecutionKey === 'build') return '尚未创建构建 PipelineRun'
  return selectedTarget.value ? targetExecutionState(selectedTarget.value).description : '执行不存在'
})
const waitingDescription = computed(() => props.selectedExecutionKey === 'build'
  ? '此构建没有关联 PipelineRun。'
  : '当前环境还没有可读取的 Deploy-only PipelineRun。')
</script>

<style scoped>
.execution-panel{padding:18px 20px 20px}.execution-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.execution-heading span{color:var(--primary);font-size:9px;font-weight:800;letter-spacing:.12em}.execution-heading h3{margin:4px 0 0;font-size:16px}.execution-heading small{color:var(--muted);font-size:11px}.execution-tabs{display:flex;gap:8px;margin-top:14px;overflow-x:auto;padding:2px 2px 5px;scrollbar-width:thin}.execution-tab{min-width:150px;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 11px;border:1px solid var(--border-soft);border-radius:10px;background:var(--surface-soft);color:var(--text-2);cursor:pointer;text-align:left}.execution-tab.active{border-color:var(--primary);background:var(--surface);box-shadow:0 0 0 2px var(--primary-soft)}.execution-tab strong{overflow:hidden;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.execution-panel :deep(.step-log-panel){padding:10px 0 0}.execution-waiting{margin-top:10px;padding:24px;border:1px dashed var(--border);border-radius:10px;color:var(--muted);text-align:center}.execution-waiting p{margin:6px 0 0;font-size:12px}@media(max-width:600px){.execution-panel{padding:15px 14px 16px}.execution-tab{min-width:132px}}
</style>
