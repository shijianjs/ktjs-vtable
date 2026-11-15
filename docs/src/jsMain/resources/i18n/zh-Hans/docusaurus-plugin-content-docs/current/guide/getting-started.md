---
sidebar_position: 2
title: 快速开始
---

# 快速开始

## 环境要求

- JDK 21 或更高；Gradle wrapper 已随仓库提供（9.4.1）。
- Node 与 npm 由 Kotlin Gradle 插件下载和驱动，不需要记 `npm install`；`kotlin.js.yarn=false` 保证包管理器是 npm。
- 第一次跑浏览器测试时由 Playwright 下载 Chromium。

## 安装

```kotlin
dependencies {
    implementation("io.github.shijianjs:ktjs-vtable:1.26.8-kt.1")
}
```

模块已经把 `@visactor/vtable` 与 `@visactor/vtable-editors` 声明为 npm 依赖，使用方不必再加。两者都是
MIT 许可，不会额外拉进 VTable 的其它包。

## 第一张表

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
            textColumn("name", "姓名", 150.0),
            textColumn("role", "方向", 160.0),
            textColumn("city", "城市", 130.0),
        )
        records(
            row("name" to "Ada Lovelace", "role" to "分析引擎", "city" to "伦敦"),
            row("name" to "Grace Hopper", "role" to "编译器", "city" to "纽约"),
        )
        frozenColCount = 1.0
        widthMode = StandardOrAdaptiveOrAutoWidths.adaptive
    })
}
```

尺寸来自 CSS，因为构造表格之前容器必须已经有尺寸：

```css
.table-host {
    width: 100%;
    height: 460px;
}
```

两处细节：

- **构造前容器必须有尺寸。** VTable 会测量容器；零高度的元素只会得到零高度的 canvas。`ListTable`
  会在你传入的元素里自己追加 `<div>` 与 `<canvas>`。
- **`ListTable(options)` 也可以**，前提是 options 里带了 `container`。演示页用的是两参数形式。

## 构建、测试、发布

```bash
./gradlew build                    # 编译、Detekt、浏览器测试
./gradlew :ktjs-vtable:jsBrowserTest
./gradlew :demo:e2eTest            # Playwright 打打包后的 demo 页面
./gradlew :docs:docusaurusBuild    # 文档站
./gradlew pagesSite                # 文档在根目录、demo 在 /demo/、Dokka 在 /api/
```

`build` 不跑 demo 的端到端套件，也不组装 Pages 站点：两者都需要浏览器，在 CI 里是单独的步骤。

## 开发

```bash
./gradlew :docs:docusaurusStart    # 本站的开发服务器
./gradlew :demo:jsBrowserRun       # demo 页的开发服务器
```

Docusaurus 监听站点目录，改 Markdown 会自动刷新；改 Kotlin 需要先跑一次
`./gradlew :docs:docusaurusSite`，因为站点引用的是编译产物。

## 锁文件

整个 workspace 的 npm 依赖只解析一次，钉在 `kotlin-js-store/package-lock.json`。新增或升级 npm 依赖、或者
改了模块版本之后要重新生成：

```bash
./gradlew kotlinUpgradePackageLock
```

CI 会校验提交的锁文件，忘了重新生成会构建失败，而不是悄悄漂移。
