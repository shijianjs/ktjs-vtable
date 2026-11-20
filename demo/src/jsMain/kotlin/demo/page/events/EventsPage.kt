package demo.page.events

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
import io.github.shijianjs.ktjs.demo.page.EventLog
import io.github.shijianjs.ktjs.dom.element.inlineStyle
import io.github.shijianjs.ktjs.dom.element.invoke
import io.github.shijianjs.ktjs.dom.webcomponent.CustomElementReferenceAdapter
import io.github.shijianjs.ktjs.vtable.BaseTable
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.dsl.columns
import io.github.shijianjs.ktjs.vtable.dsl.listTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.textColumn
import kotlin.js.JsAny
import kotlin.js.unsafeCast
import web.animations.requestAnimationFrame
import web.cssom.px
import web.html.HTMLElement
import web.html.HtmlTagName

private val eventsEnglish: EventsTexts = EventsTexts(
    title = "Events",
    summary = "Table events arrive as plain JavaScript arguments: `table.on(\"click_cell\") { args -> … }` " +
        "hands over the coordinates of the cell that was clicked.",
    tableHeading = "Click a cell",
    hint = "Click any cell: the log below keeps the six newest clicks, newest last.",
    colName = "Name",
    colCity = "City",
    colScore = "Score",
    placeholder = "No clicks yet.",
    hit = "click_cell row {row} col {col}",
)

private val eventsChinese: EventsTexts = EventsTexts(
    title = "事件",
    summary = "表格事件以普通 JavaScript 参数传入：`table.on(\"click_cell\") { args -> … }` 给出被点击单元格的坐标。",
    tableHeading = "点一下单元格",
    hint = "点击任意单元格：下面的日志保留最近六次点击，最新的在最后。",
    colName = "姓名",
    colCity = "城市",
    colScore = "得分",
    placeholder = "还没有点击。",
    hit = "click_cell 行 {row} 列 {col}",
)

private val eventsTexts: Translations<EventsTexts> = texts(
    Langs.EN to eventsEnglish,
    Langs.ZH_HANS to eventsChinese,
)

/** The upstream event payload: only the coordinates this page prints are typed. */
private external interface ClickedCell {
    var row: Double
    var col: Double
}

/**
 * The events page: the table plus a log of the cells that were clicked.
 */
internal class EventsPage : DemoPage() {

    private val texts = Binder(eventsTexts)

    private var current: EventsTexts = eventsEnglish

    private var language: Lang = Langs.EN

    private var table: BaseTable? = null

    private val host: HTMLElement = HtmlTagName.div {
        setAttribute("data-table", "events")
        inlineStyle.apply {
            height = 240.px
        }
    }

    private val log = EventLog.NAME { show(capacity = 6) }

    init {
        val section = SectionBlock.NAME { show() }
        texts.bind(section.heading, { it.tableHeading })
        texts.bind(section.hint, { it.hint })
        section.body.append(exampleBox(null, host), log.root)
        body.append(section.root)
        log.root.setAttribute("data-log", "")

        createOnceMounted()
    }

    private fun createOnceMounted() {
        if (table != null) return
        if (!host.isConnected || host.clientWidth < 200) {
            requestAnimationFrame { _ -> createOnceMounted() }
            return
        }
        val created = ListTable(host, options())
        table = created
        created.on("click_cell".unsafeCast<JsAny>()) { args ->
            val cell = args.unsafeCast<ClickedCell>()
            log.add(
                current.hit
                    .replace("{row}", cell.row.toInt().toString())
                    .replace("{col}", cell.col.toInt().toString()),
            )
            null.unsafeCast<JsAny>()
        }
    }

    private fun options() = listTableOptions {
        columns(
            textColumn("name", current.colName, 150.0),
            textColumn("city", current.colCity, 140.0),
            textColumn("score", current.colScore, 100.0),
        )
        records(*people(language).toRecords())
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    }

    override fun applyTranslation(lang: Lang) {
        current = eventsTexts[lang]
        language = lang
        setTitle(current.title)
        setSummary(current.summary)
        texts.apply(lang)
        // The headers are inside the canvas, so the table is rebuilt; the log is the page's own and
        // keeps what it has, in whatever language those lines were written.
        table?.release()
        table = null
        host.replaceChildren()
        createOnceMounted()
    }

    companion object : CustomElementReferenceAdapter<EventsPage>(EventsPage::class.js, "vtable-events-page")
}
