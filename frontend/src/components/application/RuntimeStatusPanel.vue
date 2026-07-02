<template>
  <div v-if="status" class="runtime">
    <div class="runtime-cards">
      <section class="surface deployment">
        <div class="surface-header">
          <div><h3>Deployment</h3><p>{{ status.namespace }} / {{ status.deployment.name }}</p></div>
          <StatusBadge :status="status.status"/>
        </div>
        <div class="deploy-body">
          <div class="replicas"><strong>{{ status.deployment.ready_replicas }}</strong><span>/ {{ status.deployment.replicas }} ready</span></div>
          <div class="bars"><i v-for="n in Math.max(status.deployment.replicas,1)" :key="n" :class="{ready:n<=status.deployment.ready_replicas}"/></div>
          <code>{{ status.deployment.images?.[0] || 'No image deployed' }}</code>
        </div>
      </section>
      <section class="surface network">
        <div class="surface-header"><div><h3>Network</h3><p>Service 与 Ingress</p></div></div>
        <dl>
          <div><dt>Service</dt><dd>{{ status.service?.name || 'Not configured' }}</dd><small>{{ status.service?.type }} {{ status.service?.cluster_ip }}</small></div>
          <div><dt>Ingress</dt><dd>{{ status.ingress?.host || 'Not configured' }}</dd><small>{{ status.ingress?.address }}</small></div>
        </dl>
      </section>
    </div>

    <section class="surface data-card">
      <div class="surface-header"><div><h3>Pods</h3><p>工作负载实时状态</p></div><span>{{ status.pods.length }} pods</span></div>
      <el-table :data="status.pods">
        <el-table-column label="Pod" prop="name" min-width="260"/>
        <el-table-column label="状态" width="130"><template #default="{row}"><StatusBadge :status="row.ready?'Healthy':row.status"/></template></el-table-column>
        <el-table-column label="Ready" width="80"><template #default="{row}">{{ row.ready?'Yes':'No' }}</template></el-table-column>
        <el-table-column label="Restarts" prop="restart_count" width="85"/>
        <el-table-column label="Node" prop="node" min-width="140"/>
        <el-table-column label="操作" width="130">
          <template #default="{row}">
            <el-button link :loading="loadingPod===row.name" @click="openPod(row.name,'logs')">Logs</el-button>
            <el-button link :loading="loadingPod===row.name" @click="openPod(row.name,'yaml')">YAML</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-if="!status.pods.length" title="暂无 Pod" description="应用尚未部署，或工作负载还未创建。"/>
    </section>

    <div class="inventory-grid">
      <ResourceList title="ReplicaSets" :items="status.replica_sets || []" empty="暂无 ReplicaSet"/>
      <ResourceList title="PVC" :items="status.persistent_volume_claims || []" empty="暂无持久化存储"/>
      <ResourceList title="ConfigMaps" :items="status.config_maps || []" empty="暂无 ConfigMap"/>
      <ResourceList title="Secrets" :items="status.secrets || []" empty="暂无 Secret"/>
    </div>

    <section class="surface events data-card">
      <div class="surface-header"><div><h3>Events</h3><p>Kubernetes 最近事件</p></div></div>
      <div v-if="status.events.length">
        <article v-for="(event,i) in status.events" :key="i">
          <StatusBadge :status="event.type==='Warning'?'Failed':'Succeeded'" :label="event.type"/>
          <b>{{ event.reason }}</b><p>{{ event.message }}</p><span>×{{ event.count }}</span>
        </article>
      </div>
      <EmptyState v-else title="没有异常事件" description="当前应用没有需要关注的 Kubernetes Event。" icon="✓"/>
    </section>

    <el-drawer v-model="drawer" :title="`${selectedPod} · ${drawerMode.toUpperCase()}`" size="62%">
      <div class="drawer-tools"><el-button size="small" @click="copyContent">复制</el-button></div>
      <pre class="pod-output">{{ podContent }}</pre>
    </el-drawer>
  </div>
  <EmptyState v-else title="运行状态不可用" description="尚未部署应用，或暂时无法连接 Kubernetes。"/>
</template>

