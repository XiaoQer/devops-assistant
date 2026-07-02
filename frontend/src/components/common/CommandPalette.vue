<template>
  <teleport to="body">
    <transition name="palette-fade">
      <div v-if="commandStore.isOpen" class="palette-overlay" @click.self="commandStore.close()">
        <section class="palette surface glass-card">
          <header class="palette-header">
            <div class="palette-input-wrap">
              <span>⌘</span>
              <input
                ref="inputRef"
                :value="commandStore.query"
                type="text"
                placeholder="Ask Aegis what to do next"
                @input="onInput"
              />
            </div>
            <button class="close-button" @click="commandStore.close()">Esc</button>
          </header>

          <div class="palette-body">
            <div class="palette-hints">
              <span>⌘K 打开</span>
              <span>↑↓ 选择</span>
              <span>Enter 执行</span>
            </div>

            <div v-if="showHighlights" class="highlight-grid">
              <section v-if="recommendedCommands.length" class="highlight-card">
                <h4>Recommended</h4>
                <button
                  v-for="command in recommendedCommands"
                  :key="command.id"
                  class="highlight-item"
                  :class="{ active: command.id === activeCommand?.id }"
                  @mouseenter="setActive(command.id)"
                  @click="handleExecute(command)"
                >
                  <strong>{{ command.title }}</strong>
                  <p>{{ command.description }}</p>
                </button>
              </section>

              <section v-if="recentCommands.length" class="highlight-card">
                <h4>Recent</h4>
                <button
                  v-for="command in recentCommands"
                  :key="command.id"
                  class="highlight-item"
                  :class="{ active: command.id === activeCommand?.id }"
                  @mouseenter="setActive(command.id)"
                  @click="handleExecute(command)"
                >
                  <strong>{{ command.title }}</strong>
                  <p>{{ command.description }}</p>
                </button>
              </section>
            </div>

            <div v-if="visibleGroups.length" class="group-list">
              <section v-for="group in visibleGroups" :key="group.section" class="command-group">
                <h4>{{ group.section }}</h4>
                <button
                  v-for="command in group.items"
                  :key="command.id"
                  class="command-item"
                  :class="{ active: command.id === activeCommand?.id }"
                  @mouseenter="setActive(command.id)"
                  @click="handleExecute(command)"
                >
                  <div>
                    <strong>{{ command.title }}</strong>
                    <p>{{ command.description }}</p>
                  </div>
                  <span v-if="command.shortcut" class="shortcut">{{ command.shortcut }}</span>
                </button>
              </section>
            </div>

            <EmptyState v-else title="没有找到匹配命令" description="换个关键词试试，或者直接用更自然的描述方式输入你的意图。" icon="⌘" />
          </div>
        </section>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCommandStore } from '../../stores/command'
import { useCommandCenter, type CommandItem } from '../../composables/useCommandCenter'
import EmptyState from './EmptyState.vue'

const commandStore = useCommandStore()
const { commands, recentCommands, recommendedCommands, ensureApplicationCommands, executeCommand } = useCommandCenter()
const inputRef = ref<HTMLInputElement>()
const activeId = ref('')

const filteredCommands = computed(() => {
  const query = commandStore.query.trim().toLowerCase()
  if (!query) return commands.value

  return commands.value.filter(command => {
    const haystack = [command.title, command.description, command.section, ...command.keywords].join(' ').toLowerCase()
    return query.split(/\s+/).every(word => haystack.includes(word))
  })
})

const showHighlights = computed(() => !commandStore.query.trim())

const visibleGroups = computed(() => {
  const groups = new Map<string, CommandItem[]>()
  for (const command of filteredCommands.value) {
    const items = groups.get(command.section) || []
    items.push(command)
    groups.set(command.section, items)
  }
  return Array.from(groups.entries()).map(([section, items]) => ({ section, items }))
})

