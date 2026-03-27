# Stage 1: Builder
FROM python:3.12-slim-bookworm as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# System dependencies with BuildKit Cache for APT
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc libsqlite3-dev build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv for hyper-speed dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Prepare virtual environment
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Pre-install heavy dependencies with BuildKit Cache for UV
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install fastapi uvicorn httpx sqlite-vec sentence-transformers onnxruntime cryptography pydantic

COPY pyproject.toml README.md ./
COPY cortex/ ./cortex/

# Install the remaining dependencies and the package
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install ".[api]"

# Pre-download the embedding model
ENV HF_HOME=/app/models
RUN --mount=type=cache,target=/root/.cache/uv \
    python -c "from cortex.embeddings import LocalEmbedder; LocalEmbedder()"

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

LABEL maintainer="borjamoskv.com" \
      description="CORTEX — Sovereign Memory Engine for AI Agents" \
      org.opencontainers.image.source="https://github.com/borjamoskv/cortex" \
      version="0.3.1-b1"

WORKDIR /app

# Runtime deps + tini for signal handling
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-0 curl tini && \
    rm -rf /var/lib/apt/lists/*

# Run as non-root user
RUN useradd -m -u 1000 cortex && \
    mkdir -p /data && \
    chown -t cortex:cortex /data
USER cortex

# Copy content from builder
COPY --chown=cortex:cortex --from=builder /app/.venv /app/.venv
COPY --chown=cortex:cortex --from=builder /app/models /app/models

ENV PATH="/app/.venv/bin:$PATH" \
    CORTEX_DB="/data/cortex.db" \
    ANONYMIZED_TELEMETRY="False" \
    HF_HOME="/app/models" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

VOLUME /data

EXPOSE 8484

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD curl -fSs http://localhost:8484/health || exit 1

# Tini as init system to handle SIGTERM/SIGINT correctly for SQLite persistence
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "cortex.api:app", "--host", "0.0.0.0", "--port", "8484", "--workers", "1"]
