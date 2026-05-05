# HermesAgent Automation

This project can be driven by `scripts/hermes_auto_runner.py`. The runner keeps
one AIMiner swarm alive during the Beijing-time auto window and leaves manual
runs alone outside that window.

## Default Schedule

- Time zone: `Asia/Shanghai`
- Auto window: every day `00:00 <= now < 08:00`
- Auto behavior: start if no run is active; restart if the run exits inside the
  window; stop auto-started runs after `08:00`
- Manual behavior: `resume` starts immediately outside the window and is not
  stopped by the scheduler

## Default Command

```bash
/home/wh/.conda/envs/aiminer/bin/python manager.py --iterations 300 --mode ricequant --data-backend local \
  --llm-provider mimo --llm-model Mimo-v2.5pro \
  --embedding-provider glm \
  --market-start 2015-01-01 --market-end 2020-12-01 \
  --roles "动量专家" "波动率专家" "统计套利专家" "基本面套利专家" \
          "反转专家" "流动性专家" "期限结构专家" \
  --parallel --swarm-global-timeout-seconds 0 --disable-early-stop
```

Set `AIMINER_HERMES_COMMAND` to override the full command.
Set `AIMINER_PYTHON` to override only the Python interpreter used by the default
command.
MiMo defaults to `MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1`.

## HermesAgent Commands

Use one of these patterns:

```bash
# Preferred: keep this running under HermesAgent supervision.
python scripts/hermes_auto_runner.py watch --interval-seconds 60

# Alternative: let HermesAgent call this once per minute.
python scripts/hermes_auto_runner.py tick
```

Manual controls:

```bash
python scripts/hermes_auto_runner.py status
python scripts/hermes_auto_runner.py stop
python scripts/hermes_auto_runner.py resume
```

`stop` sends SIGTERM to the AIMiner process group, then escalates to SIGKILL if
it does not exit. If called inside the auto window, it pauses auto restart until
08:00. `resume` clears that pause and starts immediately.

Logs are written to `logs/hermes_auto_*.log` or `logs/hermes_manual_*.log`.
Runner state is stored in `results/hermes_runner/state.json`.

Checkpoint resume uses the runner's stable `--run-id` plus AIMiner's
`agent_checkpoints` table. A stopped run resumes from the last persisted best
agent checkpoint; any in-flight LLM call that had not reached a checkpoint is
repeated.
