package demo.page.edit

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
import io.github.shijianjs.ktjs.dom.webcomponent.CustomElementReferenceAdapter
import io.github.shijianjs.ktjs.vtable.BaseTable
import io.github.shijianjs.ktjs.vtable.IEditor
import io.github.shijianjs.ktjs.vtable.InputEditor
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.dsl.columns
import io.github.shijianjs.ktjs.vtable.dsl.listTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.row
import io.github.shijianjs.ktjs.vtable.dsl.textColumn
import io.github.shijianjs.ktjs.vtable.editor
import kotlin.js.JsAny
import kotlin.js.unsafeCast
import web.animations.requestAnimationFrame
import web.cssom.px
import web.html.HTMLElement
import web.html.HtmlTagName

/** Every string this page shows, in one language. */
private class EditTexts(
    val title: String,
    val summary: String,
    val tableHeading: String,
    val hint: String,
    val colName: String,
    val colRole: String,
    val colCity: String,
)

private val editEnglish: EditTexts = EditTexts(
    title = "Editable cells",
    summary = "Columns with an editor open an input when you double-click a cell: the upstream " +
        "@visactor/vtable-editors input editor, registered by name.",
    tableHeading = "Edit in place",
    hint = "Double-click a role or city cell to edit it; the name column stays read-only.",
    colName = "Name",
    colRole = "Role",
    colCity = "City",
)

private val editChinese: EditTexts = EditTexts(
    title = "可编辑单元格",
    summary = "带编辑器的列在双击单元格时弹出输入框：就是上游 @visactor/vtable-editors 的输入编辑器，按名字注册。",
    tableHeading = "原地编辑",
    hint = "双击方向或城市单元格即可编辑；姓名列是只读的。",
    colName = "姓名",
    colRole = "方向",
    colCity = "城市",
)

private val editTexts: Translations<EditTexts> = texts(
    Langs.EN to editEnglish,
    Langs.ZH_HANS to editChinese,
)

/**
 * The editable table: two columns carry an editor, the frozen name column does not.
 */
internal class EditPage : DemoPage() {

    private val texts = Binder(editTexts)

    private var current: EditTexts = editEnglish

    private var language: Lang = Langs.EN

    private var table: BaseTable? = null

    private val host: HTMLElement = HtmlTagName.div {
        setAttribute("data-table", "edit")
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

        // One global registration by name: the column then refers to the editor as `"input"`.
        editor("input", InputEditor(null).unsafeCast<IEditor>())

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
            textColumn("name", current.colName, 150.0),
            textColumn("role", current.colRole, 180.0) {
                this.editor = "input".unsafeCast<JsAny>()
            },
            textColumn("city", current.colCity, 140.0) {
                this.editor = "input".unsafeCast<JsAny>()
            },
        )
        records(*people(language).toRecords())
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    }

    override fun applyTranslation(lang: Lang) {
        current = editTexts[lang]
        language = lang
        setTitle(current.title)
        setSummary(current.summary)
        texts.apply(lang)
        table?.release()
        table = null
        host.replaceChildren()
        createOnceMounted()
    }

    companion object : CustomElementReferenceAdapter<EditPage>(EditPage::class.js, "vtable-edit-page")
}
