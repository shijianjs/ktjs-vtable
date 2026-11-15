package demo

import io.github.shijianjs.ktjs.vtable.BaseTable
import io.github.shijianjs.ktjs.vtable.IEditor
import io.github.shijianjs.ktjs.vtable.ITableThemeDefine
import io.github.shijianjs.ktjs.vtable.InputEditor
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.PivotTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.TableTheme
import io.github.shijianjs.ktjs.vtable.dsl.VTable
import io.github.shijianjs.ktjs.vtable.dsl.row
import io.github.shijianjs.ktjs.vtable.dsl.textColumn
import io.github.shijianjs.ktjs.vtable.dsl.listTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.groupColumn
import io.github.shijianjs.ktjs.vtable.dsl.pivotTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.columns
import io.github.shijianjs.ktjs.vtable.editor
import js.objects.unsafeJso
import kotlin.js.JsAny
import kotlin.js.unsafeCast
import web.cssom.ClassName
import web.dom.document
import web.events.EventHandler
import web.html.HTMLElement
import web.html.HtmlTagName

private const val PROJECT_NAME = "ktjs-vtable"
private const val SOURCE_URL = "https://github.com/shijianjs/ktjs-vtable"

// ------------------------------------------------------------------------------------------------
// Page chrome
// ------------------------------------------------------------------------------------------------

private var lang = Lang.EN
private lateinit var titleEl: HTMLElement
private lateinit var subtitleEl: HTMLElement
private lateinit var navEl: HTMLElement
private lateinit var stageEl: HTMLElement
private lateinit var docsLink: HTMLElement
private lateinit var apiLink: HTMLElement
private lateinit var sourceLink: HTMLElement
private lateinit var langEn: HTMLElement
private lateinit var langZh: HTMLElement
private var activeDemo = "basic"
private var currentTable: BaseTable? = null

fun main() {
    val page = document.createElement(HtmlTagName.div).apply { className = ClassName("page") }
    page.append(buildHeader(), buildBody())
    document.body.append(page)
    select(activeDemo)
}

private fun buildHeader(): HTMLElement {
    val logo = document.createElement(HtmlTagName.img).apply {
        className = ClassName("logo")
        setAttribute("src", "img/ktjs-vtable-logo.png")
        setAttribute("alt", "$PROJECT_NAME logo")
    }
    titleEl = document.createElement(HtmlTagName.h1).apply { textContent = PROJECT_NAME }
    subtitleEl = document.createElement(HtmlTagName.p).apply { className = ClassName("subtitle") }

    val links = document.createElement(HtmlTagName.nav).apply { className = ClassName("top-links") }
    docsLink = link("../", "", "")
    apiLink = link("../api/", "", "")
    sourceLink = link(SOURCE_URL, "", "")
    links.append(docsLink, apiLink, sourceLink)

    langEn = document.createElement(HtmlTagName.button).apply {
        className = ClassName("lang")
        textContent = "EN"
        onclick = EventHandler { setLang(Lang.EN) }
    }
    langZh = document.createElement(HtmlTagName.button).apply {
        className = ClassName("lang")
        textContent = "中文"
        onclick = EventHandler { setLang(Lang.ZH) }
    }
    val langSwitch = document.createElement(HtmlTagName.div).apply {
        className = ClassName("lang-switch")
        append(langEn, langZh)
    }

    val branding = document.createElement(HtmlTagName.div).apply {
        className = ClassName("branding")
        append(logo, wrap(titleEl, subtitleEl))
    }

    return document.createElement(HtmlTagName.header).apply {
        className = ClassName("header")
        append(branding, langSwitch, links)
    }
}

private fun buildBody(): HTMLElement {
    navEl = document.createElement(HtmlTagName.nav).apply { className = ClassName("toc") }
    stageEl = document.createElement(HtmlTagName.section).apply { className = ClassName("stage") }
    return document.createElement(HtmlTagName.main).apply {
        className = ClassName("layout")
        append(navEl, stageEl)
    }
}

