# Stage 1: Builder
FROM python:3.12-slim-bookworm as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System dependencies for building SQLite extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libsqlite3-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies into a virtual environment
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY cortex/ ./cortex/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[api,mcp]" && \
    pip install --no-cache-dir sentence-transformers onnxruntime

# Pre-create the Hugging Face cache path so the runtime-stage COPY remains valid
# even if the embedder initialization skips downloading model artifacts.
RUN mkdir -p /root/.cache/huggingface && \
    python -c "from cortex.embeddings import LocalEmbedder; LocalEmbedder()"

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

LABEL maintainer="borjamoskv.com"
LABEL description="CORTEX — Sovereign Memory Engine for AI Agents"
LABEL org.opencontainers.image.source="https://github.com/borjamoskv/Cortex-Persist"

WORKDIR /app

# Runtime deps only
RUN apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment and editable-install source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/cortex /app/cortex

# Run as non-root user
RUN useradd -m -u 1000 cortex && \
    mkdir -p /data /home/cortex/.cache && \
    chown -R cortex:cortex /app /data /home/cortex/.cache
COPY --from=builder --chown=cortex:cortex /root/.cache/huggingface /home/cortex/.cache/huggingface
USER cortex

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    CORTEX_DB=/data/cortex.db \
    HF_HOME=/home/cortex/.cache/huggingface \
    ANONYMIZED_TELEMETRY=False

VOLUME /data

EXPOSE 8484

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD curl -f http://localhost:8484/health || exit 1

CMD ["uvicorn", "cortex.api:app", "--host", "0.0.0.0", "--port", "8484", "--workers", "1"]
