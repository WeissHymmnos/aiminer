# LLM Provider Switch History — ox-alpha / opencode-go / CPA gemini (2026-08-21)

本文档详细记录 2026-08-21 当天 LLM 接入与切换的全部操作、根因分析、踩坑与修复。
对应代码改动：`scripts/hermes_auto_runner.py`、`.env`、skill `aminer-daemon`。

---

## 背景

- 原 LLM：MiMo（Mimo-v2.5 / v2.5pro，`https://token-plan-cn.xiaomimimo.com/v1`），因 FactorAgent 频繁超时弃用。
- 用户要求：把本机 Hermes 里用的 **ox-alpha** 模型接入 AIMiner swarm。

## Hermes 侧模型链路（调研结论）

| 模型显示名 | 实际 provider | 端点 | 模型 ID | key 来源 |
|---|---|---|---|---|
| ox-alpha（当前对话模型） | opencode-go | `https://opencode.ai/zen/go/v1` | `ox-alpha-free` | `OPENCODE_GO_API_KEY`（~/.hermes/.env，67位 sk-Umw80...） |
| ox-alpha 备选路由 | openrouter | `https://openrouter.ai/api/v1` | `stealth/ox-alpha` | `OPENROUTER_API_KEY` |
| Gemini 3.7 Flash high | 本机 CPA 反代 (cli-proxy-api 7.2.54) | `http://127.0.0.1:8317/v1` | `gemini-3.7-flash-high` | `huahongrui`（config.yaml api-keys） |

- OpenRouter 免费层 stealth 模型每日 1000 次（北京时间 08:00 重置），当天 19:18 打满 → 弃用该路由。
- opencode-go 端点 quirks：
  - 裸 urllib 无浏览器 UA 会 403；openai SDK 正常。
  - `/v1/models` 需要 UA；chat/completions 不需要。
- CPA (cli-proxy-api) quirks：
  - 本地访问 key 是 config.yaml `api-keys:` 列表项（明文 `huahongrui`），不是上游 key。
  - 管理 API 用同一 key：`GET /v0/management/auth-files`（账户状态）、`/v0/management/api-key-usage`。
  - antigravity 账户是 standard-tier 免费个人版，Google 不暴露剩余配额计数器；只能看成功/失败计数与 cooldown 状态。

## 最终接入方式（当前生效）

AIMiner 的 `core/llm.py` 走 LangChain ChatOpenAI，opencode-go 是 OpenAI 兼容端点，
因此**零代码改动**接入：

```python
DEFAULT_COMMAND = [
    DEFAULT_PYTHON,
    "-m", "aiminer.manager",          # src/ 布局迁移后根目录 manager.py 已删
    "--iterations", "300",
    "--mode", "ricequant",
    "--data-backend", "local",
    "--engine", "polars",
    "--llm-provider", "openai",       # OpenAI 兼容协议
    "--llm-model", "ox-alpha-free",
    "--llm-base-url", "https://opencode.ai/zen/go/v1",
    ...
]
```

### hermes_auto_runner.py 三处配套改动

1. **启动入口改为 `-m aiminer.manager`**
   - 根目录 manager.py 在 src 迁移中删除，conda env 未安装包 → 必须 `PYTHONPATH=src`。
   - `_with_run_id()` 的目标检测同步加了 `"aiminer.manager"` 分支。

2. **start() 注入子进程环境**
   ```python
   child_env["PYTHONPATH"] = f"{ROOT}/src{os.pathsep}{existing}" 
   child_env.update(_load_project_env_overrides())   # 新增函数
   ```
   - `_load_project_env_overrides()`：解析项目 `.env`，覆盖继承的 shell 环境变量。
   - **原因（401 根因）**：用户 shell 导出了旧 `OpenAI_KEY`（settings.py 对 provider=openai 的首选变量），
     `load_dotenv()` 默认不覆盖已有变量 → 子进程拿到旧 key → 401 Invalid API key。
   - 项目 `.env` 双写 `OPENAI_API_KEY=` 和 `OpenAI_KEY=` 两个名字。

3. **删除 `_apply_model_for_mode()` 的 MiMo 换模逻辑**
   - 原逻辑 auto=Mimo-v2.5pro / manual=Mimo-v2.5 会强制覆盖 --llm-model，必须移除。

## 当天切换时间线

