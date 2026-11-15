---
sidebar_position: 6
title: 开发
---

# 开发

## 生成的声明

`ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable/` 由两个 npm 包生成，禁止手改。
`scripts/generate-api.py` 读每个包的 `.d.ts` 树，按上游模块一个文件地输出 Kotlin 声明，另外生成
联合类型、字面量常量和 API 面报告：

```bash
python scripts/generate-api.py \
    --types node_modules/@visactor/vtable/es \
    --editors-types node_modules/@visactor/vtable-editors/es \
    --emit
```

| 参数 | 含义 |
| --- | --- |
| `--types` | `@visactor/vtable` 的 `.d.ts` 目录 |
| `--editors-types` | `@visactor/vtable-editors` 的 `.d.ts` 目录 |
| `--emit` | 写出 Kotlin 文件（不带时只报告） |
| `--out` | 输出目录，默认 `ktjs-vtable/src/jsMain/kotlin/io/github/shijianjs/ktjs/vtable` |
| `--report` | 报告位置，默认 `docs/development/api-surface-report.md` |

当前产出：445 个可达声明、277 个导出名、138 个 Kotlin 文件。报告列出无法直接表达的声明（索引签名、
交叉类型、未解析引用），让缺口是可见的而不是藏起来的。

## 生成器遵循的规则

- 每个上游模块一个 Kotlin 文件，`@file:JsModule` 指向运行时的 `.js` 路径
  （`@visactor/vtable/es/...js`）。`@visactor/vtable-editors` 的 `exports` 只暴露根，所以它的声明
  统一从包根导入。
- 公开别名优先拿短 Kotlin 名（`ListTableAll` 变成 `ListTable`），上游导出名通过 `@JsName` 保留原拼写。
- external 类一律 `open`（上游会继承自己的类型），且不能实现接口，所以 `implements` 子句折进类体；
  继承来的同名同签名成员跳过，签名不同的改名并用 `@JsName` 映射回去。
- 联合类型落成一个不透明 `external interface` 加每支一个工厂；字符串字面量联合落成
  `sealed external interface` 加常量对象。上游的 `Either` 直接解析成联合，`Function` 变成 `Function<*>`。
- getter/setter 对合并成一个 `var`。名为 `_`、`__` 的成员暴露为 `typedUnderscore<N>` 并用 `@JsName` 映射。

每条规则的来由都记在 `docs/development/technical-decisions.md`；生成器新增规则时在那里补一条。

## 手写代码

`.../vtable/dsl/VTableDsl.kt` 是手写层：

- `listTableOptions`、`pivotTableOptions`、`pivotChartOptions` —— 基于生成类型的 `unsafeJso` 构造器。
- `textColumn`、`linkColumn`、`checkboxColumn`、`progressbarColumn`、`imageColumn`、`groupColumn`。
- `row(...)` —— 构造一条记录。这是 DSL 里唯一动态创建对象的地方，因为记录是以列名为键的开放字典；
  其它对象都有有类型的形状。
- `VTable` —— 主题查找与注册。

手写文件不要放进生成目录：生成器在写出前会删掉那里的所有 `.kt`。

## 本地镜像

仓库本身从不指向镜像：CI 和任何克隆都走官方源。网络拉不动时，只在本地会话里改：

```bash
export YARN_REGISTRY=https://registry.npmmirror.com
export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
```

Gradle 镜像放到 `~/.gradle/init.d/`，不要写进 `settings.gradle.kts`。

注意：对着镜像刷新的锁文件会把**新增**包的地址记成镜像地址，CI 随后会报
`Lock file was changed`。提交前用官方源重新刷一次锁。

## 进度跟踪

本仓库遵循 `long-task-tracking` 技能：`TODO.md` 记总数，明细清单放在 `docs/development/`。
`api-coverage.md` 是按包的任务清单（已完成 / 待完成 / 明确不做，附理由），`api-surface-report.md` 是
生成器输出。新增包时两边都更新，并保证 `总数 = 已完成 + 明确不做 + 待完成`。
