package demo

import demo.page.basic.newBasicPage
import demo.page.edit.newEditPage
import demo.page.events.newEventsPage
import demo.page.group.newGroupPage
import demo.page.overview.newOverviewPage
import demo.page.pivot.newPivotPage
import demo.page.theme.newThemePage
import io.github.shijianjs.ktjs.demo.nav.DemoMenu
import io.github.shijianjs.ktjs.demo.nav.Entry
import io.github.shijianjs.ktjs.demo.nav.Group

/** The VTable version this demo is built against; the navbar shows it under the site name. */
const val SITE_VERSION: String = "1.26.8"

/** The documentation site. */
const val DOCS_URL: String = "https://shijianjs.github.io/ktjs-vtable/"

/** Dokka reference assembled by `pagesSite` next to the demo. */
const val API_URL: String = "https://shijianjs.github.io/ktjs-vtable/api/"

/** Source repository, linked from the navbar's link menu. */
const val SOURCE_URL: String = "https://github.com/shijianjs/ktjs-vtable"

internal val START: Group = Group("start", "lucide:sparkles")

internal val TABLES: Group = Group("tables", "lucide:table")

internal val INTERACTION: Group = Group("interaction", "lucide:mouse-pointer-click")

/**
 * The site: one entry per page.
 *
 * Adding a page means adding one entry here and its titles in [siteTexts].
 */
fun siteMenu(): DemoMenu = DemoMenu(
    listOf(
        Entry("overview", START) { newOverviewPage() },
        Entry("basic", TABLES) { newBasicPage() },
        Entry("group", TABLES) { newGroupPage() },
        Entry("pivot", TABLES) { newPivotPage() },
        Entry("edit", INTERACTION) { newEditPage() },
        Entry("theme", INTERACTION) { newThemePage() },
        Entry("events", INTERACTION) { newEventsPage() },
    ),
)
