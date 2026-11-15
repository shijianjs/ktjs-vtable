---
sidebar_position: 6
title: Development
---

# Development

## Generated declarations

`ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable/` is generated from the two npm
packages and must not be edited. `scripts/generate-api.py` reads the `.d.ts` tree of each package and
emits one Kotlin file per upstream module plus shared files for unions, literal constants and the API
surface report:

```bash
python scripts/generate-api.py \
    --types node_modules/@visactor/vtable/es \
    --editors-types node_modules/@visactor/vtable-editors/es \
    --emit
```

| Flag | Meaning |
| --- | --- |
| `--types` | the `.d.ts` directory of `@visactor/vtable` |
| `--editors-types` | the `.d.ts` directory of `@visactor/vtable-editors` |
| `--emit` | write the Kotlin files (without it the script only reports) |
| `--out` | output directory, default `ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable` |
| `--report` | where the surface report goes, default `docs/development/api-surface-report.md` |

Current output: 444 reachable declarations, 277 exported names, 138 Kotlin files. The report lists the
declarations that could not be expressed directly (index signatures, intersections, unresolved
references) so the gap is visible instead of hidden.

## Rules the generator follows

- One Kotlin file per upstream module, each with `@file:JsModule` pointing at the runtime `.js` path
  (`@visactor/vtable/es/...js`). `@visactor/vtable-editors` exposes only its root in `exports`, so all
  of its declarations import the package root.
- A public alias wins the short Kotlin name (`ListTableAll` becomes `ListTable`), and the upstream
  export keeps its own spelling through `@JsName`.
- External classes are `open` (upstream subclasses its own types) and cannot implement interfaces, so
  an `implements` clause is folded into the class body; inherited members with the same signature are
  skipped, ones with a different signature are renamed and mapped back with `@JsName`.
- Unions become one opaque `external interface` plus one factory per branch; string-literal unions
  become `sealed external interface` plus a constant object. `either` upstream types collapse to a
  union, and `Function` becomes `Function<*>`.
- Getter/setter pairs merge into one `var`. Members named `_`, `__` are exposed as
  `typedUnderscore<N>` with `@JsName`.

The reasoning behind each of those choices is recorded in
`docs/development/technical-decisions.md`; add a note there when the generator gains a new rule.

## Hand-written code

`.../vtable/dsl/VTableDsl.kt` is the hand-written layer:

- `listTableOptions`, `pivotTableOptions`, `pivotChartOptions` — `unsafeJso` builders over the
  generated option types.
- `textColumn`, `linkColumn`, `checkboxColumn`, `progressbarColumn`, `imageColumn`, `groupColumn`.
- `row(...)` — builds one record. It is the only place in the DSL that creates an object dynamically,
  because a record is an open dictionary keyed by column names; every other object has a typed shape.
- `VTable` — theme lookup and registration.

Keep hand-written files out of the generated directory: the generator deletes every `.kt` file there
before emitting.

## Local mirrors

The repository never points at a mirror: CI and every clone use the official registries. When the
network cannot reach them, set the registry for the local session only:

```bash
export YARN_REGISTRY=https://registry.npmmirror.com
export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
```

Gradle mirrors belong in `~/.gradle/init.d/`, never in `settings.gradle.kts`.

Note that a lock file refreshed against a mirror records mirror URLs for packages it adds, and CI then
reports `Lock file was changed`. Refresh the lock against the official registry before committing.

## Progress tracking

This repository follows the `long-task-tracking` skill: `TODO.md` holds the totals, and the detailed
checklists live under `docs/development/`. `api-coverage.md` is the per-package checklist (done /
pending / out of scope, with reasons), `api-surface-report.md` is generator output. Update both when a
package is added, and keep `total = done + excluded + pending`.
