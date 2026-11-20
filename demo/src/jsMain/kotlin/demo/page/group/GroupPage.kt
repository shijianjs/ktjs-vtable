package demo.page.group

import io.github.shijianjs.ktjs.demo.page.DemoPage
import io.github.shijianjs.ktjs.demo.i18n.Binder
import io.github.shijianjs.ktjs.demo.i18n.Lang
import io.github.shijianjs.ktjs.demo.i18n.Langs
import io.github.shijianjs.ktjs.demo.i18n.Translations
import io.github.shijianjs.ktjs.demo.i18n.texts
import io.github.shijianjs.ktjs.demo.page.Blocks.exampleBox
import io.github.shijianjs.ktjs.demo.page.SectionBlock
import io.github.shijianjs.ktjs.dom.element.inlineStyle
import io.github.shijianjs.ktjs.dom.element.invoke
import io.github.shijianjs.ktjs.dom.webcomponent.CustomElementReferenceAdapter
import io.github.shijianjs.ktjs.vtable.BaseTable
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.dsl.columns
import io.github.shijianjs.ktjs.vtable.dsl.groupColumn
import io.github.shijianjs.ktjs.vtable.dsl.listTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.row
import io.github.shijianjs.ktjs.vtable.dsl.textColumn
import web.animations.requestAnimationFrame
import web.cssom.px
import web.html.HTMLElement
import web.html.HtmlTagName

/**
 * The grouped-header table: two group headers, five score columns below them.
 */
internal class GroupPage : DemoPage() {

    private val texts = Binder(groupTexts)

    private var current: GroupTexts = groupEnglish

    private var table: BaseTable? = null

    private val host: HTMLElement = HtmlTagName.div {
        setAttribute("data-table", "group")
        inlineStyle.apply {
            height = 240.px
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
            textColumn("name", current.colName, 130.0),
            groupColumn(
                current.halfOne,
                textColumn("q1", "Q1", 90.0),
                textColumn("q2", "Q2", 90.0),
                textColumn("q3", "Q3", 90.0),
            ),
            groupColumn(
                current.halfTwo,
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

    override fun applyTranslation(lang: Lang) {
        current = groupTexts[lang]
        setTitle(current.title)
        setSummary(current.summary)
        texts.apply(lang)
        // The group titles are part of the column tree, so the canvas is rebuilt rather than patched.
        table?.release()
        table = null
        host.replaceChildren()
        createOnceMounted()
    }

    companion object : CustomElementReferenceAdapter<GroupPage>(GroupPage::class.js, "vtable-group-page") {

        private val groupEnglish: GroupTexts = GroupTexts(
            title = "Grouped header",
            summary = "Columns nest: a group header holds the quarterly score columns underneath it, and hovering a " +
                "cell highlights its whole group.",
            tableHeading = "Nested columns",
            hint = "Q1–Q3 sit under the first half-year header, Q4–Q5 under the second: `groupColumn(title, …)` is " +
                "the whole API.",
            colName = "Name",
            halfOne = "2025 H1",
            halfTwo = "2025 H2",
        )
        private val groupChinese: GroupTexts = GroupTexts(
            title = "分组表头",
            summary = "列可以嵌套：一个分组表头下面挂若干季度分数列，鼠标停在单元格上时整组一起高亮。",
            tableHeading = "嵌套的列",
            hint = "Q1–Q3 挂在上半年表头下，Q4–Q5 挂在下半年：`groupColumn(title, …)` 就是全部 API。",
            colName = "姓名",
            halfOne = "2025 上半年",
            halfTwo = "2025 下半年",
        )
        private val groupTexts: Translations<GroupTexts> = texts(
            Langs.EN to groupEnglish,
            Langs.ZH_HANS to groupChinese,
        )
    }
}