private fun wrap(vararg children: HTMLElement): HTMLElement =
    document.createElement(HtmlTagName.div).apply { append(*children) }

private fun link(href: String, label: String, title: String): HTMLElement =
    document.createElement(HtmlTagName.a).apply {
        setAttribute("href", href)
        className = ClassName("top-link")
    }.also { element ->
        if (label.isNotEmpty()) element.textContent = label
        if (title.isNotEmpty()) element.setAttribute("title", title)
    }

// ------------------------------------------------------------------------------------------------
// Navigation and language
// ------------------------------------------------------------------------------------------------

private fun setLang(next: Lang) {
    if (next == lang) return
    lang = next
    refreshChrome()
    select(activeDemo)
}

private fun refreshChrome() {
    subtitleEl.textContent = t("subtitle")
    docsLink.textContent = t("docs")
    apiLink.textContent = t("api")
    sourceLink.textContent = t("source")
    langEn.className = ClassName(if (lang == Lang.EN) "lang active" else "lang")
    langZh.className = ClassName(if (lang == Lang.ZH) "lang active" else "lang")
}

private fun select(id: String) {
    activeDemo = id
    refreshChrome()
    currentTable?.release()
    currentTable = null
    navEl.replaceChildren()
    for (demo in demos) {
        val button = document.createElement(HtmlTagName.button).apply {
            className = ClassName(if (demo.id == id) "toc-item active" else "toc-item")
            textContent = t("nav.${demo.id}")
            onclick = EventHandler { select(demo.id) }
        }
        navEl.append(button)
    }
    stageEl.replaceChildren()
    val heading = document.createElement(HtmlTagName.h2).apply { textContent = t("demo.${id}.title") }
    val body = document.createElement(HtmlTagName.p).apply {
        className = ClassName("intro")
        textContent = t("demo.${id}.intro")
    }
    stageEl.append(heading, body)
    try {
        demos.first { it.id == id }.build(stageEl)
    } catch (error: Throwable) {
        // A demo that cannot build should say so in place instead of leaving an empty pane: the
        // message is what makes an upstream behaviour change visible on the published page.
        stageEl.append(
            document.createElement(HtmlTagName.pre).apply {
                className = ClassName("error")
                textContent = error.stackTraceToString()
            },
        )
    }
}

// ------------------------------------------------------------------------------------------------
// Demos
// ------------------------------------------------------------------------------------------------

private class Demo(val id: String, val build: (HTMLElement) -> Unit)

private val demos = listOf(
    Demo("basic") { buildBasic(it) },
    Demo("group") { buildGrouped(it) },
    Demo("pivot") { buildPivot(it) },
    Demo("edit") { buildEditable(it) },
    Demo("theme") { buildThemes(it) },
    Demo("events") { buildEvents(it) },
)

/** A canvas-backed table needs an element with a real size before it is constructed. */
private fun host(): HTMLElement =
    document.createElement(HtmlTagName.div).apply { className = ClassName("table-host") }

private fun note(text: String): HTMLElement =
    document.createElement(HtmlTagName.p).apply {
        className = ClassName("note")
        textContent = text
    }

private fun buildBasic(stage: HTMLElement) {
    val container = host()
    stage.append(container)
    val options = listTableOptions {
        columns(
            textColumn("name", t("col.name"), 150.0),
            textColumn("role", t("col.role"), 160.0),
            textColumn("city", t("col.city"), 130.0),
            textColumn("score", t("col.score"), 100.0),
        )
        records(*people())
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    }
    currentTable = ListTable(container, options)
}

