<template>
  <div class="page-content page-stack pod-detail-page">
    <DetailBreadcrumb :items="[
      { label: 'Runtime', to: runtimeLocation },
      { label: environment },
      { label: podName, current: true },
    ]" />
    <PageHeader eyebrow="Pod details" :title="podName" :description="pod ? `${pod.application_name} · ${pod.namespace}` : '正在读取 Pod 运行详情…'">
      <el-button :loading="loading" @click="loadDetail">刷新</el-button>
      <el-button :disabled="!pod" @click="enterTerminal">终端</el-button>
      <el-button type="danger" plain :disabled="!pod" @click="deletePod">删除 Pod</el-button>
    </PageHeader>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="pod">
      <div class="pod-summary surface">
        <el-tag :type="podStatusTone(pod.status, pod.ready)">{{ pod.status }}</el-tag>
        <span><b>{{ pod.containers.filter(item => item.ready).length }}/{{ pod.containers.length }}</b> Containers Ready</span>
        <span><b>{{ pod.restart_count }}</b> Restarts</span>
        <span><b>{{ pod.node || '—' }}</b> Node</span>
        <span><b>{{ pod.pod_ip || '—' }}</b> Pod IP</span>
      </div>
      <section class="surface detail-card">
        <el-tabs v-model="activeTab" @tab-change="loadTabData">
          <el-tab-pane label="Overview" name="overview"><PodOverview :pod="pod" /></el-tab-pane>
          <el-tab-pane label="Containers" name="containers">
            <div class="container-grid">
              <article v-for="container in pod.containers" :key="container.name" class="container-card">
                <header><strong>{{ container.name }}</strong><el-tag :type="container.ready ? 'success' : 'warning'" size="small">{{ containerStateLabel(container) }}</el-tag></header>
                <code>{{ container.image }}</code>
                <dl><div><dt>Ready</dt><dd>{{ container.ready ? 'Yes' : 'No' }}</dd></div><div><dt>Restarts</dt><dd>{{ container.restart_count }}</dd></div><div><dt>Started</dt><dd>{{ formatRuntimeTime(container.started_at) }}</dd></div></dl>
                <p v-if="container.message">{{ container.message }}</p>
              </article>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Events" name="events">
            <el-table :data="pod.events" empty-text="暂无 Events">
              <el-table-column prop="type" label="类型" width="100" /><el-table-column prop="reason" label="原因" min-width="160" />
              <el-table-column prop="message" label="消息" min-width="360" /><el-table-column prop="count" label="次数" width="80" />
              <el-table-column label="时间" width="190"><template #default="{ row }">{{ formatRuntimeTime(row.timestamp) }}</template></el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="Logs" name="logs">
            <div class="tab-toolbar"><el-select v-model="selectedContainer" @change="loadLogs"><el-option v-for="item in pod.containers" :key="item.name" :label="item.name" :value="item.name" /></el-select><el-select v-model="tail" @change="loadLogs"><el-option label="最近 100 行" :value="100"/><el-option label="最近 500 行" :value="500"/><el-option label="最近 1000 行" :value="1000"/><el-option label="最近 5000 行" :value="5000"/></el-select><el-button :loading="tabLoading" @click="loadLogs">刷新日志</el-button><el-button :disabled="!logs" @click="copyLogs">复制日志</el-button></div>
            <pre class="code-view">{{ logs || '暂无日志' }}</pre>
          </el-tab-pane>
          <el-tab-pane label="YAML" name="yaml">
            <div class="tab-toolbar"><el-button :loading="tabLoading" @click="loadYaml">刷新 YAML</el-button></div>
            <pre class="code-view">{{ yaml || '暂无 YAML' }}</pre>
          </el-tab-pane>
        </el-tabs>
      </section>
    </template>
    <el-skeleton v-else :loading="loading" animated :rows="12" />
    <RuntimeTerminalDrawer v-model="terminalOpen" :title="`${podName} · ${selectedContainer}`" :session="session" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runtimeApi } from '../api/runtime'
import type { RuntimeExecSession, RuntimePodDetail } from '../types'
import DetailBreadcrumb from '../components/common/DetailBreadcrumb.vue'
import PageHeader from '../components/common/PageHeader.vue'
import PodOverview from '../components/runtime/PodOverview.vue'
import RuntimeTerminalDrawer from '../components/runtime/RuntimeTerminalDrawer.vue'
import { confirmationCopy, isProduction } from '../components/runtime/runtime-view-model'
import { containerStateLabel, formatRuntimeTime, podStatusTone } from '../components/runtime/pod-detail-view-model'

