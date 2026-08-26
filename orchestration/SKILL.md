---
name: orchestration
description: 编排域统一入口。用于跨领域、跨阶段或包含提交授权边界的工作流，根据任务阶段路由到自动代码实施编排或提交前审查编排。只负责选择主编排器，不替代领域 Skill 和项目权威生命周期。
---

# 编排域

## 职责

本 Skill 管理跨域工作流入口，权威映射位于
`references/orchestration-mapping.yaml`。领域判断与专业执行仍由对应领域 Skill 负责。

## 路由规则

1. 用户显式指定编排器时直接执行。
2. 每次只选择一个主编排器，禁止两个编排器同时拥有 Git 权限。
3. 项目已有 OpenSpec、QEDA 或其他权威生命周期时，编排器必须服从其实时状态。
4. 从映射取得规范 `skill_name`，再通过根注册表解析 `<skill>/SKILL.md`；Git、PR 和部署动作仍需遵守用户授权边界。
