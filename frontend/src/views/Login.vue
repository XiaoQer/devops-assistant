<template>
  <main class="login-page">
    <section class="login-card">
      <div class="brand-mark" aria-hidden="true"><i/><i/><i/></div>
      <p class="eyebrow">AEGIS SOFTWARE OS</p>
      <h1>Welcome back</h1>
      <p class="intro">Sign in to continue to your delivery workspace.</p>

      <el-alert
        v-if="sessionUnavailable"
        class="session-alert"
        title="We could not verify your session. Please sign in again."
        type="warning"
        :closable="false"
        show-icon
      />

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="Username" :error="errors.username">
          <el-input
            v-model="username"
            autocomplete="username"
            placeholder="Enter your username"
            @input="errors.username = ''"
          />
        </el-form-item>
        <el-form-item label="Password" :error="errors.password">
          <el-input
            :key="passwordInputKey"
            v-model="password"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="Enter your password"
            @input="errors.password = ''"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button class="submit" type="primary" native-type="submit" :loading="submitting">
          Sign in
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { resolveSafeRedirect } from '../router/safeRedirect'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const passwordInputKey = ref(0)
const submitting = ref(false)
const errors = reactive({ username: '', password: '' })
const sessionUnavailable = computed(() =>
  route.query.session_unavailable !== undefined || route.query.error === 'session_unavailable',
)

const submit = async () => {
  if (submitting.value) return
  errors.username = username.value.trim() ? '' : 'Username is required'
  errors.password = password.value ? '' : 'Password is required'
  if (errors.username || errors.password) return

  submitting.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    await router.replace(resolveSafeRedirect(router, route.query.redirect))
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Unable to sign in')
  } finally {
    password.value = ''
    passwordInputKey.value += 1
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page{min-height:100vh;display:grid;place-items:center;padding:32px;background:radial-gradient(circle at 50% 0,rgba(59,130,246,.18),transparent 36%),var(--theme-bg)}
.login-card{width:min(100%,400px);padding:38px;border:1px solid var(--border-soft);border-radius:22px;background:var(--theme-panel);box-shadow:0 24px 70px rgba(15,23,42,.18)}
.brand-mark{width:46px;height:46px;margin-bottom:24px;border-radius:14px;display:flex;align-items:center;justify-content:center;gap:4px;background:linear-gradient(145deg,#3b82f6,#1d4ed8);box-shadow:0 12px 28px rgba(37,99,235,.24)}
.brand-mark i{width:4px;height:18px;border-radius:3px;background:#fff}.brand-mark i:first-child,.brand-mark i:last-child{height:10px}
.eyebrow{margin:0;color:var(--primary);font-size:10px;font-weight:700;letter-spacing:.14em}.login-card h1{margin:8px 0;font-size:28px;color:var(--text)}.intro{margin:0 0 26px;color:var(--muted);font-size:13px;line-height:1.6}.session-alert{margin-bottom:20px}.submit{width:100%;margin-top:6px}
</style>
