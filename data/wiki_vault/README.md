# Wiki 种子知识库 (`data/wiki_vault/`)

本目录存放由 `aiminer.core.wiki.LLMWiki` 读写与索引的 Obsidian 风格 Markdown 知识卡片。Web 工作台的 `/wiki` 页面会解析此目录下的 YAML Frontmatter 与 `[[wikilink]]` 双向链接，渲染全局与局部知识图谱。

## 版本控制纳入的种子页面

Git 仓库仅跟踪用于初始化新环境的基准知识页（Seed Pages）：

- `index.md`：知识库总索引页
- `market_regime_base.md`：市场状态与宏观环境基准说明
- `strategy_families_base.md`：主流策略家族与风格分类参考
- `qlib_operator_guide.md`：内置横截面与时序算子速查手册

## 运行期生成且被 Git 忽略的文件

以下文件在系统运行过程中动态产生，已在 `.gitignore` 中排除：

- `*_iter*.md`：Swarm 或单智能体挖掘过程中自动沉淀的有效因子卡片
- `log.md`：知识库变更与增量写入日志
- `.obsidian/`：本地 Obsidian 编辑器工作区配置

首次启动 Swarm 时若传入 `--wiki-bootstrap`，系统会结合 `data/rag_docs/` 中的文献与算子资料自动合成初始知识卡片，并同步写入 `data/wiki_db/` 向量库。
