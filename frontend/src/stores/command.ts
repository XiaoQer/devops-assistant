import { defineStore } from 'pinia'
import { ref } from 'vue'

type RecentCommand = {
  id: string
  title: string
  section: string
}

const RECENT_COMMANDS_KEY = 'aegis-command-recent'
const MAX_RECENT = 6

export const useCommandStore = defineStore('command', () => {
  const isOpen = ref(false)
  const query = ref('')
  const recent = ref<RecentCommand[]>([])

  function loadRecent() {
    if (typeof window === 'undefined') return
    try {
      const stored = window.localStorage.getItem(RECENT_COMMANDS_KEY)
      recent.value = stored ? JSON.parse(stored) as RecentCommand[] : []
    } catch {
      recent.value = []
    }
  }

  function persistRecent() {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(RECENT_COMMANDS_KEY, JSON.stringify(recent.value))
  }

  function remember(command: RecentCommand) {
    recent.value = [command, ...recent.value.filter(item => item.id !== command.id)].slice(0, MAX_RECENT)
    persistRecent()
  }

  function open(nextQuery = '') {
    isOpen.value = true
    query.value = nextQuery
    if (!recent.value.length) loadRecent()
  }

  function close() {
    isOpen.value = false
    query.value = ''
  }

  function setQuery(nextQuery: string) {
    query.value = nextQuery
  }

  function toggle(nextQuery = '') {
    if (isOpen.value) {
      close()
      return
    }
    open(nextQuery)
  }

  return {
    isOpen,
    query,
    recent,
    open,
    close,
    setQuery,
    toggle,
    remember,
    loadRecent,
  }
})
