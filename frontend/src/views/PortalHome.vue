<template>
  <div class="page-content portal">
    <PageHeader eyebrow="Enterprise portal" title="Choose your workspace" description="治理与交付相互独立，通过 Project 资源边界协同工作。" />
    <div class="system-grid">
      <article class="surface system-card governance">
        <span class="system-icon">▦</span><small>UPSTREAM SYSTEM</small>
        <h2>Project Center</h2>
        <p>管理项目空间、成员权限、环境、Kubernetes 集群、Namespace 与镜像仓库。</p>
        <ul><li>Project governance</li><li>Members & roles</li><li>Infrastructure boundaries</li></ul>
        <el-button type="primary" @click="openCenter('/project-center')">进入项目治理中心 →</el-button>
      </article>
      <article class="surface system-card delivery">
        <span class="system-icon">↗</span><small>DOWNSTREAM SYSTEM</small>
        <h2>DevCenter</h2>
        <p>在 Project Center 提供的边界内完成源码识别、Pipeline、发布与 Runtime 管理。</p>
        <ul><li>Application delivery</li><li>Tekton pipelines</li><li>Runtime & releases</li></ul>
        <el-button type="primary" @click="openCenter('/devcenter')">进入应用交付中心 →</el-button>
      </article>
    </div>
    <section class="boundary surface"><b>Project Center 提供边界</b><span>Project · Permission · Environment · Cluster · Registry</span><i>→</i><b>DevCenter 在边界内执行</b><span>Application · Pipeline · Release · Runtime</span></section>
  </div>
</template>
<script setup lang="ts">
import PageHeader from '../components/common/PageHeader.vue'

function openCenter(path: string) {
  window.open(path, '_blank', 'noopener,noreferrer')
}
</script>
<style scoped>.portal{max-width:1200px}.system-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.system-card{padding:28px;min-height:390px;position:relative;overflow:hidden}.system-card:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-110px;top:-110px;background:var(--primary-soft)}.system-icon{width:48px;height:48px;border-radius:13px;display:grid;place-items:center;background:var(--primary-soft);color:#afa5ff;font-size:21px;margin-bottom:24px}.system-card small{color:var(--subtle);letter-spacing:1.4px;font-size:11px}.system-card h2{font-size:28px;margin:10px 0}.system-card p{color:var(--muted);line-height:1.75;max-width:480px}.system-card ul{padding-left:18px;color:var(--text-2);line-height:2;margin:20px 0 28px}.delivery{background:radial-gradient(circle at 100% 0,rgba(72,155,255,.14),transparent 45%),var(--surface)}.boundary{margin-top:18px;padding:18px 22px;display:grid;grid-template-columns:auto 1fr auto auto 1fr;align-items:center;gap:16px}.boundary span{color:var(--muted);font-size:12px}.boundary i{color:var(--primary);font-size:20px}@media(max-width:900px){.system-grid{grid-template-columns:1fr}.boundary{display:flex;flex-direction:column;align-items:flex-start}}</style>
