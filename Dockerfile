# --- Stage 1: Frontend Build ---
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python Build Stage ---
FROM python:3.11-slim-bullseye AS builder

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (required for polars_plugins)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build

# Install Python build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel maturin

# Copy locked requirements and install dependencies to a temporary location
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock.txt

# Copy and build the Polars Rust plugin
COPY polars_plugins/ ./polars_plugins/
WORKDIR /build/polars_plugins
# Build and install the plugin into the same prefix
RUN maturin build --release --strip && \
    pip install --no-cache-dir --prefix=/install target/wheels/*.whl

# --- Stage 3: Runtime Stage ---
FROM python:3.11-slim-bullseye

WORKDIR /app

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

# Install runtime-only system dependencies if any (e.g., libssl)
RUN apt-get update && apt-get install -y \
    libssl1.1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the application source code
COPY . .
COPY --from=frontend-builder /frontend/dist ./frontend_dist

# Create necessary directories for mounting
RUN mkdir -p data/chroma_db data/wiki_db results logs

# Expose port if running the API
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app/src

# Default command (can be overridden in docker-compose or docker run)
CMD ["python", "-m", "aiminer.main"]
