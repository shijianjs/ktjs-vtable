# ktjs-vtable

<p align="center"><img src="docs/src/jsMain/resources/static/img/ktjs-vtable-logo.png" width="120" alt="ktjs-vtable"></p>

A Kotlin/JS wrapper for the open-source packages of
[VisActor VTable](https://github.com/VisActor/VTable) — the canvas table library behind
`@visactor/vtable`. Typed declarations are generated from the package's own `.d.ts` files, and a
small hand-written DSL sits on top of them for the everyday case.

[English](README.md) | [简体中文](README.zh-CN.md)

**[Documentation](https://shijianjs.github.io/ktjs-vtable/)** ·
**[Live demo](https://shijianjs.github.io/ktjs-vtable/demo/)** ·
**[API reference](https://shijianjs.github.io/ktjs-vtable/api/)**

```kotlin
val table = ListTable(container, listTableOptions {
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
```

## Scope

Only the **open-source, MIT-licensed** part of VTable is wrapped:

| Upstream package | Status |
| --- | --- |
| `@visactor/vtable` (core: list table, pivot table, events, themes, register) | wrapped |
| `@visactor/vtable-editors` (input / text area / date picker editors) | wrapped |
| `@visactor/vtable-export`, `-search`, `-plugins`, `-gantt`, `-sheet`, `-calendar` | not started |
| `@visactor/react-vtable`, `-vue-vtable`, `-openinula-vtable` | deliberately excluded |

The framework bindings are excluded because Kotlin/JS has no use for a React/Vue/OpenInula
component; the remaining packages are tracked in
[`docs/development/api-coverage.md`](docs/development/api-coverage.md).

## Modules

| Module | npm packages | Wrapper version |
| --- | --- | --- |
| [ktjs-vtable](ktjs-vtable/README.md) | `@visactor/vtable`, `@visactor/vtable-editors` | `1.26.8-kt.1` |

The core and the editors package share one upstream version and one release cadence, so they share
one Gradle module and one Kotlin package (`io.github.shijianjs.ktjs.vtable`) — the same reasoning the
other `ktjs-*` wrappers follow.

## Versioning

Each module is versioned as `{upstream npm version}-kt.{revision}`. The upstream npm versions are
declared once in the root [`package.json`](package.json); the revision is read per module from
[`wrapper-revisions.properties`](wrapper-revisions.properties). Gradle derives the base version and
the `npm(...)` dependencies from these two files:

- Only `-kt.N` versions are published; a version without the suffix never exists.
- A working tree always adds `-SNAPSHOT`: the derived number is the *next* release, which Central does
  not have yet, so development builds never impersonate it. Publishing passes `-Pktjs.release=true`,
  which drops the suffix.
- Upstream upgrade: change the version in `package.json`; the base version follows automatically
  while the revision stays, even when the wrapper code itself did not change.
- Wrapper-only fix: the revision increments (`kt.2`, `kt.3`, ...) while the base version stays.

## Generated declarations

`ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable/` is generated; do not edit it. The
generator reads the `.d.ts` files of both npm packages and emits one Kotlin file per upstream module,
plus unions, literals and the API surface report:

```bash
python scripts/generate-api.py \
    --types node_modules/@visactor/vtable/es \
    --editors-types node_modules/@visactor/vtable-editors/es \
    --emit
```

The report lands in `docs/development/api-surface-report.md`; the rules the generator follows (and the
upstream shapes it deliberately flattens) are in
[`docs/development/technical-decisions.md`](docs/development/technical-decisions.md). Hand-written
code lives beside the generated files in the `dsl` sub-package, which the generator leaves alone.

## Requirements

- JDK 21 or newer (the build uses Gradle 9.4.1).
- Node and npm are downloaded automatically by the Kotlin Gradle plugin; `kotlin.js.yarn=false` in
  `gradle.properties` keeps npm as the package manager.
- Chromium is downloaded by Playwright the first time browser tests run.

## Build and test

```bash
./gradlew build                    # compile, Detekt, browser tests
./gradlew :ktjs-vtable:jsBrowserTest

# End-to-end checks for the demo page (Playwright, against the bundled output)
./gradlew :demo:e2eTest

# Documentation site: Kotlin configuration, Markdown pages, built by ktjs-docusaurus
./gradlew :docs:docusaurusBuild

# GitHub Pages site (documentation at the root, demo under /demo/, Dokka output under /api/)
./gradlew pagesSite
```

After adding or upgrading an npm dependency, refresh the shared lock file:

```bash
./gradlew kotlinUpgradePackageLock
```

On a network that cannot reach the npm registry, point npm at a mirror **for the local build only**;
nothing in the repository or in CI reads these variables:

```bash
export YARN_REGISTRY=https://registry.npmmirror.com       # PowerShell: $env:YARN_REGISTRY="..."
export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
```

## Publishing

Publishing is configured once in the root [`build.gradle.kts`](build.gradle.kts) for all modules.
Releases run through `.github/workflows/release.yml`: it signs the artifacts, packages one archive per
Maven coordinate and registers them with the shared Maven Central hub, which merges the pending
registrations into a single deployment.

## License

Released under the [MIT License](LICENSE). VTable itself is MIT-licensed as well; the wrapper only
declares types, the upstream code is the shipped runtime.
