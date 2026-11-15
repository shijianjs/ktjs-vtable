---
sidebar_position: 7
title: 包覆盖
---

# 包覆盖

范围是「VTable 的开源包」，不是挑几个功能。本页是清单；带逐项细节的版本在
[`docs/development/api-coverage.md`](https://github.com/shijianjs/ktjs-vtable/blob/main/docs/development/api-coverage.md)。

## 已封装

| 包 | Kotlin 包 | 说明 |
| --- | --- | --- |
| `@visactor/vtable` | `io.github.shijianjs.ktjs.vtable` | `ListTable`、`PivotTable`、`PivotChart`、事件、主题、`register`。445 个可达声明、138 个文件 |
| `@visactor/vtable-editors` | 同一个包 | `InputEditor`、`TextAreaEditor`、`DatePickerEditor`；上游只导出 `.`，所以从包根导入 |

两个包共用一个 Gradle 模块和一个 Kotlin 包：上游版本和发版节奏一致，拆开只会让每次发布多一个 Maven 版本。

## 待完成

| 包 | 为什么还没做 |
| --- | --- |
| `@visactor/vtable-export` | 需要给生成器加第二个 npm 依赖，并为产出的文件补一套浏览器驱动的测试 |
| `@visactor/vtable-search` | 同样是生成步骤；搜索面板自己挂 DOM，还要配一个演示页 |
| `@visactor/vtable-plugins` | 插件选项会伸到 VChart 与 VRender 的类型里，生成器要先能解析那些 |
| `@visactor/vtable-gantt` | 选项面很大，且它自己的布局类型不在单个入口导出 |
| `@visactor/vtable-sheet` | 同甘特 |
| `@visactor/vtable-calendar` | 同甘特 |

每个待完成的包进入仓库的方式都与编辑器包相同：把它的 `.d.ts` 目录加进生成器调用、加 npm 依赖、重新生成，
再补演示与测试。

## 明确不做

| 包 | 理由 |
| --- | --- |
| `@visactor/react-vtable` | React 组件；Kotlin/JS 调用方直接构造表格 |
| `@visactor/vue-vtable` | Vue 绑定，同上 |
| `@visactor/openinula-vtable` | OpenInula 绑定，同上 |

它们属于框架绑定而不是表格本身：封装出来只会得到「必须引入对应框架才能用」的声明。
