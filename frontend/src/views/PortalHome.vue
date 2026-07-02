<template>
  <div class="page-content portal">
    <div class="page-title">
      <div>
        <span class="eyebrow">平台概览</span>
        <h1>Aegis Software OS</h1>
        <p>面向研发团队的软件操作系统，统一组织软件、团队、交付与运行。</p>
      </div>
      <div class="platform-state"><i />平台服务正常</div>
    </div>

    <section class="overview-panel">
      <div class="overview-copy">
        <span class="product-label">SOFTWARE OPERATING SYSTEM</span>
        <h2>将软件全生命周期组织成统一上下文</h2>
        <p>
          Aegis 不只是触发流水线的 DevOps 工具。它以 Project 组织团队与资源边界，
          以 Application 承载软件定义，将代码、环境、配置、审批、发布和运行状态连接起来，
          让人和 AI 都能基于同一份软件上下文理解系统、做出决策并推动交付。
        </p>
        <div class="principles">
          <span><i>01</i>统一软件模型</span>
          <span><i>02</i>全生命周期上下文</span>
          <span><i>03</i>人机协同工作流</span>
        </div>
      </div>
      <div class="scope-panel">
        <div class="scope-header"><span>Software OS 构成</span><small>SYSTEM MODEL</small></div>
        <dl>
          <div><dt>System of Record · 事实层</dt><dd>项目、应用、环境、配置、发布历史</dd></div>
          <div><dt>Control Plane · 控制层</dt><dd>部署计划、审批、策略与交付编排</dd></div>
          <div><dt>Execution Plane · 执行层</dt><dd>Tekton、Kaniko、Kubernetes</dd></div>
          <div><dt>Intelligence · 智能层</dt><dd>意图理解、上下文建议与辅助决策</dd></div>
        </dl>
      </div>
    </section>

    <section class="workspace-section">
      <div class="section-header">
        <div>
          <h2>工作空间</h2>
          <p>根据当前任务进入对应的管理区域。</p>
        </div>
        <span>2 个可用工作空间</span>
      </div>
      <div class="workspace-grid">
        <article class="workspace-card">
          <div class="workspace-identity">
            <div class="workspace-icon governance-icon"><span /><span /><span /></div>
            <div><small>GOVERNANCE WORKSPACE</small><h3>Project Center</h3></div>
          </div>
          <p>建立 Software OS 的组织与资源边界，管理成员角色、Kubernetes 集群与镜像仓库。</p>
          <div class="workspace-meta">
            <span>适用角色</span><b>项目负责人 · 平台管理员</b>
          </div>
          <ul><li>项目与成员管理</li><li>集群与环境资源</li><li>镜像仓库配置</li></ul>
          <el-button @click="openCenter('/project-center')">进入 Project Center <span>→</span></el-button>
        </article>

        <article class="workspace-card primary-card">
          <div class="workspace-identity">
            <div class="workspace-icon delivery-icon">↗</div>
            <div><small>DELIVERY WORKSPACE</small><h3>DevCenter</h3></div>
          </div>
          <p>围绕 Application 管理软件上下文，完成接入、配置、流水线、发布与运行态检查。</p>
          <div class="workspace-meta">
            <span>适用角色</span><b>开发工程师 · 交付负责人</b>
          </div>
          <ul><li>应用与环境管理</li><li>流水线与发布</li><li>日志与运行状态</li></ul>
          <el-button type="primary" @click="openCenter('/devcenter')">进入 DevCenter <span>→</span></el-button>
        </article>
      </div>
    </section>

    <section class="lifecycle-section">
      <div class="section-header">
        <div><h2>Software OS 生命周期</h2><p>软件从定义到运行，再从运行反馈到持续演进。</p></div>
      </div>
      <div class="delivery-flow" aria-label="从代码到运行的交付链路">
        <div v-for="(step, index) in deliverySteps" :key="step.label" class="delivery-step">
          <span class="step-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div><strong>{{ step.label }}</strong><small>{{ step.description }}</small></div>
          <i v-if="index < deliverySteps.length - 1">→</i>
        </div>
      </div>
    </section>
  </div>
</template>
<script setup lang="ts">
const deliverySteps = [
  { label: '定义软件', description: 'Project & Application' },
  { label: '组织上下文', description: 'Environment & Config' },
  { label: '执行交付', description: 'Pipeline & Release' },
  { label: '理解运行', description: 'Runtime & Events' },
  { label: '持续演进', description: 'Feedback & Intelligence' },
]

