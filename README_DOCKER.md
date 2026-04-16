# AI Alpha Miner - Docker Usage Guide

This project supports containerized execution via Docker, ensuring a consistent environment for factor mining across different operating systems.

## Prerequisites
- Docker installed
- Docker Compose installed (optional but recommended)

## Quick Start (with Docker Compose)

1. **Setup Environment**:
   Ensure your `.env` file is present in the root directory with the necessary API keys (OpenAI, RiceQuant, etc.).

2. **Build and Start**:
   ```bash
   docker-compose up --build -d
   ```
   This will build the image (compiling the Rust Polars plugins) and start both the researcher app and the API.

3. **Run a Task**:
   To run a manual mining iteration:
   ```bash
   docker exec -it aiminer_app python main.py --iterations 3
   ```

4. **Access the API**:
   The API will be available at `http://localhost:8000`.

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
     --env-file .env \
     aiminer:latest python main.py --iterations 1
   ```

## Notes on Persistence
- All research data (`data/`), results (`results/`), and logs (`logs/`) are mounted as volumes. This ensures that your factor pool and Wiki pages are preserved even if the container is deleted.
- The Rust Polars plugins are built during the image construction stage for maximum performance.
