package demo.page.basic

import io.github.shijianjs.ktjs.demo.page.DemoPage
import demo.page.samples.people
import demo.page.samples.toRecords
import io.github.shijianjs.ktjs.demo.i18n.Binder
import io.github.shijianjs.ktjs.demo.i18n.Lang
import io.github.shijianjs.ktjs.demo.i18n.Langs
import io.github.shijianjs.ktjs.demo.i18n.Translations
import io.github.shijianjs.ktjs.demo.i18n.texts
import io.github.shijianjs.ktjs.demo.page.Blocks.exampleBox
import io.github.shijianjs.ktjs.demo.page.SectionBlock
import io.github.shijianjs.ktjs.dom.element.inlineStyle
import io.github.shijianjs.ktjs.dom.element.invoke
import io.github.shijianjs.ktjs.vtable.BaseTable
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.dsl.columns
import io.github.shijianjs.ktjs.vtable.dsl.listTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.textColumn
import web.animations.requestAnimationFrame
import web.cssom.px
import web.html.HTMLElement
import web.html.HtmlTagName

/**
 * The basic list table.
 *
 * VTable paints into a canvas, so the host needs a real width *and* height before the table is
 * constructed: a canvas created against a zero-width box stays empty and the browser never redoes it.
 */
internal class BasicPage : DemoPage() {

    private val texts = Binder(basicTexts)

    private var current: BasicTexts = basicEnglish

    /** The language the sample rows are written in; they are part of the content, not of the chrome. */
    private var language: Lang = Langs.EN

    private var table: BaseTable? = null

    private val host: HTMLElement = HtmlTagName.div {
        setAttribute("data-table", "basic")
        inlineStyle.apply {
            height = 320.px
        }
    }

    init {
        val section = SectionBlock.NAME { show() }
        texts.bind(section.heading, { it.tableHeading })
        texts.bind(section.hint, { it.hint })
        section.body.append(exampleBox(null, host))
        body.append(section.root)

        createOnceMounted()
    }

    /** Builds the table once the host is attached and laid out. */
    private fun createOnceMounted() {
        if (table != null) return
        if (!host.isConnected || host.clientWidth < 200) {
            requestAnimationFrame { _ -> createOnceMounted() }
            return
        }
        table = ListTable(host, options())
    }

    private fun options() = listTableOptions {
        columns(
            textColumn("name", current.colName, 150.0),
            textColumn("role", current.colRole, 180.0),
            textColumn("city", current.colCity, 140.0),
            textColumn("score", current.colScore, 100.0),
        )
        records(*people(language).toRecords())
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    }

    override fun applyTranslation(lang: Lang) {
        current = basicTexts[lang]
        language = lang
        setTitle(current.title)
        setSummary(current.summary)
        texts.apply(lang)
        // The column headers are baked into the table at construction, so a language switch rebuilds
        // it; the table is a canvas, there is no header node to rewrite.
        table?.release()
        table = null
        host.replaceChildren()
        createOnceMounted()
    }

    companion object : BasicPageDefaultReference() {

        private val basicEnglish: BasicTexts = BasicTexts(
            title = "Basic table",
            summary = "Four text columns, one frozen column, adaptive width — everything built with the hand-written " +
                "DSL on top of the generated declarations.",
            tableHeading = "List table",
            hint = "Drag the header edge to resize a column; the first column is frozen, so it stays while the rest " +
                "scrolls sideways.",
            colName = "Name",
            colRole = "Role",
            colCity = "City",
            colScore = "Score",
        )
        private val basicChinese: BasicTexts = BasicTexts(
            title = "基础表格",
            summary = "四个文本列、一列冻结、宽度自适应 —— 全部用生成声明之上的手写 DSL 构造。",
            tableHeading = "列表",
            hint = "拖动表头边缘可以改列宽；第一列冻结，横向滚动时它不动。",
            colName = "姓名",
            colRole = "方向",
            colCity = "城市",
            colScore = "得分",
        )
        private val basicTexts: Translations<BasicTexts> = texts(
            Langs.EN to basicEnglish,
            Langs.ZH_HANS to basicChinese,
        )
    }
}