private fun buildGrouped(stage: HTMLElement) {
    val container = host()
    stage.append(note(t("groupnote")), container)
    val options = listTableOptions {
        columns(
            textColumn("name", t("col.name"), 130.0),
            groupColumn(
                t("col.h1"),
                textColumn("q1", "Q1", 90.0),
                textColumn("q2", "Q2", 90.0),
                textColumn("q3", "Q3", 90.0),
            ),
            groupColumn(
                t("col.h2"),
                textColumn("q4", "Q4", 90.0),
                textColumn("q5", "Q5", 90.0),
            ),
        )
        records(
            row("name" to "Ada", "q1" to 88.0, "q2" to 92.0, "q3" to 95.0, "q4" to 91.0, "q5" to 93.0),
            row("name" to "Grace", "q1" to 91.0, "q2" to 90.0, "q3" to 89.0, "q4" to 94.0, "q5" to 96.0),
            row("name" to "Linus", "q1" to 78.0, "q2" to 84.0, "q3" to 87.0, "q4" to 88.0, "q5" to 90.0),
        )
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.standard
    }
    currentTable = ListTable(container, options)
}

private fun buildPivot(stage: HTMLElement) {
    val container = host()
    stage.append(note(t("pivotnote")), container)
    val options = pivotTableOptions {
        records(
            row("region" to t("region.east"), "category" to t("cat.a"), "sales" to 120.0, "profit" to 30.0),
            row("region" to t("region.east"), "category" to t("cat.b"), "sales" to 90.0, "profit" to 18.0),
            row("region" to t("region.west"), "category" to t("cat.a"), "sales" to 150.0, "profit" to 42.0),
            row("region" to t("region.west"), "category" to t("cat.b"), "sales" to 60.0, "profit" to 12.0),
        )
        this.rows = arrayOf<JsAny>(unsafeJso<PivotDimension> { field = "region"; title = t("dim.region") })
        this.columns = arrayOf<JsAny>(unsafeJso<PivotDimension> { field = "category"; title = t("dim.category") })
        this.indicators = arrayOf<JsAny>(
            unsafeJso<PivotIndicator> {
                field = "sales"
                title = t("ind.sales")
                aggregationType = "SUM"
            },
            unsafeJso<PivotIndicator> {
                field = "profit"
                title = t("ind.profit")
                aggregationType = "SUM"
            },
        )
        widthMode = StandardOrAdaptiveOrAutoWidths.standard
    }
    currentTable = PivotTable(container, options)
}

private fun buildEditable(stage: HTMLElement) {
    val container = host()
    stage.append(note(t("editnote")), container)
    editor("input", InputEditor(null).unsafeCast<IEditor>())
    val options = listTableOptions {
        columns(
            textColumn("name", t("col.name"), 150.0),
            textColumn("role", t("col.role"), 160.0) {
                this.editor = "input".unsafeCast<JsAny>()
            },
            textColumn("city", t("col.city"), 130.0) {
                this.editor = "input".unsafeCast<JsAny>()
            },
        )
        records(*people())
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    }
    currentTable = ListTable(container, options)
}

private fun buildThemes(stage: HTMLElement) {
    val container = host()
    val toolbar = document.createElement(HtmlTagName.div).apply { className = ClassName("toolbar") }
    for ((label, themeName) in listOf(
        t("theme.default") to "default",
        t("theme.dark") to "dark",
        t("theme.bright") to "bright",
    )) {
        toolbar.append(
            document.createElement(HtmlTagName.button).apply {
                className = ClassName("chip")
                textContent = label
                onclick = EventHandler {
                    buildWithTheme(container, themeName)
                }
            },
        )
    }
    stage.append(note(t("themnote")), toolbar, container)
    buildWithTheme(container, "default")
}

private fun buildWithTheme(container: HTMLElement, themeName: String) {
    currentTable?.release()
    val theme: TableTheme = VTable.themeOr(themeName)
    val options = listTableOptions {
        columns(
            textColumn("name", t("col.name"), 150.0),
            textColumn("role", t("col.role"), 160.0),
            textColumn("score", t("col.score"), 100.0),
        )
        records(*people())
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
        this.theme = theme.unsafeCast<ITableThemeDefine>()
    }
    currentTable = ListTable(container, options)
}

