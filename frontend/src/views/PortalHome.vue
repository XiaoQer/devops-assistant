<template>
  <div class="portal">
    <section class="hero">
      <div class="hero-glow hero-glow-left" />
      <div class="hero-glow hero-glow-right" />
      <div class="hero-content">
        <span class="eyebrow"><i />AI-Native Software Delivery Platform</span>
        <h1>
          让每一次软件交付<br>
          <span>清晰、可靠、可掌控</span>
        </h1>
        <p class="hero-description">
          Aegis 将代码仓库、构建流水线、镜像、环境与运行状态连接在同一个项目上下文中，
          帮助团队从代码出发，安全地完成发布，并持续理解软件正在如何运行。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="openCenter('/devcenter')">
            开始交付应用 <span>→</span>
          </el-button>
          <el-button size="large" @click="openCenter('/project-center')">
            管理项目资源
          </el-button>
        </div>
      </div>

      <div class="delivery-map" aria-label="从代码到运行的交付链路">
        <div v-for="(step, index) in deliverySteps" :key="step.label" class="delivery-step">
          <div class="step-icon" :class="`step-${index + 1}`">{{ step.icon }}</div>
          <div>
            <small>{{ step.meta }}</small>
            <strong>{{ step.label }}</strong>
          </div>
          <span v-if="index < deliverySteps.length - 1" class="step-line">→</span>
        </div>
      </div>
    </section>

    <section class="platform-intro">
      <div class="section-heading">
        <span>ONE PLATFORM, TWO WORKSPACES</span>
        <h2>从资源治理到应用交付，团队在同一个平台协作</h2>
        <p>项目负责人定义边界，开发者在边界内完成交付。职责清晰，过程连贯。</p>
      </div>

      <div class="workspace-grid">
        <article class="workspace-card governance">
          <div class="card-topline">
            <span class="workspace-number">01</span>
            <span class="workspace-tag">面向项目负责人</span>
          </div>
          <div class="workspace-icon governance-icon"><span /><span /><span /></div>
          <h3>Project Center</h3>
          <h4>定义团队与交付资源</h4>
          <p>创建项目空间，组织成员与角色，统一管理 Kubernetes 集群和镜像仓库，为应用交付建立清晰、安全的资源边界。</p>
          <div class="capability-list">
            <span>项目与成员</span><span>集群与环境</span><span>镜像仓库</span>
          </div>
          <button class="workspace-link" @click="openCenter('/project-center')">
            进入项目治理中心 <span>↗</span>
          </button>
        </article>

        <article class="workspace-card delivery">
          <div class="card-topline">
            <span class="workspace-number">02</span>
            <span class="workspace-tag">面向开发与交付团队</span>
          </div>
          <div class="workspace-icon delivery-icon"><span>↗</span></div>
          <h3>DevCenter</h3>
          <h4>让代码持续、可靠地运行</h4>
          <p>从 Git 仓库创建应用，自动识别构建方式，触发 Tekton 流水线，并在统一工作空间中查看发布、日志和运行状态。</p>
          <div class="capability-list">
            <span>应用接入</span><span>流水线与发布</span><span>运行态检查</span>
          </div>
          <button class="workspace-link" @click="openCenter('/devcenter')">
            进入应用交付中心 <span>↗</span>
          </button>
        </article>
      </div>
    </section>

    <section class="promise">
      <span class="promise-mark">A</span>
      <div>
        <small>THE AEGIS PROMISE</small>
        <p>基础设施保持强大，交付体验不必复杂。</p>
      </div>
      <span class="promise-detail">Project-aware · Kubernetes-native · AI-ready</span>
    </section>
  </div>
</template>
<script setup lang="ts">
const deliverySteps = [
  { icon: '</>', meta: 'SOURCE', label: 'Git Repository' },
  { icon: '⌁', meta: 'BUILD', label: 'Tekton Pipeline' },
  { icon: '◇', meta: 'PACKAGE', label: 'Container Image' },
  { icon: '⬡', meta: 'RUN', label: 'Kubernetes' },
  { icon: '✓', meta: 'CONTROL', label: 'Release & Runtime' },
]

