---
name: project-param-compare
description: ParamCompare 项目代码审查规则：对比引擎、容差配置、单位比较、批量操作、指标模型
origin: param-compare
---

# ParamCompare 项目代码审查

## 触发条件

变更涉及以下路径时自动触发：

- `src/param_compare/`
- `category-level.yaml`
- `tests/param_compare/`
- `sandbox/`

## 项目架构

- **对比引擎**: `core.py` — flatten() 展平 → match_val() 叶值比较 → compare() 对比 → batch_compare() 批量
- **类别管理**: `categories.py` — 从 category-level.yaml 加载 P0/P1/P2 优先级 + tolerance/unit 配置
- **数据存储**: `store.py` — YAML 读写 + manifest 管理 + 配置持久化
- **CLI 入口**: `__main__.py` — check/batch/verify/init/edit 子命令
- **Web 编辑器**: `app/` (NiceGUI) — 多视图切换编辑器
  - `main.py` — 主入口 + 视图切换栏 + main_panel_view() 分发
  - `enums.py` — ViewMode 枚举（EMPTY/SINGLE_FILE/DIFF/TABLE），独立模块避免循环导入
  - `diff_panel.py` — Monaco 并排对比（ViewMode.DIFF）
  - `table_panel.py` — AG Grid 表格对比（ViewMode.TABLE）
  - `tree_panel.py` — ui.tree 单文件树形视图（ViewMode.SINGLE_FILE）
  - `sidebar.py` — 文件选择 + 指标仪表盘
- **服务层**: `app/service.py` — `run_compare()` 统一比较入口 + `serialize_for_monaco()` + `get_visible_diffs()` + `build_table_rows()`
- **树操作**: `app/actions.py` — `parse_path/set_by_path/get_by_path/accept_diff/apply_gt_values`
- **指标**: `app/metrics.py` — `compute_metrics/gauge_style/PRIORITY_CONFIG`

## 审查检查清单

### 1. 容差配置

- [ ] category-level.yaml 中 `value_with_unit` / `percentage` / `resistance` 类型类别应配置 `tolerance` 和 `unit`
- [ ] `tolerance` 为 float 类型，表示相对容差（如 0.01 = 1%）
- [ ] `unit` 为 string 类型，表示期望物理单位（如 "V", "A", "Ω"）
- [ ] 未配置 tolerance/unit 的类别回退到默认值，不破坏兼容性

### 2. 单位感知比较

- [ ] `match_val()` 接受 `unit` 参数进行单位归一化比较
- [ ] 新增单位族时添加到 `_UNIT_FAMILIES`，格式 `{base: 1, derived: factor}`
- [ ] `_normalize_unit()` 在单位族不匹配时返回 None，调用方应回退到纯数值比较
- [ ] `_NEAR_ZERO_EPS = 1e-6`（电子工程场景），不可改为 `1e-9`

### 3. 对比结果结构

- [ ] `compare()` 返回值必须包含：`match_rate`, `coverage`, `precision`, `f1_score`, `matched`, `mismatched`, `ai_only`, `gt_only`, `ignored`, `mismatched_details`, `ignored_details`
- [ ] `mismatched_details` 每条记录必须包含：`path`, `ai_val`, `gt_val`, `tolerance`, `magnitude`
- [ ] `precision = matched / (matched + ai_only)`，`f1_score = 2*P*R/(P+R)`
- [ ] 新增字段不得破坏向后兼容性（调用方使用 `.get()` 读取）

### 4. 差异操作

- [ ] 批量采用 GT 值使用 `_apply_gt_values()` 而非内联重复代码
- [ ] `compare()` 调用时传入 `ignored_paths` 以排除被忽略的差异
- [ ] GT 文件变化时必须清空 `_ignored_paths`
- [ ] 被忽略的差异计入 `ignored` 和 `ignored_details`，不计入 `mismatched`

### 5. 差异幅度显示

- [ ] 数值差异使用 `_diff_magnitude()` 计算百分比偏差，公式 `(AI-GT)/GT × 100%`
- [ ] 非数值差异 _diff_magnitude() 返回 None
- [ ] 差异卡片显示格式：`AI: {val} → GT: {val} (+10.0%) (容差 5%)`

### 6. CLI 输出格式

- [ ] 单文件对比需输出 match_rate / coverage / precision / f1 四项指标
- [ ] 批量对比表格需包含 match / cover / prec / f1 四列
- [ ] 使用 argparse 子命令体系（check/batch/verify/init/edit）
- [ ] 差异输出按优先级分组（P0 / P1 / P2 / unclassified）

### 7. NiceGUI 编辑器约定