private fun buildEvents(stage: HTMLElement) {
    val container = host()
    val log = document.createElement(HtmlTagName.ul).apply { className = ClassName("log") }
    stage.append(note(t("eventnote")), container, log)
    val options = listTableOptions {
        columns(
            textColumn("name", t("col.name"), 150.0),
            textColumn("city", t("col.city"), 130.0),
            textColumn("score", t("col.score"), 100.0),
        )
        records(*people())
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    }
    val table = ListTable(container, options)
    currentTable = table
    table.on("click_cell".unsafeCast<JsAny>()) { args ->
        val cell = args.unsafeCast<ClickedCell>()
        val item = document.createElement(HtmlTagName.li).apply {
            textContent = t("event.hit")
                .replace("{row}", cell.row.toInt().toString())
                .replace("{col}", cell.col.toInt().toString())
        }
        log.insertBefore(item, log.firstChild)
        while (log.childElementCount > 6) {
            log.lastChild?.let { log.removeChild(it) }
        }
        null.unsafeCast<JsAny>()
    }
}

private fun people(): Array<JsAny> {
    val rows = if (lang == Lang.ZH) {
        listOf(
            row("name" to "Ada Lovelace", "role" to "分析引擎", "city" to "伦敦", "score" to 96.0),
            row("name" to "Grace Hopper", "role" to "编译器", "city" to "纽约", "score" to 92.0),
            row("name" to "Linus Torvalds", "role" to "内核", "city" to "赫尔辛基", "score" to 88.0),
            row("name" to "Margaret Hamilton", "role" to "导航软件", "city" to "波士顿", "score" to 99.0),
            row("name" to "Barbara Liskov", "role" to "分布式系统", "city" to "波士顿", "score" to 94.0),
        )
    } else {
        listOf(
            row("name" to "Ada Lovelace", "role" to "Analytical engine", "city" to "London", "score" to 96.0),
            row("name" to "Grace Hopper", "role" to "Compiler", "city" to "New York", "score" to 92.0),
            row("name" to "Linus Torvalds", "role" to "Kernel", "city" to "Helsinki", "score" to 88.0),
            row("name" to "Margaret Hamilton", "role" to "Navigation software", "city" to "Boston", "score" to 99.0),
            row("name" to "Barbara Liskov", "role" to "Distributed systems", "city" to "Boston", "score" to 94.0),
        )
    }
    return rows.toTypedArray()
}

// Upstream pivot options take dimension/indicator objects; only the fields the demo uses are typed.
private external interface PivotDimension {
    var field: String
    var title: String?
}

private external interface PivotIndicator {
    var field: String
    var title: String?
    var aggregationType: String?
}

private external interface ClickedCell {
    var row: Double
    var col: Double
}

// ------------------------------------------------------------------------------------------------
// Strings
// ------------------------------------------------------------------------------------------------

private enum class Lang { EN, ZH }

private object Strings {
    val en: Map<String, String> = mapOf(
        "subtitle" to "Kotlin/JS wrapper for the open-source packages of VisActor VTable",
        "docs" to "Documentation",
        "api" to "API reference",
        "source" to "Source",
        "nav.basic" to "Basic table",
        "nav.group" to "Grouped header",
        "nav.pivot" to "Pivot table",
        "nav.edit" to "Editable cells",
        "nav.theme" to "Themes",
        "nav.events" to "Events",
        "demo.basic.title" to "Basic list table",
        "demo.basic.intro" to "Five text columns, one frozen column, adaptive width. " +
            "Everything is built with the hand-written DSL on top of the generated declarations.",
        "demo.group.title" to "Grouped header",
        "demo.group.intro" to "Columns can nest: a group header holds the quarterly score columns below it.",
        "groupnote" to "Hover a quarter column: the group header stays highlighted while the cell is under the pointer.",
        "demo.pivot.title" to "Pivot table",
        "demo.pivot.intro" to "Rows and columns are dimensions, indicators are aggregated values. " +
            "Drag a row-header cell to reorder the dimensions.",
        "pivotnote" to "The pivot table aggregates the same flat records by the row and column dimensions.",
        "demo.edit.title" to "Editable cells",
        "demo.edit.intro" to "Columns with an editor open an input when you double-click a cell. " +
            "The editor is the upstream @visactor/vtable-editors input editor, registered by name.",
        "editnote" to "Double-click a role or city cell to edit it.",
        "demo.theme.title" to "Themes",
        "demo.theme.intro" to "Themes are tables of design tokens; the built-in ones ship with the package " +
            "and the wrapper resolves them by name.",
        "themnote" to "Pick a theme: the table is rebuilt with that theme's design tokens.",
        "theme.default" to "Default",
        "theme.dark" to "Dark",
        "theme.bright" to "Bright",
        "demo.events.title" to "Events",
        "demo.events.intro" to "Table events arrive as plain JavaScript arguments; " +
            "click a cell to see the coordinates.",
        "eventnote" to "Click any cell.",
        "event.hit" to "click_cell row {row} col {col}",
        "col.name" to "Name",
        "col.role" to "Role",
        "col.city" to "City",
        "col.score" to "Score",
        "col.h1" to "2025 H1",
        "col.h2" to "2025 H2",
        "dim.region" to "Region",
        "dim.category" to "Category",
        "ind.sales" to "Sales",
        "ind.profit" to "Profit",
        "region.east" to "East",
        "region.west" to "West",
        "cat.a" to "Category A",
        "cat.b" to "Category B",
    )

