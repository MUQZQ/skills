---
name: meta-skills
description: 元技能域统一入口。用于创建、修改、评估 Skill，或同步 AGENTS.md 与多客户端 Skill Junction。根据权威映射只选择一个主 Skill；用户显式指定叶子 Skill 时直接服从。
---

# 元技能域

## 职责

本 Skill 只负责识别元技能意图并路由，不复制叶子 Skill 的执行流程。权威映射位于
`references/meta-skill-mapping.yaml`。

## 路由规则

1. 用户显式指定子 Skill 时直接执行。
2. 每次只选择一个主 Skill；混合请求按用户最终交付物选择。
3. 从映射取得规范 `skill_name`，再通过根注册表解析 `<skill>/SKILL.md` 并严格执行其步骤。
4. 无法匹配时说明缺口，不在元技能域内发明新的专业工具流程。