- [ ] 服务层统一入口 — UI 组件调用 `service.run_compare(state)` 进行重比较，禁止在多处重复 `compare()` + `state.compare_result =` 模式
- [ ] Monaco 数据序列化使用 `service.serialize_for_monaco()`，禁止在多处重复 `yaml.dump()` + `json.dumps()`
- [ ] 差异筛选使用 `service.get_visible_diffs(state)`，禁止在多处重复筛选逻辑
- [ ] 表格行数据使用 `service.build_table_rows(state)`，禁止在多处重复 flatten + 状态判断
- [ ] 核心公共常量 (`ID_KEYS`, `find_id`) 从 `param_compare` 顶层导入，禁止重复定义
- [ ] UI 不直接调用 `core` 模块 — 需要调用 core 工具函数时，在 `service.py` 增加薄封装（如 `path_in_gt()`），UI 通过 service 层间接调用；`actions.py` 作为数据处理层可导入 core
- [ ] EditorState 通过模块级单例 `STATE` 管理
- [ ] 所有 UI 色彩值统一定义在 `app/metrics.py` 为 `GAUGE_*` / `COLOR_*` 公共常量，其他 UI 模块导入使用，禁止硬编码或重复定义
- [ ] `render_sidebar` 应为纯组装入口（< 50 行），具体区域 UI 提取为 `_render_*_section()` 独立函数，每函数返回其创建的控件引用供上层回调绑定

### 7a. ViewMode 状态机

- [ ] ViewMode 枚举定义在 `app/enums.py`，供 `main.py` / `sidebar.py` 共同导入，**禁止存在循环导入**
- [ ] `_reload_compare()` 加载文件后自动推断 `state.view_mode`（双文件 → DIFF，单文件 → SINGLE_FILE，空 → EMPTY）
- [ ] 非 DIFF 模式下必须清空 `state.compare_result`，避免指标面板展示陈旧数据
- [ ] 单文件加载失败时必须通过 `ui.notify` 通知用户（禁止静默忽略）
- [ ] `main_panel_view()` 按 ViewMode 分发到对应 render 函数（`render_tree_view` / `render_diff_panel` / `render_table_view`）

### 7b. 视图面板

- [ ] **树形视图** — `tree_panel.py` 的 `_dict_to_tree_nodes()` 节点 ID 必须全局唯一，使用 `/` 分隔父路径
- [ ] 树形视图底部显示键数/字段数统计（通过 `_count_nodes()` 获取）
- [ ] **表格视图** — `table_panel.py` 的 AG Grid 使用社区版（`modules` 默认），行数据由 `service.build_table_rows()` 提供
- [ ] 表格每行包含 `path`, `ai_val`, `gt_val`, `status`, `magnitude`, `tolerance`, `priority` 七列
- [ ] 操作栏提供「全部采用」「全部忽略」「导出CSV」按钮
- [ ] 行内编辑通过 `cellValueChanged` 事件 → `set_by_path()` 更新 AI 数据 → `run_compare()` 重算
- [ ] **并排对比** — `diff_panel.py` 的 `render_diff_panel()` 监听了错误处理，不直接修改（保留原有逻辑）

### 8. 测试约定

- [ ] 新增核心逻辑必须有对应单元测试
- [ ] 测试数据使用 `tests/fixtures/` 目录，禁止外部路径硬编码
- [ ] E2E 测试使用 `sandbox/` 目录的真实数据
- [ ] `conftest.py` 提供共享 fixture（如 `fixture_dir`, `loaded_tree`）
- [ ] E2E 测试中引用的 UI 文案（placeholder、标签文本、按钮文本）应与生产代码同步变更，UI 文本修改时必须更新对应 E2E 断言

## 最佳实践

1. **容差粒度** — P0 参数 ≤1% 容差，P1 ≤5%，P2 ≤10%
2. **单位配置** — 电压用 V，电流用 A，频率用 Hz，不跨单位族混合
3. **指标完备** — 每个对比输出必须有 match_rate + coverage + precision + f1 四项
4. **批量操作** — "全部采用"前应提示确认，避免误操作
5. **服务层单一入口** — 所有"重新比较+更新状态"逻辑必须通过 `service.run_compare(state)` 执行
6. **UI 不直接调 core** — diff_panel/sidebar 通过 service 层调用 core.compare，不直接导入核心比较函数；需要 core 工具函数时在 service.py 增加薄封装
7. **重复零容忍** — 公共常量（ID_KEYS）、工具函数（find_id）、序列化逻辑（serialize_for_monaco）、色彩常量（GAUGE_*/COLOR_*）全项目仅定义一次
8. **区域函数拆分** — render_sidebar 等大型 UI 函数按功能区域拆为独立的 `_render_*_section()` 函数
9. **枚举独立模块** — 被多个模块引用的枚举/常量提取到独立模块（如 `app/enums.py`），消除循环导入
10. **视图状态清理** — 切换视图模式前确保上一模式的临时状态已清空（如 compare_result、diff_index）
11. **表格数据统一出口** — 表格行数据构建统一使用 `service.build_table_rows()`，不在 table_panel 中重复实现路径展平+状态判断
