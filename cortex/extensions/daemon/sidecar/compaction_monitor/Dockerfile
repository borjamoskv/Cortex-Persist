# syntax=docker/dockerfile:1

# ---- Builder Stage ----
FROM python:3.12-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc-dev && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies
COPY cortex/daemon/sidecar/compaction_monitor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy sidecar package source
COPY cortex/daemon/sidecar/compaction_monitor/ ./compaction_monitor/

# ---- Runtime Stage ----
FROM python:3.12-slim AS runtime
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/compaction_monitor ./compaction_monitor

# Set non‑root user for zero‑trust
RUN useradd -m sidecar && chown -R sidecar:sidecar /app
USER sidecar

# Entry point
CMD ["python", "-m", "compaction_monitor.runner"]
