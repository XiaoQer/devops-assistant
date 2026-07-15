# Sticky Build History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the desktop build-history card visible and internally scrollable beside long pipeline logs without changing mobile flow.

**Architecture:** Apply page-level sticky positioning to the history component and make the component a viewport-bounded flex column. Let the history list consume remaining card height and scroll internally; reset positioning and height at the existing 760px breakpoint.

**Tech Stack:** Vue 3 scoped CSS, Vite, Vitest, vue-tsc.

## Global Constraints

- Do not change build selection, routing, polling, logs, APIs, or column widths.
- Desktop history remains a separate card and must not stretch to detail height.
- At 760px and below, restore normal document flow and the existing 280px history-list limit.

---

### Task 1: Sticky Viewport-Bounded History

**Files:**
- Modify: `frontend/src/views/ApplicationBuildExplorer.vue`
- Modify: `frontend/src/components/pipeline/ApplicationBuildHistory.vue`

**Interfaces:**
- Consumes: existing `.explorer-layout`, `.build-history`, and `.history-list` layout classes.
- Produces: desktop sticky history card with internal scrolling and a mobile reset.

- [ ] **Step 1: Add page-level sticky positioning**

Set the direct history child of `.explorer-layout` to `position: sticky`, `top: 12px`, and a viewport-bounded `max-height`. Reset `position`, `top`, and height constraints inside the existing 760px media query.

- [ ] **Step 2: Make the history card a flex column**

Set `.build-history` to a flex column with a matching viewport-bounded height. Make the skeleton wrapper and `.history-list` able to shrink, then change the desktop list from `max-height` to `flex: 1; min-height: 0; overflow: auto`.

- [ ] **Step 3: Preserve mobile behavior**

At 760px and below, set the card height to auto and restore `.history-list { flex: none; max-height: 280px; }`.

- [ ] **Step 4: Verify**

Run: `npm --prefix frontend test && npm --prefix frontend run build && ./scripts/verify.sh`

Expected: frontend tests, Vue type checking, production build, and full repository verification pass.

- [ ] **Step 5: Document and commit**

Update `docs/current-state.md`, record exact verification evidence, mark the active spec accepted, move it to `specs/completed/`, and commit with `fix: keep build history visible beside logs`.
