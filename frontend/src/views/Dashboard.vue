<template>
  <div class="page-content">
    <PageHeader eyebrow="Platform overview" title="Dashboard" description="交付系统、应用健康与最近发布的实时概览">
      <el-button @click="refresh" :loading="loading">刷新数据</el-button><el-button type="primary" @click="$router.push('/applications/new')">＋ 创建应用</el-button>
    </PageHeader>
    <el-skeleton :loading="loading && !store.items.length" animated :rows="8">
      <div class="metrics">
        <MetricCard title="项目总数" :value="projectCount" icon="▦" helper="当前 Workspace"/>
        <MetricCard title="应用总数" :value="store.items.length" icon="◇" tone="blue" trend="+1" helper="本周期"/>
        <MetricCard title="Pipeline 总数" :value="pipelineCount" icon="↯" tone="green" helper="累计执行"/>
        <MetricCard title="最近失败" :value="failedCount" icon="!" tone="red" helper="需要关注"/>
      </div>
      <div class="dashboard-grid">
        <section class="surface health-panel">
          <div class="surface-header"><div><h3>应用健康分布</h3><p>按最近部署状态统计</p></div><span class="period">Last 24h</span></div>
          <div class="health-content">
            <div class="donut" :style="donutStyle"><div><strong>{{ successRate }}%</strong><span>成功率</span></div></div>
            <div class="legend"><div><i class="green"/><span>Healthy</span><b>{{ healthyCount }}</b></div><div><i class="amber"/><span>Progressing</span><b>{{ runningCount }}</b></div><div><i class="red"/><span>Failed</span><b>{{ failedCount }}</b></div><div><i class="gray"/><span>Unknown</span><b>{{ unknownCount }}</b></div></div>
          </div>
        </section>
        <section class="surface ai-card">
          <span class="ai-icon">✦</span><div><small>AEGIS AI</small><h3>让 AI 分析交付风险</h3><p>汇总失败流水线、异常 Pod 与最近发布，给出优先级明确的修复建议。</p><el-button class="ai-action" type="primary">生成风险摘要 <span>→</span></el-button></div>
        </section>
      </div>
      <div class="dashboard-grid lower">
        <section class="surface">
          <div class="surface-header"><div><h3>最近 PipelineRun</h3><p>最新构建与部署执行</p></div><router-link to="/applications">查看全部</router-link></div>
          <div v-if="recentPipelines.length" class="pipeline-list">
            <article v-for="item in recentPipelines" :key="item.pipeline_run_name" @click="$router.push(`/pipelines/${item.pipeline_run_name}`)"><span class="pipeline-icon">↯</span><div><b>{{ item.pipeline_run_name }}</b><small>{{ item.appName }} · {{ formatTime(item.created_at) }}</small></div><StatusBadge :status="item.status"/><i>›</i></article>
          </div>
          <EmptyState v-else title="暂无 Pipeline 执行" description="从应用详情发起一次部署后，执行状态会显示在这里。"/>
        </section>
        <section class="surface">
          <div class="surface-header"><div><h3>最近发布</h3><p>跨应用发布活动</p></div></div>
          <div v-if="releases.length" class="release-list"><article v-for="release in releases.slice(0,5)" :key="release.id"><span class="release-dot"/><div><b>{{ release.image_tag }}</b><small>{{ release.environment.toUpperCase() }} · {{ release.deploy_user }}</small></div><StatusBadge :status="release.deploy_status"/><time>{{ formatShort(release.created_at) }}</time></article></div>
          <EmptyState v-else title="暂无发布记录" description="发布记录将作为审计轨迹保留。"/>
        </section>
      </div>
    </el-skeleton>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useApplicationStore } from '../stores/application'
