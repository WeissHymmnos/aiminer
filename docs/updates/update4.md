# Update 4

## 目标

根据“`instruction.md` 需要更多图表”的要求，对技术说明文档补充可视化内容，提升架构可读性与维护效率。

## 变更文件

- `instruction.md`

## 主要更新内容

- 新增总链路图（1.1）
  - 在仓库定位说明后补充高层执行链路 `flowchart LR`，从“配置解析”到“前端结果消费”形成闭环。

- 新增目录与产物关系图（2.5）
  - 增加仓库级别的流向图，覆盖 `api.py`、`manager.py`、`tui.py`、`frontend`、`data`、`results` 之间的数据交互关系。

- 新增手工回测流程图（3.2）
  - 以 `sequenceDiagram` 方式展现 `Frontend -> api.py -> core.manual_runner -> Evaluator -> 持久化 -> 响应回传` 的完整时序。

- 新增策略回测流程图（3.3）
  - 新增 `flowchart TD`，覆盖策略请求到持久化与结果页回显的执行链路。

- 新增 Wiki 图谱流程图（3.4）
  - 用图结构说明 `wiki_vault` 文件、`_load_wiki_pages`、`_build_wiki_graph`、`/api/wiki/index`、`/api/wiki/graph` 与前端渲染的关系。

- 新增 Web 前端运行流图（3.5）
  - 以 `flowchart LR` 明确 `BrowserRouter -> Layout -> React Query / WebSocket -> API -> 页面状态` 的交互路径。

- 新增 Swarm 生命周期图（3.6）
  - 增加 `stateDiagram-v2`，新增 `Active / Stopping / Failed / Retired / OrphanRecovered` 等状态与迁移，反映 manifest + pid 重构后的状态判断边界。

- 新增 Swarm 运行流图（3.6）
  - 以 `flowchart LR` 说明启动、子进程、`alpha_pool`、`strategy_backtests`、`Queue -> JSONL -> WebSocket` 的实时回传链路。

- 新增 Swarm 时序图（3.6）
  - 通过 `sequenceDiagram` 记录 `Frontend/TUI -> FastAPI -> PortfolioManager -> Worker -> 回传 -> 前端消费` 的事件路径。

## 影响范围

- 文档层：`instruction.md` 变得更便于运维/维护人员快速掌握关键控制流。
- 行为层：本次更新未改动运行时代码，仅补齐文档和可视化说明。

## 风险与说明

- 图表以 Mermaid 表达，部分查看器在渲染能力上可能有差异；建议在支持 Markdown Mermaid 的阅读器中查看（如支持该能力的 IDE/文档预览器）。

## 后续建议

- 可继续为各业务页面补充“API 契约表 + 图形”组合（如 SwarmRuns、Strategy、Wiki）。
- 可新增“异常流”图（启动失败、日志丢失、manifest 损坏）作为运维快速排障附录。
