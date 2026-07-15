<template>
  <el-drawer :model-value="modelValue" :title="title" size="62%" @close="$emit('update:modelValue', false)">
    <div class="drawer-tools">
      <el-button :disabled="!content" @click="copy">复制</el-button>
    </div>
    <el-skeleton :loading="loading" animated :rows="12">
      <pre class="resource-output">{{ content }}</pre>
    </el-skeleton>
  </el-drawer>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const props = defineProps<{
  modelValue: boolean
  title: string
  content: string
  loading?: boolean
}>()
defineEmits<{ 'update:modelValue': [value: boolean] }>()

async function copy() {
  await navigator.clipboard.writeText(props.content)
  ElMessage.success('内容已复制')
}
</script>

<style scoped>
.drawer-tools { display: flex; justify-content: flex-end; margin-bottom: 12px; }
.resource-output {
  min-height: 420px; margin: 0; padding: 18px; overflow: auto; border-radius: 12px;
  background: #111827; color: #d1fae5; font: 12px/1.65 ui-monospace, SFMono-Regular, Menlo, monospace;
  white-space: pre-wrap; word-break: break-word;
}
</style>
