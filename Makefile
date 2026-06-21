.PHONY: help install dev test lint format build serve docs deploy clean bench repo-health repo-health-all smoke-api

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install CORTEX
	pip install -e .

dev: ## Install with dev dependencies
	pip install -e ".[dev]"

test: ## Run all tests
	@echo "🚀 Running all tests (with 60s timeout)..."
	.venv/bin/pytest tests/ -v

test-fast: ## Run fast tests (excludes slow embedding/rag tests)
	@echo "⚡ Running fast tests..."
	.venv/bin/pytest tests/ -v -m "not slow"

test-slow: ## Run only slow tests
	@echo "🐢 Running slow tests..."
	.venv/bin/pytest tests/test_graph_rag.py tests/test_mejoralo_rounds3_5.py -v
 --tb=short

lint: ## Run linter
	ruff check cortex/ tests/

repo-health: ## Check changed/untracked files for conflict markers and Python syntax errors
	python3 scripts/repo_health_changed.py

repo-health-all: ## Check all tracked and untracked files for conflict markers and Python syntax errors
	python3 scripts/repo_health_changed.py --all

smoke-api: ## Smoke-check API import, engine init, and CLI help
	python3 scripts/smoke_test_api.py

format: ## Auto-format code
	ruff format cortex/ tests/

build: ## Build distribution package
	uv build

serve: ## Start CORTEX API server (development)
	uvicorn cortex.api.core:app --reload --host 0.0.0.0 --port 8000

docs: ## Build documentation
	mkdocs build

docs-serve: ## Serve documentation locally
	mkdocs serve

deploy-docs: ## Deploy docs to GitHub Pages
	mkdocs gh-deploy --force

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info site/ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

bench: ## Run benchmarks
	.venv/bin/python tests/bench_search.py

bench-fast: ## Run quick benchmarks (import time + source size)
	.venv/bin/python benchmarks/bench_repo.py --quick

docker: ## Build Docker image
	docker build -t cortex:latest .

docker-run: ## Run CORTEX in Docker
	docker run -d --name cortex -p 8000:8000 -v cortex-data:/data cortex:latest

ship: ## Ship gate — blocks deploy if quality checks fail
	@echo "🚢 Running Ship Gate..."
	.venv/bin/python scripts/ship_gate.py

ship-fast: ## Ship gate (fast — skip slow tests)
	@echo "⚡ Running Ship Gate (fast mode)..."
	.venv/bin/python scripts/ship_gate.py --fast

typecheck: ## Run type checker
	.venv/bin/mypy cortex/ --ignore-missing-imports --no-error-summary 2>&1 | tail -20

mcp: ## Start MCP server
	python run_mcp_server.py

deploy: ## Validate and orchestrate deployment
	python -c "from schema.event_v1 import EventV1; from daemon.execution_bus import run; import skills.deploy; result = run(EventV1(event_type='command_received', source='cli', skill_id='deploy', payload={'command': 'validate'})); print(result.artifact)"
