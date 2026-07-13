# Project Kubernetes Visual Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the oversized single-column Kubernetes cluster presentation with responsive two-column resource cards and visually unify onboarding and form dialogs without changing behavior.

**Architecture:** Keep all changes local to `ProjectKubernetesSettings.vue`. Recompose existing safe data and handlers into a clearer template, use Element Plus Dropdown for secondary actions, and add scoped CSS for responsive cards and form sections.

**Tech Stack:** Vue 3, TypeScript, Element Plus, scoped CSS, Vite

## Global Constraints

- Do not change API, data model, route, validation, persistence, or connectivity behavior.
- Preserve every existing cluster field and action.
- Keep delete behind the existing confirmation dialog.
- Use a two-column grid above approximately 1100px available content width and one column below it.
- Keep Aliyun initialization unavailable and visibly marked as future functionality.
- Keep kubeconfig write-only in the UI lifecycle and render its textarea with a monospace style.

---

### Task 1: Recompose the page and cluster resource cards

**Files:**
- Modify: `frontend/src/views/ProjectKubernetesSettings.vue`

**Interfaces:**
- Consumes: existing `clusters`, `testSavedConnection`, `openEditDialog`, `setDefaultCluster`, and `removeCluster`.
- Produces: responsive `cluster-grid`, `cluster-card`, `connection-panel`, and `cluster-footer` template structure.

- [x] **Step 1: Replace the section header and card markup**

Add a compact section count using `{{ clusters.length }} clusters`. Structure each card as identity,
connection panel, badges, optional description, and footer. Keep test/edit visible and add:

```vue
<el-dropdown trigger="click">
  <el-button class="more-button" aria-label="更多集群操作">•••</el-button>
  <template #dropdown>
    <el-dropdown-menu>
      <el-dropdown-item v-if="!cluster.is_default" @click="setDefaultCluster(cluster.id)">
        设为默认
      </el-dropdown-item>
      <el-dropdown-item divided @click="removeCluster(cluster)">删除集群</el-dropdown-item>
    </el-dropdown-menu>
  </template>
</el-dropdown>
```

- [x] **Step 2: Add scoped responsive card styling**

Use `grid-template-columns: repeat(2, minmax(0, 1fr))`, a 16px gap, white resource cards, contained
connection panels, 26px compact badges, and a bordered footer. At `max-width: 1100px`, switch to one
column; at `max-width: 720px`, stack footer content without hiding actions.

- [x] **Step 3: Run the frontend production build**

Run: `npm --prefix frontend run build`

Expected: TypeScript and Vite exit 0.

### Task 2: Unify onboarding choices and form sections

**Files:**
- Modify: `frontend/src/views/ProjectKubernetesSettings.vue`

**Interfaces:**
- Consumes: existing dialog state, form bindings, context parsing, transient testing, saving, and sensitive cleanup.
- Produces: `form-block`, `form-block-header`, `kubeconfig-field`, and refined `choice-card` presentation.

- [x] **Step 1: Divide the form into three visual blocks**

Move existing fields without changing bindings:

- Basic information: name, environment label, description.
- Connection configuration: kubeconfig, kube context, Namespace Prefix, and test alert.
- Governance settings: default and active switches.

Apply `class="kubeconfig-field"` to the kubeconfig form item and keep the same `@input`, required state,
and placeholder.

- [x] **Step 2: Refine choice and form styles**

Make the available choice card use a blue-tinted icon/background and hover elevation. Keep the Aliyun
card disabled with neutral gray treatment. Give form blocks distinct borders and headers; apply a
monospace font, tinted background, and 1.6 line-height to `.kubeconfig-field :deep(.el-textarea__inner)`.

- [x] **Step 3: Run frontend and full verification**

Run: `npm --prefix frontend run build`

Expected: TypeScript and Vite exit 0.

Run: `./scripts/verify.sh`

Expected: all backend tests and the frontend production build pass.

### Task 3: Record acceptance

**Files:**
- Modify: `docs/current-state.md`
- Move: `specs/active/project-kubernetes-visual-refresh.md` to `specs/completed/project-kubernetes-visual-refresh.md`

**Interfaces:**
- Consumes: verified visual implementation.
- Produces: completed specification and current-state evidence.

- [x] **Step 1: Update documentation**

Record the responsive two-column cards, action hierarchy, and three-section form in current state. Check
every acceptance criterion, add actual build/test evidence, set status to `已验收`, and archive the spec.

- [x] **Step 2: Run final verification after documentation changes**

Run: `./scripts/verify.sh`

Expected: exit 0.

- [x] **Step 3: Commit the completed change**

```bash
git add frontend/src/views/ProjectKubernetesSettings.vue docs/current-state.md docs/superpowers/plans/2026-07-13-project-kubernetes-visual-refresh.md specs/active/project-kubernetes-visual-refresh.md specs/completed/project-kubernetes-visual-refresh.md
git commit -m "feat: refine kubernetes resource workspace"
```
