---
sidebar_position: 5
title: 主题与编辑器
---

# 主题与编辑器

```mermaid
flowchart LR
    THEME["VTable.theme / themeOr / registerTheme"] --> OPT["options.theme"]
    EDITOR["editor("input", InputEditor)"] --> OPT
    COL["列上 editor = "input""] --> OPT
    OPT --> TBL["ListTable / PivotTable"]
    TBL --> EV["table.on("click_cell") 等上游事件名"]
    EV --> CB["回调收到 JsAny 事件对象，按事件名 cast"]
```


## 主题

主题是一组作用到整张表的设计变量。上游自带五个命名主题——`DEFAULT`、`DARK`、`BRIGHT`、`ARCO`、
`SIMPLIFY`——封装通过 `VTable` 对象按名字取用：

```kotlin
val options = listTableOptions {
    columns(textColumn("name", "姓名", 150.0))
    records(row("name" to "Ada"))
    theme = VTable.themeOr("dark").unsafeCast<ITableThemeDefine>()
}
```

| 成员 | 行为 |
| --- | --- |
| `VTable.theme(name)` | 等价于 `of(name)`：把已注册的名字或已构造的主题转成主题对象，取不到返回 `null` |
| `VTable.themeOr(name)` | 同上，取不到时回退到 `DEFAULT` |
| `VTable.registerTheme(name, theme)` | 注册主题，后续表格可以按名字取用 |

生成的 `DARK`、`BRIGHT`、`ARCO`、`SIMPLIFY`、`DEFAULT` 就是上游常量，可以直接用。

## 编辑器

单元格编辑器来自 `@visactor/vtable-editors`，封装在同一个模块里。按名字注册，然后从列上引用这个名字：

```kotlin
editor("input", InputEditor(null).unsafeCast<IEditor>())

val options = listTableOptions {
    columns(
        textColumn("name", "姓名", 150.0),
        textColumn("role", "方向", 160.0) {
            editor = "input".unsafeCast<JsAny>()
        },
    )
}
```

`InputEditor`、`TextAreaEditor`、`DatePickerEditor` 是上游的三个编辑器；构造器接收一个可选的配置对象
（`InputEditorConfig` 等）。编辑器本身是上游对象，封装只给它的类和配置补了 Kotlin 类型。

## 事件

表格事件是属性，属性名就是上游事件字符串。回调收到一个 `JsAny` 参数——事件对象，形状由事件名决定：

```kotlin
val table = ListTable(container, options)
table.on("click_cell".unsafeCast<JsAny>()) { args ->
    val cell = args.unsafeCast<ClickedCell>()   // { row: number, col: number, … }
    println("行 ${cell.row}，列 ${cell.col}")
    null.unsafeCast<JsAny>()                    // 回调返回值会被忽略
}
```

`on` 的声明是 `(JsAny, TableEventListener) -> EventListenerId`，所以像函数一样调用。事件名用上游的
（`click_cell`、`dblclick_cell`、`mouseenter_cell`、`selected_cell` …）；生成的 `TableEvents` 接口按
参数类型列出了它们。

## 接下来

- [开发](guide/development.md) — 重新生成声明、跑检查。
- [包覆盖](guide/scope.md) — 每个上游包的状态。
