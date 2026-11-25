# ktjs-vtable

<p align="center"><img src="docs/src/jsMain/resources/static/img/ktjs-vtable-logo.png" width="120" alt="ktjs-vtable"></p>

[VisActor VTable](https://github.com/VisActor/VTable) 开源部分的 Kotlin/JS 封装。声明由上游
`.d.ts` 生成，日常用法再由一层手写 DSL 兜住。

[English](README.md) | [简体中文](README.zh-CN.md)

**[文档](https://shijianjs.github.io/ktjs-vtable/zh-Hans/)** ·
**[在线演示](https://shijianjs.github.io/ktjs-vtable/demo/)** ·
**[API 文档](https://shijianjs.github.io/ktjs-vtable/api/)**

```kotlin
val table = ListTable(container, listTableOptions {
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
```

## 范围

只封装 VTable 里 **开源、MIT 许可** 的部分：

| 上游包 | 状态 |
| --- | --- |
| `@visactor/vtable`（核心：列表、透视表、事件、主题、register） | 已封装 |
| `@visactor/vtable-editors`（输入 / 文本域 / 日期编辑器） | 已封装 |
| `@visactor/vtable-export`、`-search`、`-plugins`、`-gantt`、`-sheet`、`-calendar` | 未开始 |
| `@visactor/react-vtable`、`-vue-vtable`、`-openinula-vtable` | 明确不做 |

框架绑定不做，因为 Kotlin/JS 用不上 React/Vue/OpenInula 组件；其余包的进度记在
[`docs/development/api-coverage.md`](docs/development/api-coverage.md)。

## 模块

| 模块 | npm 包 | wrapper 版本 |
| --- | --- | --- |
| [ktjs-vtable](ktjs-vtable/README.zh-CN.md) | `@visactor/vtable`、`@visactor/vtable-editors` | `1.26.8-kt.1` |

核心包和编辑器包上游版本一致、发版节奏一致，因此共用一个 Gradle 模块与一个 Kotlin 包
（`io.github.shijianjs.ktjs.vtable`），沿用的是其它 `ktjs-*` 封装的既有做法。

## 版本约定

每个模块的版本为 `{上游 npm 版本}-kt.{修订号}`。上游 npm 版本只在根 [`package.json`](package.json)
中声明；每个模块的修订号在 [`wrapper-revisions.properties`](wrapper-revisions.properties) 中维护。
Gradle 从这两份文件推导基础版本和 `npm(...)` 依赖：

- 只发布带 `-kt.N` 后缀的版本，不存在不带后缀的版本。
- 工作树里的版本一律再带 `-SNAPSHOT`：推导出的是「下一个要发的版本」，Central 上还没有，开发构建不冒用它。
  发布时才用 `-Pktjs.release=true` 去掉后缀。
- 上游升级：改 `package.json` 里的版本，基础版本自动跟随，修订号保持不变。
- 仅 wrapper 修复：只把对应模块的修订号加一（`kt.2`、`kt.3`……）。

## 生成的声明

`ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable/` 是生成目录，不要手改。生成器读取两个
npm 包的 `.d.ts`，按上游模块一个文件地输出 Kotlin 声明，外加联合类型、字面量常量与 API 面报告：

```bash
python scripts/generate-api.py \
    --types node_modules/@visactor/vtable/es \
    --editors-types node_modules/@visactor/vtable-editors/es \
    --emit
```

报告写到 `docs/development/api-surface-report.md`。生成器遵循的规则、以及它对上游写法的固定处理方式，记在
[`docs/development/technical-decisions.md`](docs/development/technical-decisions.md)。手写代码放在
`dsl` 子包里，生成器不会碰。

## 环境要求

- JDK 21 或更高（构建使用 Gradle 9.4.1）。
- Node 与 npm 由 Kotlin Gradle 插件自动下载；`gradle.properties` 里的 `kotlin.js.yarn=false` 保证包管理器
  是 npm。
- 第一次跑浏览器测试时由 Playwright 下载 Chromium。

## 构建与测试

```bash
./gradlew build                    # 编译、Detekt、浏览器测试
./gradlew :ktjs-vtable:jsBrowserTest

# demo 页面的端到端检查（Playwright，打打包产物）
./gradlew :demo:e2eTest

# 文档站：Kotlin 配置 + Markdown 页面，由 ktjs-docusaurus 构建
./gradlew :docs:docusaurusBuild

# GitHub Pages 站点（根目录是文档，demo 在 /demo/，API 文档在 /api/）
./gradlew pagesSite
```

新增或升级 npm 依赖后，刷新共享锁文件：

```bash
./gradlew kotlinUpgradePackageLock
```

网络拉不动 npm 时，用国内镜像**只影响本地构建**；仓库与 CI 都不读这两个变量：

```bash
export YARN_REGISTRY=https://registry.npmmirror.com       # PowerShell: $env:YARN_REGISTRY="..."
export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
```

`docs` 模块同样是 Kotlin/JS 项目。三个 ktjs-docusaurus 版本都写在 `gradle/libs.versions.toml` 里：wrapper klib、
Gradle 插件、以及首页分区用到的工具箱——那个项目的每个模块各自带 `-kt.N` 修订号。写 SNAPSHOT 时从
`mavenLocal` 解析。工具箱的浏览器那一半不是独立的 Maven 产物，而是 kit klib 里的资源，由
`extractKitBundle` 解到站点的 `static/ktjs-client/`。

## 发布

发布配置统一在根 [`build.gradle.kts`](build.gradle.kts) 里，对所有模块生效。`.github/workflows/release.yml`
签名、按 Maven 坐标打包并注册到共享的 Maven Central hub，由 hub 合并成一次 deployment。

## 许可证

[MIT](LICENSE)。VTable 本身也是 MIT；封装只提供声明，运行时用到的仍是上游代码。
