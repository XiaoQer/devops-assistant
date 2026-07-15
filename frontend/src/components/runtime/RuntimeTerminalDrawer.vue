<template>
  <el-drawer
    :model-value="modelValue"
    :title="title"
    size="72%"
    destroy-on-close
    @open="openTerminal"
    @close="closeTerminal"
  >
    <div class="terminal-meta">
      <span :class="['connection-dot', connectionStatus]"></span>
      <span>{{ statusLabel }}</span>
      <small>会话内容不会写入审计日志</small>
    </div>
    <div ref="host" class="terminal-host"></div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import type { RuntimeExecSession } from '../../types'
import { decodeTerminalFrame, encodeResizeFrame } from './runtime-view-model'

const props = defineProps<{
  modelValue: boolean
  title: string
  session?: RuntimeExecSession
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const host = ref<HTMLElement>()
const connectionStatus = ref<'connecting' | 'connected' | 'closed'>('closed')
let terminal: Terminal | undefined
let fitAddon: FitAddon | undefined
let socket: WebSocket | undefined
let resizeObserver: ResizeObserver | undefined

const statusLabel = computed(() => ({
  connecting: '正在连接', connected: '已连接', closed: '已关闭',
})[connectionStatus.value])

function websocketUrl(path: string) {
  const url = new URL(path, window.location.origin)
  url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

async function openTerminal() {
  if (!props.session) return
  await nextTick()
  connectionStatus.value = 'connecting'
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    theme: { background: '#0b1020', foreground: '#dbeafe' },
  })
  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(host.value!)
  fitAddon.fit()
  terminal.writeln('\x1b[36mAegis Pod Terminal\x1b[0m')
  socket = new WebSocket(websocketUrl(props.session.websocket_url))
  socket.addEventListener('open', () => {
    connectionStatus.value = 'connected'
    socket?.send(encodeResizeFrame(terminal?.cols || 80, terminal?.rows || 24))
  })
  socket.addEventListener('message', event => {
    const frame = decodeTerminalFrame(String(event.data))
    if (frame.type === 'stdout') terminal?.write(frame.data || '')
    else if (frame.type === 'stderr') terminal?.write(`\x1b[31m${frame.data || ''}\x1b[0m`)
    else if (frame.status) terminal?.writeln(`\r\n[${frame.status}]`)
  })
  socket.addEventListener('close', () => {
    connectionStatus.value = 'closed'
    terminal?.writeln('\r\n\x1b[33m会话已关闭\x1b[0m')
  })
  socket.addEventListener('error', () => {
    terminal?.writeln('\r\n\x1b[31m终端连接失败\x1b[0m')
  })
  terminal.onData(data => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stdin', data }))
    }
  })
  terminal.onResize(({ cols, rows }) => {
    if (socket?.readyState === WebSocket.OPEN) socket.send(encodeResizeFrame(cols, rows))
  })
  resizeObserver = new ResizeObserver(() => fitAddon?.fit())
  resizeObserver.observe(host.value!)
}

function closeTerminal() {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'close' }))
  }
  socket?.close()
  socket = undefined
  resizeObserver?.disconnect()
  resizeObserver = undefined
  terminal?.dispose()
  terminal = undefined
  fitAddon = undefined
  connectionStatus.value = 'closed'
  emit('update:modelValue', false)
}

onBeforeUnmount(closeTerminal)
</script>

<style scoped>
.terminal-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: var(--muted); font-size: 13px; }
.terminal-meta small { margin-left: auto; }
.connection-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }
.connection-dot.connected { background: #22c55e; }
.connection-dot.connecting { background: #f59e0b; }
.terminal-host { height: calc(100vh - 180px); min-height: 420px; padding: 12px; border-radius: 12px; background: #0b1020; }
</style>
