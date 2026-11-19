package demo.page.samples

import io.github.shijianjs.ktjs.demo.i18n.Lang
import io.github.shijianjs.ktjs.demo.i18n.code
import io.github.shijianjs.ktjs.vtable.dsl.row
import kotlin.js.JsAny

/** One row of the sample table: the shape every page but the pivot one shares. */
internal class Person(val name: String, val role: String, val city: String, val score: Double)

/**
 * The sample rows, in the page's language.
 *
 * The score column is a number on purpose: a text column renders it without the locale's separators,
 * which is what the pages want to show.
 */
internal fun people(lang: Lang): List<Person> =
    if (lang.code.startsWith("zh")) listOf(
        Person("Ada Lovelace", "分析引擎", "伦敦", 96.0),
        Person("Grace Hopper", "编译器", "纽约", 92.0),
        Person("Linus Torvalds", "内核", "赫尔辛基", 88.0),
        Person("Margaret Hamilton", "导航软件", "波士顿", 99.0),
        Person("Barbara Liskov", "分布式系统", "波士顿", 94.0),
    ) else listOf(
        Person("Ada Lovelace", "Analytical engine", "London", 96.0),
        Person("Grace Hopper", "Compiler", "New York", 92.0),
        Person("Linus Torvalds", "Kernel", "Helsinki", 88.0),
        Person("Margaret Hamilton", "Navigation software", "Boston", 99.0),
        Person("Barbara Liskov", "Distributed systems", "Boston", 94.0),
    )

/** Turns the sample rows into the untyped records the table DSL takes. */
internal fun List<Person>.toRecords(): Array<JsAny> = map { person ->
    row("name" to person.name, "role" to person.role, "city" to person.city, "score" to person.score)
}.toTypedArray()
