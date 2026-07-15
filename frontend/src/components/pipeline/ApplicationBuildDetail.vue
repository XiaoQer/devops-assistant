<template>
  <section ref="detailElement" class="build-detail surface">
    <el-skeleton :loading="loading" animated :rows="10">
      <template v-if="build">
        <header class="detail-head">
          <div>
            <span>SELECTED BUILD</span>
            <h2>{{ build.version }}</h2>
            <p>{{ build.commit_message || '没有 Commit message' }}</p>
          </div>
          <StatusBadge :status="build.status" />
        </header>

        <dl class="build-facts">
          <div><dt>镜像版本</dt><dd>{{ build.image }}</dd></div>
          <div><dt>代码版本</dt><dd>{{ build.git_branch }} · {{ build.git_commit || '未锁定提交' }}</dd></div>
          <div><dt>PipelineRun</dt><dd>{{ build.pipeline_run_name || '尚未创建' }}</dd></div>
          <div><dt>触发人</dt><dd>{{ build.created_by }}</dd></div>
          <div><dt>开始时间</dt><dd>{{ format(build.created_at) }}</dd></div>
          <div><dt>结束时间</dt><dd>{{ format(build.finished_at) }}</dd></div>
        </dl>

        <p v-if="build.error_message" class="build-error">{{ build.error_message }}</p>

        <DeliveryExecutionPanel
          :build="build"
          :batch="batch"
          :selected-execution-key="selectedExecutionKey"
          :steps="steps"
          :selected-step-id="selectedStepId"
          :loading="executionLoading"
          :error="logsError"
          @select-execution="$emit('select-execution', $event)"
          @select-step="$emit('select-step', $event)"
          @retry="$emit('retry-logs')"
        />
      </template>
    </el-skeleton>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'
import DeliveryExecutionPanel from './DeliveryExecutionPanel.vue'
import type { BuildVersion, ReleaseBatch } from '../../types'
import type { DeliveryExecutionKey, ExecutionStepDetail } from '../../features/build-explorer/state'

defineProps<{
  build?: BuildVersion
  steps: ExecutionStepDetail[]
  selectedStepId?: string
  loading: boolean
  executionLoading?: boolean
  logsError?: string
  batch?: ReleaseBatch
  selectedExecutionKey: DeliveryExecutionKey
}>()

defineEmits<{
  'select-step': [stepId: string]
  'retry-logs': []
  'select-execution': [key: DeliveryExecutionKey]
}>()

const detailElement = ref<HTMLElement>()
defineExpose({
  scrollIntoView: () => detailElement.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
})

function format(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

</script>

<style scoped>
.build-detail {
  min-width: 0;
  overflow: hidden;
  box-shadow: none;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.detail-head {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-soft);
}

.detail-head span {
  color: var(--primary);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .12em;
}

.detail-head h2 {
  margin: 5px 0 0;
  font-size: 23px;
}

.detail-head p {
  margin: 7px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.build-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  background: var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.build-facts div {
  min-width: 0;
  padding: 13px 16px;
  background: var(--surface);
}

.build-facts dt {
  color: var(--subtle);
  font-size: 10px;
}

.build-facts dd {
  margin: 5px 0 0;
  overflow: hidden;
  color: var(--text-2);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.build-error {
  margin: 14px 20px 0;
  padding: 10px 12px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--danger) 8%, transparent);
  color: var(--danger);
  font-size: 12px;
}

@media (max-width: 1000px) {
  .build-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .build-facts {
    grid-template-columns: 1fr;
  }
}
</style>
