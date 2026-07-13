# Project Governance Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Project governance metadata for GitHub and Aliyun boundaries and make the Project Center form match real backend fields.

**Architecture:** Extend the existing `Project` model and service instead of adding a new aggregate. Keep members, Kubernetes clusters, registries, and applications as Project child resources. Add an Alembic migration, route/service tests, frontend types/API payloads, and a richer Project Center form.

**Tech Stack:** Flask, SQLAlchemy, Alembic, unittest, Vue 3, TypeScript, Element Plus, Vite.

## Global Constraints

- Project 本体只保存治理与外部资源绑定元信息。
- 成员、Kubernetes 集群、Registry 和 Application 继续作为 Project 子资源。
- Aliyun 是主要云目标；不要使用含混的通用 `cloud_provider` 字段作为本次核心模型。
- 不保存 AccessKey、Secret、GitHub Token、kubeconfig 或应用 Secret。
- 后端 API 保持统一响应结构：`success`、`message`、`data`、`timestamp`、`trace_id`。
- Schema 演进必须包含 Alembic migration。
- 完成前运行 `./scripts/verify.sh`。

---

### Task 1: Backend Project Metadata Contract

**Files:**
- Modify: `backend/tests/test_project_routes.py`
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/services/project_service.py`
- Create: `backend/migrations/versions/c3d4e5f6a7b8_add_project_governance_metadata.py`

**Interfaces:**
- Produces: `Project.to_dict(include_stats=False)` returns `status`, `business_owner`, `billing_owner`, `github_group`, `github_default_visibility`, `aliyun_account_id`, `aliyun_resource_group_id`, `aliyun_region`, `aliyun_vpc_id`, `aliyun_binding_status`.
- Produces: `ProjectService.create(payload)` and `ProjectService.update(project, payload)` persist and validate those fields.

- [ ] Add failing route tests for create/update/invalid metadata/sensitive payload rejection.
- [ ] Run the targeted backend test and confirm failures are about missing fields or validation.
- [ ] Add Project model columns and serialization.
- [ ] Add service validation helpers for status, GitHub visibility, Aliyun binding status, field lengths, and sensitive keys.
- [ ] Add Alembic migration with upgrade and downgrade.
- [ ] Run the targeted backend tests and confirm they pass.

### Task 2: Migration Verification

**Files:**
- Create: `backend/tests/test_project_governance_migration.py`

**Interfaces:**
- Consumes: Alembic revision `c3d4e5f6a7b8`.

- [ ] Add a migration test that stamps `a7c8d9e0f1a2`, upgrades to `c3d4e5f6a7b8`, verifies new Project columns, then downgrades to `a7c8d9e0f1a2`.
- [ ] Run the migration test and confirm it passes.

### Task 3: Frontend Project Center Form

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/project.ts`
- Modify: `frontend/src/views/ProjectCenter.vue`

**Interfaces:**
- Consumes: Project metadata fields from backend API.
- Produces: Project create/update payloads containing only real backend-supported fields.

- [ ] Extend the Project TypeScript interface and Project API payload types.
- [ ] Replace Project Center dialog with grouped sections for basic info, people ownership, GitHub boundary, and Aliyun binding.
- [ ] Remove default Kubernetes cluster fields from Project CRUD form.
- [ ] Show GitHub and Aliyun metadata on Project cards.
- [ ] Run frontend build/typecheck through the project verification script.

### Task 4: Product State Documentation

**Files:**
- Modify: `docs/current-state.md`
- Modify: `specs/active/project-governance-foundation.md`

**Interfaces:**
- Produces: current-state documentation that records implemented Project governance metadata without claiming external GitHub/Aliyun initialization.

- [ ] Update current-state after implementation.
- [ ] Add verification evidence to the active spec.
- [ ] Move the spec to `specs/completed/` only after verification passes.
