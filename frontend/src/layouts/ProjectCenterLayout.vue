<template>
  <div class="system-shell project-theme">
    <aside v-if="projectId">
      <div class="system-head"><router-link to="/portal">← Portal</router-link><span>GOVERNANCE</span></div>
      <router-link class="system-brand" :to="projectId?'/project-center/projects':'/project-center'"><span>{{projectId?'PR':'PC'}}</span><div><b>{{projectId?`Project #${projectId}`:'Project Center'}}</b><small>{{projectId?'Management Space':'Project Governance'}}</small></div></router-link>
      <p class="nav-label">{{projectId?'Current Project':'Project Center'}}</p>
      <nav>
        <router-link v-for="item in menu" :key="item.path" :to="item.path"><i>{{item.icon}}</i>{{item.name}}</router-link>
      </nav>
      <div class="boundary-note"><b>{{projectId?'Project asset view':'Governance boundary'}}</b><p>{{projectId?'Applications 仅用于资产查看，交付操作请进入 DevCenter。':'Project Center 全局态只负责 Project 列表。'}}</p></div>
    </aside>
    <main :class="{ standalone: !projectId }"><header><div class="header-title"><small>PROJECT CENTER</small><h2>{{title}}</h2></div><div class="header-actions"><router-link v-if="!projectId" class="switch" to="/portal">← Portal</router-link><router-link class="switch secondary-switch" to="/devcenter">Switch to DevCenter →</router-link><CurrentUserMenu/></div></header><div class="content"><router-view/></div></main>
  </div>
