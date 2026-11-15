package io.github.shijianjs.ktjs.vtable

import io.github.shijianjs.ktjs.vtable.dsl.*
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlin.js.JsAny
import kotlin.js.unsafeCast
import js.objects.unsafeJso
import web.dom.document
import web.html.HTMLElement
import web.html.HtmlTagName

/** The pivot options take dimension this object; only the fields a test needs are typed. */
private external interface TestPivotDimension {
    var field: String
    var title: String?
}

/** The same for indicators: the field, the label and the upstream aggregation name. */
private external interface TestPivotIndicator {
    var field: String
    var title: String?
    var aggregationType: String?
}

/**
 * Smoke tests against the real upstream packages: every case builds a table in a sized container,
 * the way a browser application would. A table measures its container, so the host is given an
 * explicit width and height before the constructor runs.
 */
class VTableTest {
    private fun host(): HTMLElement {
        val element = document.createElement(HtmlTagName.div).unsafeCast<HTMLElement>()
        element.setAttribute("style", "width: 640px; height: 400px;")
        document.body?.append(element)
        return element
    }

    private fun cleanup(vararg hosts: HTMLElement) {
        hosts.forEach { it.remove() }
    }

    @Test
    fun listTableRendersTheRecordsItWasGiven() {
        val host = host()
        val table = ListTable(host, listTableOptions {
            columns(
                textColumn("name", "Name", 160.0),
                textColumn("role", "Role", 160.0),
            )
            records(
                row("name" to "Ada Lovelace", "role" to "Analytical Engine"),
                row("name" to "Grace Hopper", "role" to "Compiler"),
                row("name" to "Katherine Johnson", "role" to "Orbital mechanics"),
            )
            frozenColCount = 1.0
            widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
        })

        assertEquals(3.0, table.typedRecordsCount, "every row built by the DSL reaches the table")
        assertEquals(2, table.columns.size, "two columns were handed to the constructor")

        table.release()
        cleanup(host)
    }

    @Test
    fun groupColumnKeepsItsChildren() {
        val options = listTableOptions {
            columns(
                textColumn("name", "Name", 120.0),
                groupColumn(
                    "2025",
                    textColumn("q1", "Q1", 80.0),
                    textColumn("q2", "Q2", 80.0),
                ),
            )
        }

        assertEquals(2, options.columns?.size, "a group is one top-level column")
        val group = options.columns?.get(1)
        assertEquals(2, group?.unsafeCast<GroupColumnDefine>()?.columns?.size, "the group keeps both children")
    }

    @Test
    fun themesResolveByNameAndFallBack() {
        val host = host()
        val table = ListTable(host, listTableOptions {
            columns(textColumn("name", "Name", 160.0))
            records(row("name" to "Ada"))
            theme = VTable.themeOr("dark").unsafeCast<ITableThemeDefine>()
        })

        assertNotNull(VTable.theme("dark"), "a built-in theme is reachable by name")
        assertNotNull(VTable.theme("default"))
        assertNull(VTable.theme("no-such-theme"), "an unknown name resolves to null")
        assertEquals(
            VTable.theme("default")?.unsafeCast<JsAny>(),
            VTable.themeOr("no-such-theme").unsafeCast<JsAny>(),
            "themeOr falls back to the default theme",
        )

        table.release()
        cleanup(host)
    }

    @Test
    fun literalConstantsKeepTheUpstreamStrings() {
        assertEquals("adaptive", StandardOrAdaptiveOrAutoWidths.adaptive.unsafeCast<String>())
        assertEquals("standard", StandardOrAdaptiveOrAutoWidths.standard.unsafeCast<String>())
        assertEquals("autoWidth", StandardOrAdaptiveOrAutoWidths.autoWidth.unsafeCast<String>())
    }

    @Test
    fun editorIsRegisteredUnderTheNameAColumnUses() {
        val inputEditor = InputEditor(null)
        editor("inline-input", inputEditor.unsafeCast<IEditor>())

        // The registry returns the same object it stored, so a column named "inline-input" gets it.
        val registered = io.github.shijianjs.ktjs.vtable.editor("inline-input", null)
        assertTrue(registered.unsafeCast<InputEditor>() === inputEditor)
    }

    @Test
    fun pivotTableAcceptsDimensionsAndIndicators() {
        val host = host()
        val options = pivotTableOptions {
            records(
                row("region" to "East", "category" to "A", "sales" to 120.0),
                row("region" to "West", "category" to "A", "sales" to 150.0),
            )
            rows = arrayOf<JsAny>(unsafeJso<TestPivotDimension> { field = "region"; title = "Region" })
            columns = arrayOf<JsAny>(unsafeJso<TestPivotDimension> { field = "category"; title = "Category" })
            indicators = arrayOf<JsAny>(
                unsafeJso<TestPivotIndicator> {
                    field = "sales"
                    title = "Sales"
                    aggregationType = "SUM"
                },
            )
        }
        val table = PivotTable(host, options)

        assertNotNull(table, "the pivot table constructs from the typed options")

        table.release()
        cleanup(host)
    }
}
