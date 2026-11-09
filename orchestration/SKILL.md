---
name: orchestration
description: 编排域统一入口。用于跨领域、跨阶段或包含提交授权边界的工作流，根据任务阶段路由到自动代码实施编排（含 PR 前本地验证）或提交前审查选择闸门。提交请求不得自动开启代码审查；未指定时只询问一次“1. 快速 / 2. 不做 / 3. 全量”。
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
5. 提交请求路由到 `code-review-before-commit` 仅用于选择闸门；不得在用户选择前启动 `code-review`。
6. 同一请求同时涉及多种编排能力时按阶段选择：还需实施或要从需求推进到验证/PR 时走
   `auto-code-generator`；实施已完成、只差提交时走 `code-review-before-commit`。两者都要求时，
   先由 `auto-code-generator` 完成交付前验证，再按其流程调用提交闸门。
