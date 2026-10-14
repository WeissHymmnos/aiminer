# HermesAgent 自动化值守说明

`scripts/hermes_auto_runner.py` 用于配合定时调度器（如 HermesAgent 或系统 Cron）在夜间窗口自动运行 AI Alpha Miner Swarm 挖掘任务，并在窗口外保持人工发起的任务不受干扰。

## 默认调度窗口与行为

- **时区**：`Asia/Shanghai`（北京时间）
- **自动运行窗口**：每日 `00:00 <= now < 08:00`
- **窗口内行为**：若当前无活跃任务则自动拉起 Swarm；若任务在窗口内异常退出或提前结束，自动重启续跑；到达 `08:00` 后自动向由调度器拉起的任务发送终止信号。
- **人工介入行为**：通过 `resume` 手动拉起的任务可在任意时段运行，且不会在 `08:00` 被调度器自动关闭；在自动窗口内执行 `stop` 后，当天 `08:00` 前不再自动拉起，直至手动执行 `resume` 或进入次日窗口。

## 默认启动命令

未额外覆盖时，Runner 默认使用如下命令拉起长周期并行挖掘：

```bash
PYTHONPATH=src /home/wh/.conda/envs/aiminer/bin/python -m aiminer.manager \
  --iterations 300 \
  --mode ricequant \
  --data-backend local \
  --llm-provider mimo \
  --llm-model Mimo-v2.5pro \
  --embedding-provider glm \
  --market-start 2015-01-01 \
  --market-end 2020-12-01 \
  --roles "动量专家" "波动率专家" "统计套利专家" "基本面套利专家" \
          "反转专家" "流动性专家" "期限结构专家" \
  --parallel \
  --swarm-global-timeout-seconds 0 \
  --disable-early-stop
```

可通过环境变量调整执行行为：

- `AIMINER_HERMES_COMMAND`：完全覆盖默认启动命令字符串。
- `AIMINER_PYTHON`：仅替换默认命令所使用的 Python 解释器路径。
- `MIMO_BASE_URL`：MiMo 接口地址，默认值为 `https://token-plan-cn.xiaomimimo.com/v1`。

## 常用操作命令

### 守护与巡检

```bash
# 方式一（推荐）：常驻后台每 60 秒巡检一次
python scripts/hermes_auto_runner.py watch --interval-seconds 60

# 方式二：由外部 Cron / HermesAgent 每分钟触发一次单步检查
python scripts/hermes_auto_runner.py tick
```

### 手动控制

```bash
python scripts/hermes_auto_runner.py status   # 查看当前运行状态、PID 与检查点信息
python scripts/hermes_auto_runner.py stop     # 终止当前运行并在当日窗口内暂停自动拉起
python scripts/hermes_auto_runner.py resume   # 清除暂停标记并立即拉起任务
```

执行 `stop` 时，Runner 会先向 AIMiner 进程组发送 `SIGTERM`，若超时未退出则升级为 `SIGKILL`。

## 日志与断点续跑

- **运行日志**：自动窗口日志写入 `logs/hermes_auto_*.log`，手动触发日志写入 `logs/hermes_manual_*.log`。
- **调度器状态**：保存在 `results/hermes_runner/state.json`。
- **断点恢复**：Runner 通过固定 `--run-id` 结合 SQLite 中的 `agent_checkpoints` 表实现断点续跑。任务重启后会从各角色已持久化的最佳检查点继续迭代，中断时未落盘的单次 LLM 请求会在恢复后重新执行。
