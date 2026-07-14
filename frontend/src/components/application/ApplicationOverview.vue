<template>
  <div class="overview-stack">
    <section class="surface info-card">
      <div class="surface-header">
        <div>
          <h3>Application information</h3>
          <p>面向交付决策的基础信息摘要</p>
        </div>
      </div>
      <dl class="info-grid">
        <div>
          <dt>Language</dt>
          <dd>{{ application.language }}</dd>
        </div>
        <div>
          <dt>Framework</dt>
          <dd>{{ application.framework }}</dd>
        </div>
        <div>
          <dt>Build type</dt>
          <dd>{{ application.build_type }}</dd>
        </div>
        <div>
          <dt>Service port</dt>
          <dd>{{ application.port }}</dd>
        </div>
        <div>
          <dt>Namespace</dt>
          <dd>{{ application.namespace }}</dd>
        </div>
        <div>
          <dt>Branch</dt>
          <dd>{{ application.branch }}</dd>
        </div>
      </dl>
    </section>

    <el-collapse class="spec-collapse">
      <el-collapse-item name="spec">
        <template #title><span class="spec-title">Application Spec</span><span class="spec-hint">声明式定义 · 开发诊断</span></template>
        <div class="spec-toolbar"><span>平台生成的应用定义，可用于排查构建和部署参数。</span><el-button link type="primary" @click="copy">复制</el-button></div>
        <pre class="code-block spec-block">{{ spec }}</pre>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import yaml from 'js-yaml'
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { Application } from '../../types'

const props = defineProps<{ application: Application }>()
const spec = computed(() => yaml.dump(props.application.application_spec || {}))

function copy() {
  navigator.clipboard.writeText(spec.value)
  ElMessage.success('Application Spec 已复制')
}
</script>

<style scoped>
.overview-stack {
  display: grid;
  gap: 12px;
}

.info-card,
.spec-collapse {
  overflow: hidden;
  box-shadow: none;
}

.info-card dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  margin: 0;
  padding: 4px 24px 18px;
}

.info-card dl div {
  padding: 12px 18px 12px 0;
  border-bottom: 1px solid var(--border-soft);
}

dt {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 8px;
}

.dd,
dd {
  margin: 0;
  font-size: 13px;
  color: var(--text-2);
  font-weight: 600;
  word-break: break-word;
}

.spec-collapse :deep(.el-collapse-item__header) {
  padding: 0 20px;
  color: var(--text-2);
  font-weight: 700;
}

.spec-title {
  margin-right: 12px;
}

.spec-hint {
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
}

.spec-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  color: var(--muted);
  font-size: 12px;
}

.spec-block {
  margin: 0 20px 18px;
  max-height: 300px;
  overflow: auto;
}

@media (max-width: 1000px) {
  .info-card dl {
    grid-template-columns: 1fr;
  }
}
</style>
