package demo.page.events

import io.github.shijianjs.ktjs.dom.element.invoke

/** Every string this page shows, in one language. */
internal class EventsTexts(
    val title: String,
    val summary: String,
    val tableHeading: String,
    val hint: String,
    val colName: String,
    val colCity: String,
    val colScore: String,
    val placeholder: String,
    /** The log line's template: `{row}` and `{col}` are the click's coordinates. */
    val hit: String,
)
