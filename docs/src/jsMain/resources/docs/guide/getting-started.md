---
sidebar_position: 2
title: Getting started
---

# Getting started

## Requirements

- JDK 21 or newer; the Gradle wrapper is checked in (9.4.1).
- Node and npm are downloaded and driven by the Kotlin Gradle plugin — there is no `npm install` step
  to remember, and `kotlin.js.yarn=false` keeps npm as the package manager.
- Chromium is downloaded by Playwright the first time a browser test runs.

## Install

```kotlin
dependencies {
    implementation("io.github.shijianjs:ktjs-vtable:1.26.8-kt.1")
}
```

The module declares `@visactor/vtable` and `@visactor/vtable-editors` as npm dependencies, so a
consumer does not add them separately. Both are MIT-licensed; nothing else from VTable is pulled in.

## A first table

```kotlin
import io.github.shijianjs.ktjs.vtable.ListTable
import io.github.shijianjs.ktjs.vtable.StandardOrAdaptiveOrAutoWidths
import io.github.shijianjs.ktjs.vtable.dsl.*
import web.cssom.ClassName
import web.dom.document
import web.html.HtmlTagName

fun main() {
    val container = document.createElement(HtmlTagName.div).apply {
        className = ClassName("table-host")
    }
    document.body.append(container)

    ListTable(container, listTableOptions {
        columns(
            textColumn("name", "Name", 150.0),
            textColumn("role", "Role", 160.0),
            textColumn("city", "City", 130.0),
        )
        records(
            row("name" to "Ada Lovelace", "role" to "Analytical engine", "city" to "London"),
            row("name" to "Grace Hopper", "role" to "Compiler", "city" to "New York"),
        )
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    })
}
```

The size comes from CSS, because the element must be sized before the table is constructed:

```css
.table-host {
    width: 100%;
    height: 460px;
}
```

Two details matter:

- **The container needs a size before the table is constructed.** VTable measures its container; a
  zero-height element produces a zero-height canvas. `ListTable` appends its own `<div>` and `<canvas>`
  inside the element you pass.
- **`ListTable(options)` also works** when the options object carries `container`. The two-argument form
  is the one the demo uses.

## Build, test, publish

```bash
./gradlew build                    # compile, Detekt, browser tests
./gradlew :ktjs-vtable:jsBrowserTest
./gradlew :demo:e2eTest            # Playwright against the bundled demo page
./gradlew :docs:docusaurusBuild    # the documentation site
./gradlew pagesSite                # documentation at /, demo at /demo/, Dokka at /api/
```

`build` does not run the demo's end-to-end suite or assemble the Pages site: both need a browser and
are part of CI as separate steps.

## Develop

```bash
./gradlew :docs:docusaurusStart    # dev server for this site
./gradlew :demo:jsBrowserRun       # dev server for the demo page
```

Docusaurus watches the site directory, so Markdown edits reload; Kotlin changes need a first
`./gradlew :docs:docusaurusSite`, because the site imports the compiled module.

## The lock file

npm dependencies are resolved once for the whole workspace and pinned in
`kotlin-js-store/package-lock.json`. After adding or upgrading an npm dependency — or changing a
module's version — regenerate it:

```bash
./gradlew kotlinUpgradePackageLock
```

CI verifies the committed file, so a forgotten regeneration fails the build rather than drifting.
