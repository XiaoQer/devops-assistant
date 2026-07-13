<template>
  <div class="portal-shell">
    <header class="portal-header">
      <router-link class="portal-brand" to="/portal">
        <span class="brand-mark"><i/><i/><i/></span>
        <div><strong>Aegis Portal</strong><small>Enterprise Software Platform</small></div>
      </router-link>
      <nav>
        <router-link to="/portal">Home</router-link>
        <router-link to="/project-center">Project Center</router-link>
        <router-link to="/devcenter">DevCenter</router-link>
      </nav>
      <CurrentUserMenu />
    </header>
    <main><router-view/></main>
  </div>
</template>
<script setup lang="ts">
import CurrentUserMenu from '../components/common/CurrentUserMenu.vue'
</script>
<style scoped>
.portal-shell{min-height:100vh;background:radial-gradient(circle at 50% -10%,rgba(59,130,246,.14),transparent 34%),var(--theme-bg)}.portal-header{height:72px;padding:0 42px;border-bottom:1px solid var(--border-soft);display:flex;align-items:center;gap:36px;background:color-mix(in srgb,var(--theme-panel) 88%,transparent);backdrop-filter:blur(18px);position:sticky;top:0;z-index:10}.portal-brand{display:flex;align-items:center;gap:11px;color:var(--text);text-decoration:none}.brand-mark{width:36px;height:36px;border-radius:11px;display:flex;align-items:center;justify-content:center;gap:3px;background:linear-gradient(145deg,#3b82f6,#1d4ed8)}.brand-mark i{width:3px;height:14px;background:white;border-radius:2px}.brand-mark i:first-child,.brand-mark i:last-child{height:8px}.portal-brand strong,.portal-brand small{display:block}.portal-brand strong{font-size:15px}.portal-brand small{font-size:10px;color:var(--muted);margin-top:2px}.portal-header nav{display:flex;gap:6px;flex:1}.portal-header nav a{padding:9px 12px;border-radius:8px;color:var(--muted);font-size:12px;text-decoration:none}.portal-header nav a.router-link-active{color:var(--text);background:var(--primary-soft)}.portal-shell main{min-height:calc(100vh - 72px)}
@media(max-width:700px){.portal-header{height:64px;padding:0 20px}.portal-header nav,.portal-header :deep(.user-menu .identity),.portal-header :deep(.user-menu .chevron){display:none}.portal-brand{margin:0 auto 0 0}.portal-brand small{font-size:9px}.portal-shell main{min-height:calc(100vh - 64px)}}
</style>