const route=useRoute(),router=useRouter()
const projectId=Number(route.params.projectId),applicationId=Number(route.params.applicationId)
const environment=String(route.params.environment),podName=String(route.params.podName)
const pod=ref<RuntimePodDetail>(),loading=ref(false),tabLoading=ref(false),error=ref('')
const activeTab=ref('overview'),selectedContainer=ref(''),tail=ref(500),logs=ref(''),yaml=ref('')
const terminalOpen=ref(false),session=ref<RuntimeExecSession>()
const runtimeLocation=computed(()=>({path:`/devcenter/projects/${projectId}/runtime`,query:{environment,resource:'pods'}}))
async function loadDetail(){loading.value=true;try{pod.value=await runtimeApi.podDetail(projectId,applicationId,environment,podName);selectedContainer.value=selectedContainer.value||pod.value.containers[0]?.name||'';error.value=''}catch(e){error.value=e instanceof Error?e.message:'Pod 详情读取失败'}finally{loading.value=false}}
async function loadLogs(){if(!selectedContainer.value)return;tabLoading.value=true;try{logs.value=(await runtimeApi.podLogs(projectId,applicationId,environment,podName,selectedContainer.value,tail.value)).logs}catch(e){ElMessage.error(e instanceof Error?e.message:'日志读取失败')}finally{tabLoading.value=false}}
async function loadYaml(){tabLoading.value=true;try{yaml.value=JSON.stringify(await runtimeApi.podYaml(projectId,applicationId,environment,podName),null,2)}catch(e){ElMessage.error(e instanceof Error?e.message:'YAML 读取失败')}finally{tabLoading.value=false}}
async function copyLogs(){try{await navigator.clipboard.writeText(logs.value);ElMessage.success('日志已复制')}catch{ElMessage.error('日志复制失败')}}
function loadTabData(name:string|number){if(name==='logs'&&!logs.value)void loadLogs();if(name==='yaml'&&!yaml.value)void loadYaml()}
async function enterTerminal(){if(!selectedContainer.value){ElMessage.warning('请选择 Container');return}try{const {value:reason}=await ElMessageBox.prompt('请填写进入终端的操作原因。原因会写入审计记录。','确认进入 Pod 终端',{confirmButtonText:'确认并连接',cancelButtonText:'取消',inputPattern:/\S{3,}/,inputErrorMessage:'操作原因至少 3 个字符',type:isProduction(environment)?'warning':'info'});session.value=await runtimeApi.createExecSession(projectId,applicationId,environment,podName,selectedContainer.value,reason);terminalOpen.value=true}catch(e){if(e instanceof Error&&e.message!=='cancel')ElMessage.error(e.message)}}
async function deletePod(){try{await ElMessageBox.confirm(confirmationCopy('delete-pod',environment,podName),'确认 Runtime 操作',{type:isProduction(environment)?'error':'warning',confirmButtonText:'确认删除',cancelButtonText:'取消'});await runtimeApi.deletePod(projectId,applicationId,environment,podName);ElMessage.success('Pod 删除已提交');await router.push(runtimeLocation.value)}catch(e){if(e instanceof Error&&e.message!=='cancel')ElMessage.error(e.message)}}
onMounted(loadDetail)
</script>
<style scoped>
.pod-summary{display:flex;align-items:center;gap:28px;padding:16px 20px;box-shadow:none}.pod-summary span{display:grid;gap:3px;color:var(--muted);font-size:12px}.pod-summary b{color:var(--text);font-size:14px}.detail-card{padding:0 20px 20px;box-shadow:none}.container-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.container-card{padding:18px;border:1px solid var(--border-soft);border-radius:12px}.container-card header{display:flex;justify-content:space-between;gap:12px}.container-card code{display:block;margin:14px 0;color:var(--muted);font-size:11px;word-break:break-all}.container-card dl{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0}.container-card dl div{display:grid;gap:4px}.container-card dt{color:var(--muted);font-size:11px}.container-card dd{margin:0;font-size:13px}.container-card p{color:var(--danger);font-size:12px}.tab-toolbar{display:flex;gap:10px;margin-bottom:12px}.tab-toolbar .el-select{width:180px}.code-view{min-height:420px;max-height:65vh;overflow:auto;margin:0;padding:18px;border-radius:10px;background:#0b1020;color:#dbeafe;font:12px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap}@media(max-width:800px){.pod-summary{align-items:flex-start;flex-wrap:wrap}.container-grid{grid-template-columns:1fr}}
</style>
