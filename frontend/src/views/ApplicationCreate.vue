<template>
  <div class="page-content page-stack">
    <PageHeader
      eyebrow="Create workspace"
      title="Create application"
      description="先描述你想交付什么，再让平台自动识别技术栈、生成应用工作区与交付基础配置。"
    />

    <div class="create-grid">
      <section class="surface hero-card glass-card">
        <span class="soft-pill">AI assisted setup</span>
        <h2>Describe the software you want to ship</h2>
        <p>把创建流程从“填很多表”变成“表达意图 + 连接代码仓库”。平台会自动推断运行时、构建方式与默认部署配置。</p>
        <div class="intent-box">
          <textarea v-model="intent" placeholder="Create a Java 21 Spring Boot service for order management"></textarea>
          <div class="intent-suggestions">
            <button v-for="item in suggestions" :key="item.label" @click="applySuggestion(item)">{{ item.label }}</button>
          </div>
        </div>
      </section>

      <section class="surface form-card">
        <div class="surface-header">
          <div>
            <h3>Repository connection</h3>
            <p>保留少量必需信息，其余交给平台自动识别。</p>
          </div>
        </div>
        <div class="form-body">
          <el-form label-position="top" :model="form">
            <el-form-item label="应用名称">
              <el-input v-model="form.name" placeholder="order-api" />
            </el-form-item>
            <el-form-item label="GitHub 仓库地址">
              <el-input v-model="form.repo_url" placeholder="https://github.com/org/repo.git" />
            </el-form-item>
            <div class="inline-grid">
              <el-form-item label="分支">
                <el-input v-model="form.branch" />
              </el-form-item>
              <el-form-item label="Namespace">
                <el-input v-model="form.namespace" />
              </el-form-item>
            </div>
            <div class="callout">
              <strong>平台默认行为</strong>
              <p>自动克隆仓库、识别语言与框架、生成 Application Spec，并为后续交付设置合理默认值。</p>
            </div>
            <el-button class="submit" type="primary" :loading="loading" @click="submit">分析并创建应用</el-button>
          </el-form>
        </div>
      </section>
    </div>

    <section class="surface result-card">
      <div class="surface-header">
        <div>
          <h3>Recognition result</h3>
          <p>创建成功后，这里会展示平台自动识别出的运行时与交付规格。</p>
        </div>
        <el-button v-if="result" type="primary" @click="router.push(`/applications/${result.id}`)">进入应用工作区</el-button>
      </div>
      <div v-if="result" class="result-content">
        <div class="result-overview">
          <span class="soft-pill">{{ result.language }}</span>
          <span class="soft-pill">{{ result.framework }}</span>
          <span class="soft-pill">{{ result.build_type }}</span>
          <span class="soft-pill">Port {{ result.port }}</span>
        </div>
        <pre class="code-block">{{ yaml }}</pre>
      </div>
      <EmptyState v-else title="等待仓库分析结果" description="提交仓库后，平台会在这里生成软件工作区摘要与 Application Spec。" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import yamlLib from 'js-yaml'
import { applicationApi } from '../api/application'
import type { Application } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const form = reactive({ name: '', repo_url: '', branch: 'main', namespace: 'default' })
const loading = ref(false)
const result = ref<Application>()
const intent = ref('')

const suggestions = [
  {
    label: 'Spring Boot service',
    intent: 'Create a Java 21 Spring Boot service for order management',
    name: 'order-service',
  },
  {
    label: 'Node.js API',
    intent: 'Create a Node.js API for payment orchestration',
    name: 'payment-api',
  },
  {
    label: 'Frontend app',
    intent: 'Create a Vue frontend for internal operations',
    name: 'ops-web',
  },
]

const yaml = computed(() => result.value ? yamlLib.dump(result.value.application_spec) : '')

function applySuggestion(item: { label: string; intent: string; name: string }) {
  intent.value = item.intent
  if (!form.name) form.name = item.name
}

async function submit() {
  if (!form.name || !form.repo_url) return ElMessage.warning('请填写应用名称和仓库地址')
  loading.value = true
  try {
    result.value = await applicationApi.create(form)
    ElMessage.success('仓库分析完成')
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.create-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(420px, 0.95fr);
  gap: 16px;
}

.hero-card,
.form-card,
.result-card {
  box-shadow: none;
}

.hero-card {
  padding: 24px;
}

.hero-card h2 {
  margin: 16px 0 10px;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -0.05em;
}

.hero-card p {
  margin: 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.8;
}

.intent-box {
  margin-top: 24px;
}

.intent-box textarea {
  width: 100%;
  min-height: 180px;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: var(--theme-panel);
  color: var(--text);
  resize: vertical;
  outline: none;
  font: inherit;
  line-height: 1.7;
}

.intent-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.intent-suggestions button {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  cursor: pointer;
}

.form-body {
  padding: 8px 24px 24px;
}

.inline-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.callout {
  margin-top: 8px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.callout strong,
.callout p {
  display: block;
}

.callout p {
  margin: 8px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.submit {
  width: 100%;
  margin-top: 18px;
}

.result-content {
  padding: 14px 24px 24px;
}

.result-overview {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .create-grid,
  .inline-grid {
    grid-template-columns: 1fr;
  }

  .hero-card h2 {
    font-size: 30px;
  }
}
</style>
