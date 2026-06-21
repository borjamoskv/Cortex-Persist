#!/bin/bash
echo "Installing dependencies..."
pip install fastapi uvicorn pydantic > /dev/null

echo "Starting CORTEX-PERSIST Causal Demo Backend..."
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
