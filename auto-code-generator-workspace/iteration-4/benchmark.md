# Skill Benchmark: auto-code-generator

**Model**: deepseek-v4-flash（provider 自动升级 deepseek-v4-pro）  
**Date**: 2026-08-15T02:59:55Z  
**Evals**: 1–12（每种配置各 1 次）

## Summary

| Metric | With Skill v4.3 | Old Skill v4.2 | Delta（v4.3 - v4.2） |
|---|---:|---:|---:|
| Eval 平均通过率 | 100% ± 0% | 85% ± 31% | +15 个百分点 |
| 断言加权通过率 | 55/55（100%） | 48/55（87%） | +13 个百分点 |
| Time | 69.4s ± 11.4s | 68.2s ± 22.7s | +1.2s |
| Tokens | 21,901 ± 2,262 | 17,934 ± 2,188 | +3,967 |

旧行为回归 eval 1–8 的新旧版本均通过；新版增益集中在 eval 9–12 的维护视图语义边界、实施偏差三方验证、显式 Luna 会话授权和 provider 降级合同。eval 9 的前三项对旧版提示较强，后续应加入未命名状态或冲突输入提高区分度。
