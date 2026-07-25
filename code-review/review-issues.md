# Code Review - DayT 策略胜率优化

## Round 1 - 2026-07-26

### Summary
- **Files:** 5 modified (indicators.py, dayt_strategy.py, prompts.py, market_filter.py, trade_stats.py) + 2 test files
- **Key Changes:** 市场过滤, 指标注入, 多TF确认, 限价单优化, 胜负统计
- **Issues Found:** 20 total (5 P0, 8 P1, 7 P2)

---

### P0 - 必须修复

| # | 问题描述 | 文件 | 位置 | 建议修复 | 状态 |
|---|----------|------|------|----------|------|
| 1 | on_bar裸Exception吞异常 | dayt_strategy.py | L276 | 改用log.exception保留traceback | ✅ |
| 2 | DayTStrategyConfig可变默认值 | dayt_strategy.py | L107-108 | 使用field(default_factory=...) | ✅ |
| 3 | _compute_adx同tick重复调用 | market_filter.py | L135+157 | 在should_trade中缓存ADX结果 | ✅ |
| 4 | 提示词注入风险 | prompts.py | L355 | 对新闻标题做长度限制和字符过滤 | ✅ |
| 5 | 每日MA全量重算性能 | dayt_strategy.py | L1082-1099 | 改为增量更新 | ✅ |

### P1 - 应该修复

| # | 问题描述 | 文件 | 位置 | 建议修复 | 状态 |
|---|----------|------|------|----------|------|
| 6 | InstrumentId重复创建7次 | dayt_strategy.py | 多处 | 缓存为self._instrument_id | ✅ |
| 7 | _update_daily_mas全量喂入 | dayt_strategy.py | L1089 | 使用计数器增量喂入 | ✅ |
| 8 | MA键名映射混乱(ma20→ma5) | dayt_strategy.py | L952-956 | 修正键名对应关系 | ✅ |
| 9 | trade_stats参数过多(9个) | trade_stats.py | L73 | 使用dataclass封装 | 🔴 推迟 |
| 10 | trade_stats类型注解缺失 | trade_stats.py | L137 | Callable类型注解 | 🔴 推迟 |
| 11 | 北京时间重复计算 | dayt_strategy.py | L701+L1006 | 提取_beijing_hour工具函数 | ✅ |
| 12 | 魔法数字未提取常量 | dayt_strategy.py | 多处 | 提取为类级常量 | 🔴 推迟 |
| 13 | prompts RSI区间不一致 | prompts.py | L253 | 补充中位描述 | 🔴 推迟 |

### P2 - 建议修改

| # | 问题描述 | 文件 | 位置 | 状态 |
|---|----------|------|------|------|
| 14 | God Class 1516行 | dayt_strategy.py | - | 🔲 后续重构 |
| 15 | trade_history死代码 | prompts.py | L417-419 | 🔲 后续清理 |
| 16 | _llm_interactions_buffer临时字段 | dayt_strategy.py | L176 | 🔲 后续重构 |
| 17 | 日志格式不统一 | dayt_strategy.py | 多处 | 🔲 后续修复 |
| 18 | _get_last_bar防御性不足 | dayt_strategy.py | L705-718 | 🔲 后续修复 |
| 19 | ADX冷启动精度 | market_filter.py | L193-196 | 🔲 后续优化 |
| 20 | prompts胜率格式化无类型检查 | prompts.py | L325 | 🔲 后续修复 |

### 审查结论

P0 5/5 已修复，P1 5/8 已修复，P2 0/7。

**保留问题**: P1 参数过多、类型注解、魔法数字、RSI描述 推迟到后续重构。
