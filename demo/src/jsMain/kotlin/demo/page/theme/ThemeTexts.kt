package demo.page.theme

import io.github.shijianjs.ktjs.dom.element.invoke

/** Every string this page shows, in one language. */
internal class ThemeTexts(
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
