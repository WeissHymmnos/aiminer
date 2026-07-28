# AI Alpha Miner — 完整技术说明书

本文档是系统的权威技术参考，覆盖架构设计、模块职责、数据流、算子规范、验证规则、已知陷阱与开发规范。任何新代码的修改均应以本文档为基础。

---

## 目录

1. [项目概述](#1-项目概述)
2. [环境搭建](#2-环境搭建)
3. [运行系统](#3-运行系统)
4. [整体架构](#4-整体架构)
5. [LangGraph 状态机](#5-langgraph-状态机)
6. [各模块详解](#6-各模块详解)
7. [因子表达式系统](#7-因子表达式系统)
8. [求值引擎](#8-求值引擎)
9. [RiceQuant 回测流程](#9-ricequant-回测流程)
10. [模拟回退机制](#10-模拟回退机制)
11. [早停与 patience 机制](#11-早停与-patience-机制)
12. [知识库系统](#12-知识库系统)
13. [LLM 网关](#13-llm-网关)
14. [Manager 与 SubAgent 协调](#14-manager-与-subagent-协调)
15. [输出结构](#15-输出结构)
16. [AlphaMinerState 字段说明](#16-alphaminerstate-字段说明)
17. [关键参数速查](#17-关键参数速查)
18. [已知问题与规避方式](#18-已知问题与规避方式)
19. [测试](#19-测试)
20. [开发规范](#20-开发规范)

---

## 1. 项目概述

**AI Alpha Miner** 是一个端到端的量化 Alpha 因子自动发现系统。系统通过 **Manager–SubAgent Swarm** 架构，由多个 LLM 驱动的量化研究员 Agent 并发工作，自主完成以下完整流水线：

```
市场假说生成 → 数学公式化 → Qlib 代码实现 → 回测（RiceQuant/Qlib）→ 正交化筛选 → 因子池
```

核心设计原则：

- **全自动**：从假说到最终因子池无需人工干预
- **多角色**：每个 SubAgent 被赋予不同的量化研究角色（动量专家、统计套利专家等），鼓励策略多样性
- **知识积累**：每次迭代的结果（成功或失败）写入 LLMWiki 和 RAG，后续 Agent 从中学习，避免重复失败
- **安全执行**：所有 LLM 生成的代码在 AST 级白名单验证后方可执行，通过 `SafeEvalTransformer` 隔离危险名称
- **容错设计**：回测失败降级为模拟指标，模拟状态全面隔离，不污染因子池、不触发早停、不写知识库

---

## 2. 环境搭建

### 依赖安装

```bash
conda env create -f environment.yml && conda activate aiminer
pip install -r requirements.txt
```

### 环境变量配置

```bash
cp .env.example .env
# 然后编辑 .env 填入 API 密钥
```

必填的 `.env` 变量：

| 变量名 | 用途 |
|---|---|
| `ZHIPU_API_KEY` / `GLM_KEY` | 智谱 GLM 系列 LLM |
| `LLM_KEY` / `KIMI_API_KEY` | Kimi（Moonshot）|
| `QWEN_API_KEY` | 通义千问 |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `OPENAI_API_KEY` / `OpenAI_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` / `ClaudeCode_KEY` | Claude |
| `OPENROUTER_API_KEY` | OpenRouter（多模型代理）|
| `GROQ_API_KEY` | Groq（高速推理）|
| `RQ_TOKEN` | RiceQuant License Token（优先）|
| `RQ_USER` / `RQ_PASS` | RiceQuant 账号密码（备用）|
| `USE_LOCAL_EMBEDDING` | 设为 `true` 启用本地 Embedding（Qwen3-Embedding-4B）|

RiceQuant 认证优先级：Token > 账号密码。Token 长度须 > 50 字符。认证全局只执行一次（`_rq_initialized` 标志位），多进程共享主进程的认证状态。

---

## 3. 运行系统

### 主模式：多 Agent Swarm

```bash
python manager.py \
  --iterations 5 \
  --mode ricequant \
  --llm-provider glm \
  --llm-model glm-4-flash \
  --roles "动量反转专家" "统计套利专家" "基本面量价专家" \
  --parallel \
  --wiki-bootstrap
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--iterations` | 每个 SubAgent 最大迭代轮数 | `5` |
| `--mode` | 回测引擎：`ricequant` 或 `qlib` | `ricequant` |
| `--engine` | 因子计算引擎：`pandas` 或 `polars` | `pandas` |
| `--llm-provider` | LLM 提供商（见第 13 节）| 自动检测 |
| `--llm-model` | 模型名称 | 各 provider 内置默认 |
| `--roles` | 各 SubAgent 的角色 prompt，空格分隔 | 内置 3 个角色 |
| `--parallel` | 多进程并行执行 SubAgent | 默认串行 |
| `--wiki-bootstrap` | 启动前将 RAG 文档编译为 Wiki 卡片 | 关闭 |
| `--rebuild-rag` | 强制重新 Embedding RAG 文档 | 关闭 |
| `--embedding-provider` | `local`（Qwen3 本地）或 API | API |
| `--market-start` | 回测/市场分析起始日期 | `2018-01-01` |
| `--market-end` | 回测/市场分析截止日期 | `2025-12-31` |

### 单 Agent 模式（调试用）

```bash
python main.py --iterations 3 --mode ricequant --llm-provider kimi
```

### 推荐的稳定启动参数（A 股 RiceQuant）

```bash
python manager.py \
  --iterations 5 \
  --mode ricequant \
  --engine pandas \
  --llm-provider kimi \
  --roles "动量反转专家" "统计套利专家" \
  --wiki-bootstrap
```

> **建议**：`--engine pandas` 在稳定性上优于 `polars`，调试时优先使用。Polars 引擎对深层嵌套表达式有额外要求（见第 8 节）。

---

## 4. 整体架构

### 数据流

```
manager.py (PortfolioManager)
│
├─ [可选] WikiBootstrapper
│   └─ 将 data/rag_docs/ 文档编译为 LLMWiki 卡片（一次性）
│
├─ dispatch_tasks(): 为每个 role 生成 SubAgent 任务参数
│
├─ ProcessPoolExecutor (--parallel) 或串行
│   └─ sub_agent.py (AlphaResearcher.run())
│       └─ workflow/graph.py (LangGraph StateGraph)
│           ├─ idea_agent     → 生成假说（RAG + Wiki + 宏观/市场状态注入）
│           ├─ factor_agent   → 假说 → 数学公式 → Qlib 表达式（含 AST 验证 + 干跑）
│           ├─ eval_agent     → 回测（RiceQuant pandas/polars 或 Qlib）+ LLM 评审
│           ├─ wiki_update    → 将本轮结果写入 LLMWiki
│           └─ increment      → 更新计数器、清空临时状态、决策继续/终止
│
├─ evaluate_and_combine(results_list)
│   ├─ 第一轮过滤：IC > 0.005（真实回测，排除 is_simulated 且排除空 returns）
│   ├─ 第二轮过滤：Pearson 相关 < 0.7（去多重共线性，需至少 10 个重叠数据点）
│   └─ 遗传杂交：top-2 因子注入 Crossover Agent，产生混合因子（IC 门槛 0.01）
│
└─ 持久化：SQLite WAL（results/alpha_miner.db）+ JSON + Markdown 报告 + 图表
```

### 核心文件索引

| 文件 | 职责 |
|---|---|
| `manager.py` | 最外层编排：角色分发、并行执行、因子过滤、遗传杂交、持久化 |
| `sub_agent.py` | `AlphaResearcher`：初始化 LangGraph app、执行 workflow、汇总结果 |
| `workflow/graph.py` | LangGraph 图定义、路由函数、`increment_iteration` 节点 |
| `workflow/state.py` | `AlphaMinerState` TypedDict：流过图的唯一状态对象（见第 16 节）|
| `agents/idea_agent.py` | 假说生成，注入 RAG + Wiki + 宏观 + 市场状态上下文 |
| `agents/factor_agent.py` | 数学公式化 + Qlib 代码生成 + AST 验证白名单（含全部约束规则）|
| `agents/eval_agent.py` | 回测执行 + LLM 评审 + 早停状态更新 + 模拟状态保护 |
| `agents/summary_agent.py` | 为通过筛选的因子生成 Markdown 报告与权益曲线图 |
| `core/llm.py` | 多 provider LLM 网关，返回 `ChatOpenAI` 兼容对象 |
| `core/rag.py` | ChromaDB 向量检索 + 经验写入 |
| `core/wiki.py` | LLMWiki：YAML frontmatter 结构化因子卡片库 |
| `core/hybrid_knowledge.py` | 融合 RAG + Wiki；去重；回测后更新 Wiki |
| `core/wiki_bootstrapper.py` | 将 RAG 文档批量编译为 Wiki 卡片 |
| `core/alphaeval/rq_eval.py` | RiceQuant 回测：数据拉取、因子计算（pandas/polars）、IC 计算、分层、画图 |
| `core/alphaeval/polars_engine.py` | Polars 算子实现 + `_eager_eval` 两步物化引擎 |
| `core/alphaeval/modeltester.py` | Qlib 适配器（`AlphaEval`）|
| `schemas/messages.py` | 所有 LLM 结构化输出的 Pydantic 模型 |

---

## 5. LangGraph 状态机

### 图结构

```
[ENTRY] idea_agent
    │
    ├─ error 或 hypothesis_name 缺失 ─────────────────→ END
    └─ → factor_agent
           │
           ├─ error ──────────────────────────────────→ END
           └─ → eval_agent          （is_valid_syntax=False 也继续）
                  │
                  ├─ error ─────────────────────────→ END
                  └─ → wiki_update
                         │
                         ├─ IC ≥ 0.05 且非模拟 ─────→ END  [早停：优质因子]
                         ├─ patience_counter ≥ 4 ──→ END  [早停：无改善]
                         ├─ iteration == max_iter ──→ END  [轮数耗尽]
                         └─ → increment → [LOOP] idea_agent
```

### 路由函数说明

**`route_after_idea`**：
- `state["error"]` 不为空 → `"end"`
- `state["hypothesis_name"]` 缺失 → `"end"`（记录 ERROR 日志）
- 否则 → `"factor_agent"`

**`route_after_factor`**：
- `state["error"]` 不为空 → `"end"`
- `state["code_expression"]` 缺失 → `"end"`
- `is_valid_syntax=False`：记录 WARNING 但**不终止**（表达式可能在运行时成功，给 eval 一次机会）
- 否则 → `"eval_agent"`

**`route_after_eval`**：
- `state["error"]` 不为空 → `"end"`
- 否则 → `"wiki_update"`（统一先更新知识库，再决策是否继续）

**`route_after_wiki`**（核心决策节点）：
- 读取 `current_ic = state["backtest_metrics"]["information_coefficient"]`
- 读取 `is_simulated = state["is_simulated"]`
- **早停 1**：`current_ic >= 0.05 AND NOT is_simulated` → `"end"`，打印 SUCCESS 日志
- **跳过陷阱**：`current_ic >= 0.05 AND is_simulated` → 打印 WARNING，**继续**
- **早停 2**：`patience_counter >= 4` → `"end"`
- `iteration < max_iterations` → `"increment"`
- 否则 → `"end"`

**`increment_iteration`**（节点，非路由）：
- `iteration += 1`
- **保留**跨轮字段：`best_ic`、`best_code_expression`、`patience_counter`、`market_regime_summary`、`macro_news_summary`
- **清空**单轮字段：`hypothesis_name`、`hypothesis_description`、`rationale`、`code_expression`、`math_formula`、`variables_defined`、`backtest_metrics`、`review_summary`、`is_effective`、`suggested_improvements`、`error`
- `is_simulated` 重置为 `False`，`is_valid_syntax` 重置为 `True`

---

## 6. 各模块详解

### 6.1 IdeaAgent

**文件**：`agents/idea_agent.py`  
**LLM 温度**：0.7（创意优先）

**执行流程**：

1. 从 `HybridKnowledge.retrieve()` 获取 RAG + Wiki 融合上下文（查询基于角色 prompt，去重后截断至 6000 字符）
2. 若 ricequant 模式且 `macro_news_summary` 为空：RAG 检索宏观新闻（"央行政策、贸易数据、通胀趋势"），缓存在 state（跨轮复用）
3. 若 ricequant 模式且 `market_regime_summary` 为空：调用 `RiceQuantEval.get_market_regime()` 拉取价格趋势、波动率、成交量等统计数据，缓存在 state（跨轮复用）。拉取失败时降级为占位文本 `"[市场数据暂时不可用]"`，不阻断流程
4. 拼接 `combined_context = rag_wiki + 宏观 + 市场状态`，截断至 6000 字符
5. 若 `iteration > 1` 且存在 `suggested_improvements`：将上轮评审建议注入 system_msg 和 user_prompt 末尾，要求 LLM 明确响应反馈
6. 调用 LLM，解析 `HypothesisOutput` JSON

**输出字段**（写入 state）：
```json
{
  "hypothesis_name": "string",
  "hypothesis_description": "string",
  "rationale": "string",
  "rag_context": "string",
  "macro_news_summary": "string",
  "market_regime_summary": "string"
}
```

**关键 Prompt 约束**（硬编码在代码里）：
- 必须产生**连续信号**（continuous signal），在截面上平滑分布，覆盖全部股票的排名谱
- 禁止重复 Wiki 中记载的失败逻辑或相同数学结构
- 信号应关联宏观经济逻辑（央行信号、贸易数据、通胀趋势）
- 需与市场状态匹配（高波动率时期 vs 趋势市）

---

### 6.2 FactorAgent

**文件**：`agents/factor_agent.py`  
**LLM 温度**：0.1（精确优先）

**执行流程**：

**第一步 — 数学公式化（单次调用）**：
- 输入：`hypothesis_description` + `rationale`
- 输出：`FormalizationOutput`（`math_formula` LaTeX 字符串 + `variables_defined` 字典）

**第二步 — Qlib 代码实现（带重试对话循环，最多 2 次重试）**：
1. 携带 OPERATOR_SIGNATURES + 字段白名单 + 11 条强制规则的 system prompt
2. 基于 `math_formula` + `variables_defined` 请求 LLM 生成 `code_expression`
3. 调用 `_validate_qlib_expression()` 做完整 AST 验证（见第 7.3 节）
4. 验证通过后调用 `RiceQuantEval.dry_run()` 做运行时干跑（在 5×1 小数据集上执行）
5. 若有失败：将错误信息作为 assistant + user 消息追加到对话末尾，再次请求 LLM 修复（sliding window：只保留最初 2 条消息 + 最新一轮重试消息对，避免无限 token 增长）
6. 重试次数耗尽时，`is_valid_syntax=False` 但仍返回最后生成的表达式（给 eval 节点一次尝试机会）

**LLM 生成的 JSON Schema**：
```json
{
  "code_expression": "string",
  "is_valid_syntax": true
}
```

**System Prompt 中的 11 条强制规则**（已编码，修改需同步更新规则编号）：

| 规则编号 | 内容 |
|---|---|
| 1 | 只使用 OPERATOR_SIGNATURES 中列出的算子 |
| 2 | 数据字段只能用白名单中的 6 个（`$close/$open/$high/$low/$volume/$vwap`），禁止 `$beta_spx`、`$market_cap` 等 |
| 3 | 窗口参数必须是常量正整数（5、10、20 等），禁止动态表达式 |
| 4 | 若需要未列出的算子，用现有算子组合近似实现 |
| 5 | 避免空洞逻辑（`$close/$close`、`Sign(1)` 等），因子必须有截面方差 |
| 6 | 只返回纯 JSON，不加 markdown |
| 7 | 正确 JSON 转义所有特殊字符 |
| 8 | 避免纯二元信号（`If(cond, 1, 0)` 作为最外层），优先连续表达式 |
| 8（重复）| **禁止 Look-ahead Bias**：`Ref(x, n)` 中 n 不得为负数 |
| 9 | **禁止自相关**：`Corr(a, a, n)` 或 `Cov(a, a, n)` 两参数不得相同 |
| 10 | **禁止恒等式**：`Div(x, x)`、`Sub(x, x)` 等两参数相同的运算恒为常数 |
| 11 | `Rank()` 和 `CSRank()` 只接受 1 个参数，不传窗口大小 |

> **注意**：规则 8 编号重复（代码中存在两条规则 8）是历史遗留，不影响功能但在维护时应注意统一编号。

---

### 6.3 EvalAgent

**文件**：`agents/eval_agent.py`  
**LLM 温度**：0.4（评审）

**执行流程**：

1. 调用 `_execute_alphaeval_backtest()` 执行真实回测（`RiceQuantEval` 或 `AlphaEval`）
2. 若抛出任何异常 → 降级为**哈希确定性模拟指标**，`_simulated=True`（见第 10 节）
3. 提取 `is_simulated`、`daily_returns`、`plot_paths`，其余为回测指标
4. 调用 LLM 进行反思性评审，生成 `ReflexiveReviewOutput`（`review_summary` + `is_effective` + `suggested_improvements`）
5. 若 `NOT is_simulated`：将本轮经验写入 RAG（`add_experience`）
6. 更新早停状态（`best_ic`、`patience_counter`），**模拟状态完全冻结**

**模拟状态保护逻辑**（`eval_agent.py` 第 202–225 行）：

```python
if is_simulated:
    # 冻结所有早停状态，treat 本轮为 no-op
    new_best_ic = best_ic          # 不更新
    new_patience_counter = patience_counter  # 不递增，也不清零
    new_best_code = state.get("best_code_expression", code)
elif current_ic > best_ic:
    new_best_ic = current_ic
    new_patience_counter = 0
    new_best_code = code
else:
    new_best_ic = best_ic
    new_patience_counter = patience_counter + 1
    new_best_code = state.get("best_code_expression", code)
```

**回测指标说明**：

| 指标键 | 含义 |
|---|---|
| `information_coefficient` | IC：因子值与下期收益的 Pearson 相关（主选择指标）|
| `rank_ic` | RankIC：因子排名与收益排名的 Spearman 相关 |
| `oos_ic` | OOS（Out-of-Sample）阶段 IC，OOS 分割点为 2023-01-01 |
| `sharpe` | G5-G1 分层多空组合的年化 Sharpe 比率 |
| `max_drawdown` | 最大回撤（负值）|
| `rre` | Rank Return Efficiency（排名收益效率）|
| `plot_paths` | 图表文件绝对路径字典（`equity`, `layers`）|

---

### 6.4 SummaryAgent

**文件**：`agents/summary_agent.py`  
**LLM 温度**：0.3

作用：为每个通过 Manager 筛选的因子生成结构化研究报告。

- `generate_equity_curve(returns, factor_id)`：绘制累积收益曲线 PNG，存入 `results/charts/`
- `generate_markdown_report(factor_data)`：调用 LLM 生成含经济直觉分析的 Markdown 报告（存入 `results/reports/`），内嵌图片路径（来自 `RiceQuantEval.plot_paths` 或 `generate_equity_curve`）

---

### 6.5 PortfolioManager

**文件**：`manager.py`

**两轮筛选逻辑**（`evaluate_and_combine`）：

**第一轮 — 绝对门槛**：
- `perf_metric（IC）> 0.005`
- `perf_metric` 直接来自 SubAgent 的 `backtest_metrics["information_coefficient"]`
- 模拟因子 `daily_returns` 为空，在 Manager 中因 `empty returns series` 被自动剔除（即使误传了高模拟 IC）

**第二轮 — 相关性去重**：
- 新因子与 `final_pool` 中每个已有因子的日收益序列做 Pearson 相关
- 相关性需要至少 10 个重叠数据点（避免样本不足的虚假相关）
- Pearson ≥ 0.7 视为冗余，剔除新因子

**遗传杂交**（`run_swarm` 末尾）：
- 条件：`alpha_pool` 中至少有 2 个因子
- 将 top-2 因子的假说和代码注入特殊角色 prompt
- 杂交因子同样需过 IC > 0.01 + Pearson < 0.7 两关

**并行执行细节**：
- `ProcessPoolExecutor(max_workers=len(roles))`
- 每个 SubAgent 进程启动前随机 sleep 0.1–1.0 秒（分散 SQLite 写入压力）
- 超时 600 秒后跳过（`future.result(timeout=600)`）

---

## 7. 因子表达式系统

### 7.1 数据字段白名单

**仅支持以下 6 个字段**，均以 `$` 前缀引用：

| 字段 | 含义 | pandas 矩阵键 |
|---|---|---|
| `$close` | 收盘价 | `fields['close']` |
| `$open` | 开盘价 | `fields['open']` |
| `$high` | 最高价 | `fields['high']` |
| `$low` | 最低价 | `fields['low']` |
| `$volume` | 成交量 | `fields['volume']` |
| `$vwap` | 成交量加权均价（total_turnover / volume）| `fields['vwap']` |

**任何其他字段均不存在于数据库**。常见幻觉字段（会被验证器立即拒绝）：

`$beta`、`$beta_spx`、`$market_cap`、`$pe_ratio`、`$pb`、`$dividend`、`$factor`、`$sector`、`$index`、`$PPI`、`$CPI`、`$swap`、`$cash`、`$debt`、`$shares`、`$cap`、`$free_float`、`$turnover_rate`

> `$vwap` 是在 `compute_factors()` 中计算的：`fields['vwap'] = total_turnover / volume.replace(0, NaN)`，然后 ffill + fallback to close。

---

### 7.2 算子完整签名表

#### 截面算子（横向：某天对全部股票操作）

| 算子 | 签名 | 参数数量 | 返回值范围 |
|---|---|---|---|
| `Rank` | `Rank(df)` | **恰好 1 个**（禁止传窗口！）| (0, 1] |
| `CSRank` | `CSRank(df)` | **恰好 1 个** | (0, 1] |
| `CSZScore` | `CSZScore(df)` | 1（n 被忽略，兼容性接受）| (-∞, +∞)，标准化 |
| `GroupNeutral` | `GroupNeutral(df)` | 1 | 减去截面均值后 |
| `Winsorize` | `Winsorize(df, pct=0.05)` | 1–2 | clip 至分位数区间 |
| `Percentile` | `Percentile(df)` | 1 | 等价于 Rank |
| `Scale` | `Scale(df, a=1)` | 1–2 | sum(abs) = a |

#### 时间序列算子（纵向：单只股票的时间轴）

| 算子 | 签名 | 说明 |
|---|---|---|
| `Mean(df, n)` | `Mean(df, n)` | n 日滚动均值 |
| `Std(df, n)` | `Std(df, n)` | n 日滚动标准差 |
| `Median(df, n)` | `Median(df, n)` | n 日滚动中位数 |
| `EMA(df, n)` | `EMA(df, n)` | 指数移动平均，span=n |
| `WMA(df, n)` | `WMA(df, n)` | 线性加权移动平均，span=n |
| `Sum(df, n)` | `Sum(df, n)` | n 日滚动求和 |
| `Ref(df, n)` | `Ref(df, n)` | n 日**前**的值（**n 必须为正整数**；负数 = 未来数据，AST 验证器拒绝！）|
| `Delta(df, n)` | `Delta(df, n)` | df − Ref(df, n)，即 n 日变化量 |
| `Ts_Rank(df, n)` | `Ts_Rank(df, n)` | 过去 n 日中当前值的百分位排名（Rust plugin）|
| `Ts_Max(df, n)` | `Ts_Max(df, n)` | n 日滚动最大值 |
| `Ts_Min(df, n)` | `Ts_Min(df, n)` | n 日滚动最小值 |
| `Ts_ArgMax(df, n)` | `Ts_ArgMax(df, n)` | 过去 n 日最大值出现在几天前（Rust plugin）|
| `Ts_ArgMin(df, n)` | `Ts_ArgMin(df, n)` | 过去 n 日最小值出现在几天前（Rust plugin）|
| `Ts_Percentile(df, n, p=50)` | `Ts_Percentile(df, n, p)` | 过去 n 日第 p 百分位数值（p 在 0–100，默认 50）|

> **所有时间序列算子的窗口参数 n 必须是常量正整数**（如 5、10、20），不能是字段引用、变量或表达式。

#### 相关性算子

| 算子 | 签名 | 约束 |
|---|---|---|
| `Corr(df1, df2, n)` / `Correlation(df1, df2, n)` | 3 个参数 | df1 和 df2 的 AST 不得相同（否则恒为 1.0）|
| `Cov(df1, df2, n)` | 3 个参数 | df1 和 df2 的 AST 不得相同 |

#### 数学单参数算子

| 算子 | 签名 | 说明 |
|---|---|---|
| `Abs(df)` | 1 个参数 | 绝对值 |
| `Log(df)` | 1 个参数 | 自然对数（df 须为正）|
| `Sign(df)` | 1 个参数 | 符号函数，返回 -1/0/1 |
| `Sqrt(df)` | 1 个参数 | 平方根 |
| `Exp(df)` | 1 个参数 | e 的 df 次方（pandas 版 clip 上限 500 防溢出）|
| `Ceil(df)` | 1 个参数 | 向上取整 |
| `Floor(df)` | 1 个参数 | 向下取整 |
| `Neg(df)` | 1 个参数 | 取反（等价于 `-df`）|
| `Inv(df)` | 1 个参数 | 倒数（1/df）|

> **Polars 版本注意**：以上单参数算子已通过 `_ensure_expr(x)` 处理，支持直接传入 Python `int`/`float` 常量（如 `Sign(1)`）。

#### 数学双参数算子与别名

| 算子 | 别名 | 说明 |
|---|---|---|
| `Add(a, b)` | `Plus(a, b)` | 加法 |
| `Sub(a, b)` | `Minus(a, b)`, `Subtract(a, b)` | 减法（两参数相同时 AST 验证拒绝）|
| `Mul(a, b)` | `Mult(a, b)`, `Multiply(a, b)` | 乘法 |
| `Div(a, b)` | `Divi(a, b)`, `Divide(a, b)` | 除法（两参数相同时 AST 验证拒绝）|
| `Pow(a, b)` | — | 幂运算 |
| `Max(a, b)` | — | 逐元素取大 |
| `Min(a, b)` | — | 逐元素取小 |

#### 逻辑与条件算子

| 算子 | 签名 | 说明 |
|---|---|---|
| `If(cond, a, b)` | 3 个参数 | 逐元素条件：True → a，False → b |
| `Greater(a, b)` | — | a > b |
| `Less(a, b)` | — | a < b |
| `GreaterEqual(a, b)` | — | a >= b |
| `LessEqual(a, b)` | — | a <= b |
| `Equal(a, b)` | — | a == b |
| `NotEqual(a, b)` | — | a != b |
| `And(a, b)` | — | 逻辑与 |
| `Or(a, b)` | — | 逻辑或 |
| `Not(a)` | — | 逻辑非 |
| `Clip(df, lower, upper)` | — | 截断至 [lower, upper] |

#### 内部算子（Rust 编译器生成，不由 LLM 直接使用）

| 算子 | 说明 |
|---|---|
| `Const(x)` | 将常量 x 包装为 Polars `pl.lit(x)`，由 Rust 编译器自动插入 |

---

### 7.3 AST 验证规则

`FactorAgent._validate_qlib_expression(expr: str) -> (bool, str)` 顺序执行以下检查（任一失败即返回 `(False, 错误信息)`）：

1. **非空检查**：`expr` 不能为空或纯空白
2. **LLM 拒绝语检测**：含 `"Cannot be expressed"` 或 `"whitelist"` 说明 LLM 返回了解释文本而非代码，直接拒绝
3. **括号平衡**：使用 depth 计数器遍历全字符串，检测多余 `)` 或未闭合 `(`
4. **字段引用检查**：表达式中必须至少包含一个 `$field`（纯常量无意义）
5. **字段白名单**：正则 `\$\w+` 提取全部字段引用，逐一对照 `QLIB_FIELDS`，不在白名单中的字段报错并列出白名单内容
6. **AST 解析**：将 `$field` 替换为 `field_xxx` 后 `ast.parse(expr, mode="eval")`，SyntaxError 时报具体错误信息
7. **算子白名单**：遍历所有 `ast.Call` 节点，检查 `node.func.id` 是否在 `QLIB_OPERATORS` 中（允许 `fields`、`np`、`pd`）
8. **单参数算子上限检查**：`Rank`/`CSRank` 的位置参数 `> 1` 时拒绝（详见 `unary_ops` 集合中的其他算子检查）
9. **双参数算子下限检查**：`Mean`、`Std`、`Ref`、`Delta`、`Corr` 等需要 `arg_count >= 2`
10. **三参数算子下限检查**：`Corr`、`Cov`、`Ts_Percentile`、`If` 需要 `arg_count >= 3`
11. **恒等式检测（Tautology）**：`Div/Divi/Divide/Sub/Subtract/Minus` 的两个参数 `ast.dump()` 相同时拒绝（结果恒为常数）
12. **自相关检测**：`Corr/Correlation/Cov` 的前两个参数 `ast.dump()` 相同时拒绝（结果恒为 1.0）
13. **Look-ahead 检测**：`Ref(x, n)` 中若 n 为负整数（`ast.Constant` 或 `ast.UnaryOp(USub, Constant)` 解析），则拒绝

---

### 7.4 Rust 编译器 vs Python 回退

**`PolarsEngine.evaluate(expression)`** 两步降级：

**步骤 1 — Rust 编译器**（`lib.compile_alpha(expression)`）：
- 速度最快，将 Qlib 表达式编译为 Polars 惰性表达式字符串
- 若返回以 `"Error:"` 开头的字符串，降级到步骤 2

**步骤 2 — Python 回退**（`_python_compile_alpha`）：
- 正则将 `$field` 替换为裸名称
- eval 时依赖 `_ColFallback.__missing__` 将未知名称自动映射到 `pl.col(name)`
- 仍然失败则抛出异常

**`_eager_eval`**（`compute_all` 调用的路径）：
- 解析表达式为 Python AST
- 递归调用 `_eval_ast_node` 逐节点求值
- 为 `_CS_OPS` 和 `_TS_PLUGIN_OPS` 的复合参数物化临时列（见第 8.2 节）

---

## 8. 求值引擎

### 8.1 Pandas 矩阵引擎

**激活**：`--engine pandas`（默认，稳定性优于 Polars）

**设计思想**：将所有股票的某字段展开为 `(datetime × instrument)` 二维矩阵（`pd.DataFrame`）：
- 时间序列算子（Rolling）沿列（时间轴）操作
- 截面算子（Rank、CSZScore 等）沿行（截面，`axis=1`）操作

**eval 上下文**（`compute_factors()` 内部 `context` 字典）中包含的已实现函数：

| 类别 | 函数 |
|---|---|
| 截面 | `Rank`, `CSRank`, `CSZScore`, `GroupNeutral`, `Winsorize`, `Percentile`, `Scale` |
| 时序 | `Mean`, `Std`, `Median`, `EMA`, `WMA`, `Sum`, `Ref`, `Delta`, `Ts_Rank`, `Ts_Max`, `Ts_Min`, `Ts_ArgMax`, `Ts_ArgMin`, `Ts_Percentile` |
| 相关 | `Corr`, `Cov`, `Correlation` |
| 数学 | `Abs`, `Log`, `Sign`, `Sqrt`, **`Exp`**, **`Ceil`**, **`Floor`**, `Neg`, `Inv` |
| 双参数 | `Add`, `Sub`, `Mul`, `Div`, `Mult`, `Divi`, `Plus`, `Minus`, `Pow`, `Max`, `Min`, `Divide`, `Multiply`, `Subtract`, `Negate` |
| 逻辑 | `Greater`, `Less`, `GreaterEqual`, `LessEqual`, `Equal`, `NotEqual`, `And`, `Or`, `Not`, `If`, `Clip`, `Count` |
| 杂项 | `Const`, **`Scale`**, **`WMA`** |

> 加粗函数为近期补充（2026-04-15），之前版本存在 `name 'Exp' is not defined` 运行时错误。

**未知字段降级**（`compute_factors()` 第 575–590 行）：
- 包含 `"vol"` → `fields['volume']`
- 包含 `"share"` → `1.0`
- 其他 → `fields['close']`

**安全机制**：`SafeEvalTransformer`（`rq_eval.py`）将 eval 上下文中未知的 `Name` 节点转为字符串常量，阻止代码注入。

---

### 8.2 Polars 引擎与 eager_eval

**激活**：`--engine polars`

**`PolarsEngine._eager_eval(df, expr_str)`** 解决的核心问题：

在 Polars 中，`.over('instrument')` 嵌套在 `.over('datetime')` 内部会产生**全 null 输出**。`_eager_eval` 通过"两步物化"规避此限制：

1. 解析表达式为 Python AST
2. 递归调用 `_eval_ast_node` 求值
3. 遇到 `_CS_OPS` 算子时，若其**第一个数据参数**为复合表达式（非裸列引用），先物化为临时列（`__cs_arg_N__`），再将 `pl.col(tmp)` 传入算子
4. 遇到 `_TS_PLUGIN_OPS` 算子时，同样物化其**第一个数据参数**（Rust plugin 只能接收裸列引用）
5. 计算完成后统一删除所有临时列

```python
_CS_OPS = frozenset({
    "Rank", "CSRank", "CSZScore", "GroupNeutral", "Winsorize", "Percentile", "Scale"
})
_TS_PLUGIN_OPS = frozenset({
    "Ts_Rank",    # Rust plugin
    "Ts_ArgMax",  # Rust plugin
    "Ts_ArgMin",  # Rust plugin
})
```

**示例**：`CSRank(Ts_Rank(Log($close), 18))` 的求值过程：
1. `Log($close)` = `pl.col("close").log(math.e)` → 复合表达式
2. `Ts_Rank(复合, 18)` → `Ts_Rank` 在 `_TS_PLUGIN_OPS` 中 → 物化 `Log($close)` 为 `__ts_arg_0__`
3. `register_ts_rank(pl.col("__ts_arg_0__"), 18).over("instrument")` → 正确执行
4. 结果为 `pl.col("__cs_arg_1__")` 传入 `CSRank`（`_CS_OPS`）→ `.rank().over("datetime")`
5. 清理 `__ts_arg_0__` 和 `__cs_arg_1__`

**`_ensure_expr(x)`** 辅助函数：
```python
def _ensure_expr(x):
    if isinstance(x, (int, float)):
        return pl.lit(float(x))
    return x
```
确保 `Sign(1)`、`Abs(-2.5)`、`Exp(0)` 等常量参数不报 `AttributeError`。

---

## 9. RiceQuant 回测流程

**文件**：`core/alphaeval/rq_eval.py`，`RiceQuantEval` 类

### 回测参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `test_start_date` | `"2018-01-01"` | 回测开始（含 IS 和 OOS）|
| `test_end_date` | `"2025-12-31"` | 回测结束 |
| `oos_split_date` | `"2023-01-01"`（**硬编码**）| IS/OOS 分割点，早于此日期为 IS |
| `market` | `"000300.XSHG"`（沪深 300）| 股票池 |
| `daily_normalize` | `True` | 每日截面 Z-score 标准化 |
| `engine` | `"pandas"` | 因子计算引擎 |
| `noise_level` | `0.0` | 向原始数据注入高斯噪声（鲁棒性测试用）|
| `output_dir` | `"results/reports"` | 图表输出目录 |

### 完整执行步骤

**`fetch_data()`**：
1. `rq.index_components(market, test_end_date)` 获取成分股列表
2. `rq.get_price(instruments, fields=["close","open","high","low","volume","total_turnover"])` 拉取 OHLCV
3. MultiIndex 调整：`(order_book_id, date)` → `(datetime, instrument)`
4. 若 `noise_level > 0`：对每个数值列按各自标准差比例注入高斯噪声
5. label 计算：`close.shift(-1) / close - 1`（在 instrument 分组内 shift，避免跨股票数据泄漏）
6. 统一日期类型为 `datetime64[ns]`

**`compute_factors()`**（pandas 引擎）：
1. 将各字段 unstack 为 `(datetime × instrument)` 矩阵
2. 计算 vwap：`total_turnover / volume.replace(0, NaN)` → ffill → fallback to close
3. 通过 AST 安全求值执行表达式
4. `_normalize_factors()`：每日截面 Z-score 标准化（若 `daily_normalize=True`），填充 inf/nan → 0
5. 因子矩阵加权合并：`factor_data.dot(weights)` → `alphacombo`

**`run()`**（核心回测）：
1. 拼接 `alphacombo` 与 `label_data`，dropna
2. 全期 IC：`alphacombo.corr(label, method='pearson')`
3. IS IC（`< oos_split_date`）和 OOS IC（`>= oos_split_date`）分别计算
4. 调用 `calculate_layered_returns()` 分 5 组（G1 最低因子值，G5 最高）
5. G5-G1 多空收益 → `daily_ret`
6. Sharpe：`daily_ret.mean() / daily_ret.std() * sqrt(252)`
7. 最大回撤：`(cum_ret / cum_ret.cummax() - 1).min()`
8. 调用 `generate_plots()` 生成图表

**`calculate_layered_returns(all_data, n_groups=5)`**：
- `groupby('datetime', group_keys=False)['factor'].apply(assign_groups)` 分组
  - `group_keys=False`：防止 pandas 新版本 `apply` 默认 `group_keys=True` 导致额外索引层级（产生 3 级 MultiIndex 的 bug 已修复）
- `pd.qcut(x.rank(method='first'), n_groups, labels=['G1'...'G5'])` 等分分位数

**`generate_plots(daily_ret, layer_ret, factor_name)`**：
- 权益曲线：`(1 + daily_ret.fillna(0)).cumprod()`，标注 OOS 分割红线
- 分层收益：G1–G5 各组累积收益
- 保存为 PNG（`results/reports/<safe_name>_equity.png` 和 `_layers.png`）

**`dry_run(expression)`**（静态方法）：
- 用 5 行×1 列的假数据（`close=1..5`、`volume=1000`、`vwap=1..5`）运行表达式
- 不访问 RiceQuant API，不需要认证
- 返回 `(True, "OK")` 或 `(False, "错误信息")`

---

## 10. 模拟回退机制

当真实回测失败（`FileNotFoundError`/`ValueError`/`ImportError` 或任何其他 `Exception`）时，`_execute_alphaeval_backtest()` 降级为：

```python
seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
rng = random.Random(seed)
return {
    "information_coefficient": round(rng.uniform(-0.05, 0.15), 3),
    "rank_ic": round(rng.uniform(-0.05, 0.15), 3),
    "rre": round(rng.uniform(0.0, 1.0), 3),
    # ...其他随机指标...
    "daily_returns": {},    # 空！无法生成权益曲线
    "_simulated": True,
}
```

**为何是哈希确定性而非完全随机**：相同的 `code_expression` 每次运行都产生相同的模拟 IC，避免同一因子在多轮中得到不同的模拟评分，使 Wiki 记录更稳定。

**陷阱**：模拟 IC 范围（-0.05, 0.15）与真实 A 股优质因子 IC 范围（0.003–0.05）大量重叠，极易产生假阳性。

**四层保护机制**：

| 保护层 | 文件 | 机制 |
|---|---|---|
| 1 | `eval_agent.py` | `is_simulated=True` → 冻结 `best_ic` 和 `patience_counter` |
| 2 | `workflow/graph.py` | 模拟 IC ≥ 0.05 → 跳过早停，打印 WARNING 继续 |
| 3 | `eval_agent.py` | 模拟数据不写入 RAG（经验库不污染）|
| 4 | `manager.py` | `daily_returns` 为空 → `returns series` 为空 → 第一轮过滤剔除 |

**常见触发原因**：
- RiceQuant Quota 耗尽（`Quota exceeded`，最常见）
- RiceQuant 账号未认证或 Token 过期
- 因子计算运行时错误（除零、字段不存在、括号层级错误等）
- 数据日期范围无数据

---

## 11. 早停与 patience 机制

### patience_counter 更新规则

| 条件 | `best_ic` | `patience_counter` | `best_code_expression` |
|---|---|---|---|
| `is_simulated=True` | **不变** | **不变** | 不变 |
| `current_ic > best_ic`（真实）| = `current_ic` | = 0（清零）| = 当前代码 |
| `current_ic <= best_ic`（真实）| 不变 | += 1 | 不变 |

### 早停触发条件（`route_after_wiki`）

| 条件 | 结果 | 备注 |
|---|---|---|
| `current_ic >= 0.05 AND NOT is_simulated` | `"end"` | 发现优质因子，记 SUCCESS 日志 |
| `current_ic >= 0.05 AND is_simulated` | 继续 | 打印 WARNING，防止 Quota 触发假早停 |
| `patience_counter >= 4` | `"end"` | 连续 4 轮无 IC 改善 |
| `iteration >= max_iterations` | `"end"` | 轮数耗尽 |

### 参数调优建议

| 参数 | 当前值 | 理由 |
|---|---|---|
| `max_iterations` | 5（默认）| 低于 5 轮 Wiki 知识无法充分积累；建议 5–7 |
| `patience_counter 阈值` | 4 | 旧值 3 太保守；4 给更多探索空间 |
| Manager IC 门槛 | 0.005 | A 股真实有效因子 IC 多在 0.003–0.008，旧值 0.01 过高 |
| 早停 IC 门槛 | 0.05（非模拟）| 真实 IC ≥ 0.05 在 A 股属于极优质因子 |

---

## 12. 知识库系统

### 12.1 RAGModule

**文件**：`core/rag.py`

- 向量数据库：ChromaDB，持久化在 `data/chroma_db/`
- Embedding 模式：
  - **API 模式**（默认）：按 LLM 提供商选择对应的 OpenAI-compatible embedding API
  - **本地模式**（`USE_LOCAL_EMBEDDING=true`）：`Qwen/Qwen3-Embedding-4B`，支持 GPU（`--use-gpu`）；HuggingFace 镜像备用（`hf-mirror.com`）
- 文档来源：`data/rag_docs/`（Markdown 格式）
- `rebuild=True`（`--rebuild-rag`）：强制重新 Embedding 所有文档
- `add_experience(hypothesis, code, metrics, is_effective, review)`：将每次**真实**回测经验以文档形式写入 ChromaDB，供后续 Agent 检索

### 12.2 LLMWiki

**文件**：`core/wiki.py`

存储**经过验证的结构化因子卡片**，格式为带 YAML frontmatter 的 Markdown 文件。

文件位置：
- `data/wiki_vault/`：人类可读 Markdown（可用 Obsidian 打开查看）
- `data/wiki_db/`：ChromaDB 向量索引（机器检索用）

**卡片 Frontmatter 结构**：
```yaml
---
title: "因子名称（人类可读）"
slug: "snake_case_unique_id"
type: "factor_card"
status: "active"      # active | failed | deprecated
summary: "一句话描述因子逻辑"
updated: "2026-04-15"
tags: ["momentum", "mean_reversion", "volume"]
related: ["correlated_factor_slug"]
---

## 核心逻辑

（因子的经济直觉和数学描述）

## 代码实现

```
Qlib 表达式
```

## 历史表现

IC 均值: 0.023 | RankIC: 0.021 | OOS IC: 0.019
```

**卡片来源**：
- `WikiBootstrapper`（`--wiki-bootstrap`）：在 swarm 启动前将 `data/rag_docs/` 中的文档批量 LLM 编译为卡片，存入 `wiki_vault/`
- `HybridKnowledge.update_wiki_after_eval(state)`：每轮 `wiki_update` 节点后调用，将本轮因子的结果（无论成功或失败）写入 Wiki，供后续 Agent 学习

**去重机制**：Wiki 按 `slug` 去重；同一因子多次实验时更新 `status` 和性能指标，不创建重复卡片

### 12.3 HybridKnowledge

**文件**：`core/hybrid_knowledge.py`

融合两个知识源的门面类，屏蔽 RAG 和 Wiki 的实现细节。

```
retrieve(query, n_results=3) 流程：
  1. rag_context  = RAG.retrieve(query, n_results)   → 原始语料检索结果
  2. wiki_context = Wiki.retrieve(query, n_results)  → 结构化因子卡片检索结果
  3. 去重：提取 wiki_context 中所有 **标题** 模式（`re.match(r"\*\*(.+?)\*\*", line)`）
         → 若 rag_context 某行（小写后）包含这些标题中的任意一个 → 丢弃该行
  4. 返回："[RAG CONTEXT]\n{去重后}\n\n[WIKI CONTEXT]\n{wiki_context}"
```

`update_wiki_after_eval(state)`：
- 从 state 提取 `hypothesis_name`、`code_expression`、`backtest_metrics`、`is_effective`、`suggested_improvements`
- 生成或更新对应 Wiki 卡片
- 更新 `data/wiki_vault/log.md`（追加本轮记录）和 `data/wiki_vault/index.md`

`bootstrap_wiki(force=False)`：
- 调用 `WikiBootstrapper.run(force=False)`，若 `force=False` 则跳过已有卡片的文档

---

## 13. LLM 网关

**文件**：`core/llm.py`

`get_llm(temperature, model_name, provider)` 返回 LangChain `BaseChatModel`（`ChatOpenAI` 兼容实例）。

### 支持的 Provider

| Provider 名 | 环境变量 | 默认模型 | Base URL |
|---|---|---|---|
| `kimi` | `LLM_KEY` / `KIMI_API_KEY` | `kimi-k2-turbo-preview` | `https://api.moonshot.cn/v1` |
| `qwen` | `QWEN_API_KEY` | `qwen-max` | dashscope（阿里）|
| `glm` | `GLM_KEY` / `ZHIPU_API_KEY` | `glm-5` | bigmodel（智谱）|
| `openai` | `OpenAI_KEY` / `OPENAI_API_KEY` | `gpt-4o` | `https://api.openai.com/v1` |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-reasoner` | `https://api.deepseek.com/v1` |
| `claude` | `ClaudeCode_KEY` / `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` | Anthropic |
| `openrouter` | `OPENROUTER_API_KEY` | `anthropic/claude-sonnet-4-6` | `https://openrouter.ai/api/v1` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | Groq |
| `ollama` | 固定 `"ollama"` | `llama3` | `http://localhost:11434/v1` |
| `vllm` | 固定 `"vllm"` | `meta-llama/...` | `http://localhost:8000/v1` |

**自动检测顺序**：不指定 `--llm-provider` 时，按上表从上到下扫描，使用第一个有效 API key 的 provider。

**Temperature 约定**：

| Agent | Temperature | 设计意图 |
|---|---|---|
| IdeaAgent | 0.7 | 鼓励多样性，产生新颖假说 |
| FactorAgent | 0.1 | 精确代码生成，避免随机语法错误 |
| EvalAgent | 0.4 | 评审需要一定灵活性，但不能太发散 |
| SummaryAgent | 0.3 | 专业报告写作，保持客观 |

---

## 14. Manager 与 SubAgent 协调

### SubAgent 初始状态

每个 `AlphaResearcher.run()` 启动时注入 LangGraph 的初始状态：

```python
{
    "iteration": 1,
    "max_iterations": max_iterations,         # 默认 5，由 --iterations 覆盖
    "role_prompt": role_prompt,               # 角色描述字符串
    "evaluation_mode": evaluation_mode,       # "ricequant" | "qlib"
    "evaluation_engine": evaluation_engine,   # "pandas" | "polars"
    "market_analysis_start_date": market_start,
    "market_analysis_end_date": market_end,
    "best_ic": -999.0,                        # 初始化为极小值
    "patience_counter": 0,
    "messages": ["[System] Starting SubAgent with Role: ..."],
    # 所有其他字段均为 None（TypedDict total=False）
}
```

### SubAgent 结果对象（`AlphaResearcher.run()` 返回）

```python
{
    "role": role_prompt,
    "hypothesis": hypothesis_name,             # 最终假说名称
    "code": code_expression,                   # 最终代码表达式
    "metrics": backtest_metrics,               # 完整指标字典
    "perf_metric": float,                      # = IC，主排序指标
    "returns": pd.Series,                      # 日期索引日收益序列（模拟时为空）
    "is_effective": bool,                      # LLM 评审结论
    "error": Optional[str],                    # 若 workflow 异常则非空
    "plot_paths": dict,                        # 图片绝对路径（equity, layers）
}
```

`perf_metric` 强制等于 `backtest_metrics["information_coefficient"]`（不使用 Sharpe 或其他指标），与 Manager 门槛（0.005）统一。

### SQLite 表结构

```sql
-- results/alpha_miner.db，WAL 模式
CREATE TABLE IF NOT EXISTS alpha_pool (
    id           TEXT PRIMARY KEY,     -- "alpha_" + UUID hex[:8]
    role         TEXT,                 -- 角色 prompt
    hypothesis   TEXT,                 -- 假说名称
    code         TEXT,                 -- Qlib 表达式
    ic           REAL,                 -- IC 值
    rank_ic      REAL,                 -- RankIC 值
    report_path  TEXT,                 -- Markdown 报告绝对路径
    metrics_json TEXT,                 -- 完整 metrics 字典的 JSON 字符串
    returns_json TEXT,                 -- {iso_date: float} 日收益字典
    is_effective INTEGER,              -- 0 或 1
    perf_metric  REAL                  -- = IC
);
```

数据库的 WAL 模式（`PRAGMA journal_mode=WAL`）允许并发读取——TUI/HTTP API 读取时不会被 SubAgent 写入操作阻塞。

---

## 15. 输出结构

```
results/
├── alpha_miner.db           # SQLite 因子池（主要存储，WAL 模式）
├── factor_pool.json         # JSON 备份（字段结构与 SQLite 相同）
├── reports/
│   ├── <factor_name>.md           # LLM 生成的 Markdown 研究报告
│   ├── <factor_name>_equity.png   # 权益曲线（含 OOS 红色分割线，由 RiceQuantEval 生成）
│   └── <factor_name>_layers.png   # G1–G5 分层累积收益图
└── charts/
    └── <factor_id>_curve.png      # SummaryAgent 生成的简版权益曲线

data/
├── rag_docs/                # RAG 原始文档（Markdown 格式，手动维护）
├── chroma_db/               # ChromaDB 向量索引（RAG 用）
├── wiki_vault/              # LLMWiki Markdown 卡片（可用 Obsidian 打开）
│   ├── index.md             # 因子总览索引
│   ├── log.md               # 每轮更新日志
│   ├── market_regime_base.md    # 市场状态基础文档
│   ├── strategy_families_base.md # 策略族群基础文档
│   └── <factor_slug>.md     # 各因子卡片（由系统自动生成）
└── wiki_db/                 # ChromaDB 向量索引（Wiki 用）
    ├── glm_embedding-3/     # GLM embedding 索引
    └── openai_text-embedding-3-large/  # OpenAI embedding 索引
```

---

## 16. AlphaMinerState 字段说明

**文件**：`workflow/state.py`，`class AlphaMinerState(TypedDict, total=False)`

`total=False` 表示所有字段均可选，未设置时为 `None`。

| 字段 | 类型 | 生命周期 | 说明 |
|---|---|---|---|
| `iteration` | `int` | 持久（跨轮递增）| 当前轮数，从 1 开始 |
| `max_iterations` | `int` | 持久 | 最大轮数上限 |
| `rag_context` | `str` | 单轮（不清空）| 本轮检索到的 RAG+Wiki 拼接文本 |
| `wiki_context` | `str` | 单轮（wiki_update 节点更新）| Wiki 检索结果 |
| `market_regime_summary` | `str` | **跨轮缓存** | 市场状态描述，IdeaAgent 首次拉取后缓存 |
| `macro_news_summary` | `str` | **跨轮缓存** | 宏观新闻摘要，IdeaAgent 首次拉取后缓存 |
| `hypothesis_name` | `str` | 单轮（increment 清空）| 本轮假说名称 |
| `hypothesis_description` | `str` | 单轮（increment 清空）| 假说详细描述 |
| `rationale` | `str` | 单轮（increment 清空）| 经济直觉说明 |
| `math_formula` | `str` | 单轮（increment 清空）| LaTeX 数学公式 |
| `variables_defined` | `Dict[str, str]` | 单轮（increment 清空）| 公式变量定义字典 |
| `code_expression` | `str` | 单轮（increment 清空）| Qlib 表达式字符串 |
| `is_valid_syntax` | `bool` | 单轮（increment 重置 True）| AST 验证结果 |
| `backtest_metrics` | `Dict[str, float]` | 单轮（increment 清空）| 回测指标字典 |
| `daily_returns` | `Dict[str, float]` | 单轮（SubAgent 结束时读取）| `{iso_date: float}` 日收益 |
| `review_summary` | `str` | 单轮（increment 清空）| LLM 评审摘要 |
| `is_effective` | `bool` | 单轮（increment 清空）| LLM 评审是否认定有效 |
| `is_simulated` | `bool` | 单轮（increment 重置 False）| 本轮是否使用模拟指标 |
| `suggested_improvements` | `str` | 单轮（increment 清空）| 传递给下一轮 IdeaAgent 的改进建议 |
| `best_ic` | `float` | **持久**（模拟数据不更新）| 历史最佳真实 IC，初始 -999.0 |
| `best_code_expression` | `Optional[str]` | **持久** | 产生 best_ic 的代码表达式 |
| `patience_counter` | `int` | **持久**（模拟数据不更新）| 连续无改善轮数 |
| `role_prompt` | `Optional[str]` | 持久（从不改变）| 本 SubAgent 的角色描述 |
| `evaluation_mode` | `str` | 持久 | `"ricequant"` 或 `"qlib"` |
| `evaluation_engine` | `str` | 持久 | `"pandas"` 或 `"polars"` |
| `market_analysis_start_date` | `Optional[str]` | 持久 | 市场分析起始日 |
| `market_analysis_end_date` | `Optional[str]` | 持久 | 市场分析截止日 |
| `market_analysis_lookback_days` | `Optional[int]` | 持久 | 回望天数（默认 60）|
| `error` | `Optional[str]` | 单轮（increment 清空）| 节点错误信息 |
| `messages` | `List[str]` | **追加合并**（`Annotated[List, operator.add]`）| 全程日志消息流 |

---

## 17. 关键参数速查

| 参数 | 文件:行 | 当前值 | 可配置方式 |
|---|---|---|---|
| IC 过滤门槛 | `manager.py:182` | `0.005` | 直接修改源码 |
| 相关性剔除阈值 | `manager.py:226` | `0.7` | 直接修改源码 |
| 早停 IC 门槛 | `graph.py:55` | `0.05`（仅真实数据）| 直接修改源码 |
| patience 上限 | `graph.py:59` | `4` | 直接修改源码 |
| SubAgent 默认迭代数 | `sub_agent.py:10` | `5` | `--iterations` 命令行参数 |
| OOS 分割日期 | `rq_eval.py:119` | `"2023-01-01"`（硬编码）| 修改源码 |
| 默认股票池 | `rq_eval.py:109` | `"000300.XSHG"`（沪深 300）| `RiceQuantEval(market=...)` |
| 默认回测开始 | `rq_eval.py:107` | `"2018-01-01"` | `--market-start` |
| 默认回测结束 | `rq_eval.py:108` | `"2025-12-31"` | `--market-end` |
| FactorAgent 最大重试 | `factor_agent.py:~351` | `2` | 直接修改源码 |
| SubAgent 启动抖动 | `manager.py:23` | `0.1–1.0 秒` | 直接修改源码 |
| SubAgent 超时 | `manager.py:284` | `600 秒` | 直接修改源码 |
| 遗传杂交 IC 门槛 | `manager.py:327` | `0.01` | 直接修改源码（高于普通因子门槛）|
| context 截断长度 | `idea_agent.py:~117` | `6000 字符` | 直接修改源码 |
| 市场状态回望天数 | `idea_agent.py:~81` | `60 天` | state 字段 `market_analysis_lookback_days` |

---

## 18. 已知问题与规避方式

### 问题 1：RiceQuant Quota 耗尽

**现象**：大量 `RiceQuant backtest unexpected failure: Quota exceeded`，后续 IC 全为模拟随机值。

**根本原因**：RiceQuant 按数据调用量计费，多进程并发时极易超限。

**保护**：`is_simulated=True` 全面隔离，4 层保护防止污染（见第 10 节）。

**规避措施**：
- 减少 `--iterations`（每轮一次完整 RQ 请求）
- 避免 `--parallel`（串行可复用单次数据拉取）
- 指定更短的回测区间（`--market-start 2020-01-01 --market-end 2022-12-31`）
- 多个 SubAgent 间共享一次数据拉取（需架构改造）

---

### 问题 2：Polars 嵌套表达式求值

**现象**：`CSRank(Ts_Rank(Log($close), 18))` 等深层嵌套在 Polars 引擎下产生全 null 输出，或 Rust plugin 函数报 `TypeError`。

**根本原因**：
- Polars `.over('instrument')` 嵌套在 `.over('datetime')` 内会产生全 null
- Rust plugin 函数只能接收裸 `pl.col()` 引用，不能接收复合惰性表达式

**保护**：`_eager_eval` 的 `_CS_OPS` + `_TS_PLUGIN_OPS` 物化机制（见第 8.2 节）。

**规避措施**：
- 复杂嵌套因子优先用 `--engine pandas` 测试；Polars 引擎用于性能优化，不用于调试
- 遇到 Polars 错误时，检查是否为新增的嵌套模式，考虑将相关算子加入 `_TS_PLUGIN_OPS`

---

### 问题 3：LLM 幻觉字段

**现象**：`FactorAgent` 生成含 `$beta_spx`、`$market_cap`、`$sector` 等不存在字段的表达式。

**根本原因**：LLM 将常见量化文献中的变量名直接用作字段名，而非遵守白名单。

**保护**：`_validate_qlib_expression` 字段白名单检查（步骤 5），错误信息中列出完整白名单，触发 FactorAgent 重试时 LLM 能看到正确字段列表。

**规避措施**：在 system prompt 中显式列出禁止字段示例（已实现），并在每次重试时重申白名单（已通过 sliding window 对话传递）。

---

### 问题 4：LLM 生成恒等式因子

**现象**：`Divide($close, $close)`、`Sub($volume, $volume)` 等截面全为常数的因子通过语法检查，最终因 empty returns 被 Manager 剔除，但浪费了一次回测 Quota。

**根本原因**：LLM 为了通过验证器，简化公式到极端情况。

**保护**：AST 级恒等式检测（验证步骤 11），在回测前即拦截。

---

### 问题 5：Rank 传入双参数

**现象**：LLM 参考 WorldQuant Alpha101 写法，调用 `Rank($close, 20)`（将窗口参数传给截面 Rank）。

**根本原因**：Alpha101 的 rank 函数有时序参数，但我们的系统 `Rank` 是纯截面操作。

**保护**：验证器 `unary_ops` 集合检查，`Rank`/`CSRank` 位置参数 > 1 时拒绝，错误信息明确说明"Rank 是截面操作，无窗口参数"。

---

### 问题 6：Look-ahead Bias（未来数据）

**现象**：`Ref($close, -1)` 使用负偏移引用未来价格。

**保护**：验证步骤 13，`Ref` 第二参数为负整数时拒绝。

---

### 问题 7：Self-Correlation（自相关）

**现象**：`Corr(Delta($close,3), Delta($close,3), 30)` 自相关，结果恒为 1.0，是无效因子。

**保护**：验证步骤 12，两数据参数 `ast.dump()` 相同时拒绝。

---

### 问题 8：Exp/Ceil/Floor 在 pandas 引擎中不存在

**现象**：`name 'Exp' is not defined`，LLM 生成了合法白名单算子，但 pandas eval 上下文中未注册。

**保护**：已于 2026-04-15 将 `Exp`、`Ceil`、`Floor`、`Scale`、`WMA` 补充到 `context` 字典（`rq_eval.py` 第 557–580 行）。

---

## 19. 测试

### pytest 测试套件

```bash
# 全量测试
python -m pytest tests/

# 数值一致性：pandas 与 polars 引擎结果对比
python -m pytest tests/test_numerical_consistency.py

# Polars 算子全面测试（含嵌套）
python -m pytest tests/test_polars_ops_extensive.py -v
```

### 独立脚本（非 pytest，需要 RiceQuant 账号）

```bash
python test_eval.py    # 端到端回测流程测试
python test_ctx.py     # 上下文检索与知识库测试
```

### 验证器单元测试（无需任何外部账号）

```python
from agents.factor_agent import FactorAgent
fa = FactorAgent.__new__(FactorAgent)

# 应通过（ok=True）
assert fa._validate_qlib_expression("CSRank(Ts_Rank(Log($close), 18))")[0]
assert fa._validate_qlib_expression("Div(Delta($close,5), Ref($close,5))")[0]
assert fa._validate_qlib_expression("Corr(Delta($close,5), Delta($volume,5), 20)")[0]
assert fa._validate_qlib_expression("Exp(Std($close, 10))")[0]

# 应拒绝（ok=False）
assert not fa._validate_qlib_expression("Rank($close, 20)")[0]           # Rank 双参数
assert not fa._validate_qlib_expression("Divide($close, $close)")[0]     # 恒等式
assert not fa._validate_qlib_expression("Sub($volume, $volume)")[0]      # 恒等式
assert not fa._validate_qlib_expression("Ref($close, -1)")[0]            # look-ahead
assert not fa._validate_qlib_expression("Corr(Delta($close,3), Delta($close,3), 30)")[0]  # 自相关
assert not fa._validate_qlib_expression("Rank($beta_spx)")[0]            # 非法字段
assert not fa._validate_qlib_expression("SomeFakeOp($close, 10)")[0]     # 非法算子
assert not fa._validate_qlib_expression("Ref($close, Mean($close, 5))")[0]  # 动态窗口（无字段引用）
```

### Polars 引擎快速验证

```python
import polars as pl
from core.alphaeval.polars_engine import Sign, Abs, Exp, PolarsEngine

# 常量参数测试
assert isinstance(Sign(1), pl.Expr)
assert isinstance(Abs(-2.5), pl.Expr)
assert isinstance(Exp(0), pl.Expr)

# _TS_PLUGIN_OPS 集合验证
pe = PolarsEngine()
assert "Ts_Rank" in pe._TS_PLUGIN_OPS
assert "Ts_ArgMax" in pe._TS_PLUGIN_OPS
```

---

## 20. 开发规范

### 新增算子

遵循"三处必改"原则：

**1. 实现引擎**（至少一处，建议两处都改）：

- **Polars 引擎**（`core/alphaeval/polars_engine.py`）：
  - 在文件顶层定义算子函数，单参数算子内调用 `_ensure_expr(x)` 处理常量参数
  - 若算子内部使用 Rust plugin（`register_plugin_function`）：加入 `_TS_PLUGIN_OPS`
  - 若算子内部使用 `.over('datetime')`（截面）：加入 `_CS_OPS`
  - 在 `PolarsEngine.context` 字典中注册

- **Pandas 引擎**（`core/alphaeval/rq_eval.py`，`compute_factors()` 内部）：
  - 在函数体内定义同名函数（操作 `(datetime × instrument)` 二维矩阵）
  - 在 `context` 字典中注册
  - 注意：pandas 矩阵引擎中时序操作沿 Rolling 轴（单只股票），截面操作沿 `axis=1`

**2. 算子白名单**（`agents/factor_agent.py`）：
  - 将算子名加入 `QLIB_OPERATORS` 集合（`FactorAgent` 类顶部）
  - 在 `OPERATOR_SIGNATURES` 字符串中添加完整签名说明（含参数含义和约束）
  - 更新对应的参数数量检查集合：
    - 1 个参数的算子 → 加入 `unary_ops`
    - 2 个参数的算子 → 加入 `binary_ops`
    - 3 个参数的算子 → 加入 `ternary_ops`

---

### 新增 LLM Provider

在 `core/llm.py` 中：

1. `get_llm_config()` 的 `providers` 字典中添加 `"new_provider": os.getenv("NEW_PROVIDER_API_KEY")`
2. `get_llm()` 中添加 `elif provider == "new_provider":` 分支，设置 `base_url` 和默认 `model_name`
3. 在 `.env.example` 中添加对应变量示例

---

### 修改路由逻辑

路由函数（`workflow/graph.py`）必须保持**纯函数**：
- 只读取 `state`，不修改
- 只返回字符串节点名称（或 `"end"`）
- 不调用任何有副作用的函数

状态修改应在：
- Agent 节点（`__call__` 方法返回的字典）
- `increment_iteration` 函数

---

### 新增验证规则

在 `FactorAgent._validate_qlib_expression()` 的 `for node in ast.walk(tree)` 循环内，遵循以下模式：

```python
# 在恰当位置插入
if op in {"待检查算子名"}:
    # 验证逻辑
    if <错误条件>:
        return (
            False,
            f"明确说明：是什么问题 + 如何修复的错误信息（LLM 在重试时会看到此信息）",
        )
```

**原则**：
- 错误信息必须**可操作**：告诉 LLM 具体哪里错了、应该怎么改
- 不要使用过于宽泛的错误信息（如"表达式无效"），这会导致 LLM 无法定向修复

---

### 状态清理约定（increment 节点）

`increment_iteration()` 函数（`workflow/graph.py`）负责清空所有**单轮临时字段**。

**规则**：新增任何仅用于单轮的 state 字段时，**必须**在 `increment_iteration` 返回的字典中显式设为 `None`（或适当的默认值），否则上一轮残留值会在下一轮中被错误使用（状态污染）。

**跨轮字段（不清空）**：`best_ic`、`patience_counter`、`best_code_expression`、`market_regime_summary`、`macro_news_summary`、`role_prompt`、`evaluation_mode`、`evaluation_engine`、`market_analysis_*`

---

### 模拟状态的处理原则

任何新增的基于回测指标的逻辑，都必须检查 `is_simulated` 标志：

```python
if not is_simulated:
    # 只有真实回测数据才执行的逻辑
    do_something_with_real_metrics()
```

绝对不能在 `is_simulated=True` 时：
- 更新 `best_ic` 或 `patience_counter`
- 向 RAG 或 Wiki 写入经验
- 将因子纳入 Manager 筛选候选池（`daily_returns` 为空自然被剔除，但不应依赖此默认行为）

---

### 代码格式与注释

- 关键业务逻辑必须有行内注释说明**为什么**这么做，而非只说做了什么
- 修改早停逻辑、验证规则、知识库更新等高风险路径时，在 PR 中说明对哪些陷阱做了测试
- 所有 LLM prompt 的修改需同步更新本文档第 6 节对应的"关键 Prompt 约束"或"强制规则"列表
