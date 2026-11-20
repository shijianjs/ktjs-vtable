package demo.page.pivot

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
import io.github.shijianjs.ktjs.vtable.PivotTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.dsl.pivotTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.row
import js.objects.unsafeJso
import kotlin.js.JsAny
import web.animations.requestAnimationFrame
import web.cssom.px
import web.html.HTMLElement
import web.html.HtmlTagName

private val pivotEnglish: PivotTexts = PivotTexts(
    title = "Pivot table",
    summary = "Rows and columns are dimensions, indicators are aggregated values: the same flat records " +
        "arranged by region and category.",
    tableHeading = "Aggregated view",
    hint = "Drag a row-header cell to reorder the dimensions; the indicators are summed, as the " +
        "`aggregationType` says.",
    dimRegion = "Region",
    dimCategory = "Category",
    indSales = "Sales",
    indProfit = "Profit",
    east = "East",
    west = "West",
    categoryA = "Category A",
    categoryB = "Category B",
)

private val pivotChinese: PivotTexts = PivotTexts(
    title = "透视表",
    summary = "行与列是维度，指标是聚合后的数值：同一批平坦记录，按区域与类别重排。",
    tableHeading = "聚合视图",
    hint = "拖动行表头单元格可以调整维度顺序；指标按 `aggregationType` 求和。",
    dimRegion = "区域",
    dimCategory = "类别",
    indSales = "销售额",
    indProfit = "利润",
    east = "华东",
    west = "西部",
    categoryA = "类别 A",
    categoryB = "类别 B",
)

private val pivotTexts: Translations<PivotTexts> = texts(
    Langs.EN to pivotEnglish,
    Langs.ZH_HANS to pivotChinese,
)

/** Upstream pivot options take dimension/indicator objects; only the fields the demo uses are typed. */
private external interface PivotDimension {
    var field: String
    var title: String?
}

private external interface PivotIndicator {
    var field: String
    var title: String?
    var aggregationType: String?
}

/**
 * The pivot table: two indicators over two dimensions.
 */
internal class PivotPage : DemoPage() {

    private val texts = Binder(pivotTexts)

    private var current: PivotTexts = pivotEnglish

    private var table: BaseTable? = null

    private val host: HTMLElement = HtmlTagName.div {
        setAttribute("data-table", "pivot")
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
        table = PivotTable(host, options())
    }

    private fun options() = pivotTableOptions {
        records(
            row("region" to current.east, "category" to current.categoryA, "sales" to 120.0, "profit" to 30.0),
            row("region" to current.east, "category" to current.categoryB, "sales" to 90.0, "profit" to 18.0),
            row("region" to current.west, "category" to current.categoryA, "sales" to 150.0, "profit" to 42.0),
            row("region" to current.west, "category" to current.categoryB, "sales" to 60.0, "profit" to 12.0),
        )
        rows = arrayOf<JsAny>(unsafeJso<PivotDimension> { field = "region"; title = current.dimRegion })
        columns = arrayOf<JsAny>(unsafeJso<PivotDimension> { field = "category"; title = current.dimCategory })
        indicators = arrayOf<JsAny>(
            unsafeJso<PivotIndicator> {
                field = "sales"
                title = current.indSales
                aggregationType = "SUM"
            },
            unsafeJso<PivotIndicator> {
                field = "profit"
                title = current.indProfit
                aggregationType = "SUM"
            },
        )
        widthMode = StandardOrAdaptiveOrAutoWidths.standard
    }

    override fun applyTranslation(lang: Lang) {
        current = pivotTexts[lang]
        setTitle(current.title)
        setSummary(current.summary)
        texts.apply(lang)
        // Dimension titles and the record values are baked in at construction: rebuild the canvas.
        table?.release()
        table = null
        host.replaceChildren()
        createOnceMounted()
    }

    companion object : CustomElementReferenceAdapter<PivotPage>(PivotPage::class.js, "vtable-pivot-page")
}
