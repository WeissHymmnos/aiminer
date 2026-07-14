#!/usr/bin/env bash
# AIMiner Web 模式一键启动: 后端(api.py) + 前端(vite dev) + 浏览器
# 用法:  ./start_web.sh                   # 默认开发模式
#        ./start_web.sh --prod            # 生产模式: 用打包后的 dist, 只起后端
#        BACKEND_PORT=9000 ./start_web.sh # 改后端端口

set -euo pipefail

# ===== 可调参数 =====
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
CONDA_ENV="${CONDA_ENV:-aiminer}"
MODE="dev"
[[ "${1:-}" == "--prod" ]] && MODE="prod"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AIMINER_DATA_DIR="${AIMINER_DATA_DIR:-${REPO_ROOT}/data}"
export AIMINER_RESULTS_DIR="${AIMINER_RESULTS_DIR:-${REPO_ROOT}/results}"
export AIMINER_LOG_DIR="${AIMINER_LOG_DIR:-${REPO_ROOT}/logs}"

LOG_DIR="${AIMINER_LOG_DIR}"
mkdir -p "${LOG_DIR}" "${AIMINER_RESULTS_DIR}"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
PIDS=()
SHUTDOWN_GRACE_SECONDS="${SHUTDOWN_GRACE_SECONDS:-10}"

# ===== 颜色输出 =====
C_RESET='\033[0m'; C_GREEN='\033[32m'; C_YELLOW='\033[33m'; C_RED='\033[31m'; C_CYAN='\033[36m'
log()  { printf "${C_CYAN}[start_web]${C_RESET} %s\n" "$*"; }
ok()   { printf "${C_GREEN}[ok]${C_RESET}        %s\n" "$*"; }
warn() { printf "${C_YELLOW}[warn]${C_RESET}      %s\n" "$*"; }
err()  { printf "${C_RED}[err]${C_RESET}       %s\n" "$*" >&2; }

# ===== 退出时清理 =====
cleanup() {
  log "收到退出信号, 关闭子进程..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  # 给 uvicorn/FastAPI shutdown hook 足够时间清理活跃 Swarm 子进程.
  for ((i=0; i<SHUTDOWN_GRACE_SECONDS; i++)); do
    local any_alive=0
    for pid in "${PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        any_alive=1
        break
      fi
    done
    [[ "$any_alive" == "0" ]] && break
    sleep 1
  done
  for pid in "${PIDS[@]}"; do
    kill -9 "$pid" 2>/dev/null || true
  done
  ok "已退出"
}
trap cleanup EXIT INT TERM

# ===== 自动找空闲端口 =====
port_in_use() {
  (echo > "/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

pick_free_port() {
  local start=$1 name=$2 p
  for ((p=start; p<start+50; p++)); do
    if ! port_in_use "$p"; then
      echo "$p"
      return 0
    fi
  done
  err "${name}: 从 ${start} 起连续 50 个端口都被占用, 放弃"
  exit 1
}

if port_in_use "$BACKEND_PORT"; then
  NEW=$(pick_free_port "$BACKEND_PORT" backend)
  warn "后端 ${BACKEND_PORT} 已占用 → 自动改用 ${NEW}"
  BACKEND_PORT=$NEW
fi
if [[ "$MODE" == "dev" ]] && port_in_use "$FRONTEND_PORT"; then
  NEW=$(pick_free_port "$FRONTEND_PORT" frontend)
  warn "前端 ${FRONTEND_PORT} 已占用 → 自动改用 ${NEW}"
  FRONTEND_PORT=$NEW
fi

# ===== 启动后端 =====
log "启动后端 (port ${BACKEND_PORT})..."
cd "$REPO_ROOT"

# 优先用 conda 环境的 python; 否则降级到当前环境
PY_CMD="python"
if command -v conda >/dev/null 2>&1 && conda env list | grep -qE "^${CONDA_ENV}\s"; then
  PY_CMD="conda run --live-stream -n ${CONDA_ENV} python"
  ok "使用 conda 环境: ${CONDA_ENV}"
else
  warn "未找到 conda 环境 ${CONDA_ENV}, 使用当前 PATH 中的 python"
fi

# 同步 CORS 白名单, 让换端口后的前端不被拦
export AIMINER_CORS_ORIGINS="${AIMINER_CORS_ORIGINS:-http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT},http://localhost:${BACKEND_PORT},http://127.0.0.1:${BACKEND_PORT}}"

PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}" ${PY_CMD} -m uvicorn aiminer.api:app --host 0.0.0.0 --port "${BACKEND_PORT}" \
  >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
PIDS+=("$BACKEND_PID")
log "后端 PID=${BACKEND_PID}, 日志: ${BACKEND_LOG}"

# ===== 等后端就绪 =====
log "等待后端就绪..."
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/swarm/status" >/dev/null 2>&1 \
     || curl -fsS "http://127.0.0.1:${BACKEND_PORT}/" >/dev/null 2>&1; then
    ok "后端就绪 (用时 ${i}s)"
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    err "后端进程已退出, 看日志:"
    tail -30 "${BACKEND_LOG}" >&2
    exit 1
  fi
  sleep 1
  if [[ $i == 30 ]]; then
    err "后端 30s 内没起来, 看日志:"
    tail -30 "${BACKEND_LOG}" >&2
    exit 1
  fi
done

# ===== 启动前端 (仅 dev 模式) =====
if [[ "$MODE" == "dev" ]]; then
  log "启动前端 dev server (port ${FRONTEND_PORT})..."
  cd "${REPO_ROOT}/frontend"
  if [[ ! -d node_modules ]]; then
    log "首次运行, 安装前端依赖..."
    npm install >"${FRONTEND_LOG}" 2>&1
  fi
  # 把 vite 代理目标指到实际后端端口
  export VITE_API_PROXY="http://127.0.0.1:${BACKEND_PORT}"
  npm run dev -- --port "${FRONTEND_PORT}" --strictPort \
    >"${FRONTEND_LOG}" 2>&1 &
  FRONTEND_PID=$!
  PIDS+=("$FRONTEND_PID")
  log "前端 PID=${FRONTEND_PID}, 日志: ${FRONTEND_LOG}"

  # 等前端就绪
  log "等待前端就绪..."
  for i in {1..30}; do
    if curl -fsS "http://127.0.0.1:${FRONTEND_PORT}" >/dev/null 2>&1; then
      ok "前端就绪 (用时 ${i}s)"
      break
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
      err "前端进程已退出, 看日志:"
      tail -30 "${FRONTEND_LOG}" >&2
      exit 1
    fi
    sleep 1
  done
  URL="http://localhost:${FRONTEND_PORT}"
else
  # 生产模式: 直接访问后端 (后端会从 frontend/dist 提供静态文件)
  if [[ ! -f "${REPO_ROOT}/frontend/dist/index.html" ]]; then
    warn "frontend/dist 不存在, 先打包: cd frontend && npm run build"
  fi
  URL="http://localhost:${BACKEND_PORT}"
fi

# ===== 打开浏览器 =====
log "打开浏览器: ${URL}"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v start >/dev/null 2>&1; then
  start "$URL"
else
  warn "未找到浏览器启动命令, 请手动打开: $URL"
fi

# ===== 持续运行 =====
ok "全部启动完成. Ctrl+C 退出."
log "后端日志: tail -f ${BACKEND_LOG}"
[[ "$MODE" == "dev" ]] && log "前端日志: tail -f ${FRONTEND_LOG}"

# 等任一子进程退出就一并清理
wait -n "${PIDS[@]}" 2>/dev/null || true
