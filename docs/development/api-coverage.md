# API / 交付覆盖清单

## 来源与范围

- 上游：<https://github.com/VisActor/VTable>，本地克隆 `S:\workspace\github\VisActor\VTable`
- 版本：`1.26.8`（npm 包 `@visactor/vtable` 与 `@visactor/vtable-editors`）
- 核对日期：2026-11-15
- 纳入统计：`packages/` 下全部对外发布的 npm 包（11 个），加上生成质量、demo、文档三组交付事项
- 不纳入：仓库内部构建工具、`tools/`、`share/` 等不对外发布的包

## 统计

| 状态 | 数量 |
|---|---:|
| 总计 | 27 |
| 已完成 | 16 |
| 明确不做 | 3 |
| 待完成 | 8 |

`总数 = 已完成 + 明确不做 + 待完成`

## 1. npm 包覆盖（11）

| 包 | 状态 | 说明 |
|---|---|---|
| `@visactor/vtable` | 已完成 | 主体：`ListTable` / `PivotTable` / `PivotChart` 及其构造选项、主题、事件、工具函数；444 条可达声明、138 个 Kotlin 文件，`:ktjs-vtable:compileKotlinJs` 通过 |
| `@visactor/vtable-editors` | 已完成 | `InputEditor` / `TextAreaEditor` / `DateInputEditor`；从包根导入（上游 `exports` 只暴露 `.`），编辑器注册已在 demo 验证 |
| `@visactor/vtable-export` | 待完成 | CSV / Excel 导出，依赖 `exceljs`；需要生成器支持第二个 npm 依赖 |
| `@visactor/vtable-search` | 待完成 | 表内搜索组件，自带面板 DOM，需要生成 + 演示 |
| `@visactor/vtable-plugins` | 待完成 | 插件集合（右键菜单、行列拖拽、单元格样式等），选项伸进 VChart / VRender 类型 |
| `@visactor/vtable-gantt` | 待完成 | 甘特图子产品，独立 `Gantt` 组件 |
| `@visactor/vtable-sheet` | 待完成 | 电子表格子产品，独立 `SheetTable` 组件 |
| `@visactor/vtable-calendar` | 待完成 | 日历子产品 |
| `@visactor/react-vtable` | 明确不做 | React 组件绑定，Kotlin/JS 不绑定 React 运行时 |
| `@visactor/vue-vtable` | 明确不做 | Vue 组件绑定，同上 |
| `@visactor/openinula-vtable` | 明确不做 | OpenInula 组件绑定，同上 |

## 2. 生成与质量（5）

| 事项 | 状态 | 说明 |
|---|---|---|
| `scripts/generate-api.py` 可重跑 | 已完成 | 读两个包的 `.d.ts`，输出 138 个 Kotlin 文件；规则与理由见 [technical-decisions.md](technical-decisions.md) |
| Kotlin/JS 编译通过 | 已完成 | `:ktjs-vtable:compileKotlinJs` BUILD SUCCESSFUL（仅剩 inline 性能提示） |
| detekt + 浏览器测试（`./gradlew check`） | 已完成 | `check` 通过；`VTableTest` 6 个用例在 Chromium 里造真实表格（列表、分组、主题、字面量、编辑器注册、透视表） |
| API surface 报告 | 已完成 | [api-surface-report.md](api-surface-report.md)，随生成脚本更新 |
| 生成脚本默认读 `node_modules` | 已完成 | 已验证 `build/js/node_modules/@visactor/vtable/es` 与 `...-editors/es` 可用，重跑结果与提交的声明一致 |

## 3. Demo（7）

| Demo | 状态 | 说明 |
|---|---|---|
| 基础列表 | 已完成 | `ListTable` + 列定义 + 记录 + 冻结列 + 自适应宽度 |
| 分组表头 / 冻结列 | 已完成 | `groupColumn` 嵌套列 + `frozenColCount` |
| 透视表 | 已完成 | `PivotTable` 行/列维度 + `indicators` |
| 透视图表 | 待完成 | `PivotChart` 的指标需要 VChart chart spec（`IChartIndicator.chartSpec`），生成器尚未解析 VChart 类型；先记录为待完成，不做过期演示 |
| 可编辑单元格 | 已完成 | 注册 `InputEditor` + 列的 `editor` |
| 主题 | 已完成 | `VTable.themeOr` 切换内置 `default` / `dark` / `bright`；自定义主题注册 API 已封装，demo 未展示 |
| 事件 | 已完成 | `on("click_cell")` + 事件日志面板 |

## 4. 文档与站点（4）

| 事项 | 状态 | 说明 |
|---|---|---|
| intro / getting-started（中英） | 已完成 | 站点根路径 `/` + `/zh-Hans/` |
| 列 / 透视表 / 主题与编辑器（中英） | 已完成 | 构造选项、列定义、记录、主题、编辑器、事件 |
| 开发 / 包覆盖（中英） | 已完成 | 生成声明怎么读、哪些是 `JsAny`、包边界与进度口径 |
| Pages 站点与 demo / API 跳转 | 已完成 | `gh api` 以 `build_type=workflow` 开启 Pages，`pages.yml` 部署成功；`/`、`/demo/`、`/api/`、`/zh-Hans/` 均返回 200 |

## 已完成明细（不重复列名）

- 2 个 npm 包的主体声明与编译
- 生成脚本 + API surface 报告 + 技术决策文档
- 6 个 demo + 中英切换 + Playwright 端到端套件（`./gradlew :demo:e2eTest` 通过）
- 双语文档站（7 个英文页 + 7 个中文页）
