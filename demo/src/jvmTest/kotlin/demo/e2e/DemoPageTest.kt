package demo.e2e

import com.microsoft.playwright.Page
import com.microsoft.playwright.junit.UsePlaywright
import com.microsoft.playwright.options.WaitUntilState
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import org.junitpioneer.jupiter.RetryingTest

/**
 * Smoke checks for the demo page: it must load the bundle, apply its stylesheet, render a VTable
 * canvas per demo, switch language, and produce no console errors or failed requests.
 */
@UsePlaywright(DemoOptions::class)
class DemoPageTest {
    @RetryingTest(maxAttempts = 2)
    fun `page renders the project chrome`(page: Page) {
        openPage(page)

        assertTrue(page.title().contains("ktjs-vtable"), "title: ${page.title()}")
        assertEquals("ktjs-vtable", page.locator("h1").textContent())

        // The logo is copied in from the site's static files by the `brandAssets` task.
        assertTrue(page.locator("img.logo").isVisible(), "the demo serves the project logo")

        val display = page.locator(".page").evaluate("(node) => getComputedStyle(node).display") as String
        assertTrue(display != "contents", "the stylesheet applies to .page (display = $display)")
    }

    @RetryingTest(maxAttempts = 2)
    fun `the first demo draws a table onto a canvas`(page: Page) {
        openPage(page)

        val host = page.locator(".table-host").first()
        assertTrue(host.isVisible(), "the demo reserves a sized element for the table")

        val canvas = host.locator("canvas").first()
        canvas.waitFor()
        assertTrue(canvas.isVisible(), "VTable renders its grid into a canvas")
        assertTrue(
            (canvas.evaluate("(node) => node.width") as Number).toDouble() > 0,
            "the canvas has a backing store width",
        )
    }

    @RetryingTest(maxAttempts = 2)
    fun `switching the language relabels the navigation and the stage`(page: Page) {
        openPage(page)

        assertEquals("Basic table", page.locator(".toc-item").first().textContent())
        page.getByRole(com.microsoft.playwright.options.AriaRole.BUTTON, Page.GetByRoleOptions().setName("中文"))
            .click()

        assertEquals("基础表格", page.locator(".toc-item").first().textContent())
        assertEquals("基础列表", page.locator(".stage h2").textContent())
        assertTrue(page.locator(".table-host canvas").first().isVisible(), "the table survives the switch")
    }

    @RetryingTest(maxAttempts = 2)
    fun `clicking a cell reports the event`(page: Page) {
        openPage(page)

        page.locator(".toc-item").last().click()
        val canvas = page.locator(".table-host canvas").first()
        canvas.waitFor()
        canvas.click()

        val entry = page.locator(".log li").first()
        entry.waitFor()
        assertTrue(entry.textContent().contains("click_cell"), "event log: ${entry.textContent()}")
    }

    @RetryingTest(maxAttempts = 2)
    fun `page logs no console errors or failed requests`(page: Page) {
        val consoleErrors = mutableListOf<String>()
        val failedRequests = mutableListOf<String>()
        page.onConsoleMessage { message ->
            if (message.type() == "error") consoleErrors += message.text()
        }
        page.onRequestFailed { request ->
            failedRequests += "${request.url()} ${request.failure()}"
        }

        openPage(page)

        assertTrue(consoleErrors.isEmpty(), "console errors: $consoleErrors")
        assertTrue(failedRequests.isEmpty(), "failed requests: $failedRequests")
    }

    private fun openPage(page: Page) {
        page.navigate("/", Page.NavigateOptions().setWaitUntil(WaitUntilState.NETWORKIDLE))
    }
}
