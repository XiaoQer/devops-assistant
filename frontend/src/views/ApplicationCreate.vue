<template>
  <div class="page-head"><div><h1>创建应用</h1><p>连接 GitHub 仓库，平台会自动识别技术栈。</p></div></div>
  <div class="create-grid">
    <div class="panel">
      <el-form label-position="top" :model="form">
        <el-form-item label="应用名称"><el-input v-model="form.name" placeholder="order-api" /></el-form-item>
        <el-form-item label="GitHub 仓库地址"><el-input v-model="form.repo_url" placeholder="https://github.com/org/repo.git" /></el-form-item>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="分支"><el-input v-model="form.branch" /></el-form-item></el-col><el-col :span="12"><el-form-item label="Kubernetes Namespace"><el-input v-model="form.namespace" /></el-form-item></el-col></el-row>
        <el-alert title="分析过程会临时克隆仓库，完成后立即清理。" type="info" :closable="false" />
        <el-button class="submit" type="primary" :loading="loading" @click="submit">分析并创建应用</el-button>
      </el-form>
    </div>
    <div class="panel result">
      <template v-if="result">
        <h3>识别结果</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="语言">{{ result.language }}</el-descriptions-item>
          <el-descriptions-item label="框架">{{ result.framework }}</el-descriptions-item>
          <el-descriptions-item label="构建">{{ result.build_type }}</el-descriptions-item>
          <el-descriptions-item label="端口">{{ result.port }}</el-descriptions-item>
        </el-descriptions>
        <h3>Application Spec</h3><pre class="spec">{{ yaml }}</pre>
        <el-button type="primary" @click="$router.push(`/applications/${result.id}`)">进入应用详情</el-button>
      </template>
      <el-empty v-else description="提交仓库后，这里会展示识别结果与 Application Spec" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import yamlLib from 'js-yaml'
import { applicationApi } from '../api/application'
import type { Application } from '../types'
const form = reactive({ name:'', repo_url:'', branch:'main', namespace:'default' })
const loading = ref(false); const result = ref<Application>()
const yaml = computed(() => result.value ? yamlLib.dump(result.value.application_spec) : '')
async function submit() {
  if (!form.name || !form.repo_url) return ElMessage.warning('请填写应用名称和仓库地址')
  loading.value=true
  try { result.value=await applicationApi.create(form); ElMessage.success('仓库分析完成') }
  catch(e) { ElMessage.error((e as Error).message) } finally { loading.value=false }
}


</script>
<style scoped>.create-grid{display:grid;grid-template-columns:minmax(380px,.8fr) minmax(480px,1.2fr);gap:20px}.submit{width:100%;margin-top:22px}.result h3{margin-top:0}.result .spec+h3{margin-top:24px}@media(max-width:900px){.create-grid{grid-template-columns:1fr}}</style>