| 时间 | 操作 | 结果 |
|---|---|---|
| 19:33 | 切 openrouter stealth/ox-alpha 并启动 | 19:18 配额已满，全 429，空转 |
| 19:28-19:32 | 改走 opencode-go 直连 + 修 shell 旧 OpenAI_KEY 401 | 冒烟通过 |
| 19:59 | 启动 swarm (ox-alpha-free via opencode-go) | 正常，IC 最高 0.0197 |
| 20:48-21:00 | 应用户要求切 CPA gemini-3.7-flash-high | 结构化输出验证通过后切换 |
| 21:00-22:50 | gemini 轮运行 | 70 策略入库，最佳 Sharpe 1.02 |
| 21:46-22:54 | **watch daemon 缓存旧配置**，自动重启的轮次仍用 ox-alpha+新key → 401 空转 3 轮 | 杀老 watch 重启修复 |
| 22:34 | 查 CPA 双账户额度（管理API） | 两账户 active，428/442 成功，无限流 |
| 23:00 | 应用户要求切回 ox-alpha-free | 重启 watch+swarm，确认生效 |

## 关键坑位（必读）

### PITFALL 1: watch daemon 缓存配置（本次最大坑）
`watch` 进程常驻内存，`DEFAULT_COMMAND` 改动后它不会重载——它自动重启的每一轮
都用旧配置。表现为"改了配置但新日志里还是旧模型"。**改任何配置必须连 watch 一起
kill 再重启。**

### PITFALL 2: shell 环境变量优先于 .env
settings.py 读 key 的顺序：`OpenAI_KEY` > `OPENAI_API_KEY`。shell 若导出旧的
`OpenAI_KEY`，.env 里的新值不生效（load_dotenv 不覆盖）。runner 已用
`_load_project_env_overrides()` 强制以项目 .env 为准。

### PITFALL 3: src 布局后不能直接跑 manager.py
包未 pip install 进 conda env，必须 `-m aiminer.manager` + PYTHONPATH=src。
runner 已内置注入。

### PITFALL 4: OpenRouter 免费层日限 1000 次
stealth 模型共享免费池，跑 swarm 一天必打满。X-RateLimit-Reset = 北京时间 08:00。
打满时所有请求 429 `free-models-per-day-stealth`，进程不崩但整轮空转。

### PITFALL 5: reasoning 模型的 JSON 围栏
gemini-3.7-flash-high 等 reasoning 模型偶尔把 JSON 包进 ```json 围栏。
IdeaAgent/FactorAgent 有 `_strip_markdown_json` + 重试兜底；
portfolio_agent 的 `with_structured_output` 偶尔会解析失败（有重试）。

### PITFALL 6: 日志里的假报错
时间戳含 "401"/"429"（如 wiki `_backlink_audit:401` DEBUG 行）会污染
`grep -c '401'` 统计。真实错误要 grep `\| ERROR` 且排除 DEBUG 行。

## 回测产出记录（2026-08-21）

### ox-alpha-free 第一轮（19:59-20:44）
- 因子 6 个入库，最佳 IC 0.0197 / 0.0144
- 2 次 FactorAgent 网络瞬断（Connection error），系统自愈

### gemini-3.7-flash-high 轮（21:00-22:54）
- 策略 70 个入库
- Sharpe Top: ts_asym_liquidity_momentum_filtered 年化9.5% / Sharpe 1.02 / MaxDD -8.6%
- 年化 Top: ts_weekly_raw_threshold_reversal 年化10.1% / Sharpe 0.58 / MaxDD -37.2%

### CPA 账户额度快照（22:34）
- andygreskodpg47@gmail.com: 总成功 428 / 失败 5，active
- weisshymmnos@gmail.com: 总成功 442 / 失败 0，active
- round-robin 均衡，无 cooldown/limit 触发

## 快速切换手册

```bash
# 1. 改 scripts/hermes_auto_runner.py DEFAULT_COMMAND 的三行:
#    --llm-model <model> 和 --llm-base-url <url>
# 2. 改项目 .env 的 OPENAI_API_KEY= 与 OpenAI_KEY=
# 3. 全量重启（watch 必须一起重启!）
pkill -f 'hermes_auto_runner.py watch'
python scripts/hermes_auto_runner.py stop --force
python scripts/hermes_auto_runner.py resume   # 或重启 watch 让它自动拉起
# 4. 验证: 最新日志第一行 Model: 应为新模型
ls -t logs/hermes_*.log | head -1 | xargs grep -am1 'Using LLM Provider'
```

可用端点速查：
- opencode-go: model=`ox-alpha-free`, url=`https://opencode.ai/zen/go/v1`, key=OPENCODE_GO_API_KEY(~/.hermes/.env)
- CPA: model=`gemini-3.7-flash-high`(及54个其他), url=`http://127.0.0.1:8317/v1`, key=`huahongrui`
