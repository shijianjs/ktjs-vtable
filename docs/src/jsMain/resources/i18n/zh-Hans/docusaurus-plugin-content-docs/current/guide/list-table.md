---
sidebar_position: 3
title: 列表
---

# 列表

`ListTable` 把平坦的记录按列排开。封装保留上游的 `ListTableConstructorOptions` 类型，另外补了一层 DSL，
省掉手写选项对象的重复劳动。

## 选项

```kotlin
val options = listTableOptions {
    columns(
        textColumn("name", "姓名", 150.0),
        textColumn("role", "方向", 160.0),
    )
    records(
        row("name" to "Ada", "role" to "分析引擎"),
    )
    frozenColCount = 1.0
    widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
}
```

`listTableOptions { }` 构造的就是上游的 `ListTableConstructorOptions`；上游声明的每个字段都能在
lambda 里赋值，包括 DSL 没碰的那些（`hover`、`keyboardOptions`、`excelOptions`、`customRender` 等）。
DSL 补的只有这几项：

| 助手 | 上游字段 | 说明 |
| --- | --- | --- |
| `columns(vararg ColumnDefine)` | `columns` | 接收 `textColumn` / `groupColumn` 造出来的列 |
| `records(vararg Any)` | `records` | 接收 `row(...)` 造出来的行 |
| `row(vararg Pair<String, Any?>)` | 一条记录 | 键是列的 `field` 名 |

## 列

`textColumn`、`linkColumn`、`checkboxColumn`、`progressbarColumn`、`imageColumn` 的签名都是
`(field, title, width)` 加一个可选的配置块：

```kotlin
textColumn("role", "方向", 160.0) {
    editor = "input".unsafeCast<JsAny>()   // 按名字注册过的编辑器
    showSort = true
    style = unsafeJso<ITextStyleOption> { textAlign = TextAlign.center }
}
```

配置块的类型是 `ColumnSpec`，声明了演示页和文档用到的字段：`field`、`title`、`width`、`cellType`、
`style`、`headerStyle`、`editor`、`headerEditor`、`sort`、`showSort`，以及分组用的 `columns`。要设的字段
不在这份清单里时，改用生成的声明构造列：

```kotlin
val column: ColumnDefine = unsafeJso<TextColumnDefine> {
    field = "role".unsafeCast<FieldDef>()
    title = "方向".unsafeCast<StringOrString2>()
    // …
}
```

## 分组表头

`groupColumn` 把一个表头挂在若干子列之上：

```kotlin
columns(
    textColumn("name", "姓名", 130.0),
    groupColumn(
        "2025 上半年",
        textColumn("q1", "Q1", 90.0),
        textColumn("q2", "Q2", 90.0),
    ),
)
```

## 数据行

`row` 接收键值对，构造一个普通 JavaScript 对象，所以一条记录只需要包含它那些列会读的字段：

```kotlin
row("name" to "Ada Lovelace", "score" to 96.0)
```

值按原样写入：字符串、数字、布尔、日期、嵌套对象都能直接传。缺的键读出来是空单元格，多出来的键会被忽略。

## 逃生通道

没有隐藏任何东西：生成的声明就是完整的上游类型面，任何选项都能直接赋值；某个字段的类型是 DSL 没包装的
联合时，`unsafeJso<ListTableConstructorOptions>` 永远可用。

## 接下来

- [透视表](guide/pivot-table.md) — 同一批记录按维度聚合。
- [主题与编辑器](guide/themes-and-editors.md) — 样式与可编辑单元格。
