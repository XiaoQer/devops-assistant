# Embedded Build Workspace Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the top gap above build history when the shared workspace is embedded in the Application Pipeline tab while preserving the CI/CD sticky offset.

**Architecture:** Expose the sticky top offset as a CSS custom property on the shared workspace. Keep its default at 80px and set the property to 0 only on the Application Pipeline Tab host wrapper.

**Tech Stack:** Vue 3 scoped CSS, Vite, vue-tsc.

## Global Constraints

- Do not change shared workspace data, routing, logs, polling, height, or mobile behavior.
- CI/CD host keeps the 80px default; Application host uses 0.

---

### Task 1: Host-Specific Sticky Offset

**Files:**
- Modify: `frontend/src/components/pipeline/ApplicationBuildWorkspace.vue`
- Modify: `frontend/src/views/ApplicationDetail.vue`
- Modify: `docs/current-state.md`
- Modify then move: `specs/active/embedded-build-workspace-alignment.md` to `specs/completed/embedded-build-workspace-alignment.md`

- [ ] Replace the shared `top: 80px` declaration with `top: var(--build-history-sticky-top, 80px)`.
- [ ] Wrap the Application Tab workspace in a host class and set `--build-history-sticky-top: 0px`.
- [ ] Run frontend tests and production build; inspect compiled CSS for both default and override.
- [ ] Run `./scripts/verify.sh`, record evidence, archive the specification, and commit with `fix: align embedded build workspace columns`.