const flatCommands = computed(() => {
  const highlightCommands = showHighlights.value
    ? [...recommendedCommands.value, ...recentCommands.value.filter(command => !recommendedCommands.value.some(item => item.id === command.id))]
    : []

  const unique = new Map<string, CommandItem>()
  for (const command of [...highlightCommands, ...visibleGroups.value.flatMap(group => group.items)]) {
    unique.set(command.id, command)
  }
  return Array.from(unique.values())
})

const activeCommand = computed(() => flatCommands.value.find(command => command.id === activeId.value) || flatCommands.value[0])

watch(flatCommands, commandsList => {
  if (!commandsList.length) {
    activeId.value = ''
    return
  }
  if (!commandsList.some(command => command.id === activeId.value)) {
    activeId.value = commandsList[0].id
  }
}, { immediate: true })

watch(() => commandStore.isOpen, async isOpen => {
  if (!isOpen) return
  await ensureApplicationCommands()
  await nextTick()
  inputRef.value?.focus()
  inputRef.value?.select()
})

function setActive(id: string) {
  activeId.value = id
}

function onInput(event: Event) {
  commandStore.setQuery((event.target as HTMLInputElement).value)
}

async function handleExecute(command: CommandItem) {
  await executeCommand(command)
}

function moveActive(offset: number) {
  if (!flatCommands.value.length) return
  const currentIndex = flatCommands.value.findIndex(command => command.id === activeCommand.value?.id)
  const nextIndex = currentIndex < 0 ? 0 : (currentIndex + offset + flatCommands.value.length) % flatCommands.value.length
  activeId.value = flatCommands.value[nextIndex].id
}

async function onWindowKeydown(event: KeyboardEvent) {
  const isMetaShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k'
  if (isMetaShortcut) {
    event.preventDefault()
    commandStore.toggle()
    return
  }

  if (!commandStore.isOpen) return

  if (event.key === 'Escape') {
    event.preventDefault()
    commandStore.close()
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActive(1)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActive(-1)
    return
  }

  if (event.key === 'Enter' && activeCommand.value) {
    event.preventDefault()
    await handleExecute(activeCommand.value)
  }
}

onMounted(() => {
  window.addEventListener('keydown', onWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onWindowKeydown)
})
</script>

<style scoped>
.palette-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.26);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 10vh 24px 24px;
}

.palette {
  width: min(760px, 100%);
  overflow: hidden;
  box-shadow: 0 32px 80px rgba(15, 23, 42, 0.18);
}

.palette-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-soft);
  display: flex;
  align-items: center;
  gap: 12px;
}

.palette-input-wrap {
  flex: 1;
  min-height: 58px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: var(--theme-panel);
}

.palette-input-wrap span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
}

.palette-input-wrap input {
  flex: 1;
  border: 0;
  background: transparent;
  color: var(--text);
  outline: none;
  font-size: 16px;
}

.close-button {
  min-width: 54px;
  height: 40px;
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  background: var(--surface-soft);
  color: var(--muted);
}

.palette-body {
  max-height: min(70vh, 720px);
  overflow: auto;
  padding: 14px 20px 20px;
}

.palette-hints {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.palette-hints span,
.shortcut {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 12px;
}

.highlight-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}

.highlight-card {
  padding: 14px;
  border-radius: 16px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.highlight-card h4,
.command-group h4 {
  margin: 0 0 10px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.highlight-item,
.command-item {
  width: 100%;
  padding: 16px;
  text-align: left;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--theme-panel);
  cursor: pointer;
}

.highlight-item + .highlight-item,
.command-item + .command-item {
  margin-top: 8px;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.command-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.highlight-item:hover,
.highlight-item.active,
.command-item:hover,
.command-item.active {
  border-color: rgba(37, 99, 235, 0.18);
  background: rgba(37, 99, 235, 0.05);
}

.highlight-item strong,
.command-item strong {
  display: block;
  font-size: 15px;
  letter-spacing: -0.02em;
}

.highlight-item p,
.command-item p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

.palette-fade-enter-active,
.palette-fade-leave-active {
  transition: opacity 0.18s ease;
}

.palette-fade-enter-from,
.palette-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .highlight-grid {
    grid-template-columns: 1fr;
  }
}
</style>

