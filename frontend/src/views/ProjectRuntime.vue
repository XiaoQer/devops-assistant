<template>
  <div class="page-content page-stack runtime-page">
    <PageHeader eyebrow="Kubernetes runtime" title="Runtime" description="选择一个环境，查看可分页的 Deployment 与 Pod 运行清单。">
      <el-select v-model="environment" class="environment-select" placeholder="选择环境"><el-option v-for="item in environments" :key="item.name" :label="item.display_name" :value="item.name" /></el-select>
      <el-switch v-model="autoRefresh" active-text="自动刷新" />
      <el-button :loading="loading" @click="refresh">刷新</el-button>
    </PageHeader>
    <el-alert v-if="refreshError" :title="refreshError" type="warning" :closable="false" show-icon />
    <div class="runtime-metrics">
      <MetricCard title="Deployments" :value="summary.deployments" icon="▦" tone="blue" helper="当前环境" />
      <MetricCard title="Healthy Pods" :value="summary.healthy_pods" icon="✓" tone="green" helper="Ready" />
      <MetricCard title="Unhealthy Pods" :value="summary.unhealthy_pods" icon="!" tone="red" helper="需要关注" />
      <MetricCard title="Restarts" :value="summary.restart_count" icon="↻" helper="累计重启" />
    </div>
    <section class="surface inventory-card">
      <el-tabs v-model="resource" class="resource-tabs"><el-tab-pane label="Deployments" name="deployments" /><el-tab-pane label="Pods" name="pods" /></el-tabs>
      <div class="runtime-toolbar">
        <el-input v-model="query" placeholder="搜索 Application、Deployment、Pod、镜像…" clearable />
        <el-select v-model="status" placeholder="全部状态" clearable><el-option v-for="item in statuses" :key="item" :label="item" :value="item" /></el-select>
        <span>{{ inventory?.pagination.total || 0 }} resources</span>
      </div>
      <el-skeleton :loading="loading && !inventory" animated :rows="9">
        <RuntimeResourceTable v-if="inventory?.items.length" :items="inventory.items" :resource="resource" @yaml="openYaml" @restart="restart" @pod-detail="openPod" />
        <EmptyState v-else title="当前环境没有匹配资源" description="调整筛选条件，或确认工作负载已经部署。" />
      </el-skeleton>
      <footer class="pager"><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20,50,100]" layout="total, sizes, prev, pager, next" :total="inventory?.pagination.total || 0" /></footer>
    </section>
    <RuntimeResourceDrawer v-model="drawer" :title="drawerTitle" :content="drawerContent" :loading="drawerLoading" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { runtimeApi } from '../api/runtime'
import { useProjectRuntime } from '../composables/useProjectRuntime'
import type { RuntimeInventoryItem } from '../types'
import PageHeader from '../components/common/PageHeader.vue'; import MetricCard from '../components/common/MetricCard.vue'; import EmptyState from '../components/common/EmptyState.vue'
import RuntimeResourceTable from '../components/runtime/RuntimeResourceTable.vue'; import RuntimeResourceDrawer from '../components/runtime/RuntimeResourceDrawer.vue'
import { confirmationCopy, isProduction } from '../components/runtime/runtime-view-model'
const route=useRoute(), router=useRouter(), projectId=Number(route.params.projectId)
const {environments,inventory,environment,resource,query,status,page,pageSize,loading,refreshError,autoRefresh,initialize,refresh}=useProjectRuntime(projectId,route,router)
const summary=computed(()=>inventory.value?.summary||{deployments:0,healthy_pods:0,unhealthy_pods:0,restart_count:0})
const statuses=computed(()=>resource.value==='pods'?['Running','Pending','Succeeded','Failed','CrashLoopBackOff','ImagePullBackOff','ErrImagePull','Unknown']:['Healthy','Progressing','Degraded','Failed','Unknown'])
const drawer=ref(false),drawerTitle=ref(''),drawerContent=ref(''),drawerLoading=ref(false)
async function openYaml(row:RuntimeInventoryItem){if(!row.deployment)return;drawer.value=true;drawerLoading.value=true;drawerTitle.value=`${row.deployment.name} · YAML`;try{drawerContent.value=JSON.stringify(await runtimeApi.deploymentYaml(projectId,row.application_id,environment.value,row.deployment.name),null,2)}finally{drawerLoading.value=false}}
async function restart(row:RuntimeInventoryItem){if(!row.deployment)return;await ElMessageBox.confirm(confirmationCopy('restart',environment.value,row.deployment.name),'确认 Runtime 操作',{type:isProduction(environment.value)?'error':'warning'});await runtimeApi.restartDeployment(projectId,row.application_id,environment.value,row.deployment.name);ElMessage.success('Deployment 重启已提交');await refresh()}
function openPod(row:RuntimeInventoryItem){void router.push(`/devcenter/projects/${projectId}/runtime/environments/${encodeURIComponent(environment.value)}/applications/${row.application_id}/pods/${encodeURIComponent(row.name||'')}`)}
onMounted(initialize)
</script>
<style scoped>
.environment-select{width:180px}.runtime-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.inventory-card{padding:0;overflow:hidden;box-shadow:none}.resource-tabs{padding:0 20px}.runtime-toolbar{display:grid;grid-template-columns:minmax(260px,1fr) 170px auto;gap:12px;align-items:center;padding:0 20px 16px}.runtime-toolbar span{color:var(--muted);font-size:12px}.pager{display:flex;justify-content:flex-end;padding:16px 20px;border-top:1px solid var(--border-soft)}@media(max-width:760px){.runtime-metrics{grid-template-columns:repeat(2,1fr)}.runtime-toolbar{grid-template-columns:1fr}.pager{overflow:auto;justify-content:flex-start}}
</style>