</template>
<script setup lang="ts">
import{computed}from'vue';import{useRoute}from'vue-router';import CurrentUserMenu from '../components/common/CurrentUserMenu.vue';const route=useRoute();const projectId=computed(()=>Number(route.params.projectId||route.params.id)||0);const menu=computed(()=>projectId.value?[{name:'Project Overview',path:`/project-center/projects/${projectId.value}`,icon:'⌂'},{name:'Members & Permissions',path:`/project-center/projects/${projectId.value}/members`,icon:'◎'},{name:'Kubernetes',path:`/project-center/projects/${projectId.value}/clusters`,icon:'☸'},{name:'Registries',path:`/project-center/projects/${projectId.value}/registries`,icon:'▣'},{name:'Applications',path:`/project-center/projects/${projectId.value}/applications`,icon:'◇'}]:[{name:'Projects',path:'/project-center/projects',icon:'▦'}]);const title=computed(()=>String(route.meta.title||'Project governance'));
</script>
<style scoped>
.system-shell{min-height:100vh;background:var(--theme-bg)}aside{position:fixed;inset:0 auto 0 0;width:252px;padding:18px 14px;background:#13202b;border-right:1px solid #2b3b48;display:flex;flex-direction:column;z-index:10}.system-head{display:flex;justify-content:space-between;align-items:center;padding:0 7px 18px;border-bottom:1px solid #2b3b48}.system-head a,.system-head span{font-size:10px;color:#8da2b3;text-decoration:none}.system-head span{letter-spacing:1.2px}.system-brand{display:flex;gap:11px;align-items:center;padding:22px 7px;color:#f2f6f9;text-decoration:none}.system-brand>span{width:39px;height:39px;display:grid;place-items:center;border-radius:11px;background:linear-gradient(145deg,#14b8a6,#0f766e);font-size:11px;font-weight:800}.system-brand b,.system-brand small{display:block}.system-brand b{font-size:15px}.system-brand small{font-size:10px;color:#8da2b3;margin-top:3px}.nav-label{font-size:10px;letter-spacing:1.2px;text-transform:uppercase;color:#617786;margin:8px 9px}nav{display:grid;gap:3px}nav a{height:40px;padding:0 10px;border-radius:8px;display:flex;align-items:center;gap:10px;color:#91a5b4;text-decoration:none;font-size:12px}nav a:hover{background:#192a37;color:#e8f0f5}nav a.router-link-exact-active{background:rgba(20,184,166,.14);color:#65ddd0}nav i{width:18px;text-align:center;font-style:normal}.boundary-note{margin-top:auto;padding:14px;border:1px solid #2b3b48;border-radius:10px;background:#172631}.boundary-note b{font-size:11px;color:#c5d3dc}.boundary-note p{font-size:10px;line-height:1.6;color:#7f94a3;margin:5px 0 0}.system-shell>main{margin-left:252px}.system-shell>main>header{height:68px;padding:0 34px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border-soft);background:var(--theme-panel);position:sticky;top:0;z-index:8}.system-shell header small{font-size:9px;letter-spacing:1.3px;color:#14b8a6}.system-shell header h2{font-size:15px;margin:3px 0 0}.switch{padding:8px 11px;border:1px solid var(--border-soft);border-radius:8px;color:var(--muted);font-size:11px;text-decoration:none}.content :deep(.page-content){padding-top:30px}
.system-shell>main.standalone{margin-left:0}.header-title,.header-actions{min-width:0}.header-actions{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:8px}
@media(max-width:900px){.system-shell>main>header{height:auto;min-height:68px;padding:10px 18px}.secondary-switch{display:none}}
</style>

<style>
.governance-form-overlay .el-dialog,
.governance-form-dialog {
  --el-dialog-bg-color: #f7f9fc;
  --el-dialog-border-radius: 10px;
  width: min(var(--el-dialog-width, 680px), calc(100vw - 40px)) !important;
  overflow: hidden;
  padding: 0 !important;
  border: 1px solid #d8dee8 !important;
  border-radius: 10px !important;
  background: #f7f9fc !important;
  box-shadow: 0 24px 70px rgba(6, 12, 24, 0.38);
}

.governance-form-overlay .el-dialog {
  margin-top: 8vh !important;
}

.governance-form-overlay .el-dialog.is-align-center {
  margin: auto !important;
}

.governance-form-overlay .el-dialog::before,
.governance-form-overlay .el-dialog::after {
  display: none !important;
}

.governance-form-overlay .el-dialog > * {
  background-clip: padding-box;
}

.governance-form-overlay .el-dialog__header,
.governance-form-dialog .el-dialog__header {
  margin: 0;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff !important;
}

.governance-form-overlay .el-dialog__title,
.governance-form-dialog .el-dialog__title {
  color: #172033;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0;
}

.governance-form-overlay .el-dialog__headerbtn,
.governance-form-dialog .el-dialog__headerbtn {
  top: 14px;
  right: 16px;
  width: 32px;
  height: 32px;
}

.governance-form-overlay .el-dialog__headerbtn:hover,
.governance-form-dialog .el-dialog__headerbtn:hover {
  background: #f1f5f9;
}

.governance-form-overlay .el-dialog__body,
.governance-form-dialog .el-dialog__body {
  max-height: min(72vh, 760px);
  padding: 18px 24px 0;
  overflow: auto;
  background: #f7f9fc !important;
}

.governance-form-overlay .el-dialog__footer,
.governance-form-dialog .el-dialog__footer {
  padding: 14px 24px 18px;
  border-top: 1px solid #e2e8f0;
  background: #fff !important;
}

.governance-form-overlay .form-section,
.governance-form-dialog .form-section {
  margin-bottom: 14px;
  padding: 16px 16px 2px;
  border: 1px solid #e2e7ef;
  border-radius: 9px;
  background: #fff;
}

.governance-form-overlay .section-title,
.governance-form-dialog .section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}

.governance-form-overlay .section-title h4,
.governance-form-dialog .section-title h4 {
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
}

.governance-form-overlay .section-title p,
.governance-form-dialog .section-title p {
  margin: 0;
  color: #7c8798;
  font-size: 12px;
  line-height: 1.5;
  text-align: right;
}

.governance-form-overlay .form-grid,
.governance-form-dialog .form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.governance-form-overlay .form-grid .wide,
.governance-form-dialog .form-grid .wide {
  grid-column: 1 / -1;
}

