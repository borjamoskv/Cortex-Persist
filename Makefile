.PHONY: install lint format typecheck test check

install:
	pip install -r requirements-dev.txt

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy .

test:
	pytest -q

check:
	ruff check .
	ruff format --check .
	mypy .
	pytest -q