function openCenter(path: string) {
  window.open(path, '_blank', 'noopener,noreferrer')
}
</script>
<style scoped>
.portal{min-height:calc(100vh - 72px);overflow:hidden}.hero{position:relative;padding:88px 48px 52px;border-bottom:1px solid var(--border-soft);background:linear-gradient(180deg,color-mix(in srgb,var(--theme-panel) 65%,transparent),transparent)}.hero-content{position:relative;z-index:1;max-width:860px;margin:0 auto;text-align:center}.eyebrow{display:inline-flex;align-items:center;gap:9px;padding:7px 13px;border:1px solid var(--border-soft);border-radius:999px;background:color-mix(in srgb,var(--theme-panel) 75%,transparent);color:var(--muted);font-size:10px;font-weight:700;letter-spacing:1.5px}.eyebrow i{width:6px;height:6px;border-radius:50%;background:#3b82f6;box-shadow:0 0 0 5px rgba(59,130,246,.1)}.hero h1{margin:28px 0 20px;font-size:clamp(44px,5.5vw,76px);line-height:1.06;letter-spacing:-.055em;font-weight:720}.hero h1 span{color:#2563eb}.hero-description{max-width:730px;margin:0 auto;color:var(--muted);font-size:16px;line-height:1.9}.hero-actions{display:flex;justify-content:center;gap:12px;margin-top:32px}.hero-actions .el-button{min-width:148px}.hero-actions .el-button span{margin-left:7px}.hero-glow{position:absolute;border-radius:50%;filter:blur(2px);pointer-events:none}.hero-glow-left{width:480px;height:480px;left:-290px;top:-210px;background:radial-gradient(circle,rgba(37,99,235,.13),transparent 68%)}.hero-glow-right{width:420px;height:420px;right:-230px;top:30px;background:radial-gradient(circle,rgba(56,189,248,.1),transparent 68%)}.delivery-map{position:relative;z-index:1;max-width:1040px;margin:70px auto 0;padding:18px 22px;display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--border-soft);border-radius:18px;background:color-mix(in srgb,var(--theme-panel) 82%,transparent);box-shadow:0 18px 60px rgba(15,23,42,.06);backdrop-filter:blur(18px)}.delivery-step{position:relative;display:flex;align-items:center;justify-content:center;gap:11px;min-height:54px}.step-icon{width:36px;height:36px;display:grid;place-items:center;border-radius:10px;background:var(--surface-raised);color:var(--primary);font-size:12px;font-weight:800}.delivery-step small,.delivery-step strong{display:block}.delivery-step small{color:var(--subtle);font-size:8px;letter-spacing:1.2px}.delivery-step strong{margin-top:2px;font-size:11px}.step-line{position:absolute;right:-4px;color:var(--subtle);font-size:14px}.platform-intro{max-width:1180px;margin:0 auto;padding:90px 36px 84px}.section-heading{max-width:720px;margin-bottom:38px}.section-heading span{color:#2563eb;font-size:10px;font-weight:800;letter-spacing:1.6px}.section-heading h2{margin:12px 0 12px;font-size:34px;line-height:1.25;letter-spacing:-.035em}.section-heading p{margin:0;color:var(--muted);font-size:14px}.workspace-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.workspace-card{position:relative;min-height:470px;padding:30px;border:1px solid var(--border-soft);border-radius:20px;background:var(--theme-panel);overflow:hidden;transition:transform .25s ease,border-color .25s ease,box-shadow .25s ease}.workspace-card:hover{transform:translateY(-3px);border-color:rgba(37,99,235,.2);box-shadow:0 24px 60px rgba(15,23,42,.09)}.workspace-card:after{content:"";position:absolute;width:260px;height:260px;right:-150px;bottom:-160px;border-radius:50%;background:rgba(37,99,235,.08)}.delivery:after{background:rgba(56,189,248,.1)}.card-topline{display:flex;align-items:center;justify-content:space-between}.workspace-number{font-family:"SFMono-Regular",monospace;color:var(--subtle);font-size:11px}.workspace-tag{padding:5px 9px;border-radius:999px;background:var(--surface-raised);color:var(--muted);font-size:10px}.workspace-icon{width:52px;height:52px;margin:46px 0 22px;border-radius:15px;background:var(--primary-soft);color:var(--primary)}.governance-icon{display:flex;align-items:flex-end;justify-content:center;gap:4px;padding:13px}.governance-icon span{width:6px;border-radius:3px;background:currentColor}.governance-icon span:first-child{height:14px}.governance-icon span:nth-child(2){height:25px}.governance-icon span:last-child{height:19px}.delivery-icon{display:grid;place-items:center;font-size:23px}.workspace-card h3{margin:0;color:var(--muted);font-size:13px;font-weight:650}.workspace-card h4{margin:6px 0 14px;font-size:26px;letter-spacing:-.03em}.workspace-card p{max-width:470px;min-height:76px;margin:0;color:var(--muted);font-size:13px;line-height:1.8}.capability-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}.capability-list span{padding:6px 10px;border:1px solid var(--border-soft);border-radius:8px;color:var(--text-2);font-size:10px}.workspace-link{position:absolute;z-index:1;left:30px;bottom:30px;display:flex;align-items:center;gap:8px;padding:0;border:0;background:none;color:var(--primary);font-size:12px;font-weight:700;cursor:pointer}.workspace-link span{font-size:16px;transition:transform .2s}.workspace-link:hover span{transform:translate(2px,-2px)}.promise{max-width:1108px;margin:0 auto 70px;padding:22px 24px;display:flex;align-items:center;gap:16px;border-top:1px solid var(--border-soft);border-bottom:1px solid var(--border-soft)}.promise-mark{width:38px;height:38px;display:grid;place-items:center;border-radius:12px;background:#111827;color:white;font-weight:800}.promise small{color:var(--subtle);font-size:8px;letter-spacing:1.4px}.promise p{margin:2px 0 0;font-size:13px;font-weight:650}.promise-detail{margin-left:auto;color:var(--muted);font-size:10px;letter-spacing:.5px}@media(max-width:900px){.hero{padding:64px 24px 36px}.delivery-map{grid-template-columns:1fr;margin-top:48px;padding:10px 18px}.delivery-step{justify-content:flex-start;border-bottom:1px solid var(--border-soft)}.delivery-step:last-child{border-bottom:0}.step-line{right:4px;transform:rotate(90deg)}.workspace-grid{grid-template-columns:1fr}.platform-intro{padding:64px 22px}.section-heading h2{font-size:28px}.promise{margin:0 22px 48px}.promise-detail{display:none}}@media(max-width:560px){.hero h1{font-size:42px}.hero-description{font-size:14px}.hero-actions{flex-direction:column}.hero-actions .el-button{width:100%;margin:0}.workspace-card{min-height:500px;padding:24px}.workspace-link{left:24px}.promise{align-items:flex-start}}
</style>
