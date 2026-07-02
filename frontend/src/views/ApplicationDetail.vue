<template>
  <div class="page-content">
    <el-skeleton v-if="loadingApp" animated :rows="9"/>
    <template v-else-if="app">
      <PageHeader eyebrow="Application" :title="app.name" :description="`${shortRepo(app.repo_url)} · ${app.branch}`">
        <el-select v-model="environment" style="width:112px"><el-option v-for="env in environments" :key="env" :label="env.toUpperCase()" :value="env"/></el-select>
        <el-button :loading="loadingRuntime" @click="loadRuntime">刷新状态</el-button>
        <el-button type="primary" :loading="deploying" @click="deploy">发布应用</el-button>
      </PageHeader>
      <div class="app-summary surface">
        <div class="app-avatar">{{app.name[0].toUpperCase()}}</div><div><span>Health</span><StatusBadge :status="runtime?.status||'Unknown'"/></div><div><span>Environment</span><b>{{environment.toUpperCase()}}</b></div><div><span>Replicas</span><b>{{runtime?.deployment.ready_replicas??'—'}} / {{runtime?.deployment.replicas??'—'}}</b></div><div class="image"><span>Current image</span><code>{{runtime?.deployment.images?.[0]||`${app.image_name}:${app.image_tag}`}}</code></div>
      </div>
      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="Overview" name="overview"><ApplicationOverview :application="app"/></el-tab-pane>
        <el-tab-pane label="Environments" name="environments"><EnvironmentCenter :application-id="app.id"/></el-tab-pane>
        <el-tab-pane label="Pipeline" name="pipeline"><section class="surface"><div class="surface-header"><div><h3>Pipeline executions</h3><p>最近 Tekton PipelineRun</p></div></div><el-table :data="executions"><el-table-column prop="pipeline_run_name" label="PipelineRun" min-width="280"/><el-table-column label="状态" width="130"><template #default="{row}"><StatusBadge :status="row.status"/></template></el-table-column><el-table-column label="创建时间" width="180"><template #default="{row}">{{format(row.created_at)}}</template></el-table-column><el-table-column label="操作" width="100"><template #default="{row}"><el-button link @click="$router.push(`/pipelines/${row.pipeline_run_name}`)">详情</el-button></template></el-table-column></el-table><EmptyState v-if="!executions.length" title="暂无 Pipeline 执行" description="点击发布应用以启动第一条流水线。"/></section></el-tab-pane>
        <el-tab-pane label="Release History" name="releases"><ReleaseHistoryTable :releases="releases" :rollback-id="rollbackId" @logs="openLogs" @rollback="rollback"/></el-tab-pane>
        <el-tab-pane label="Runtime Status" name="runtime"><el-skeleton :loading="loadingRuntime" animated :rows="8"><RuntimeStatusPanel :status="runtime" :application-id="app.id" :environment="environment"/></el-skeleton></el-tab-pane>
        <el-tab-pane label="Config" name="config"><ConfigurationCenter :application-id="app.id"/></el-tab-pane>
        <el-tab-pane label="Logs" name="logs"><EmptyState title="选择 Pipeline 查看日志" description="在 Pipeline 标签页中选择一次执行，查看 Task 与 Step 日志。" icon="≡"/></el-tab-pane>
        <el-tab-pane label="AI Analysis" name="ai"><section class="surface ai-panel"><span>✦</span><div><h3>AI delivery analysis</h3><p>分析流水线失败日志、Kubernetes Events 和应用配置，定位根因并给出修复建议。</p><el-button type="primary" disabled>分析当前应用</el-button></div></section></el-tab-pane>
      </el-tabs>
    </template>
    <EmptyState v-else title="应用加载失败" description="请检查后端服务连接后重试。"><el-button @click="load">重新加载</el-button></EmptyState>
  </div>
