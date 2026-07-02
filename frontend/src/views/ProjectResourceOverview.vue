<template>
  <div class="page-content">
    <PageHeader eyebrow="Project Center" :title="title" :description="description">
      <el-button :loading="loading" @click="load">刷新</el-button>
    </PageHeader>
    <section class="surface resource-panel">
      <div class="surface-header"><div><h3>{{title}}</h3><p>所有配置均归属于明确的 Project 边界</p></div><span>{{rows.length}} records</span></div>
      <el-skeleton :loading="loading" animated :rows="7">
        <el-table v-if="rows.length" :data="rows">
          <el-table-column prop="projectName" label="Project" min-width="170"/>
          <template v-if="resource==='members'">
            <el-table-column prop="username" label="Member" min-width="190"/>
            <el-table-column prop="role" label="Role" width="130"/>
            <el-table-column prop="status" label="Status" width="120"/>
          </template>
          <template v-else-if="resource==='environments'">
            <el-table-column prop="display_name" label="Environment" width="150"/>
            <el-table-column prop="namespace" label="Namespace" min-width="190"/>
            <el-table-column prop="cluster_name" label="Cluster" min-width="160"/>
            <el-table-column prop="registry_name" label="Registry" min-width="170"/>
          </template>
          <template v-else-if="resource==='clusters'">
            <el-table-column prop="name" label="Cluster" min-width="180"/>
            <el-table-column prop="kube_context" label="Kube Context" min-width="180"/>
            <el-table-column prop="api_server" label="API Server" min-width="240"/>
          </template>
          <template v-else-if="resource==='registries'">
            <el-table-column prop="name" label="Registry" min-width="170"/>
            <el-table-column prop="provider" label="Provider" width="130"/>
            <el-table-column prop="image_prefix" label="Image Prefix" min-width="280"/>
          </template>
          <el-table-column label="操作" width="120" fixed="right"><template #default="{row}"><el-button link @click="$router.push(`/project-center/projects/${row.projectId}/${resource}`)">管理</el-button></template></el-table-column>
        </el-table>
        <EmptyState v-else :title="`暂无 ${title} 数据`" description="先创建 Project，再进入项目治理工作区完成配置。"/>
      </el-skeleton>
    </section>
  </div>
</template>
<script setup lang="ts">
import{computed,onMounted,ref,watch}from'vue';import{useRoute}from'vue-router';import{projectApi}from'../api/project';import type{Project}from'../types';import PageHeader from'../components/common/PageHeader.vue';import EmptyState from'../components/common/EmptyState.vue';const route=useRoute(),projects=ref<Project[]>([]),loading=ref(false);const resource=computed(()=>String(route.meta.resource||'members'));const titles:Record<string,string>={members:'Members & Roles',environments:'Environments',clusters:'Kubernetes Clusters',registries:'Image Registries',settings:'Project Settings'};const descriptions:Record<string,string>={members:'跨 Project 查看成员与角色边界。',environments:'查看环境、Namespace、Cluster 与 Registry 绑定。',clusters:'查看 Project 允许使用的 Kubernetes 集群。',registries:'查看 Project 允许使用的镜像仓库。',settings:'Project Center 系统级治理设置。'};const title=computed(()=>titles[resource.value]||'Resources'),description=computed(()=>descriptions[resource.value]||'Project governance resources');const rows=computed(()=>projects.value.flatMap(project=>{const values=resource.value==='members'?project.members:resource.value==='environments'?project.environments:resource.value==='clusters'?project.clusters:resource.value==='registries'?project.registries:[];return(values||[]).map(value=>({...value,projectId:project.id,projectName:project.name}))}));async function load(){loading.value=true;try{const base=await projectApi.list();projects.value=await Promise.all(base.map(item=>projectApi.get(item.id)))}finally{loading.value=false}}watch(resource,load);onMounted(load);
</script>
<style scoped>.resource-panel{overflow:hidden}.surface-header>span{font-size:11px;color:var(--muted)}</style>
