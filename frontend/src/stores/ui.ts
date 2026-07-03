import { defineStore } from 'pinia'
import { ref } from 'vue'

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'aegis-ui-theme'
const SIDEBAR_KEY = 'aegis-sidebar-collapsed'

export const useUiStore = defineStore('ui', () => {
  const theme = ref<ThemeMode>('light')
  const sidebarCollapsed = ref(false)
  const initialized = ref(false)

  function applyTheme(nextTheme: ThemeMode) {
    if (typeof document !== 'undefined') {
      document.body.dataset.theme = nextTheme
    }
  }

  function setTheme(newTheme: ThemeMode) {
    theme.value = newTheme
    applyTheme(newTheme)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(THEME_KEY, newTheme)
    }
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(SIDEBAR_KEY, String(sidebarCollapsed.value))
    }
  }

  function initUi() {
    if (initialized.value) return

    if (typeof window !== 'undefined') {
      const storedTheme = window.localStorage.getItem(THEME_KEY) as ThemeMode | null
      const preferredDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
      theme.value = storedTheme || (preferredDark ? 'dark' : 'light')

      const storedSidebar = window.localStorage.getItem(SIDEBAR_KEY)
      sidebarCollapsed.value = storedSidebar === 'true'
    }

    applyTheme(theme.value)
    initialized.value = true
  }

  return {
    theme,
    sidebarCollapsed,
    initialized,
    initUi,
    setTheme,
    toggleTheme,
    toggleSidebar,
  }
})
