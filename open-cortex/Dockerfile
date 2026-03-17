FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

# Seed test data on first run
RUN python -m open_cortex.seed data/open_cortex.db || true

EXPOSE 8000

CMD ["uvicorn", "open_cortex.app:app", "--host", "0.0.0.0", "--port", "8000"]