    val zh: Map<String, String> = mapOf(
        "subtitle" to "VisActor VTable 开源部分的 Kotlin/JS 封装",
        "docs" to "文档",
        "api" to "API 参考",
        "source" to "源码",
        "nav.basic" to "基础表格",
        "nav.group" to "分组表头",
        "nav.pivot" to "透视表",
        "nav.edit" to "可编辑单元格",
        "nav.theme" to "主题",
        "nav.events" to "事件",
        "demo.basic.title" to "基础列表",
        "demo.basic.intro" to "五个文本列、一列冻结、宽度自适应。" +
            "全部用生成声明之上的手写 DSL 构造。",
        "demo.group.title" to "分组表头",
        "demo.group.intro" to "列可以嵌套：一个分组表头下面挂若干季度分数列。",
        "groupnote" to "把鼠标移到某个季度列上：分组表头会随单元格一起高亮。",
        "demo.pivot.title" to "透视表",
        "demo.pivot.intro" to "行和列是维度，指标是聚合后的数值。拖动行表头单元格可以调整维度顺序。",
        "pivotnote" to "透视表把同一批平坦记录按行、列维度聚合。",
        "demo.edit.title" to "可编辑单元格",
        "demo.edit.intro" to "带编辑器的列在双击单元格时弹出输入框。" +
            "编辑器就是上游 @visactor/vtable-editors 的输入编辑器，按名字注册。",
        "editnote" to "双击角色或城市单元格即可编辑。",
        "demo.theme.title" to "主题",
        "demo.theme.intro" to "主题是一组设计变量；内置主题随包发布，封装层按名字取用。",
        "themnote" to "选一个主题：表格会用该主题的设计变量重建。",
        "theme.default" to "默认",
        "theme.dark" to "深色",
        "theme.bright" to "明亮",
        "demo.events.title" to "事件",
        "demo.events.intro" to "表格事件以普通 JavaScript 参数传入；点击单元格查看坐标。",
        "eventnote" to "点击任意单元格。",
        "event.hit" to "click_cell 行 {row} 列 {col}",
        "col.name" to "姓名",
        "col.role" to "方向",
        "col.city" to "城市",
        "col.score" to "得分",
        "col.h1" to "2025 上半年",
        "col.h2" to "2025 下半年",
        "dim.region" to "区域",
        "dim.category" to "类别",
        "ind.sales" to "销售额",
        "ind.profit" to "利润",
        "region.east" to "华东",
        "region.west" to "西部",
        "cat.a" to "类别 A",
        "cat.b" to "类别 B",
    )

    fun get(lang: Lang, key: String): String = (if (lang == Lang.EN) en else zh)[key] ?: key
}

private fun t(key: String): String = Strings.get(lang, key)
