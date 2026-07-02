# Aegis Documentation

本目录用于系统化描述 **Aegis AI Native DevOps Platform / Software OS** 的设计、架构、运行方式与工程演进路径。

目标有两个：

1. **给人看**：让研发、架构师、运维、合作方快速理解平台是什么、为什么这样设计、如何运行与如何扩展。
2. **给 AI 看**：让大模型在理解平台上下文时有稳定、结构化、可复用的提示材料。

---

## 文档导航

### 1. 产品与架构总览
- [`01-product-overview.md`](./01-product-overview.md)
- [`02-system-architecture.md`](./02-system-architecture.md)

### 2. 领域与系统设计
- [`03-domain-model.md`](./03-domain-model.md)
- [`04-backend-architecture.md`](./04-backend-architecture.md)
- [`05-frontend-architecture.md`](./05-frontend-architecture.md)

### 3. 运行与接口
- [`06-deployment-operations.md`](./06-deployment-operations.md)
- [`07-api-design.md`](./07-api-design.md)

### 4. AI 与工程治理
- [`08-ai-context-prompt.md`](./08-ai-context-prompt.md)
- [`09-engineering-roadmap.md`](./09-engineering-roadmap.md)

---

## 推荐阅读顺序

### 面向新成员 / 合作方
1. `01-product-overview.md`
2. `02-system-architecture.md`
3. `06-deployment-operations.md`

### 面向后端研发
1. `02-system-architecture.md`
2. `03-domain-model.md`
3. `04-backend-architecture.md`
4. `07-api-design.md`

### 面向前端研发
1. `01-product-overview.md`
2. `05-frontend-architecture.md`
3. `08-ai-context-prompt.md`

### 面向 AI / 智能代理
优先使用：
1. `01-product-overview.md`
2. `02-system-architecture.md`
3. `03-domain-model.md`
4. `08-ai-context-prompt.md`

---

## 文档原则

这些文档遵循以下原则：

- 尽量描述 **真实代码现状**，而不是纯理想化设计。
- 将 **当前实现** 与 **目标形态** 分开表达。
- 用软件工程语言统一描述：分层、边界、职责、数据流、运行流、扩展点。
- 既支持工程协作，也支持 AI 作为上下文进行分析、编码和设计建议。

