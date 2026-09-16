---
name: literary-creation
description: 文学创作领域统一入口。用户要求小说、网文、短篇故事或微短剧的选题、策划、写作与创作审读时使用；先通过领域映射选择一个主 Skill，并尊重具体项目自己的 canon、连续性和写作生命周期。
---

# 文学创作域

## 职责

识别文学创作意图并路由到领域 Skill，不在入口层复制具体创作流程。权威映射位于
`references/literary-creation-mapping.yaml`。

## 路由规则

1. 用户显式指定子 Skill 时直接执行；
2. 小说、网文、短篇故事或微短剧的原创选题使用 `novel-topic-discovery`；
3. 已有项目的正文写作、连续性和状态回写服从项目本地 Skill，不由本领域入口夺权；
4. 选题完成不自动授权立项或写正文。
