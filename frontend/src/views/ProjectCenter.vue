<template>
  <div class="page-content">
    <PageHeader eyebrow="Governance system" title="Project Center Projects" description="选择一个 Project，进入对应的项目治理 Workspace。"/>
    <section class="surface project-list">
      <div class="surface-header">
        <div><h3>Accessible projects</h3><p>管理项目成员、环境、Kubernetes 集群与镜像仓库边界</p></div>
        <div class="toolbar"><el-button :loading="loading" @click="load">刷新</el-button><el-button type="primary" @click="openCreate">＋ Create Project</el-button></div>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <div v-if="items.length" class="cards">
          <article v-for="p in items" :key="p.id" @click="view(p)">
            <span>▦</span>
            <div class="project-copy">
              <div class="project-title"><h3>{{p.name}}</h3><StatusBadge :status="p.status==='Active'?'Healthy':'Unknown'" :label="p.status"/></div>
              <p>{{p.description||'Project governance workspace'}}</p>
              <small>{{p.member_count}} Members · {{p.application_count}} Applications · {{defaultCluster(p)?.name||'No cluster'}}</small>
            </div>
            <div class="card-actions" @click.stop>
              <el-button link @click="openEdit(p)">Edit</el-button>
              <el-button link type="danger" @click="remove(p)">Delete</el-button>
              <b @click="view(p)">→</b>
            </div>
          </article>
        </div>
        <EmptyState v-else title="尚未创建 Project" description="Project 是成员、环境、集群和 Registry 的治理边界。"><el-button type="primary" @click="openCreate">Create Project</el-button></EmptyState>
      </el-skeleton>
    </section>
    <el-dialog v-model="dialog" :title="editing?'Edit Project':'Create Project'" width="680px">
      <el-form label-position="top"><div class="form-grid">
        <el-form-item label="Project Name"><el-input v-model="form.name"/></el-form-item>
        <el-form-item label="Project Code"><el-input v-model="form.key" :disabled="!editing" placeholder="自动生成"/></el-form-item>
        <el-form-item class="wide" label="Description"><el-input v-model="form.description" type="textarea" :rows="3"/></el-form-item>
        <el-form-item label="Status"><el-select v-model="form.status"><el-option label="Active" value="Active"/><el-option label="Disabled" value="Disabled"/></el-select></el-form-item>
        <el-form-item label="Cloud Provider"><el-select v-model="form.cloud_provider" clearable><el-option v-for="p in ['Azure','AWS','Alibaba Cloud','GCP','Private Cloud']" :key="p" :label="p" :value="p"/></el-select></el-form-item>
        <el-form-item label="Subscription ID"><el-input v-model="form.cloud_subscription_id"/></el-form-item>
        <el-form-item label="Region"><el-input v-model="form.region"/></el-form-item>
        <el-form-item label="Resource Group / VPC"><el-input v-model="form.resource_group"/></el-form-item>
        <el-form-item label="Billing Owner"><el-input v-model="form.billing_owner"/></el-form-item>
        <template v-if="!editing"><el-form-item label="Default Cluster"><el-input v-model="form.cluster_name" placeholder="docker-desktop"/></el-form-item><el-form-item label="Kube Context"><el-input v-model="form.kube_context"/></el-form-item></template>
      </div></el-form>
      <template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存 Project</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import{onMounted,reactive,ref}from'vue';import{useRouter}from'vue-router';import{ElMessage,ElMessageBox}from'element-plus';import{projectApi}from'../api/project';import type{Project}from'../types';import PageHeader from'../components/common/PageHeader.vue';import StatusBadge from'../components/common/StatusBadge.vue';import EmptyState from'../components/common/EmptyState.vue';const router=useRouter(),items=ref<Project[]>([]),loading=ref(false),saving=ref(false),dialog=ref(false),editing=ref<Project>();const defaults={name:'',key:'',description:'',status:'Active',cloud_provider:'',cloud_subscription_id:'',region:'',resource_group:'',billing_owner:'',cluster_name:'docker-desktop',kube_context:'docker-desktop'};const form=reactive({...defaults});const defaultCluster=(p:Project)=>p.clusters?.find(c=>c.is_default),defaultRegistry=(p:Project)=>p.registries?.find(r=>r.is_default);const format=(v:string)=>new Date(v).toLocaleString('zh-CN',{hour12:false});async function load(){loading.value=true;try{const base=await projectApi.list();items.value=await Promise.all(base.map(p=>projectApi.get(p.id)))}finally{loading.value=false}}function openCreate(){editing.value=undefined;Object.assign(form,defaults);dialog.value=true}function openEdit(p:Project){editing.value=p;Object.assign(form,defaults,p);dialog.value=true}function view(p:Project){router.push(`/project-center/projects/${p.id}`)}async function save(){if(!form.name)return ElMessage.warning('请输入 Project Name');saving.value=true;try{if(editing.value)await projectApi.update(editing.value.id,form);else await projectApi.create(form);ElMessage.success('Project 已保存');dialog.value=false;load()}finally{saving.value=false}}async function remove(p:Project){await ElMessageBox.confirm(`确认删除 ${p.name}？仅空 Project 可以删除。`,'Delete Project',{type:'warning'});await projectApi.remove(p.id);ElMessage.success('Project 已删除');load()}onMounted(load);
</script>
<style scoped>
.project-list{overflow:hidden}.toolbar,.project-title,.card-actions{display:flex;align-items:center}.toolbar{gap:8px}.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:16px}.cards article{padding:17px;border:1px solid var(--border-soft);border-radius:10px;display:flex;align-items:center;gap:13px;cursor:pointer;background:var(--surface-soft);transition:border-color .2s,transform .2s}.cards article:hover{border-color:#66718a;transform:translateY(-1px)}.cards article>span{width:38px;height:38px;display:grid;place-items:center;flex:0 0 auto;border-radius:9px;background:rgba(20,184,166,.12);color:#55d6c8}.project-copy{min-width:0;flex:1}.project-title{gap:8px}.cards h3,.cards p{margin:0}.cards h3{font-size:14px}.cards p,.cards small{color:var(--muted);font-size:11px}.cards p{margin:5px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.cards small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.card-actions{gap:3px}.card-actions b{padding:6px;color:#14b8a6;cursor:pointer}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}.wide{grid-column:1/-1}@media(max-width:900px){.cards{grid-template-columns:1fr}.card-actions .el-button{display:none}}
</style>