function openCenter(path: string) {
  window.open(path, '_blank', 'noopener,noreferrer')
}
</script>
<style scoped>
.portal{max-width:1280px;--portal-secondary:color-mix(in srgb,var(--text) 72%,transparent);--portal-tertiary:color-mix(in srgb,var(--text) 54%,transparent)}.page-title{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:26px}.eyebrow{color:var(--primary);font-size:13px;font-weight:700}.page-title h1{margin:8px 0 7px;font-size:32px;letter-spacing:-.025em}.page-title p{margin:0;color:var(--portal-secondary);font-size:15px}.platform-state{display:flex;align-items:center;gap:8px;padding:9px 13px;border:1px solid var(--border-soft);border-radius:9px;background:var(--theme-panel);color:var(--portal-secondary);font-size:13px}.platform-state i{width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 0 4px color-mix(in srgb,var(--success) 12%,transparent)}.overview-panel{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(350px,.75fr);border:1px solid var(--border-soft);border-radius:14px;background:var(--theme-panel);overflow:hidden}.overview-copy{padding:38px 42px}.product-label{font-size:11px;font-weight:750;letter-spacing:1.3px;color:var(--portal-tertiary)}.overview-copy h2{margin:11px 0 16px;font-size:27px;letter-spacing:-.025em}.overview-copy>p{max-width:740px;margin:0;color:var(--portal-secondary);font-size:15px;line-height:1.85}.principles{display:flex;gap:28px;margin-top:30px;padding-top:23px;border-top:1px solid var(--border-soft)}.principles span{display:flex;align-items:center;gap:8px;color:var(--text-2);font-size:13px;font-weight:650}.principles i{color:var(--portal-tertiary);font-family:"SFMono-Regular",monospace;font-size:11px;font-style:normal}.scope-panel{padding:32px 32px;background:var(--surface-soft);border-left:1px solid var(--border-soft)}.scope-header{display:flex;align-items:center;justify-content:space-between;padding-bottom:15px;border-bottom:1px solid var(--border-soft);font-size:14px;font-weight:700}.scope-header small{color:var(--portal-tertiary);font-size:10px;letter-spacing:1px}.scope-panel dl{margin:4px 0 0}.scope-panel dl div{padding:14px 0;border-bottom:1px solid var(--border-soft)}.scope-panel dl div:last-child{border:0}.scope-panel dt{margin-bottom:5px;color:var(--portal-tertiary);font-size:11px}.scope-panel dd{margin:0;color:var(--text-2);font-size:13px}.workspace-section,.lifecycle-section{margin-top:32px}.section-header{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:15px}.section-header h2{margin:0 0 5px;font-size:19px}.section-header p{margin:0;color:var(--portal-secondary);font-size:13px}.section-header>span{color:var(--portal-tertiary);font-size:12px}.workspace-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.workspace-card{padding:26px;border:1px solid var(--border-soft);border-radius:14px;background:var(--theme-panel)}.primary-card{border-top:2px solid var(--primary)}.workspace-identity{display:flex;align-items:center;gap:14px}.workspace-icon{width:46px;height:46px;border-radius:11px;background:var(--primary-soft);color:var(--primary)}.governance-icon{display:flex;align-items:flex-end;justify-content:center;gap:3px;padding:11px}.governance-icon span{width:5px;border-radius:2px;background:currentColor}.governance-icon span:first-child{height:11px}.governance-icon span:nth-child(2){height:20px}.governance-icon span:last-child{height:15px}.delivery-icon{display:grid;place-items:center;font-size:21px}.workspace-identity small{color:var(--portal-tertiary);font-size:10px;letter-spacing:1px}.workspace-identity h3{margin:3px 0 0;font-size:20px}.workspace-card>p{min-height:48px;margin:19px 0;color:var(--portal-secondary);font-size:14px;line-height:1.75}.workspace-meta{display:flex;align-items:center;gap:14px;padding:11px 13px;border-radius:8px;background:var(--surface-soft);font-size:12px}.workspace-meta span{color:var(--portal-tertiary)}.workspace-meta b{font-weight:650}.workspace-card ul{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.workspace-card li{padding-right:10px;border-right:1px solid var(--border-soft);color:var(--portal-secondary);font-size:12px}.workspace-card li:last-child{border:0}.workspace-card .el-button{margin-top:3px}.workspace-card .el-button span span{margin-left:8px}.delivery-flow{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--border-soft);border-radius:14px;background:var(--theme-panel);overflow:hidden}.delivery-step{position:relative;display:flex;align-items:center;gap:12px;min-height:90px;padding:17px 19px;border-right:1px solid var(--border-soft)}.delivery-step:last-child{border:0}.step-index{width:30px;height:30px;display:grid;place-items:center;flex:none;border-radius:7px;background:var(--surface-raised);color:var(--portal-tertiary);font-family:"SFMono-Regular",monospace;font-size:11px}.delivery-step strong,.delivery-step small{display:block}.delivery-step strong{font-size:13px}.delivery-step small{margin-top:4px;color:var(--portal-tertiary);font-size:10px}.delivery-step>i{position:absolute;right:-6px;z-index:1;width:12px;background:var(--theme-panel);color:var(--portal-tertiary);font-size:11px;font-style:normal}@media(max-width:900px){.overview-panel{grid-template-columns:1fr}.scope-panel{border-left:0;border-top:1px solid var(--border-soft)}.workspace-grid{grid-template-columns:1fr}.delivery-flow{grid-template-columns:1fr}.delivery-step{border-right:0;border-bottom:1px solid var(--border-soft)}.delivery-step>i{right:20px;transform:rotate(90deg)}.principles{flex-wrap:wrap}}@media(max-width:600px){.portal{padding:24px 18px 48px}.page-title{display:block}.page-title h1{font-size:29px}.platform-state{width:max-content;margin-top:17px}.overview-copy,.scope-panel{padding:26px 20px}.overview-copy h2{font-size:24px}.overview-copy>p{font-size:14px}.principles{gap:15px;margin-top:23px}.principles span{width:100%}.section-header{align-items:flex-start}.section-header>span{display:none}.workspace-card{padding:21px}.workspace-card>p{min-height:0}}
</style>
