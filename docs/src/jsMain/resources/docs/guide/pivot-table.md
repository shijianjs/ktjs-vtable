---
sidebar_position: 4
title: Pivot table
---

# Pivot table

`PivotTable` aggregates the same flat records by row and column dimensions. The options type is
`PivotTableConstructorOptions`, and `pivotTableOptions { }` builds it the same way
`listTableOptions` builds the list options.

## Dimensions and indicators

```kotlin
val options = pivotTableOptions {
    records(
        row("region" to "East", "category" to "A", "sales" to 120.0),
        row("region" to "West", "category" to "A", "sales" to 150.0),
    )
    this.rows = arrayOf<JsAny>(unsafeJso<PivotDimension> { field = "region"; title = "Region" })
    this.columns = arrayOf<JsAny>(unsafeJso<PivotDimension> { field = "category"; title = "Category" })
    this.indicators = arrayOf<JsAny>(
        unsafeJso<PivotIndicator> { field = "sales"; title = "Sales"; aggregationType = "SUM" },
    )
    widthMode = StandardOrAdaptiveOrAutoWidths.standard
}
PivotTable(container, options)
```

- `rows` / `columns` are `Array<JsAny>` upstream (`(IRowDimension | string)[]`), so the wrapper hands
  them through as JS objects; declare the shape you use, as above.
- `indicators` carry the aggregation: `aggregationType` is the string the upstream aggregator registry
  understands (`SUM`, `COUNT`, `AVG`, …). A registered custom aggregator is reachable through
  `register` (see [Themes and editors](guide/themes-and-editors.md)).
- `records` accepts rows built with `row(...)`, exactly as the list table does.

## Pivot chart

`PivotChart` takes `PivotChartConstructorOptions` and renders a chart inside the cells. Its
indicators are chart indicators: each one carries a `chartSpec`, so the option object is built with
`pivotChartOptions { }` and the indicator objects come from the generated declarations — the DSL
deliberately does not invent a shape for them, because chart specs are VChart's own option tree.

## What the pivot table does not do

The wrapper does not re-implement any aggregation or layout logic: `PivotTable` and `PivotChart` are
the upstream classes, constructed with typed options. If an upstream option is not reachable through
the DSL, set it directly on the options object.

## Next

- [Themes and editors](guide/themes-and-editors.md) — why both tables look the way they do, and how cells
  become editable.
- [Package coverage](guide/scope.md) — what is wrapped today, and what is still pending.
