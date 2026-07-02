<template>
  <section class="surface viewer">
    <header>
      <div>
        <small>LOG OUTPUT</small>
        <b>{{ task?.task_name || '选择一个 Task' }}</b>
      </div>
      <div class="viewer-actions">
        <el-button size="small" @click="$emit('analyze')" :disabled="task?.status !== 'Failed'">✦ AI 分析</el-button>
        <el-button size="small" @click="$emit('retry')" :disabled="task?.status !== 'Failed'">重试执行</el-button>
        <el-button size="small" @click="copy" :disabled="!selectedStep">复制日志</el-button>
      </div>
    </header>
    <nav v-if="task?.steps?.length">
      <button v-for="step in task.steps" :key="step.container" :class="{ active: selectedStep?.container === step.container }" @click="selectedStep = step">
        {{ step.step }}
      </button>
    </nav>
    <pre class="code-block log-output">{{ selectedStep?.logs || '等待日志输出…' }}</pre>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{ task?: any }>()
defineEmits<{ analyze: []; retry: [] }>()

const selectedStep = ref<any>()

watch(() => props.task, task => {
  selectedStep.value = task?.steps?.[0]
}, { immediate: true })

function copy() {
  if (!selectedStep.value) return
  navigator.clipboard.writeText(selectedStep.value.logs)
  ElMessage.success('日志已复制')
}
</script>

<style scoped>
.viewer {
  overflow: hidden;
  box-shadow: none;
}

header {
  min-height: 72px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--border-soft);
}

header small,
header b {
  display: block;
}

header small {
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--muted);
}

header b {
  font-size: 15px;
  margin-top: 6px;
}

.viewer-actions {
  display: flex;
  gap: 8px;
}

nav {
  min-height: 50px;
  padding: 0 18px;
  display: flex;
  align-items: end;
  gap: 8px;
  border-bottom: 1px solid var(--border-soft);
  overflow: auto;
}

nav button {
  min-height: 38px;
  padding: 0 14px;
  border: 0;
  border-radius: 12px 12px 0 0;
  background: none;
  color: var(--muted);
  font-size: 13px;
}

nav button.active {
  color: var(--primary);
  background: var(--primary-soft);
}

.log-output {
  min-height: 420px;
  margin: 0;
  border-radius: 0;
  border: 0;
}
</style>
