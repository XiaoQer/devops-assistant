# Pod Detail Container-first Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Pod 详情页改造成第三版 Container-first 运维工作区，降低首屏噪音并保留现有日志、YAML、终端和删除能力。

**Architecture:** 保留 `PodDetail.vue` 的数据加载、路由和安全操作编排；将 `PodOverview.vue` 重组为左侧 Container/Conditions/Events 主区与右侧 Pod 信息栏。Container 行通过事件把选中的容器传回宿主，日志和终端仍复用现有 API/Drawer。

**Tech Stack:** Vue 3、TypeScript、Element Plus、Vitest、Vite。

## Global Constraints

- 不新增 CPU、Memory 等当前 API 不提供的指标。
- 不改变后端 API、终端票据协议、审计内容或权限模型。
- 删除 Pod 继续使用现有二次确认、生产环境强化文案和审计接口。
- 不修改工作区中 Portal 相关用户已有变更。
- Runtime 使用浅色表头、紧凑控件和现有设计 token，不引入深色表头或卡片套卡片。

### Task 1: Lock the Container-first view contract with failing tests

**Files:**
- Modify: `frontend/src/components/runtime/PodOverview.layout.test.ts` (create if absent)
- Modify: `frontend/src/views/PodDetail.layout.test.ts` (create if absent)

**Interfaces:**
- Tests inspect the rendered source contract and require `container-first`, `pod-facts`, `container-action`, and `data-runtime-action="more"` markers.

- [ ] **Step 1: Write the failing tests**

```ts
it('exposes a container-first overview with a facts rail', () => {
  expect(source).toContain('class="container-first-layout"')
  expect(source).toContain('class="pod-facts"')
  expect(source).toContain('data-runtime-action="container-logs"')
  expect(source).toContain('data-runtime-action="container-terminal"')
})

it('keeps destructive Pod actions behind the overflow menu', () => {
  expect(source).toContain('data-runtime-action="more"')
  expect(source).not.toContain('data-runtime-action="delete-pod"')
})
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `cd frontend && npm test -- --run src/components/runtime/PodOverview.layout.test.ts src/views/PodDetail.layout.test.ts`

Expected: FAIL because the current overview has no Container-first layout markers and Delete Pod is a header button.

### Task 2: Rebuild PodOverview around Container-first hierarchy

**Files:**
- Modify: `frontend/src/components/runtime/PodOverview.vue`
- Test: `frontend/src/components/runtime/PodOverview.layout.test.ts`

**Interfaces:**
- Consumes: existing `RuntimePodDetail` prop and `formatRuntimeTime` helper.
- Produces: `container-logs` and `container-terminal` events carrying the selected container name; no HTTP calls.

- [ ] **Step 1: Implement the minimal structure**

Use a `.container-first-layout` grid with `.pod-main` and `.pod-facts`. Render Container rows first, each with image, state, ready, restart count, start time, and compact log/terminal buttons. Render Conditions and Events below using light tables and explicit empty states. Render Namespace, Node, Pod IP, Host IP, QoS, creation/start times and restarts in `.pod-facts`.

- [ ] **Step 2: Add scoped responsive styles**

Use a 1fr/300px desktop grid, 32px controls, 8/12/16/24 spacing, pale headers, row dividers, and a single-column layout below 960px. Do not use dark backgrounds or nested surface cards.

- [ ] **Step 3: Run the focused component tests**

Run: `cd frontend && npm test -- --run src/components/runtime/PodOverview.layout.test.ts`

Expected: PASS.

### Task 3: Make PodDetail header compact and wire Container actions

**Files:**
- Modify: `frontend/src/views/PodDetail.vue`
- Test: `frontend/src/views/PodDetail.layout.test.ts`

**Interfaces:**
- Consumes: `PodOverview` container events and existing `loadLogs`, `enterTerminal` functions.
- Produces: selected container state shared by Logs and Terminal; refresh as the only direct header action, with delete in the Element Plus dropdown menu.

- [ ] **Step 1: Add failing interaction/source assertions**

Assert the header uses a compact title class, a status marker near the title, a more menu, and that `PodOverview` listens for `container-logs` and `container-terminal`.

- [ ] **Step 2: Implement the header and event handlers**

Reduce the title to a 24px maximum, move Application/Environment into metadata, keep refresh and terminal only as compact controls, and put Delete Pod under a `MoreFilled` dropdown command. Add handlers that set `selectedContainer` and switch to Logs or open the existing terminal confirmation flow.

- [ ] **Step 3: Run focused view tests**

Run: `cd frontend && npm test -- --run src/views/PodDetail.layout.test.ts src/components/runtime/pod-detail-view-model.test.ts`

Expected: PASS.

### Task 4: Verify the Runtime surface

**Files:**
- Modify: `specs/active/project-runtime-workspace-v2.md` (mark the visual acceptance item complete only after evidence)

- [ ] **Step 1: Run the full Runtime test slice**

Run: `cd frontend && npm test -- --run src/components/runtime src/views/PodDetail.layout.test.ts src/composables/useDeploymentPods.test.ts src/composables/useProjectRuntime.test.ts src/api/runtime.test.ts`

Expected: all selected tests pass.

- [ ] **Step 2: Run type check and production build**

Run: `cd frontend && npm run build`

Expected: vue-tsc and Vite exit 0.

- [ ] **Step 3: Run repository verification**

Run: `./scripts/verify.sh`

Expected: repository checks pass, or any unrelated pre-existing Portal layout failure is reported without changing Portal files.

- [ ] **Step 4: Check diff hygiene**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only intended Runtime/spec changes are included in the implementation commit.
