# TODO

## VTable 1.26.8 Kotlin/JS 封装

把 VisActor VTable 的开源（MIT）部分封装成 Kotlin/JS external 声明，配双语 demo 与双语文档站，
通过 GitHub Pages 发布文档 / demo / API 三件套，并接入 Maven Central 发布流程。

- 总计：27
- 已完成：13
- 明确不做：3
- 待完成：11

详细清单：[api-coverage.md](docs/development/api-coverage.md)
生成器决策：[technical-decisions.md](docs/development/technical-decisions.md)
API 面报告：[api-surface-report.md](docs/development/api-surface-report.md)

### 当前待办

- [ ] `./gradlew check`（detekt + 浏览器测试）跑通
- [ ] 透视图表 demo（等生成器能解析 VChart 的 `chartSpec`）
- [ ] 用 `gh` 开启 Pages（`build_type=workflow`）并跑一次 `pages.yml`
- [ ] 生成脚本默认参数确认 `node_modules` 路径可用
- [ ] 其余 npm 子包：export / search / plugins / gantt / sheet / calendar

### 注意事项

- 只做开源免费部分；React / Vue / OpenInula 绑定明确不做（理由见 coverage）。
- `gantt` / `sheet` / `calendar` 是独立子产品，按独立 Gradle 模块后续补，不塞进本模块。
- 生成脚本必须可重跑：上游升版只改 `package.json` 与重新生成。
- 本地用国内镜像（`YARN_REGISTRY` / `NPM_CONFIG_REGISTRY`），不提交镜像配置，CI 仍走官方源；
  镜像刷过的锁文件要在官方源下重刷，否则 CI 报 `Lock file was changed`。
- 手写文件不能放在生成目录（生成器会删掉那里的所有 `.kt`），一律放 `dsl/` 子包。
