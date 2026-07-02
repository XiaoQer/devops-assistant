# Aegis 项目记忆

本目录是人类和编码 Agent 共用的持久项目记忆。

## 阅读顺序

1. [`product.md`](./product.md)：产品目标和边界
2. [`architecture.md`](./architecture.md)：当前系统结构
3. [`domain-model.md`](./domain-model.md)：业务对象与不变量
4. [`current-state.md`](./current-state.md)：经过验证的能力状态和已知缺口
5. [`decisions/`](./decisions/)：长期架构决策及原因；新决策从
   [`decisions/template.md`](./decisions/template.md) 创建

功能意图和验收条件存放在 [`../specs/`](../specs/)，不混入架构文档。

## 事实规则

- 现状描述必须能够追溯到代码、测试或已记录的人工验证。
- 计划中的工作必须明确标注，不得列为已实现能力。
- 行为变化时先更新对应规格，并在同一变更中更新相关文档。
- 聊天记录可以提供背景，但不是权威项目记忆。
