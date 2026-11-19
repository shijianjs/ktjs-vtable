package demo.e2e

import com.microsoft.playwright.Locator
import com.microsoft.playwright.Page
import com.microsoft.playwright.junit.UsePlaywright
import com.microsoft.playwright.options.WaitUntilState
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import org.junitpioneer.jupiter.RetryingTest

/**
 * Smoke checks for the demo page: the shell comes from the kit, each page paints a VTable canvas into
 * its sized host, the theme buttons rebuild the table under different tokens, clicks land in the log,
 * and the language switch relabels the page.
 *
 * The shell lives in a shadow root; Playwright's CSS pierces shadow boundaries, `document.querySelector`
 * does not — so the waits use locators instead of `waitForFunction`.
 */
@UsePlaywright(DemoOptions::class)
class DemoPageTest {
    @RetryingTest(maxAttempts = 2)
    fun `page renders the shell, the logo and an overview`(page: Page) {
        openHome(page)

        assertTrue(page.title().contains("ktjs-vtable"), "title: ${page.title()}")
        assertTrue(page.locator("img.layout__logo").isVisible(), "the shell shows the project logo")
        assertEquals("Overview", page.locator("ktjs-demo-page h1").textContent())
        assertTrue(
            page.locator("vaadin-side-nav-item[data-route='basic']").isVisible(),
            "the sidebar lists the table routes",
        )
    }

    @RetryingTest(maxAttempts = 2)
    fun `the basic table paints a canvas into its host`(page: Page) {
        openHome(page)
        goTo(page, "basic")

        val canvas = page.locator("[data-table=basic] canvas").first()
        canvas.waitFor()
        assertTrue(
            (canvas.evaluate("(node) => node.width") as Number).toDouble() > 0,
            "the canvas has a backing store width",
        )
    }

    @RetryingTest(maxAttempts = 2)
    fun `the theme buttons rebuild the table under another theme`(page: Page) {
        openHome(page)
        goTo(page, "theme")

        page.locator("[data-theme-action='dark']").click()
        assertEquals("dark", page.locator("[data-table=theme]").getAttribute("data-theme"))
        page.locator("[data-table=theme] canvas").first().waitFor()
    }

    @RetryingTest(maxAttempts = 2)
    fun `clicking a cell reports the coordinates`(page: Page) {
        openHome(page)
        goTo(page, "events")

        val canvas = page.locator("[data-table=events] canvas").first()
        canvas.click()
        val line = page.locator("[data-log]").getByText("click_cell").first()
        line.waitFor()
        assertTrue(line.textContent().contains("row"), "event log: ${line.textContent()}")
    }

    @RetryingTest(maxAttempts = 2)
    fun `the language switch relabels the page, the menu and the buttons`(page: Page) {
        openHome(page)
        goTo(page, "theme")

        page.locator("[data-menu='lang']").first().click()
        page.locator("[data-action='lang:zh-Hans']").click()

        assertEquals("zh-Hans", page.locator("html").getAttribute("lang"))
        assertEquals("主题", page.locator("ktjs-demo-page h1").textContent())
        assertEquals("深色", page.locator("[data-theme-action='dark']").textContent())
        assertEquals("基础表格", page.locator("vaadin-side-nav-item[data-route='basic']").textContent())
        // The headers are inside the canvas, so the table is rebuilt; the canvas is back a frame later.
        page.locator("[data-table=theme] canvas").first().waitFor()
    }

    @RetryingTest(maxAttempts = 2)
    fun `page logs no console errors or failed requests`(page: Page) {
        val consoleErrors = mutableListOf<String>()
        val failedRequests = mutableListOf<String>()
        page.onConsoleMessage { message -> if (message.type() == "error") consoleErrors += message.text() }
        page.onRequestFailed { request -> failedRequests += "${request.url()} ${request.failure()}" }

        openHome(page)
        goTo(page, "theme")
        page.locator("[data-theme-action='bright']").click()

        assertTrue(consoleErrors.isEmpty(), "console errors: $consoleErrors")
        assertTrue(failedRequests.isEmpty(), "failed requests: $failedRequests")
    }

    private fun goTo(page: Page, route: String) {
        page.locator("vaadin-side-nav-item[data-route='$route']").click()
        page.locator("[data-table=$route] canvas").first()
            .waitFor(Locator.WaitForOptions().setTimeout(20_000.0))
    }

    private fun openHome(page: Page) {
        page.navigate("/", Page.NavigateOptions().setWaitUntil(WaitUntilState.NETWORKIDLE))
    }
}