.governance-form-overlay .el-form-item,
.governance-form-dialog .el-form-item {
  margin-bottom: 14px;
}

.governance-form-overlay .el-form-item__label,
.governance-form-dialog .el-form-item__label {
  padding-bottom: 5px;
  color: #536074;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.governance-form-overlay .el-input,
.governance-form-overlay .el-select,
.governance-form-dialog .el-input,
.governance-form-dialog .el-select {
  --el-input-height: 38px;
  --el-select-height: 38px;
}

.governance-form-overlay .el-input__wrapper,
.governance-form-overlay .el-textarea__inner,
.governance-form-overlay .el-select__wrapper,
.governance-form-dialog .el-input__wrapper,
.governance-form-dialog .el-textarea__inner,
.governance-form-dialog .el-select__wrapper {
  min-height: 38px !important;
  border-radius: 7px !important;
  background: #fff !important;
  box-shadow: 0 0 0 1px #d8dee8 inset !important;
}

.governance-form-overlay .el-input__wrapper:hover,
.governance-form-overlay .el-textarea__inner:hover,
.governance-form-overlay .el-select__wrapper:hover,
.governance-form-dialog .el-input__wrapper:hover,
.governance-form-dialog .el-textarea__inner:hover,
.governance-form-dialog .el-select__wrapper:hover {
  box-shadow: 0 0 0 1px #b8c4d4 inset;
}

.governance-form-overlay .el-input__wrapper.is-focus,
.governance-form-overlay .el-textarea__inner:focus,
.governance-form-overlay .el-select__wrapper.is-focused,
.governance-form-dialog .el-input__wrapper.is-focus,
.governance-form-dialog .el-textarea__inner:focus,
.governance-form-dialog .el-select__wrapper.is-focused {
  box-shadow: 0 0 0 1px #2563eb inset, 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.governance-form-overlay .el-input__inner,
.governance-form-overlay .el-textarea__inner,
.governance-form-dialog .el-input__inner,
.governance-form-dialog .el-textarea__inner {
  color: #0f172a;
  font-size: 13px;
}

.governance-form-overlay .el-input__inner::placeholder,
.governance-form-overlay .el-textarea__inner::placeholder,
.governance-form-dialog .el-input__inner::placeholder,
.governance-form-dialog .el-textarea__inner::placeholder {
  color: #94a3b8;
}

.governance-form-overlay .el-textarea__inner,
.governance-form-dialog .el-textarea__inner {
  min-height: 88px !important;
  padding: 10px 12px;
}

.governance-form-overlay .el-button,
.governance-form-dialog .el-button {
  min-height: 36px;
  border-radius: 7px;
  font-weight: 700;
}

.governance-form-overlay .el-dialog__footer .el-button,
.governance-form-dialog .el-dialog__footer .el-button {
  min-width: 92px;
}

.governance-form-overlay .el-switch,
.governance-form-dialog .el-switch {
  --el-switch-on-color: #2563eb;
}

@media (max-width: 760px) {
  .governance-form-overlay .form-grid,
  .governance-form-dialog .form-grid {
    grid-template-columns: 1fr;
  }

  .governance-form-overlay .form-grid .wide,
  .governance-form-dialog .form-grid .wide {
    grid-column: auto;
  }

  .governance-form-overlay .el-dialog__header,
  .governance-form-overlay .el-dialog__body,
  .governance-form-overlay .el-dialog__footer,
  .governance-form-dialog .el-dialog__header,
  .governance-form-dialog .el-dialog__body,
  .governance-form-dialog .el-dialog__footer {
    padding-left: 18px;
    padding-right: 18px;
  }

  .governance-form-overlay .section-title,
  .governance-form-dialog .section-title {
    display: block;
  }

  .governance-form-overlay .section-title p,
  .governance-form-dialog .section-title p {
    margin-top: 4px;
    text-align: left;
  }
}
</style>
