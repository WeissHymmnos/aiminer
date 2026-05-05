# AI Alpha Miner - Docker Usage Guide

This project supports containerized execution via Docker, ensuring a consistent environment for factor mining across different operating systems.

## Prerequisites
- Docker installed
- Docker Compose installed (optional but recommended)

## Quick Start (with Docker Compose)

1. **Setup Environment**:
   Export the required API keys in your shell or copy `.env.example` into your own environment manager. Compose no longer bind-mounts a root `.env` file, so a stray `.env` directory will not break container startup.

2. **Build and Start**:
   ```bash
   docker-compose up --build -d
   ```
   This will build the image (compiling the Rust Polars plugins) and start the API.

3. **Run a Task**:
   To run a manual mining iteration:
   ```bash
   docker compose --profile research run --rm worker
   ```

4. **Access the API**:
   The API will be available at `http://localhost:8000`.

## Standalone Frontend Container

If you want the React frontend as a separate container instead of letting FastAPI serve the built assets:

```bash
docker build -t aiminer-web:latest -f frontend/Dockerfile frontend
docker run --rm -p 8080:80 \
  -e AIMINER_API_UPSTREAM=http://host.docker.internal:8000 \
  aiminer-web:latest
```

Notes:
- The Nginx image now proxies both `/api` and `/ws` to `AIMINER_API_UPSTREAM`.
- The default upstream is `http://api:8000`, which matches a Docker network where the backend service is named `api`.
- If you need the frontend bundle to call a fixed remote backend directly, build with `--build-arg VITE_API_BASE_URL=...` and optionally `--build-arg VITE_WS_BASE_URL=...`.

## Building and Running Manually (without Compose)

1. **Build the image**:
   ```bash
   docker build -t aiminer:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -it --rm \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/results:/app/results \
     -v $(pwd)/logs:/app/logs \
     -e KIMI_API_KEY \
     -e RQ_TOKEN \
     aiminer:latest python main.py --iterations 1
   ```

## Notes on Persistence
- All research data (`data/`), results (`results/`), and logs (`logs/`) are mounted as volumes. This ensures that your factor pool and Wiki pages are preserved even if the container is deleted.
- The Rust Polars plugins are built during the image construction stage for maximum performance.
