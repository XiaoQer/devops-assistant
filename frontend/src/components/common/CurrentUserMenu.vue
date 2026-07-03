<template>
  <el-dropdown trigger="click" @command="handleCommand">
    <button class="user-menu" :class="{ compact }" type="button">
      <span class="avatar">{{ initials }}</span>
      <span class="identity">
        <b>{{ auth.user?.display_name || auth.user?.username }}</b>
        <small>@{{ auth.user?.username }}</small>
      </span>
      <span class="chevron">⌄</span>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="logout" :disabled="loggingOut">Sign out</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()
defineProps<{ compact?: boolean }>()
const loggingOut = ref(false)
const initials = computed(() => {
  const value = auth.user?.display_name?.trim() || auth.user?.username || '?'
  const words = value.split(/\s+/).filter(Boolean)
  return (words.length > 1 ? words.slice(0, 2).map(word => word[0]).join('') : value.slice(0, 2)).toUpperCase()
})

const handleCommand = async (command: string) => {
  if (command !== 'logout' || loggingOut.value) return
  loggingOut.value = true
  try {
    await auth.logout()
    await router.replace('/login')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Unable to sign out')
  } finally {
    loggingOut.value = false
  }
}
</script>

<style scoped>
.user-menu{max-width:210px;border:0;padding:4px 6px;display:flex;align-items:center;gap:9px;border-radius:10px;background:transparent;color:var(--text);cursor:pointer;text-align:left}.user-menu:hover{background:var(--surface-soft)}.avatar{width:34px;height:34px;display:grid;place-items:center;flex:none;border-radius:50%;background:var(--surface-raised);font-size:11px;font-weight:700}.identity{min-width:0}.identity b,.identity small{display:block;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.identity b{font-size:12px}.identity small{margin-top:2px;color:var(--muted);font-size:10px}.chevron{color:var(--muted);font-size:12px}.user-menu.compact .identity,.user-menu.compact .chevron{display:none}.user-menu.compact{padding:3px}
@media(max-width:760px){.user-menu .identity,.user-menu .chevron{display:none}.user-menu{padding:3px}}
</style>
