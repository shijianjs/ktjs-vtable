package io.github.shijianjs.ktjs.vtable.dsl

import io.github.shijianjs.ktjs.vtable.ColumnDefine
import io.github.shijianjs.ktjs.vtable.ColumnsDefine
import io.github.shijianjs.ktjs.vtable.DEFAULT
import io.github.shijianjs.ktjs.vtable.ITableThemeDefine
import io.github.shijianjs.ktjs.vtable.ITableThemeDefineOrString
import io.github.shijianjs.ktjs.vtable.ListTableConstructorOptions
import io.github.shijianjs.ktjs.vtable.PivotChartConstructorOptions
import io.github.shijianjs.ktjs.vtable.PivotTableConstructorOptions
import io.github.shijianjs.ktjs.vtable.TableTheme
import io.github.shijianjs.ktjs.vtable.of
import js.objects.unsafeJso
import kotlin.js.JsAny
import kotlin.js.unsafeCast

/**
 * VTable 的手写薄封装：生成声明保留上游的联合类型与常量对象，这里只补三类日常入口，
 * 避免每次构造都要走 `unsafeJso` + 联合工厂：
 *
 * - 构造选项：[listTableOptions]、[pivotTableOptions]、[pivotChartOptions]
 * - 列定义：[textColumn]、[linkColumn]、[checkboxColumn]、[groupColumn]
 * - 数据行：[row]
 *
 * 任何这里没覆盖的字段仍然可以直接在 `unsafeJso<ListTableConstructorOptions>` 里赋值，
 * 生成声明就是完整的类型面。
 */
fun listTableOptions(block: ListTableConstructorOptions.() -> Unit): ListTableConstructorOptions =
    unsafeJso(block)

/** [PivotTable] 的构造选项。 */
fun pivotTableOptions(block: PivotTableConstructorOptions.() -> Unit): PivotTableConstructorOptions =
    unsafeJso(block)

/** [PivotChart] 的构造选项。 */
fun pivotChartOptions(block: PivotChartConstructorOptions.() -> Unit): PivotChartConstructorOptions =
    unsafeJso(block)

/** 一次设置整组列定义，对应上游的 `columns`。 */
fun ListTableConstructorOptions.columns(vararg columns: ColumnDefine) {
    this.columns = columns.unsafeCast<ColumnsDefine>()
}

/** 一次设置全部数据行，对应上游的 `records`。 */
fun ListTableConstructorOptions.records(vararg records: Any) {
    this.records = records.unsafeCast<Array<Any>>()
}

/** 透视表的数据行。 */
fun PivotTableConstructorOptions.records(vararg records: Any) {
    this.records = records.unsafeCast<Array<JsAny>>()
}

/**
 * 一行记录：`row("name" to "Alice", "age" to 30)`。
 *
 * 值按原样写进普通 JS 对象；VTable 只按列 `field` 取值，不要求预先声明结构。
 */
fun row(vararg values: Pair<String, Any?>): JsAny {
    // A record is an open dictionary keyed by the column `field`s, so it has no Kotlin shape to
    // type: `unsafeJso` only lowers statically known property names, and an index assignment on an
    // external interface lowers to a `set(...)` call that plain objects do not have. This is the one
    // place in the DSL that builds an object dynamically; the values themselves stay checked by the
    // caller, and `records` is typed as `Array<JsAny>` upstream.
    val record: dynamic = js("{}")
    for ((key, value) in values) {
        record[key] = value
    }
    return record.unsafeCast<JsAny>()
}

/**
 * 文本列。`field` 是记录里的字段名，`title` 是表头文字。
 *
 * 其余上游字段（`style`、`sort`、`format`、`editor` 等）通过 [block] 以 JS 值写入；
 * 生成的 `TextColumnDefine` 声明了完整字段，需要类型检查时直接用 `unsafeJso<TextColumnDefine>`。
 */
fun textColumn(
    field: String,
    title: String? = null,
    width: Double? = null,
    block: ColumnSpec.() -> Unit = {},
): ColumnDefine = column(field, title, width, "text", block)

/** 链接列；`field` 同时作为链接文字，`templateLink` 由 [block] 设置。 */
fun linkColumn(
    field: String,
    title: String? = null,
    width: Double? = null,
    block: ColumnSpec.() -> Unit = {},
): ColumnDefine = column(field, title, width, "link", block)

/** 复选框列。 */
fun checkboxColumn(
    field: String,
    title: String? = null,
    width: Double? = null,
    block: ColumnSpec.() -> Unit = {},
): ColumnDefine = column(field, title, width, "checkbox", block)

/** 进度条列。 */
fun progressbarColumn(
    field: String,
    title: String? = null,
    width: Double? = null,
    block: ColumnSpec.() -> Unit = {},
): ColumnDefine = column(field, title, width, "progressbar", block)

/** 图片列，`field` 的值是图片地址。 */
fun imageColumn(
    field: String,
    title: String? = null,
    width: Double? = null,
    block: ColumnSpec.() -> Unit = {},
): ColumnDefine = column(field, title, width, "image", block)

/**
 * 分组表头：`groupColumn("2024", textColumn("q1", "Q1"), textColumn("q2", "Q2"))`。
 */
fun groupColumn(title: String, vararg columns: ColumnDefine): ColumnDefine =
    unsafeJso<GroupSpec> {
        this.title = title
        this.columns = columns.unsafeCast<ColumnsDefine>()
    }.unsafeCast<ColumnDefine>()

private fun column(
    field: String,
    title: String?,
    width: Double?,
    cellType: String,
    block: ColumnSpec.() -> Unit,
): ColumnDefine = unsafeJso<ColumnSpec> {
    this.field = field
    this.title = title
    this.width = width
    this.cellType = cellType
    block()
}.unsafeCast<ColumnDefine>()

/**
 * 列定义里最常用的几个字段；`style`、`editor`、`sort` 等留给调用方按 JS 值写入，
 * 因为它们的上游类型是联合类型（`TextStyleOption | ((args) -> TextStyleOption)`）。
 */
external interface ColumnSpec {
    var field: String
    var title: String?
    var width: Double?
    var cellType: String?

    /** 列样式，写 `unsafeJso<ITextStyleOption>` 即可。 */
    var style: JsAny?
    var headerStyle: JsAny?

    /** 单元格编辑器：字符串名字或 `@visactor/vtable-editors` 里的编辑器实例。 */
    var editor: JsAny?
    var headerEditor: JsAny?

    /** 排序配置，`unsafeJso<SortOption>`。 */
    var sort: JsAny?
    var showSort: Boolean?

    /** 复合列（[groupColumn]）的子列。 */
    var columns: JsAny?
}

/** 主题注册表的便捷入口，对应上游 `register` 命名空间。 */
object VTable {
    /** 注册一个主题名，随后 `theme = VTable.theme("dark-plus")` 取用。 */
    fun registerTheme(name: String, theme: ITableThemeDefine): ITableThemeDefine =
        io.github.shijianjs.ktjs.vtable.theme(name, theme)

    /** 按名字取主题：内置的是 `DEFAULT`、`DARK`、`BRIGHT`、`ARCO`、`SIMPLIFY`。 */
    fun theme(name: String): TableTheme? = of(name.unsafeCast<ITableThemeDefineOrString>())

    /** 按名字取主题，取不到时回退到内置的 `DEFAULT`。 */
    fun themeOr(name: String, fallback: TableTheme = DEFAULT): TableTheme = theme(name) ?: fallback
}

private external interface GroupSpec {
    var title: String
    var columns: JsAny
}
