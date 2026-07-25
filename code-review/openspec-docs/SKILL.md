---
name: openspec-docs
description: OpenSpec 文档审查规则：proposal.md、design.md、tasks.md 审查标准
requires_source: false
source_context: none
---

# OpenSpec 文档审查

## 上下文协议

本 skill **不需要源码**。只审查文档间的一致性（proposal ↔ design ↔ tasks）。

当从 design-review 协调层接收审查任务时，忽略所有 `【共享上下文】` 标记的代码片段。

审查输入仅包含：
- 设计文档内容（proposal.md / design.md / tasks.md / specs/**/*.md）
- 无源码片段

## 何时激活

- 变更涉及 `openspec/changes/{name}/` 目录下的文件
- 新增或修改 OpenSpec 提案、设计或任务文档

## 审查检查清单

### Proposal (proposal.md)

- [ ] 使用中文编写
- [ ] 包含问题陈述 (Why) - 为什么要做这个变更
- [ ] 包含变更内容 (What Changes) - 变更了什么
- [ ] 包含新增/修改的能力 (Capabilities)
- [ ] 包含影响范围 (Impact)
- [ ] 指定所需的角色权限
- [ ] 列出依赖的 API 端点

```markdown
# 提案名称

## 为什么做 (Why)
[问题描述]

## 变更内容 (What Changes)
- [ ] 新增功能 A
- [ ] 修改功能 B

## 能力 (Capabilities)
- 能力 1: 描述
- 能力 2: 描述

## 影响范围 (Impact)
- API 端点: /api/users
- 角色权限: Admin

## 依赖
- API 端点: /api/admin/config
```

### Design (design.md)

- [ ] 使用中文编写
- [ ] 包含架构概述
- [ ] 包含组件结构
- [ ] 包含数据模型变更
- [ ] 包含 API 设计
- [ ] 包含错误处理说明
- [ ] 与 proposal.md 保持一致

```markdown
# 设计文档

## 架构概述
[简要描述]

## 组件结构
- 组件 1: 职责
- 组件 2: 职责

## 数据模型
- 新增/修改的表/结构体

## API 设计
- GET /api/users - 用户列表
- POST /api/users - 创建用户

## 错误处理
[错误码和消息]
```

### Tasks (tasks.md)

- [ ] 使用中文编写
- [ ] 任务分解合理 (单个任务不超过 2 小时)
- [ ] 包含实现任务
- [ ] 包含测试任务
- [ ] 包含文档任务
- [ ] 遵循现有目录结构

```markdown
# 任务列表

## 实现
- [ ] Task 1: 描述
- [ ] Task 2: 描述

## 测试
- [ ] 单元测试

## 文档
- [ ] 更新 API 文档
```

## 最佳实践

1. **中文编写** - 所有文档使用中文
2. **结构完整** - 包含所有必需的章节
3. **一致性** - proposal / design / tasks 内容一致
4. **任务拆分** - 单个任务不超过 2 小时
