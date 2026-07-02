<template>
  <div class="app-shell">
    <div class="ambient-a"></div>
    <div class="ambient-b"></div>
    <aside class="sidebar">
      <router-link to="/" class="brand">
        <div class="brand-mark">
          <span></span><span></span><span></span>
        </div>
        <span class="brand-name">Aegis</span>
      </router-link>

      <div class="nav-group">
        <div class="nav-label">MENU</div>
        <router-link v-for="item in nav" :key="item.path" :to="item.path" class="nav-item" active-class="active">
          <component :is="item.icon" />
          {{ item.name }}
          <span v-if="item.path === '/approvals'" class="nav-count warning">3</span>
        </router-link>
      </div>

      <div class="nav-group nav-secondary">
        <div class="nav-label">PLATFORM</div>
        <router-link to="/settings/registries" class="nav-item" active-class="active">
          <IconRegistry />
          Registries
        </router-link>
        <a href="#" class="nav-item">
          <IconStatus />
          System Status
          <i class="nav-pulse"></i>
        </a>
      </div>

      <footer class="sidebar-footer">
        <div class="avatar">SL</div>
        <div>
          <strong>Shaoqian Li</strong>
          <span>@shaoqian</span>
        </div>
        <button class="more-button">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0-6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 12c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
        </button>
      </footer>
    </aside>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { shallowRef } from 'vue'
import IconDashboard from '../components/icons/IconDashboard.vue'
import IconApplication from '../components/icons/IconApplication.vue'
import IconPipeline from '../components/icons/IconPipeline.vue'
import IconRelease from '../components/icons/IconRelease.vue'
import IconApproval from '../components/icons/IconApproval.vue'
import IconRegistry from '../components/icons/IconRegistry.vue'
import IconStatus from '../components/icons/IconStatus.vue'

const nav = shallowRef([
  { name: 'Dashboard', path: '/dashboard', icon: IconDashboard },
  { name: 'Applications', path: '/applications', icon: IconApplication },
  { name: 'Pipelines', path: '/pipelines', icon: IconPipeline },
  { name: 'Releases', path: '/releases', icon: IconRelease },
  { name: 'Approvals', path: '/approvals', icon: IconApproval },
])
</script>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--theme-bg);
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 250px;
  padding: 24px 16px 28px;
  background: var(--theme-sidebar);
  border-right: 1px solid var(--theme-line);
  display: flex;
  flex-direction: column;
  z-index: 10;
  transition: background .2s, border-color .2s;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px;
  margin-bottom: 32px;
  text-decoration: none;
  color: var(--theme-text);
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  background: linear-gradient(145deg, #9487f3, #6655d3);
  flex-shrink: 0;
}

.brand-mark span {
  width: 4px;
  height: 16px;
  background: #fff;
  border-radius: 4px;
}

.brand-name {
  font-size: 18px;
  font-weight: 600;
}

.nav-group {
  margin-bottom: 24px;
}

.nav-label {
  margin-bottom: 8px;
  padding: 0 12px;
  color: var(--theme-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.nav-item {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  border-radius: 8px;
  color: var(--theme-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  position: relative;
  transition: color .2s, background-color .2s;
}

.nav-item:hover {
  color: var(--theme-text);
  background: var(--theme-panel-strong);
}

.nav-item.active {
  color: var(--purple);
  background: var(--theme-panel);
}

.nav-item .nav-count {
  position: absolute;
  top: 50%;
  right: 12px;
  transform: translateY(-50%);
  background: var(--purple-2);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 12px;
}

.nav-secondary {
  margin-top: auto;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--theme-line);
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--theme-panel-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--theme-text);
}

.more-button {
  width: 36px;
  height: 36px;
  border: 0;
  background: none;
  color: var(--theme-muted);
  margin-left: auto;
  cursor: pointer;
}
.more-button svg {
  fill: currentColor;
}

.main {
  margin-left: 250px;
  flex: 1;
  padding: 24px;
}
</style>
