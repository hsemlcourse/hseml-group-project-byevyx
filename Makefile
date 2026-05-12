.PHONY: help install install-dev lint format test precommit docker-build docker-up docker-down docker-logs api-train api-up clean

help:
	@echo "install       - install runtime dependencies"
	@echo "install-dev   - install dev dependencies and pre-commit hooks"
	@echo "lint          - run ruff lint on src/ and tests/"
	@echo "format        - auto-format with ruff"
	@echo "test          - run pytest"
	@echo "precommit     - run all pre-commit hooks on all files"
	@echo "docker-build  - build docker image"
	@echo "docker-up     - start JupyterLab container on :8888"
	@echo "docker-down   - stop containers"
	@echo "docker-logs   - tail container logs"
	@echo "api-train     - train models and persist artifacts to models/"
	@echo "api-up        - run FastAPI server on :8000 (with --reload)"
	@echo "clean         - remove caches"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

test:
	pytest

precommit:
	pre-commit run --all-files

docker-build:
	docker compose build

docker-up:
	docker compose up -d
	@echo "JupyterLab -> http://localhost:8888"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f jupyter

api-train:
	python -m scripts.train_and_save --ticker ^GSPC --start 2010-01-01 --end 2024-12-31

api-up:
	uvicorn src.api.main:app --reload --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