</template>
<script setup lang="ts">
import{onMounted,ref,watch}from'vue';import{useRoute,useRouter}from'vue-router';import{ElMessage,ElMessageBox}from'element-plus';import{applicationApi}from'../api/application';import type{Application,Execution,Release,RuntimeStatus}from'../types';import PageHeader from'../components/common/PageHeader.vue';import StatusBadge from'../components/common/StatusBadge.vue';import EmptyState from'../components/common/EmptyState.vue';import ApplicationOverview from'../components/application/ApplicationOverview.vue';import ReleaseHistoryTable from'../components/application/ReleaseHistoryTable.vue';import RuntimeStatusPanel from'../components/application/RuntimeStatusPanel.vue';import EnvironmentCenter from'../components/application/EnvironmentCenter.vue';import ConfigurationCenter from'../components/application/ConfigurationCenter.vue'
const route=useRoute(),router=useRouter(),app=ref<Application>(),executions=ref<Execution[]>([]),releases=ref<Release[]>([]),runtime=ref<RuntimeStatus>(),activeTab=ref('overview'),environment=ref('dev'),loadingApp=ref(true),loadingRuntime=ref(false),deploying=ref(false),rollbackId=ref(0),environments=['dev','test','staging','prod']
const shortRepo=(url:string)=>url.replace(/^https?:\/\/(www\.)?github\.com\//,'').replace(/\.git$/,''),format=(v:string)=>new Date(v).toLocaleString('zh-CN',{hour12:false})
async function load(){loadingApp.value=true;try{const id=Number(route.params.id);[app.value,executions.value,releases.value]=await Promise.all([applicationApi.get(id),applicationApi.executions(id),applicationApi.releases(id,environment.value)]);await loadRuntime()}catch(e){ElMessage.error((e as Error).message)}finally{loadingApp.value=false}}
async function loadRuntime(){loadingRuntime.value=true;try{runtime.value=await applicationApi.status(Number(route.params.id),environment.value)}catch(e){runtime.value=undefined}finally{loadingRuntime.value=false}}
async function loadEnvironment(){[releases.value]=await Promise.all([applicationApi.releases(Number(route.params.id),environment.value),loadRuntime()])}
async function deploy(){deploying.value=true;try{const run=await applicationApi.deploy(Number(route.params.id),{environment:environment.value});if(run.approval_required){ElMessage.success('Production 发布审批已提交');router.push('/approvals')}else if(run.pipeline_run_name){ElMessage.success('PipelineRun 已启动');router.push(`/pipelines/${run.pipeline_run_name}`)}}catch(e){ElMessage.error((e as Error).message)}finally{deploying.value=false}}
async function rollback(release:Release){try{await ElMessageBox.confirm(`确认将 ${app.value?.name} 回滚至 ${release.image_tag}？此操作会更新 ${release.deploy_namespace} 中的 Deployment。`,'确认回滚',{confirmButtonText:'执行回滚',cancelButtonText:'取消',type:'warning'});rollbackId.value=release.id;await applicationApi.rollback(Number(route.params.id),release.id,environment.value);ElMessage.success('回滚已提交');await loadEnvironment()}catch(e){if(e!=='cancel')ElMessage.error((e as Error).message)}finally{rollbackId.value=0}}
function openLogs(release:Release){if(release.pipeline_run_name)router.push(`/pipelines/${release.pipeline_run_name}`)}
watch(environment,loadEnvironment);onMounted(load)


</script>
<style scoped>.app-summary{min-height:70px;padding:13px 16px;display:grid;grid-template-columns:44px 120px 110px 110px 1fr;align-items:center;gap:16px;margin-bottom:17px;box-shadow:none}.app-avatar{width:38px;height:38px;display:grid;place-items:center;border-radius:9px;background:var(--primary-soft);color:#9b90ed;font-weight:700}.app-summary>div:not(.app-avatar){border-left:1px solid var(--border-soft);padding-left:16px}.app-summary span,.app-summary b{display:block}.app-summary>div>span{font-size:12px;color:var(--muted);margin-bottom:6px}.app-summary b{font-size:12px}.app-summary code{font-size:13px;color:#929bad}.detail-tabs :deep(.el-tabs__header){margin-bottom:16px}.ai-panel{min-height:260px;display:flex;align-items:center;justify-content:center;gap:18px}.ai-panel>span{width:48px;height:48px;display:grid;place-items:center;border-radius:13px;background:linear-gradient(145deg,#9689f2,#6453d3);font-size:20px}.ai-panel h3{margin:0 0 8px}.ai-panel p{max-width:500px;color:var(--muted);font-size:12px;line-height:1.6;margin:0 0 15px}@media(max-width:1000px){.app-summary{grid-template-columns:44px 1fr 1fr}.app-summary .image{display:none}}</style>
