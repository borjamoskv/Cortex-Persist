FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for psutil
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create structure to allow importing as cortex.extensions.ouroboros
RUN mkdir -p /app/cortex/extensions/ouroboros
COPY . /app/cortex/extensions/ouroboros/

ENV PYTHONPATH=/app
CMD ["uvicorn", "cortex.extensions.ouroboros.ouroboros_agent:app", "--host", "0.0.0.0", "--port", "8080"]
