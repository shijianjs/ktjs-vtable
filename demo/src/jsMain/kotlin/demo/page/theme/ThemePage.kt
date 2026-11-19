package demo.page.theme

import demo.page.samples.people
import demo.page.samples.toRecords
import io.github.shijianjs.ktjs.demo.i18n.Binder
import io.github.shijianjs.ktjs.demo.i18n.Lang
import io.github.shijianjs.ktjs.demo.i18n.Langs
import io.github.shijianjs.ktjs.demo.i18n.Translations
import io.github.shijianjs.ktjs.demo.i18n.texts
import io.github.shijianjs.ktjs.demo.nav.Page
import io.github.shijianjs.ktjs.demo.page.exampleBox
import io.github.shijianjs.ktjs.demo.page.newPage
import io.github.shijianjs.ktjs.demo.page.row
import io.github.shijianjs.ktjs.demo.page.sectionBlock
import io.github.shijianjs.ktjs.dom.element.inlineStyle
import io.github.shijianjs.ktjs.dom.element.invoke
import io.github.shijianjs.ktjs.vaadin.button.ButtonElement
import io.github.shijianjs.ktjs.vaadin.button.createButton
import io.github.shijianjs.ktjs.vtable.BaseTable
import io.github.shijianjs.ktjs.vtable.ITableThemeDefine
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.TableTheme
import io.github.shijianjs.ktjs.vtable.dsl.VTable
import io.github.shijianjs.ktjs.vtable.dsl.columns
import io.github.shijianjs.ktjs.vtable.dsl.listTableOptions
import io.github.shijianjs.ktjs.vtable.dsl.records
import io.github.shijianjs.ktjs.vtable.dsl.textColumn
import kotlin.js.unsafeCast
import web.animations.requestAnimationFrame
import web.cssom.px
import web.dom.clickEvent
import web.events.addHandler
import web.html.HTMLElement
import web.html.HtmlTagName

/** Every string this page shows, in one language. */
private class ThemeTexts(
    val title: String,
    val summary: String,
    val tableHeading: String,
    val hint: String,
    /** The button labels, in the order of [THEMES]. */
    val labels: List<String>,
    val colName: String,
    val colRole: String,
    val colScore: String,
)

private val themeEnglish: ThemeTexts = ThemeTexts(
    title = "Themes",
    summary = "Themes are tables of design tokens: the built-in ones ship with the package and the wrapper " +
        "resolves them by name.",
    tableHeading = "Design tokens",
    hint = "Pick a theme: the table is rebuilt with that theme's tokens; the rows stay the same.",
    labels = listOf("Default", "Dark", "Bright"),
    colName = "Name",
    colRole = "Role",
    colScore = "Score",
)

private val themeChinese: ThemeTexts = ThemeTexts(
    title = "主题",
    summary = "主题是一组设计变量；内置主题随包发布，封装层按名字取用。",
    tableHeading = "设计变量",
    hint = "选一个主题：表格会用该主题的设计变量重建，行数据不变。",
    labels = listOf("默认", "深色", "明亮"),
    colName = "姓名",
    colRole = "方向",
    colScore = "得分",
)

private val themeTexts: Translations<ThemeTexts> = texts(
    Langs.EN to themeEnglish,
    Langs.ZH_HANS to themeChinese,
)

/** The upstream theme names, in the order of the toolbar buttons. */
private val THEMES: List<String> = listOf("default", "dark", "bright")

/**
 * The themes page: one table, three built-in themes, rebuilt on demand.
 */
internal class ThemePage : Page {
    private val page = newPage()

    private val texts = Binder(themeTexts)

    private var current: ThemeTexts = themeEnglish

    private var language: Lang = Langs.EN

    private var themeName: String = "default"

    private var table: BaseTable? = null

    private val host: HTMLElement = HtmlTagName.div {
        setAttribute("data-table", "theme")
        setAttribute("data-theme", themeName)
        inlineStyle.apply {
            height = 320.px
        }
    }

    private val buttons: List<ButtonElement> = THEMES.map { name ->
        createButton { setAttribute("data-theme-action", name) }
    }

    override val node get() = page

    init {
        val section = sectionBlock()
        texts.bind(section.title, { it.tableHeading })
        texts.bind(section.hint, { it.hint })
        section.body.append(
            row(*buttons.toTypedArray()),
            exampleBox(null, host),
        )
        page.body.append(section.root)

        buttons.forEachIndexed { index, button ->
            button.clickEvent.addHandler { select(THEMES[index]) }
        }

        createOnceMounted()
    }

    /** Switches the theme and rebuilds the canvas: a theme is resolved when the table is constructed. */
    private fun select(name: String) {
        if (name == themeName) return
        themeName = name
        host.setAttribute("data-theme", themeName)
        table?.release()
        table = null
        host.replaceChildren()
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
            textColumn("role", current.colRole, 180.0),
            textColumn("score", current.colScore, 100.0),
        )
        records(*people(language).toRecords())
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
        this.theme = VTable.themeOr(themeName).unsafeCast<ITableThemeDefine>()
    }

    override fun applyTranslation(lang: Lang) {
        current = themeTexts[lang]
        language = lang
        page.setTitle(current.title)
        page.setSummary(current.summary)
        texts.apply(lang)
        buttons.forEachIndexed { index, button ->
            button.textContent = current.labels.getOrElse(index) { "" }
        }
        table?.release()
        table = null
        host.replaceChildren()
        createOnceMounted()
    }
}
