<template>
  <div class="overview-grid">
    <section class="surface info-card">
      <div class="surface-header">
        <div>
          <h3>Application information</h3>
          <p>面向交付决策的基础信息摘要</p>
        </div>
      </div>
      <dl>
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

    <section class="surface spec-card">
      <div class="surface-header">
        <div>
          <h3>Application spec</h3>
          <p>平台生成的声明式应用定义</p>
        </div>
        <el-button link type="primary" @click="copy">复制</el-button>
      </div>
      <pre class="code-block spec-block">{{ spec }}</pre>
    </section>
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
.overview-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 16px;
}

.info-card,
.spec-card {
  overflow: hidden;
  box-shadow: none;
}

.info-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
  margin: 0;
  padding: 8px 24px 24px;
}

.info-card dl div {
  padding: 16px 0;
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
  font-size: 14px;
  color: var(--text-2);
  font-weight: 600;
  word-break: break-word;
}

.spec-block {
  margin: 0 24px 24px;
  min-height: 360px;
}

@media (max-width: 1000px) {
  .overview-grid,
  .info-card dl {
    grid-template-columns: 1fr;
  }
}
</style>
