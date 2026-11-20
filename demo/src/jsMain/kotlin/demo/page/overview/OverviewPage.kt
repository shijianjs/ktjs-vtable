package demo.page.overview

import io.github.shijianjs.ktjs.demo.page.DemoPage
import demo.API_URL
import demo.DOCS_URL
import demo.SOURCE_URL
import io.github.shijianjs.ktjs.demo.i18n.Binder
import io.github.shijianjs.ktjs.demo.i18n.Lang
import io.github.shijianjs.ktjs.demo.i18n.Langs
import io.github.shijianjs.ktjs.demo.i18n.Translations
import io.github.shijianjs.ktjs.demo.i18n.texts
import io.github.shijianjs.ktjs.demo.page.Blocks.anchor
import io.github.shijianjs.ktjs.demo.page.Blocks.codeText
import io.github.shijianjs.ktjs.demo.page.Blocks.paragraph
import io.github.shijianjs.ktjs.demo.page.Blocks.row
import io.github.shijianjs.ktjs.demo.page.SectionBlock
import io.github.shijianjs.ktjs.dom.element.invoke
import io.github.shijianjs.ktjs.dom.element.unaryPlus
import io.github.shijianjs.ktjs.dom.webcomponent.CustomElementReferenceAdapter
import web.html.HtmlTagName

/** Every string this page shows, in one language. */
private class OverviewTexts(
    val title: String,
    val summary: String,
    val docsLink: String,
    val sourceLink: String,
    val apiLink: String,
    val purposeHeading: String,
    val body: String,
    val bullets: List<String>,
    val optionsHeading: String,
    val optionsBody: String,
    val nextHeading: String,
    val nextBody: String,
)

private val overviewEnglish: OverviewTexts = OverviewTexts(
    title = "Overview",
    summary = "A Kotlin/JS wrapper for the open-source packages of VisActor VTable: list tables, pivot " +
        "tables and the editors that go with them.",
    docsLink = "Documentation",
    sourceLink = "Source repository",
    apiLink = "API reference",
    purposeHeading = "What it wraps",
    body = "VTable draws tables on a canvas: columns, records, frozen panes, themes and editors are all " +
        "options of one constructor. The wrapper keeps the generated declarations and adds a DSL on top, " +
        "so `listTableOptions { columns(textColumn(\"name\", \"Name\", 150.0)); records(…) }` describes " +
        "a table without a dictionary of strings.",
    bullets = listOf(
        "ListTable(host, listTableOptions { … }) — rows, columns, frozen panes.",
        "groupColumn(title, …) — a header over several columns.",
        "PivotTable(host, pivotTableOptions { rows = …; columns = …; indicators = … }) — the same rows, aggregated.",
    ),
    optionsHeading = "The host needs a size",
    optionsBody = "A canvas has no layout of its own: the table measures the element it was given at " +
        "construction and paints at that size. A host that is still zero-width when the table is built " +
        "produces an empty canvas that never fills in, so every page here waits for `clientWidth >= 200`.",
    nextHeading = "Reading order",
    nextBody = "The overview, then the tables: basic, grouped header and pivot; then the interaction " +
        "pages — editing, themes and events.",
)

private val overviewChinese: OverviewTexts = OverviewTexts(
    title = "概览",
    summary = "VisActor VTable 开源部分的 Kotlin/JS 封装：列表、透视表，以及配套的编辑器。",
    docsLink = "使用文档",
    sourceLink = "源码仓库",
    apiLink = "API 文档",
    purposeHeading = "它封装了什么",
    body = "VTable 把表格画在 canvas 上：列、记录、冻结窗格、主题与编辑器都是同一个构造函数的选项。" +
        "封装保留生成声明，并在其上补一层 DSL，于是 " +
        "`listTableOptions { columns(textColumn(\"name\", \"Name\", 150.0)); records(…) }` 就能描述一张表，" +
        "而不是一堆字符串字典。",
    bullets = listOf(
        "ListTable(host, listTableOptions { … }) —— 行、列、冻结窗格。",
        "groupColumn(title, …) —— 跨若干列的表头。",
        "PivotTable(host, pivotTableOptions { rows = …; columns = …; indicators = … }) —— 同一批行，聚合展示。",
    ),
    optionsHeading = "宿主必须有尺寸",
    optionsBody = "canvas 没有自己的布局：表在构造时测量它拿到的元素、并按那个尺寸作画。宿主在创建时宽度还是 0，" +
        "画出来的就是一张永远不会补上的空白，所以这里每个页面都等 `clientWidth >= 200`。",
    nextHeading = "建议顺序",
    nextBody = "先看概览，再看表格：基础、分组表头、透视表；然后是交互页 —— 编辑、主题与事件。",
)

private val overviewTexts: Translations<OverviewTexts> = texts(
    Langs.EN to overviewEnglish,
    Langs.ZH_HANS to overviewChinese,
)

/**
 * Landing page: what the library wraps, how it is consumed, where the reference lives.
 */
internal class OverviewPage : DemoPage() {

    private val texts = Binder(overviewTexts)


    init {
        addLink(texts.bind(anchor("", DOCS_URL, external = true), { it.docsLink }))
        addLink(texts.bind(anchor("", API_URL, external = true), { it.apiLink }))
        addLink(texts.bind(anchor("", SOURCE_URL, external = true), { it.sourceLink }))

        val purpose = SectionBlock.NAME { show() }
        texts.bind(purpose.heading, { it.purposeHeading })
        // One bound <li> per bullet, so a language switch rewrites each line in place.
        val bullets = HtmlTagName.ul {
            List(3) { index -> texts.bind(+HtmlTagName.li()) { it.bullets.getOrNull(index).orEmpty() } }
        }
        purpose.body.append(texts.bind(paragraph(), { it.body }), bullets)

        val options = SectionBlock.NAME { show() }
        texts.bind(options.heading, { it.optionsHeading })
        options.body.append(
            texts.bind(paragraph(), { it.optionsBody }),
            row(codeText("listTableOptions { columns(textColumn(\"name\", \"Name\", 150.0)) }")),
        )

        val next = SectionBlock.NAME { show() }
        texts.bind(next.heading, { it.nextHeading })
        next.body.append(texts.bind(paragraph(), { it.nextBody }))

        body.append(purpose.root, options.root, next.root)
    }

    override fun applyTranslation(lang: Lang) {
        val current = overviewTexts[lang]
        setTitle(current.title)
        setSummary(current.summary)
        texts.apply(lang)
    }

    companion object : CustomElementReferenceAdapter<OverviewPage>(OverviewPage::class.js, "vtable-overview-page")
}
