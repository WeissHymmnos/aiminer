# 安全策略 (Security Policy)

## 漏洞上报

如果你在 AI Alpha Miner 中发现安全漏洞，**请勿直接提交公开的 GitHub Issue**。

请通过仓库维护者邮箱或 GitHub 私有安全通告（Private Security Advisory）私下提交报告，并尽量附带以下信息：

- 漏洞描述、触发条件及潜在影响范围
- 复现步骤或最小概念验证代码（PoC）
- 受影响的分支、版本或 Commit Hash

维护团队通常会在 7 个自然日内确认收到报告并同步处理进展。

## 密钥与凭证管理

切勿将真实的模型 API Key、RiceQuant 账号或 Token、以及 `.env` 文件提交至代码仓库：

- 本地开发请复制 `.env.example` 为 `.env` 并在本地填写密钥。
- 一旦怀疑密钥曾被意外提交到 Git 历史中，应立即在对应服务商后台吊销并轮换密钥。
- 在多人共享或对内网暴露的环境中运行 Web 工作台与 HTTP API 时，请务必设置 `AIMINER_AUTH_TOKEN` 启用 Bearer / API Key 鉴权，并限制 `AIMINER_CORS_ORIGINS` 白名单。

## 代码与表达式执行边界

系统的核心安全边界位于大模型生成的因子表达式求值链路：

- 所有因子表达式在进入回测引擎前，必须通过 `FactorAgent` 的算子与字段白名单校验，并经由 `SafeEvalTransformer`（定义于 `src/aiminer/core/alphaeval/rq_eval.py`）对 AST 语法树进行净化，禁止任意属性访问、模块导入或系统调用。
- 本地 Codex CLI 调用（`src/aiminer/core/codex_llm.py`）运行于受限的只读临时会话中，并受单次执行超时约束。
- 任何放宽 AST 校验规则、扩充可执行算子白名单或修改子进程启动参数的改动均属于安全敏感变更，合并前必须经过严格代码审查与回归测试。

## 许可协议约束

本项目采用 **AGPL-3.0-only** 协议授权。所有安全补丁与衍生修改均须保持相同许可协议发布。
