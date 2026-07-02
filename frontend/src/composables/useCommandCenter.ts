import { computed, ref, watchEffect } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { aiApi } from '../api/ai'
import { applicationApi } from '../api/application'
import { useApplicationStore } from '../stores/application'
import { useCommandStore } from '../stores/command'
import { useUiStore } from '../stores/ui'

export interface CommandItem {
  id: string
  title: string
  description: string
  section: string
  keywords: string[]
  shortcut?: string
  run: () => void | Promise<unknown>
}

const quickPrompts = [
  'Deploy payment service',
  'Rollback order service',
  'Create a Java application',
  'Show production incidents',
  'Generate CI pipeline',
  'Scale gateway to 5 replicas',
]

export function useCommandCenter() {
  const router = useRouter()
  const applicationStore = useApplicationStore()
  const commandStore = useCommandStore()
  const uiStore = useUiStore()
  const commands = ref<CommandItem[]>([])

  watchEffect(() => {
    const serviceCommands: CommandItem[] = applicationStore.items.slice(0, 8).flatMap(app => ([
      {
        id: `open-app-${app.id}`,
        title: `Open ${app.name}`,
        description: '进入这个服务的软件工作区',
        section: 'Services',
        keywords: [app.name, app.repo_url, app.language, app.framework, 'application', 'workspace', '服务', '应用', 'open'],
        run: () => {
          router.push(`/applications/${app.id}`)
        },
      },
      {
        id: `deploy-app-${app.id}`,
        title: `Deploy ${app.name}`,
        description: '为这个服务触发一次新的部署',
        section: 'Services',
        keywords: [app.name, 'deploy', 'release', '发布', '部署'],
        run: async () => {
          const result = await applicationApi.deploy(app.id)
          if (result.approval_required) {
            ElMessage.success('Production 发布审批已提交')
            router.push('/approvals')
            return
          }
          if (result.pipeline_run_name) {
            ElMessage.success(`已启动 ${result.pipeline_run_name}`)
            router.push(`/pipelines/${result.pipeline_run_name}`)
            return
          }
          ElMessage.success('部署已提交')
        },
      },
    ]))

    commands.value = [
      {
        id: 'go-dashboard',
        title: 'Open dashboard',
        description: '查看 AI 首页与推荐动作',
        section: 'Navigate',
        keywords: ['dashboard', 'overview', 'home', '首页', '总览', 'open'],
        shortcut: 'G D',
        run: () => router.push('/dashboard'),
      },
      {
        id: 'go-applications',
        title: 'Open applications',
        description: '查看所有软件服务工作区',
        section: 'Navigate',
        keywords: ['applications', 'services', 'catalog', '应用', '服务', 'open'],
        shortcut: 'G A',
        run: () => router.push('/applications'),
      },
      {
        id: 'go-pipelines',
        title: 'Open pipelines',
        description: '查看失败与进行中的执行',
        section: 'Navigate',
        keywords: ['pipelines', 'runs', 'builds', 'pipeline', '流水线', '执行', 'open'],
        shortcut: 'G P',
        run: () => router.push('/pipelines'),
      },
      {
        id: 'go-releases',
        title: 'Open releases',
        description: '查看交付活动流与回滚入口',
        section: 'Navigate',
        keywords: ['releases', 'deployments', 'rollback', '发布', '回滚', 'open'],
        shortcut: 'G R',
        run: () => router.push('/releases'),
      },
      {
        id: 'go-approvals',
        title: 'Open approvals',
        description: '处理待审批的生产变更',
        section: 'Navigate',
        keywords: ['approvals', 'governance', 'production', '审批', '治理', 'open'],
        shortcut: 'G O',
        run: () => router.push('/approvals'),
      },
      {
        id: 'go-registries',
        title: 'Open registries',
        description: '管理平台级镜像仓库连接',
        section: 'Navigate',
        keywords: ['registries', 'registry', 'container', '镜像仓库', 'open'],
        run: () => router.push('/settings/registries'),
      },
      {
        id: 'new-application',
        title: 'Create application workspace',
        description: '从代码仓库创建一个新的服务工作区',
        section: 'Create',
        keywords: ['create', 'new', 'application', 'workspace', '创建应用'],
        shortcut: 'N A',
        run: () => router.push('/applications/new'),
      },
      {
        id: 'review-failures',
        title: 'Show production incidents',
        description: '查看失败执行与近期异常',
        section: 'Operate',
        keywords: ['incident', 'failures', 'errors', '故障', '异常', 'production'],
        run: () => router.push('/pipelines'),
      },
      {
        id: 'rollback-service',
        title: 'Rollback order service',
        description: '跳转到发布中心执行回滚',
        section: 'Operate',
        keywords: ['rollback', 'order service', '回滚'],
        run: () => router.push('/releases'),
      },
      {
        id: 'deploy-payment',
        title: 'Deploy payment service',
        description: '跳转到发布中心继续部署流程',
        section: 'Operate',
        keywords: ['deploy', 'payment service', '发布', '部署'],
        run: () => router.push('/releases'),
      },
      {
        id: 'toggle-theme',
        title: uiStore.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode',
        description: '切换当前工作区主题',
        section: 'Workspace',
        keywords: ['theme', 'dark mode', 'light mode', '主题', '深色', '浅色'],
        shortcut: 'T H',
        run: () => uiStore.toggleTheme(),
      },
      {
        id: 'toggle-sidebar',
        title: uiStore.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar',
        description: '调整工作区导航宽度',
        section: 'Workspace',
        keywords: ['sidebar', 'navigation', 'collapse', 'expand', '侧边栏'],
        run: () => uiStore.toggleSidebar(),
      },
      ...serviceCommands,
    ]
  })

  const recentCommands = computed(() => {
    const ids = new Set(commandStore.recent.map(item => item.id))
    return commandStore.recent
      .map(recent => commands.value.find(command => command.id === recent.id))
      .filter((command): command is CommandItem => Boolean(command))
      .filter(command => ids.has(command.id))
  })

  const recommendedCommands = computed(() => {
    const failedCount = applicationStore.items.filter(app => app.latest_execution?.status === 'Failed').length
    const recommendedIds = failedCount
      ? ['review-failures', 'go-pipelines', 'go-releases', 'go-approvals']
      : ['new-application', 'go-dashboard', 'go-applications', 'toggle-theme']

    return recommendedIds
      .map(id => commands.value.find(command => command.id === id))
      .filter((command): command is CommandItem => Boolean(command))
  })

  async function ensureApplicationCommands() {
    if (!applicationStore.items.length && !applicationStore.loading) {
      await applicationStore.load()
    }
  }

  async function executeCommand(command: CommandItem) {
    commandStore.remember({ id: command.id, title: command.title, section: command.section })
    await command.run()
    commandStore.close()
  }

  function findCommandByRoute(route?: string) {
    if (!route) return undefined
    const routeMap: Record<string, string> = {
      '/dashboard': 'go-dashboard',
      '/applications': 'go-applications',
      '/applications/new': 'new-application',
      '/pipelines': 'go-pipelines',
      '/releases': 'go-releases',
      '/approvals': 'go-approvals',
      '/settings/registries': 'go-registries',
    }
    const commandId = routeMap[route]
    return commandId ? commands.value.find(command => command.id === commandId) : undefined
  }

  async function tryResolveByApi(rawQuery: string) {
    const resolved = await aiApi.resolveIntent(rawQuery)
    const target = resolved.target as { application_id?: number } | undefined
    const route = resolved.recommended_action?.route

    if (resolved.intent === 'deploy_application' && target?.application_id) {
      const deployCommand = commands.value.find(command => command.id === `deploy-app-${target.application_id}`)
      if (deployCommand) {
        await executeCommand(deployCommand)
        return true
      }
    }

    if (resolved.intent === 'open_application' && target?.application_id) {
      const openCommand = commands.value.find(command => command.id === `open-app-${target.application_id}`)
      if (openCommand) {
        await executeCommand(openCommand)
        return true
      }
    }

    const routeCommand = findCommandByRoute(route)
    if (routeCommand) {
      await executeCommand(routeCommand)
      return true
    }

    return false
  }

  async function runIntent(rawQuery: string) {
    const query = rawQuery.trim().toLowerCase()
    if (!query) {
      commandStore.open()
      return
    }

    await ensureApplicationCommands()

    try {
      const resolved = await tryResolveByApi(rawQuery)
      if (resolved) return
    } catch {
      // silently fallback to local rules
    }

    const exactService = applicationStore.items.find(app => query.includes(app.name.toLowerCase()))

    if (exactService && (query.includes('deploy') || query.includes('发布') || query.includes('部署'))) {
      const deployCommand = commands.value.find(command => command.id === `deploy-app-${exactService.id}`)
      if (deployCommand) {
        await executeCommand(deployCommand)
        return
      }
    }

    if (exactService && (query.includes('open') || query.includes('查看') || query.includes('打开'))) {
      const openCommand = commands.value.find(command => command.id === `open-app-${exactService.id}`)
      if (openCommand) {
        await executeCommand(openCommand)
        return
      }
    }

    const match = commands.value.find(command => {
      const haystack = [command.title, command.description, ...command.keywords].join(' ').toLowerCase()
      return haystack.includes(query) || query.split(/\s+/).every(word => haystack.includes(word))
    })

    if (match) {
      await executeCommand(match)
      return
    }

    commandStore.open(rawQuery)
  }

  return {
    quickPrompts,
    commands,
    recentCommands,
    recommendedCommands,
    ensureApplicationCommands,
    executeCommand,
    runIntent,
    openPalette: commandStore.open,
  }
}