import { applicationApi } from '../api/application'
import type { Release } from '../types'
import PageHeader from '../components/common/PageHeader.vue';import MetricCard from '../components/common/MetricCard.vue';import StatusBadge from '../components/common/StatusBadge.vue';import EmptyState from '../components/common/EmptyState.vue'
const store=useApplicationStore(),loading=ref(false),releases=ref<Release[]>([])
const executions=computed(()=>store.items.flatMap(a=>a.latest_execution?[{...a.latest_execution,appName:a.name}]:[]))
const recentPipelines=computed(()=>executions.value.sort((a,b)=>b.created_at.localeCompare(a.created_at)).slice(0,6))
const pipelineCount=computed(()=>executions.value.length),failedCount=computed(()=>executions.value.filter(e=>e.status==='Failed').length),healthyCount=computed(()=>executions.value.filter(e=>e.status==='Succeeded').length),runningCount=computed(()=>executions.value.filter(e=>['Running','Pending'].includes(e.status)).length),unknownCount=computed(()=>Math.max(store.items.length-healthyCount.value-runningCount.value-failedCount.value,0))
const projectCount=computed(()=>new Set(store.items.map(a=>a.project_id).filter(Boolean)).size||1),successRate=computed(()=>pipelineCount.value?Math.round(healthyCount.value/pipelineCount.value*100):100)
const donutStyle=computed(()=>({background:`conic-gradient(var(--success) 0 ${successRate.value}%, var(--danger) ${successRate.value}% ${successRate.value+Math.min(failedCount.value*10,20)}%, #242936 0)`}))
const formatTime=(v:string)=>new Date(v).toLocaleString('zh-CN',{hour12:false}),formatShort=(v:string)=>new Date(v).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'})
async function refresh(){loading.value=true;try{await store.load();const data=await Promise.all(store.items.slice(0,8).map(a=>applicationApi.releases(a.id).catch(()=>[])));releases.value=data.flat().sort((a,b)=>b.created_at.localeCompare(a.created_at))}finally{loading.value=false}}
onMounted(refresh)


</script>
<style scoped>
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}.dashboard-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;margin-bottom:14px}.dashboard-grid.lower{grid-template-columns:1fr 1fr}.period,.surface-header a{font-size:13px;color:#8b80ea;text-decoration:none}.health-content{height:205px;display:flex;align-items:center;justify-content:center;gap:48px}.donut{width:130px;height:130px;border-radius:50%;display:grid;place-items:center;position:relative}.donut:after{content:"";position:absolute;inset:13px;background:var(--surface);border-radius:50%}.donut div{position:relative;z-index:1;text-align:center}.donut strong,.donut span{display:block}.donut strong{font-size:23px}.donut span{font-size:12px;color:var(--muted);margin-top:4px}.legend{width:155px}.legend>div{display:grid;grid-template-columns:10px 1fr auto;align-items:center;padding:7px 0;font-size:13px;color:var(--muted)}.legend i{width:6px;height:6px;border-radius:50%}.green{background:var(--success)}.amber{background:var(--warning)}.red{background:var(--danger)}.gray{background:#687386}.legend b{color:var(--text-2)}.ai-card{padding:24px;display:flex;align-items:flex-start;gap:16px;background:radial-gradient(260px 180px at 100% 0,rgba(119,103,232,.17),transparent),var(--surface)}.ai-icon{width:39px;height:39px;display:grid;place-items:center;border-radius:11px;background:linear-gradient(145deg,#9689f2,#6655d3);font-size:17px}.ai-card small{font-size:12px;letter-spacing:1px;color:#a59bf3}.ai-card h3{font-size:15px;margin:7px 0}.ai-card p{font-size:12px;line-height:1.65;color:var(--muted);margin:0 0 18px}.ai-action span{margin-left:4px}.pipeline-list article,.release-list article{min-height:59px;padding:0 18px;display:flex;align-items:center;gap:11px;border-bottom:1px solid var(--border-soft);cursor:pointer}.pipeline-list article:hover{background:var(--surface-raised)}.pipeline-icon{width:28px;height:28px;display:grid;place-items:center;border-radius:7px;background:var(--primary-soft);color:#a399f2}.pipeline-list div,.release-list div{flex:1}.pipeline-list b,.release-list b{display:block;font-size:12px}.pipeline-list small,.release-list small{display:block;margin-top:4px;color:var(--muted);font-size:12px}.pipeline-list>article>i{font-style:normal;color:var(--subtle)}.release-dot{width:7px;height:7px;border:2px solid var(--primary);border-radius:50%}.release-list time{font-size:12px;color:var(--subtle)}@media(max-width:1100px){.metrics{grid-template-columns:1fr 1fr}.dashboard-grid,.dashboard-grid.lower{grid-template-columns:1fr}}
</style>