<script setup lang="ts">
import { defineComponent, h, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { RuntimeStatus } from '../../types'
import { applicationApi } from '../../api/application'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'

const props=defineProps<{status?:RuntimeStatus;applicationId?:number;environment?:string}>()
const drawer=ref(false),drawerMode=ref('logs'),selectedPod=ref(''),podContent=ref(''),loadingPod=ref('')

const ResourceList=defineComponent({
  props:{title:{type:String,required:true},items:{type:Array,required:true},empty:{type:String,required:true}},
  setup(p){return()=>h('section',{class:'surface inventory'},[
    h('div',{class:'inventory-title'},[h('h3',p.title),h('span',String(p.items.length))]),
    p.items.length
      ? h('div',{class:'inventory-items'},p.items.slice(0,8).map((item:any)=>h('article',[
          h('b',item.name||'resource'),
          h('small',item.status||item.type||item.storage_class||'Managed by Kubernetes'),
        ])))
      : h('p',{class:'inventory-empty'},p.empty),
  ])},
})

async function openPod(name:string,mode:'logs'|'yaml'){
  if(!props.applicationId)return
  selectedPod.value=name;drawerMode.value=mode;loadingPod.value=name
  try{
    if(mode==='logs'){
      const result=await applicationApi.podLogs(props.applicationId,name,props.environment||'dev')
      podContent.value=result.logs||'该 Pod 暂无日志。'
    }else{
      const result=await applicationApi.podYaml(props.applicationId,name,props.environment||'dev')
      podContent.value=JSON.stringify(result,null,2)
    }
    drawer.value=true
  }catch(error){ElMessage.error((error as Error).message)}
  finally{loadingPod.value=''}
}
function copyContent(){navigator.clipboard.writeText(podContent.value);ElMessage.success('内容已复制')}
</script>

<style scoped>
.runtime-cards{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin-bottom:14px}.deploy-body{padding:20px}.replicas strong{font-size:30px}.replicas span{color:var(--muted);font-size:12px}.bars{display:flex;gap:6px;margin:16px 0}.bars i{height:6px;max-width:48px;flex:1;border-radius:4px;background:#292e3a}.bars i.ready{background:var(--success)}code{display:block;padding:9px;background:#0b0d12;border-radius:6px;color:#8e98aa;font-size:13px;overflow:hidden;text-overflow:ellipsis}.network dl{margin:0;padding:7px 18px}.network dl div{padding:12px 0;border-bottom:1px solid var(--border-soft)}dt{font-size:12px;color:var(--muted)}dd{font-size:12px;margin:5px 0}.network small{font-size:12px;color:var(--subtle)}.data-card{overflow:hidden;margin-bottom:14px}.surface-header>span{font-size:12px;color:var(--muted)}.inventory-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}.inventory{box-shadow:none;overflow:hidden}.inventory-title{height:43px;padding:0 13px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border-soft)}.inventory-title h3{font-size:13px;margin:0}.inventory-title span{font-size:12px;color:var(--muted)}.inventory-items article{padding:9px 13px;border-bottom:1px solid var(--border-soft)}.inventory-items b,.inventory-items small{display:block}.inventory-items b{font-size:12px;overflow:hidden;text-overflow:ellipsis}.inventory-items small{font-size:13px;color:var(--muted);margin-top:4px}.inventory-empty{padding:18px 13px;margin:0;color:var(--subtle);font-size:12px}.events article{display:grid;grid-template-columns:80px 130px 1fr 40px;align-items:center;gap:10px;min-height:48px;padding:0 18px;border-bottom:1px solid var(--border-soft);font-size:13px}.events article b{font-size:13px}.events article p{margin:0;color:var(--muted)}.events article>span{text-align:right;color:var(--subtle)}.drawer-tools{display:flex;justify-content:flex-end;margin-bottom:9px}.pod-output{min-height:520px;margin:0;padding:16px;border-radius:8px;background:#101620;color:#c0cad8;white-space:pre-wrap;font:12px/1.7 "SFMono-Regular",Consolas,monospace}@media(max-width:1100px){.runtime-cards{grid-template-columns:1fr}.inventory-grid{grid-template-columns:1fr 1fr}}
</style>
