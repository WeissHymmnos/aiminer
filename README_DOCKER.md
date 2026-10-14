# Docker 部署指南

本项目支持通过 Docker 与 Docker Compose 进行容器化部署。根镜像采用多阶段构建：第一阶段使用 Node 20 编译 React 前端静态产物，第二阶段在 Python 3.11 环境中安装依赖并通过 Rust 工具链与 `maturin` 编译 `polars_plugins` 原生算子插件，最终阶段封装为轻量运行镜像。

## 前置条件

- Docker 24.0+
- Docker Compose v2+

## 使用 Docker Compose 启动（推荐）

### 1. 配置环境变量

在宿主机的 Shell 环境中导出所需的模型密钥与 RiceQuant 凭证，或在当前目录准备 `.env` 文件供 Compose 变量插值读取（`docker-compose.yml` 仅通过环境变量向容器注入配置，不再将根目录 `.env` 作为文件直接挂载，避免宿主机误生成同名空目录导致容器启动失败）：

```bash
export ZHIPU_API_KEY="your-zhipu-key"
export RQ_TOKEN="your-rq-token"
```

### 2. 构建并启动 API 与 Web 服务

默认服务仅包含常驻的 `api` 容器（同时托管 `/app/frontend_dist` 静态前端与 `/api/*`、`/ws` 接口）：

```bash
docker compose up -d --build
```

启动完成后访问 `http://localhost:8000` 即可打开 Web 工作台，健康检查接口位于 `http://localhost:8000/api/health`。

### 3. 运行研究任务与终端工作台

为防止有限轮次的挖掘任务在容器重启策略下重复运行，`worker` 与 `tui` 服务分别放置在独立的 Compose Profile 中，按需拉起并在退出后自动销毁容器：

```bash
# 运行一次 5 轮迭代的 Swarm 因子挖掘
AIMINER_ITERATIONS=5 docker compose --profile research run --rm worker

# 启动交互式 TUI 终端工作台
docker compose --profile tui run --rm tui
```

若需自定义 Swarm 参数，可在 `run` 命令末尾直接覆盖入口命令：

```bash
docker compose --profile research run --rm worker \
  python -m aiminer.manager --iterations 3 --mode ricequant --engine polars --parallel
```

---

## 独立部署前端容器（可选）

默认架构下 FastAPI 会直接托管前端页面。若生产环境需要前后端分离部署，可使用 `frontend/Dockerfile` 构建基于 Nginx 的独立前端镜像：

```bash
docker build -t aiminer-web:latest -f frontend/Dockerfile frontend

docker run --rm -p 8080:80 \
  -e AIMINER_API_UPSTREAM=http://host.docker.internal:8000 \
  aiminer-web:latest
```

说明：

- Nginx 容器会将 `/api` 与 `/ws`（WebSocket）反向代理至 `AIMINER_API_UPSTREAM`，默认值为 `http://api:8000`（对应同一 Docker 网络下的 `api` 服务名）。
- 若需在前端静态构建阶段写入固定远端地址，可在构建时传入 `--build-arg VITE_API_BASE_URL=...` 与 `--build-arg VITE_WS_BASE_URL=...`。

---

## 手动构建与运行（不使用 Compose）

1. 构建镜像：

```bash
docker build -t aiminer:latest .
```

2. 挂载持久化目录并运行单次任务：

```bash
docker run -it --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/results:/app/results" \
  -v "$(pwd)/logs:/app/logs" \
  -e KIMI_API_KEY \
  -e RQ_TOKEN \
  aiminer:latest python -m aiminer.main --iterations 1
```

---

## 数据持久化说明

容器内的 `/app/data`、`/app/results` 与 `/app/logs` 均映射至宿主机同名目录：

- `data/`：保存 ChromaDB 向量索引（`data/chroma_db/`、`data/wiki_db/`）、Markdown 知识库（`data/wiki_vault/`）以及本地期货/股票数据集。
- `results/`：保存 SQLite 主库（`results/alpha_miner.db`）、Swarm 运行清单与事件流（`results/swarm_runs/`）、净值图表与评估报告。
- `logs/`：保存服务端与任务运行日志。

销毁或重建容器不会影响已沉淀的因子池、策略回测记录与 Wiki 页面。
