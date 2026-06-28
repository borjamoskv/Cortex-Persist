#!/usr/bin/env bash
set -e

# CORTEX-Persist One-Click Deployment Script
# This script sets up a local environment and starts the CORTEX memory server.
# Perfect for first-time onboarding.

echo "==========================================="
echo "🧠 CORTEX-Persist One-Click Local Deploy"
echo "==========================================="
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3.10+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# 2. Setup Virtual Environment
VENV_DIR=".venv-cortex-quickstart"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# 3. Install CORTEX
echo "⬇️  Installing CORTEX-Persist..."
pip install --quiet --upgrade pip
# Assuming we are in the repo root. If not, fallback to PyPI.
if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
    pip install -e ".[all]"
else
    pip install cortex-persist
fi
echo "✅ Installation complete."

# 4. Initialize Database & Keys
export CORTEX_DB_PATH="./cortex_quickstart.db"
export CORTEX_LOG_LEVEL="INFO"

echo ""
echo "🚀 Starting CORTEX Server on http://localhost:8000"
echo "Press Ctrl+C to stop the server."
echo ""
echo "-------------------------------------------"
echo "💡 API Docs available at: http://localhost:8000/docs"
echo "-------------------------------------------"

# Start the server
uvicorn cortex.api:app --host 0.0.0.0 --port 8000 --reload
