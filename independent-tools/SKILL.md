---
name: independent-tools
description: 独立工具域统一入口。用于识别并路由边界清晰的专业工具任务，包括媒体转换、Git 分支、滴答任务、浏览器端到端测试、U 盘 Git 同步和 uv 环境管理。只选择一个主工具，不承担跨域编排。
---

# 独立工具域

## 职责

本 Skill 只负责将明确的专业工具意图路由到叶子 Skill。权威映射位于
`references/tool-mapping.yaml`。

## 路由规则

1. 用户显式指定子 Skill 时直接执行。
2. 每次只选择一个主工具；跨域生命周期交给 `orchestration`。
3. 从映射取得规范 `skill_name`，再通过根注册表解析 `<skill>/SKILL.md`；专业约束以叶子 Skill 为准。
4. 未匹配的工具需求返回缺口，不在本域临时扩展无权威定义的流程。
