package demo

import io.github.shijianjs.ktjs.demo.i18n.Langs
import io.github.shijianjs.ktjs.demo.i18n.SiteTexts
import io.github.shijianjs.ktjs.demo.i18n.Translations
import io.github.shijianjs.ktjs.demo.i18n.texts

/**
 * Every string the layout and the navigation show, in English.
 *
 * One object per language, declared once in [siteTexts].
 */
private val englishSite: SiteTexts = SiteTexts(
    siteTitle = "ktjs-vtable",
    langLabel = "English",
    languageLabel = "Language",
    themeLabel = "Theme",
    docsLabel = "Docs",
    siteDocsLabel = "Documentation",
    apiLabel = "API reference",
    sourceLabel = "GitHub",
    lightLabel = "Light",
    darkLabel = "Dark",
    systemLabel = "Follow browser",
    groupTitles = mapOf(
        "start" to "Getting started",
        "tables" to "Tables",
        "interaction" to "Interaction",
    ),
    pageTitles = mapOf(
        "overview" to "Overview",
        "basic" to "Basic table",
        "group" to "Grouped header",
        "pivot" to "Pivot table",
        "edit" to "Editable cells",
        "theme" to "Themes",
        "events" to "Events",
    ),
)

private val chineseSite: SiteTexts = SiteTexts(
    siteTitle = "ktjs-vtable",
    langLabel = "中文",
    languageLabel = "语言",
    themeLabel = "外观",
    docsLabel = "文档",
    siteDocsLabel = "使用文档",
    apiLabel = "API 文档",
    sourceLabel = "GitHub 仓库",
    lightLabel = "亮色",
    darkLabel = "暗色",
    systemLabel = "跟随浏览器",
    groupTitles = mapOf(
        "start" to "开始",
        "tables" to "表格",
        "interaction" to "交互",
    ),
    pageTitles = mapOf(
        "overview" to "概览",
        "basic" to "基础表格",
        "group" to "分组表头",
        "pivot" to "透视表",
        "edit" to "可编辑单元格",
        "theme" to "主题",
        "events" to "事件",
    ),
)

/** The layout's strings, one entry per registered language. */
val siteTexts: Translations<SiteTexts> = texts(
    Langs.EN to englishSite,
    Langs.ZH_HANS to chineseSite,
)
